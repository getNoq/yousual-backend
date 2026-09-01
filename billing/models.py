import uuid

from django.conf import settings
from django.db import models

INTERVAL_CHOICES = [("monthly", "Monthly"), ("yearly", "Yearly")]


class PlanPrice(models.Model):
    """
    Editable in Django admin — this IS the "super admin sets the
    price" mechanism. One row per interval, no env var, no redeploy
    needed to change what Business Plan costs.
    """

    interval = models.CharField(max_length=10, choices=INTERVAL_CHOICES, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    paystack_plan_code = models.CharField(max_length=255, blank=True, default="")
    flutterwave_plan_id = models.CharField(max_length=255, blank=True, default="")

    def __str__(self):
        return f"{self.get_interval_display()} — ₦{self.amount}"


class Subscription(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past due"
        CANCELED = "canceled", "Canceled"

    class Gateway(models.TextChoices):
        PAYSTACK = "paystack", "Paystack"
        FLUTTERWAVE = "flutterwave", "Flutterwave"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey("teams.Team", on_delete=models.CASCADE, related_name="subscriptions")
    gateway = models.CharField(max_length=20, choices=Gateway.choices)
    interval = models.CharField(max_length=10, choices=INTERVAL_CHOICES, default="monthly")
    gateway_customer_code = models.CharField(max_length=255, blank=True, default="")
    gateway_subscription_code = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    current_period_end = models.DateTimeField(null=True, blank=True)
    grace_period_ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.team.name} — {self.gateway} ({self.status})"


class BillingTransaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey("teams.Team", on_delete=models.CASCADE, related_name="billing_transactions")
    subscription = models.ForeignKey(Subscription, null=True, blank=True, on_delete=models.SET_NULL, related_name="transactions")
    gateway = models.CharField(max_length=20)
    gateway_reference = models.CharField(max_length=255, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, default="success")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.gateway_reference} — ₦{self.amount}"