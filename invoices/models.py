import uuid
from django.conf import settings
from django.db import models


class Invoice(models.Model):
    class Status(models.TextChoices):
        PAID = "paid", "Paid"
        DUE = "due", "Due"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="invoices")
    invoice_number = models.CharField(max_length=32)
    business_name = models.CharField(max_length=255)
    customer_name = models.CharField(max_length=255)
    customer_phone = models.CharField(max_length=11, blank=True)
    items = models.JSONField(default=list)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=4, choices=Status.choices, default=Status.DUE)
    note = models.CharField(max_length=280, blank=True, default="")
    brand_color = models.CharField(max_length=7, blank=True, default="")  # hex, e.g. "#2E8F63"
    created_at_display = models.CharField(max_length=32)
    paid_date_display = models.CharField(max_length=32, blank=True, null=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-recorded_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "invoice_number"], name="unique_invoice_number_per_user")
        ]

    def __str__(self):
        return f"{self.invoice_number} — {self.customer_name}"


class InvoiceShare(models.Model):
    """
    A public, read-only snapshot of an invoice, created purely to back
    a shareable link. Deliberately separate from Invoice: guest-mode
    shares have no user at all, and even for signed-in users this is a
    point-in-time copy — if the real Invoice later gets marked paid,
    an already-shared link intentionally keeps showing what it showed
    at share time, not live data.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="invoice_shares"
    )
    business_name = models.CharField(max_length=255)
    customer_name = models.CharField(max_length=255)
    invoice_number = models.CharField(max_length=32)
    items = models.JSONField(default=list)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=4, choices=Invoice.Status.choices)
    note = models.CharField(max_length=280, blank=True, default="")
    brand_color = models.CharField(max_length=7, blank=True, default="")  # hex, e.g. "#2E8F63"
    created_at_display = models.CharField(max_length=32)
    paid_date_display = models.CharField(max_length=32, blank=True, null=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Share of {self.invoice_number}"