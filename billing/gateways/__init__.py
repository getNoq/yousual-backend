from .paystack import PaystackGateway
from .flutterwave import FlutterwaveGateway

GATEWAYS = {
    "paystack": PaystackGateway(),
    "flutterwave": FlutterwaveGateway(),
}


def get_gateway(name):
    gateway = GATEWAYS.get(name)
    if not gateway:
        raise ValueError(f"Unknown gateway: {name}")
    return gateway