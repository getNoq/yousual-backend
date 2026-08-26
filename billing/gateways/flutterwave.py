import requests
from django.conf import settings

from .base import PaymentGateway


class FlutterwaveGateway(PaymentGateway):
    base_url = "https://api.flutterwave.com/v3"

    def _headers(self):
        return {"Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}", "Content-Type": "application/json"}

    def initialize(self, *, email, amount, plan_code, callback_url, metadata):
        payload = {
            "tx_ref": metadata.get("reference"),
            "amount": str(amount),
            "currency": "NGN",
            "redirect_url": callback_url,
            "payment_plan": plan_code,
            "customer": {"email": email},
            "meta": metadata,
        }
        res = requests.post(f"{self.base_url}/payments", json=payload, headers=self._headers(), timeout=15)
        res.raise_for_status()
        data = res.json()["data"]
        return {"authorization_url": data["link"], "reference": metadata.get("reference")}

    def verify_transaction(self, reference):
        res = requests.get(
            f"{self.base_url}/transactions/verify_by_reference",
            params={"tx_ref": reference},
            headers=self._headers(),
            timeout=15,
        )
        res.raise_for_status()
        return res.json()["data"]

    def verify_webhook_signature(self, request) -> bool:
        signature = request.headers.get("verif-hash", "")
        return bool(signature) and signature == settings.FLUTTERWAVE_WEBHOOK_SECRET_HASH