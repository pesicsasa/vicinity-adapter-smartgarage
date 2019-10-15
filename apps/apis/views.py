import uuid
import json
import requests
import rest_framework.status as status
from rest_framework.response import Response
from rest_framework.views import APIView

import logging
logger = logging.getLogger(__name__)
from datetime import datetime
from .thing_descriptors import *
from .utils import *
from .forms import GarageForm
from .models import ParkingReservation
from django.views import View
from django.shortcuts import render
from django_eventstream import send_event


class ObjectsView(APIView):
    service_object_descriptor = {
        'adapter-id': ADAPTER_ID,
        'thing-descriptions': [
            {
                'oid': SMART_GARAGE_OID,
                'name': 'VLF Smart Access Control service',
                'type': 'core:Service',
                'version': '0.1',
                'keywords': ['parking', 'key', 'voucher'],
                'properties': [RESERVE_PARKING],
                'events': [RESERVE_PARKING_EVENT],
                'actions': []
            }
        ]
    }

    def get(self, request):
        return Response(self.service_object_descriptor, status=status.HTTP_200_OK)


class ParkingReservationView(APIView):

    def put(self, request, pid):
        input_data = request.data
        if pid not in PID:
            data = {
                'error': True,
                'message': 'Invalid PID',
                'status': status.HTTP_404_NOT_FOUND
            }
            return Response(data, status=status.HTTP_404_NOT_FOUND)

        if not input_data:
            data = {
                'error': True,
                'message': 'Missing input parameters',
                'status': status.HTTP_400_BAD_REQUEST
            }
            return Response(data, status=status.HTTP_400_BAD_REQUEST)

        if pid == 'reserve_parking':
            try:
                name = input_data['name']
                email = input_data['email']
                valid_from = datetime.strptime(input_data['valid_from'], "%m/%d/%Y  %H:%M:%S")
                valid_until = datetime.strptime(input_data['valid_until'], "%m/%d/%Y  %H:%M:%S")
            except Exception as e:
                logger.error(e)
                data = {
                    'error': True,
                    'message': 'Invalid input parameters',
                    'status': status.HTTP_400_BAD_REQUEST
                }
                return Response(data, status=status.HTTP_400_BAD_REQUEST)

            output = dict()

            # call API for getting ticker info
            url = 'http://localhost:9997/agent/remote/objects/{oid}/properties/ticker'.format(
                oid=BARTER_DASH_SERVICE_OID)
            headers = {'infrastructure-id': SMART_GARAGE_OID,
                       'adapter-id': ADAPTER_ID}
            body = {
                "wallet_name": DASH_WALLET_NAME
            }

            try:
                r = requests.put(url, headers=headers, data=json.dumps(body))
                result = r.json()
                logger.info("Ticker: {}".format(result))
                if result['error']:
                    data = {
                        'error': True,
                        'message': 'Cannot get ticker info',
                        'status': status.HTTP_400_BAD_REQUEST
                    }
                    return Response(data, status=status.HTTP_400_BAD_REQUEST)
                output["payment_amount"] = round(10 / result['message'][0]['vwap'], 8)
            except Exception as e:
                logger.error(e)
                data = {
                    'error': True,
                    'message': 'Cannot get ticker info',
                    'status': status.HTTP_400_BAD_REQUEST
                }
                return Response(data, status=status.HTTP_400_BAD_REQUEST)

            # call API for getting payment address
            url = 'http://localhost:9997/agent/remote/objects/{oid}/properties/payment_address'.format(
                oid=BARTER_DASH_SERVICE_OID)
            headers = {'infrastructure-id': SMART_GARAGE_OID,
                       'adapter-id': ADAPTER_ID}
            body = {
                "wallet_name": DASH_WALLET_NAME,
                "wallet_secret": DASH_WALLET_SECRET
            }
            try:
                r = requests.put(url, headers=headers, data=json.dumps(body))
                result = r.json()
                logger.info("Payment forward: {}".format(result))
                if result['error']:
                    data = {
                        'error': True,
                        'message': 'Cannot get payment address',
                        'status': status.HTTP_400_BAD_REQUEST
                    }
                    return Response(data, status=status.HTTP_400_BAD_REQUEST)
                # set payment id and payment address for transaction
                output["payment_address"] = result['message'][0]['payment_address']
                output["payment_id"] = result['message'][0]['paymentforward_id']
            except Exception as e:
                logger.error(e)
                data = {
                    'error': True,
                    'message': 'Cannot get payment address',
                    'status': status.HTTP_400_BAD_REQUEST
                }
                return Response(data, status=status.HTTP_400_BAD_REQUEST)

            # Store info about payment in the database and mark it as vicinity request
            # which payment id, which payment address, amount requested in dash...
            ParkingReservation.objects.create(
                name=name,
                email=email,
                valid_from=valid_from,
                valid_until=valid_until,
                payment_id=output["payment_id"],
                payment_address=output["payment_address"],
                amount=output['payment_amount'],
                request_origin='vicinity',
                payment_status='pending'
            )
            # Subscribe to BARTER payment events
            url = 'http://localhost:9997/agent/objects/{oid}/events/{eid}'.format(
                oid=BARTER_DASH_SERVICE_OID, eid=DASH_EID)
            headers = {'infrastructure-id': SMART_GARAGE_OID,
                       'adapter-id': ADAPTER_ID}
            r = requests.post(url, headers=headers)
            logger.info("Subscription: {}".format(r.json()))

        # finally provide response
        logger.info(output)
        return Response(output, status=status.HTTP_200_OK)


