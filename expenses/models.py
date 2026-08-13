import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


def expense_receipt_path(instance, filename):
    return f"expense_receipts/{instance.user_id}/{uuid.uuid4()}_{filename}"


class Expense(models.Model):
    class Category(models.TextChoices):
        INVENTORY = "inventory", "Inventory / stock"
        TRANSPORT = "transport", "Transport"
        RENT = "rent", "Rent"
        UTILITIES = "utilities", "Utilities"
        SALARIES = "salaries", "Salaries / wages"
        SUPPLIES = "supplies", "Supplies"
        MARKETING = "marketing", "Marketing"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="expenses")
    expense_number = models.CharField(max_length=32)
    title = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    note = models.CharField(max_length=280, blank=True, default="")
    expense_date = models.DateField(default=timezone.localdate)
    receipt = models.FileField(upload_to=expense_receipt_path, null=True, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-expense_date", "-recorded_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "expense_number"], name="unique_expense_number_per_user")
        ]

    def __str__(self):
        return f"{self.expense_number} — {self.title}"