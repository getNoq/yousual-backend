import hashlib
import hmac

import requests
from django.conf import settings

from .base import PaymentGateway


class PaystackGateway(PaymentGateway):
    base_url = "https://api.paystack.co"

    def _headers(self):
        return {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}", "Content-Type": "application/json"}

    def initialize(self, *, email, amount, plan_code, callback_url, metadata):
        payload = {
            "email": email,
            "amount": int(amount * 100),  # Paystack expects kobo, not naira
            "plan": plan_code,
            "callback_url": callback_url,
            "metadata": metadata,
        }
        res = requests.post(f"{self.base_url}/transaction/initialize", json=payload, headers=self._headers(), timeout=15)
        res.raise_for_status()
        data = res.json()["data"]
        return {"authorization_url": data["authorization_url"], "reference": data["reference"]}

    def verify_transaction(self, reference):
        res = requests.get(f"{self.base_url}/transaction/verify/{reference}", headers=self._headers(), timeout=15)
        res.raise_for_status()
        return res.json()["data"]

    def verify_webhook_signature(self, request) -> bool:
        signature = request.headers.get("x-paystack-signature", "")
        computed = hmac.new(settings.PAYSTACK_SECRET_KEY.encode(), request.body, hashlib.sha512).hexdigest()
        return hmac.compare_digest(signature, computed)