class EventHandler(APIView):

    def put(self, request, iid, oid, eid):
        # Get info about payed reservation from Barter
        barter_notification = request.data
        # Get data from database based on payed info
        # check if payment forward id address and amount match
        reservation = ParkingReservation.objects.filter(
            payment_id=barter_notification['paymentforward_id'],
            payment_address=barter_notification['payment_address']).first()

        if not reservation:
            return Response({}, status=status.HTTP_200_OK)

        if barter_notification['received_amount_duffs'] >= reservation.amount*100000000:
            reservation.payment_status = 'completed'
            reservation.save()
            # If found, create a voucher/key
            try:
                url = 'https://smartaccessbuildingone.appspot.com/user/login'
                headers = {'Content-Type': "application/x-www-form-urlencoded"}
                data = {
                    "email": SAC_USER,
                    "pwd": SAC_PWD
                }
                session = requests.Session()
                session.post(url, data=data, headers=headers)

                data = {
                    "guest": reservation.name,
                    "guest_email": reservation.email,
                    "valid_from": datetime.strftime(reservation.valid_from, "%m/%d/%Y  %H:%M:%S"),
                    "valid_until": datetime.strftime(reservation.valid_until, "%m/%d/%Y  %H:%M:%S"),
                    "authorized_groups": ["__General__"]
                }
                url = 'https://smartaccessbuildingone.appspot.com/sa/timestamped_active_access_codes'
                r = session.post(url, json=data)
                logger.info(r.json())
                if r.status_code != 200:
                    # Publish that there was an issue with voucher creation
                    return Response({}, status=status.HTTP_200_OK)

                reservation.voucher_generated = True
                reservation.save()
            except Exception as e:
                logger.error(e)

            if reservation.voucher_generated:
                # Publish to frontend app if it's event from front
                if reservation.request_origin == 'local':
                    logger.info("PAYED FROM FRONTEND")
                    send_event('payment_notification', 'message', {
                        'status': 'reserved',
                        "received_amount": round(barter_notification['received_amount_duffs'] / 100000000, 8)
                    })
                elif reservation.request_origin == 'vicinity':
                    # Publish to reservation event if it's from VICINITY TODO CHECK FORMAT!
                    data = {
                        "payment_id": barter_notification['paymentforward_id'],
                        "payment_address": barter_notification["payment_address"],
                        "status": "reserved",
                        "payment_amount": round(barter_notification['received_amount_duffs'] / 100000000, 8)
                    }
                    url = 'http://localhost:9997/agent/events/{}'.format(SMART_GARAGE_EID)
                    headers = {'infrastructure-id': SMART_GARAGE_OID, 'adapter-id': ADAPTER_ID}
                    r = requests.put(url, data=json.dumps(data), headers=headers)
        return Response({}, status=status.HTTP_200_OK)


