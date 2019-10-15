PID = ['reserve_parking']


RESERVE_PARKING = {
    "pid": "reserve_parking",
    "monitors": "adapters:Start",
    "write_link": {
        "href": "/reservations/property/{pid}",
        "input": {
            "type": "object",
            "field": [
                {
                    "name": "name",
                    "schema": {
                        "type": "string"
                    }
                },
                {
                    "name": "email",
                    "schema": {
                        "type": "string"
                    }
                },
                {
                    "name": "valid_from",
                    "schema": {
                        "type": "string"
                    }
                },
                {
                    "name": "valid_until",
                    "schema": {
                        "type": "string"
                    }
                }
            ]
        },
        "output": {
            "type": "object",
            "field": [
                {
                    "name": "payment_address",
                    "schema": {
                        "type": "string"
                    }
                },
                {
                    "name": "payment_id",
                    "schema": {
                        "type": "string"
                    }
                },
                {
                    "name": "payment_amount",
                    "schema": {
                        "type": "double"
                    }
                }
            ]
        }
    }
}


SMART_GARAGE_EID = "reservations"

RESERVE_PARKING_EVENT = {
    "eid": SMART_GARAGE_EID,
    "monitors": "adapters:Start",
    "output": {
        "type": "object",
        "field": [
            {
                "name": "payment_id",
                "schema": {
                    "type": "string"
                }
            },
            {
                "name": "payment_address",
                "schema": {
                    "type": "string"
                }
            },
            {
                "name": "status",
                "schema": {
                    "type": "string"
                }
            },
            {
                "name": "payment_amount",
                "schema": {
                    "type": "double"
                }
            }
        ]}
}
