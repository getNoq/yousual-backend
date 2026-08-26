class PaymentGateway:
    """
    The one contract every gateway implements — adding a third
    provider later means writing one more class here, not touching
    anything in views.py or services.py.
    """

    def initialize(self, *, email, amount, plan_code, callback_url, metadata):
        raise NotImplementedError

    def verify_transaction(self, reference):
        raise NotImplementedError

    def verify_webhook_signature(self, request) -> bool:
        raise NotImplementedError