class LandingPage(View):
    def get(self, request):
        form = GarageForm()
        return render(request, 'apis/home.html', {"form": form})

    def post(self, request):
        input_data = request.POST
        try:
            name = input_data['name']
            email = input_data['email']
            valid_from = datetime.strptime(input_data['valid_from'], "%Y/%m/%d  %H:%M")
            valid_until = datetime.strptime(input_data['valid_until'], "%Y/%m/%d  %H:%M")
        except Exception as e:
            logger.error(e)
            data = {
                'error': True,
                'message': 'Invalid input parameters',
                'status': status.HTTP_400_BAD_REQUEST
            }
            return render(request, 'apis/home.html', {'data': data})

        output = dict()

        # call API for getting ticker info
        url = 'http://localhost:9997/agent/remote/objects/{oid}/properties/ticker'.format(
            oid=BARTER_DASH_SERVICE_OID)
        headers = {'infrastructure-id': SMART_GARAGE_OID,
                   'adapter-id': ADAPTER_ID}
        body = {
            "wallet_name": DASH_WALLET_NAME
        }
        try:
            r = requests.put(url, headers=headers, data=json.dumps(body))
            result = r.json()
            logger.info("Ticker: {}".format(result))
            if result['error']:
                data = {
                    'error': True,
                    'message': 'Cannot get ticker info',
                    'status': status.HTTP_400_BAD_REQUEST
                }
                return render(request, 'apis/home.html', {'data': data})
            output["payment_amount"] = round(10 / result['message'][0]['vwap'], 8)
        except Exception as e:
            logger.error(e)
            data = {
                'error': True,
                'message': 'Cannot get ticker info',
                'status': status.HTTP_400_BAD_REQUEST
            }
            return render(request, 'apis/home.html', {'data': data})

        # call API for getting payment address
        url = 'http://localhost:9997/agent/remote/objects/{oid}/properties/payment_address'.format(
            oid=BARTER_DASH_SERVICE_OID)
        headers = {'infrastructure-id': SMART_GARAGE_OID,
                   'adapter-id': ADAPTER_ID}
        body = {
            "wallet_name": DASH_WALLET_NAME,
            "wallet_secret": DASH_WALLET_SECRET
        }
        try:
            r = requests.put(url, headers=headers, data=json.dumps(body))
            result = r.json()
            logger.info("Payment forward: {}".format(result))
            if result['error']:
                data = {
                    'error': True,
                    'message': 'Cannot get payment address',
                    'status': status.HTTP_400_BAD_REQUEST
                }
                return render(request, 'apis/home.html', {'data': data})
            # set payment id and payment address for transaction
            output["payment_address"] = result['message'][0]['payment_address']
            output["payment_id"] = result['message'][0]['paymentforward_id']
        except Exception as e:
            logger.error(e)
            data = {
                'error': True,
                'message': 'Cannot get payment address',
                'status': status.HTTP_400_BAD_REQUEST
            }
            return render(request, 'apis/home.html', {'data': data})

        ParkingReservation.objects.create(
            name=name,
            email=email,
            valid_from=valid_from,
            valid_until=valid_until,
            payment_id=output["payment_id"],
            payment_address=output["payment_address"],
            amount=output['payment_amount'],
            request_origin='local',
            payment_status='pending'
        )

        url = 'http://localhost:9997/agent/objects/{oid}/events/{eid}'.format(
            oid=BARTER_DASH_SERVICE_OID, eid=DASH_EID)
        headers = {'infrastructure-id': SMART_GARAGE_OID,
                   'adapter-id': ADAPTER_ID}
        r = requests.post(url, headers=headers)
        logger.info("Subscription: {}".format(r.json()))

        name = uuid.uuid4()
        image_path = generate_qr(
            payment_address=output["payment_address"],
            payment_amount=output['payment_amount'],
            name=name
        )
        context = {
            "payment_address": output["payment_address"],
            "name": image_path,
            "payment_amount": output['payment_amount'],
            "payment_id": output['payment_id']
        }
        return render(request, 'apis/home.html', {"output": context})


class AccessLogs(APIView):
    def post(self, request):
        data = request.data
        # check secret
        if data.get("secret") == "adhhcb&@BBBW42790003BVR":
            # delete secret
            del data["secret"]
            logger.info("Access logs\n{}".format(data))
            # insert into blockchain using BARTER
            # try update, if it fails create
            url = 'http://localhost:9997/agent/remote/objects/{oid}/properties/update_asset'.format(
                oid=BARTER_REPOSITORY_SERVICE_OID)
            headers = {'infrastructure-id': SMART_GARAGE_OID,
                       'adapter-id': ADAPTER_ID}
            body = {
                "repository_name": REPOSITORY_NAME,
                "repository_secret": REPOSITORY_SECRET,
                "asset_key": data['access_code'],
                "asset_new_value": json.dumps(json.dumps(data['data']))
            }
            try:
                r = requests.put(url, headers=headers, data=json.dumps(body))
                result = r.json()
                if result['error']:
                    url = 'http://localhost:9997/agent/remote/objects/{oid}/properties/create_asset'.format(
                        oid=BARTER_REPOSITORY_SERVICE_OID)
                    headers = {'infrastructure-id': SMART_GARAGE_OID,
                               'adapter-id': ADAPTER_ID}
                    body = {
                        "repository_name": REPOSITORY_NAME,
                        "repository_secret": REPOSITORY_SECRET,
                        "asset_key": data['access_code'],
                        "asset_value": json.dumps(json.dumps(data['data']))
                    }
                    try:
                        r = requests.put(url, headers=headers, data=json.dumps(body))
                        result = r.json()
                    except Exception as e:
                        logger.error(e)
            except Exception as e:
                logger.error(e)
                url = 'http://localhost:9997/agent/remote/objects/{oid}/properties/create_asset'.format(
                    oid=BARTER_REPOSITORY_SERVICE_OID)
                headers = {'infrastructure-id': SMART_GARAGE_OID,
                           'adapter-id': ADAPTER_ID}
                body = {
                    "repository_name": REPOSITORY_NAME,
                    "repository_secret": REPOSITORY_SECRET,
                    "asset_key": data['access_code'],
                    "asset_value": json.dumps(json.dumps(data['data']))
                }
                try:
                    r = requests.put(url, headers=headers, data=json.dumps(body))
                    result = r.json()
                except Exception as e:
                    logger.error(e)

            return Response({}, status=status.HTTP_200_OK)
        return Response({"error": "Secret mismatch!"}, status=status.HTTP_200_OK)


class TestPage(APIView):
    def get(self, request):
        send_event('payment_notification', 'message', {
            'status': 'reserved',
            "received_amount": 0.20365478
        })
        return Response({"message": "test"}, status=status.HTTP_201_CREATED)