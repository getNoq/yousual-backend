import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


class ResendAPIBackend(BaseEmailBackend):
    """
    Sends email via Resend's HTTPS REST API instead of raw SMTP.
    Exists specifically because PythonAnywhere's free tier blocks
    outbound SMTP as a protocol (with one hardcoded exception for
    Gmail's servers) but allows HTTPS to allowlisted domains — plain
    HTTPS sidesteps that restriction entirely. Requires RESEND_API_KEY
    in settings; see .env.
    """

    api_url = "https://api.resend.com/emails"

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        api_key = getattr(settings, "RESEND_API_KEY", "")
        if not api_key:
            if not self.fail_silently:
                raise ValueError("RESEND_API_KEY is not set.")
            return 0

        sent_count = 0
        for message in email_messages:
            payload = {
                "from": message.from_email,
                "to": list(message.to),
                "subject": message.subject,
                "text": message.body,
            }
            try:
                response = requests.post(
                    self.api_url,
                    json=payload,
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    timeout=10,
                )
                response.raise_for_status()
                sent_count += 1
            except requests.RequestException:
                if not self.fail_silently:
                    raise

        return sent_count