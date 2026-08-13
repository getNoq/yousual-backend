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
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    note = models.CharField(max_length=280, blank=True, default="")
    # The real date the expense happened — separate from recorded_at
    # (when it was entered), since expense logging is often batched or
    # backdated: "entering last week's receipts today" is the exact
    # workflow the survey flagged as the weakest habit.
    expense_date = models.DateField(default=timezone.localdate)
    receipt = models.FileField(upload_to=expense_receipt_path, null=True, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-expense_date", "-recorded_at"]

    def __str__(self):
        return f"{self.get_category_display()} — ₦{self.amount} ({self.expense_date})"