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
    # MVP simplification: line items as JSON rather than a related
    # model — fine for display + guest-invoice import. Move to a real
    # InvoiceItem model once invoices are created/edited from the
    # dashboard itself.
    items = models.JSONField(default=list)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=4, choices=Status.choices, default=Status.DUE)
    # Display-formatted strings matching what the frontend already
    # generates (e.g. "09 Aug 2026") — kept as plain text so imported
    # guest invoices round-trip exactly, no reformatting logic needed.
    created_at_display = models.CharField(max_length=32)
    paid_date_display = models.CharField(max_length=32, blank=True, null=True)
    recorded_at = models.DateTimeField(auto_now_add=True)  # for ordering only

    class Meta:
        ordering = ["-recorded_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "invoice_number"], name="unique_invoice_number_per_user")
        ]

    def __str__(self):
        return f"{self.invoice_number} — {self.customer_name}"