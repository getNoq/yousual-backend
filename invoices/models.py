import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class InvoiceManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


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
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DUE)
    note = models.CharField(max_length=280, blank=True, default="")
    brand_color = models.CharField(max_length=7, blank=True, default="")
    team = models.ForeignKey("teams.Team", null=True, blank=True, on_delete=models.CASCADE, related_name="invoices")
    created_at_display = models.CharField(max_length=32)
    paid_date_display = models.CharField(max_length=32, blank=True, null=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    # New: soft delete + edit tracking
    is_deleted = models.BooleanField(default=False)
    last_edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    last_edited_at = models.DateTimeField(null=True, blank=True)

    objects = InvoiceManager()  # excludes soft-deleted — used everywhere by default
    all_objects = models.Manager()  # unfiltered — admin and internal use only

    class Meta:
        ordering = ["-recorded_at"]
        # Ensures GenericForeignKey lookups (the audit log) and any
        # other Django-internal resolution can still find a
        # soft-deleted invoice, even though Invoice.objects hides it.
        base_manager_name = "all_objects"
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


class PaymentManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_date_display = models.CharField(max_length=32)
    recorded_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    objects = PaymentManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["recorded_at"]
        base_manager_name = "all_objects"

    def __str__(self):
        return f"₦{self.amount} on {self.invoice.invoice_number}"


class InvoiceShare(models.Model):
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