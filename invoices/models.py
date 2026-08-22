import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class Invoice(models.Model):
    class Status(models.TextChoices):
        PAID = "paid", "Paid"
        PARTIALLY_PAID = "partially_paid", "Partially paid"
        DUE = "due", "Due"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="invoices")
    invoice_number = models.CharField(max_length=32)
    business_name = models.CharField(max_length=255)
    customer_name = models.CharField(max_length=255)
    customer_phone = models.CharField(max_length=11, blank=True)
    customer = models.ForeignKey(
        "customers.Customer", null=True, blank=True, on_delete=models.SET_NULL, related_name="invoices"
    )
    items = models.JSONField(default=list)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    # Stored, denormalized status — kept in sync by recompute_status()
    # whenever a Payment changes. amount_paid/amount_due, below, are
    # NEVER stored — always summed live from the Payment ledger, so
    # there's exactly one source of truth and nothing can drift.
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DUE)
    note = models.CharField(max_length=280, blank=True, default="")
    brand_color = models.CharField(max_length=7, blank=True, default="")
    team = models.ForeignKey("teams.Team", null=True, blank=True, on_delete=models.CASCADE, related_name="invoices")
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

    @property
    def amount_paid(self) -> Decimal:
        return self.payments.aggregate(total=Sum("amount"))["total"] or Decimal("0")

    @property
    def amount_due(self) -> Decimal:
        return self.total - self.amount_paid

    def recompute_status(self) -> str:
        """
        Called after every payment is recorded. Derives status purely
        from the ledger — the stored `status` field is a cache of
        this, never edited directly anywhere else in the codebase.
        """
        paid = self.amount_paid
        if paid <= 0:
            new_status = self.Status.DUE
        elif paid < self.total:
            new_status = self.Status.PARTIALLY_PAID
        else:
            new_status = self.Status.PAID

        update_fields = []
        if new_status != self.status:
            self.status = new_status
            update_fields.append("status")
        if new_status == self.Status.PAID and not self.paid_date_display:
            self.paid_date_display = timezone.now().strftime("%d %b %Y")
            update_fields.append("paid_date_display")
        if update_fields:
            self.save(update_fields=update_fields)
        return new_status


class Payment(models.Model):
    """
    One entry in an invoice's payment ledger — the single source of
    truth for amount_paid/amount_due above. No edit/delete support yet
    (matches the same "no edit/delete" line drawn on Invoice itself);
    a wrong entry gets fixed via Django admin for now.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_date_display = models.CharField(max_length=32)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["recorded_at"]

    def __str__(self):
        return f"₦{self.amount} on {self.invoice.invoice_number}"


class InvoiceShare(models.Model):
    """
    A public, read-only snapshot of an invoice, created purely to back
    a shareable link. Always a point-in-time copy — including
    amount_paid — so an already-shared link intentionally keeps
    showing what it showed at share time, even if more payments come
    in on the real invoice afterward.
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
    status = models.CharField(max_length=20, choices=Invoice.Status.choices)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    note = models.CharField(max_length=280, blank=True, default="")
    brand_color = models.CharField(max_length=7, blank=True, default="")
    created_at_display = models.CharField(max_length=32)
    paid_date_display = models.CharField(max_length=32, blank=True, null=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    @property
    def amount_due(self) -> Decimal:
        return self.total - self.amount_paid

    def __str__(self):
        return f"Share of {self.invoice_number}"