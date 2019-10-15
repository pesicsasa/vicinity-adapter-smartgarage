import pyqrcode
from django.conf import settings
import string
import random
media = settings.STATICFILES_DIRS[0]


def random_string_digits(string_length=10):
    """Generate a random string of letters and digits """
    letters_and_digits = string.ascii_letters + string.digits
    return ''.join(random.choice(letters_and_digits) for i in range(string_length))


def generate_qr(payment_address, payment_amount, name):
    code = pyqrcode.create("dash:{}?amount={}".format(payment_address, payment_amount))
    code.png('{}/media/qr_codes/{}.png'.format(media, name), scale=5)
    # print(code.terminal())
    return "/media/qr_codes/{}.png".format(name)


if __name__ == '__main__':
    generate_qr()

ADAPTER_ID = 'smart-access-control'
SMART_GARAGE_OID = 'smart-garage'
RESERVATION_CHANNEL = 'reservations'
BARTER_DASH_SERVICE_OID = '93525262-c195-4968-b200-c8e9f5a43be9'
BARTER_BITCOIN_SERVICE_OID = 'f422b21c-37dd-433c-9f68-ae157168cc44'
BARTER_REPOSITORY_SERVICE_OID = '6798cd1b-30c5-475c-9c8b-0a5472a897fa'

DASH_WALLET_NAME = "BnKdeGeuM1JHc8jKc4VnB3xRniXiGBWd"
DASH_WALLET_SECRET = "secret123"
DASH_EID = "dash_payments"

BITCOIN_WALLET_NAME = "Kv6Gz9DcixP7UkD8CJShESRARZXwO3Gt"
BITCOIN_WALLET_SECRET = "secret123"
BITCOIN_EID = "bitcoin_payments"

REPOSITORY_NAME = "GRuNrsuzXljfIyDhG7lDeBbJqWPj7qAb"
REPOSITORY_SECRET = "secret123"

SAC_USER = "ognjen.ikovic@gmail.com"
SAC_PWD = "Adminadmin3"

