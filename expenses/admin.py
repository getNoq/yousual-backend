from django.contrib import admin
from .models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ["category", "amount", "user", "expense_date", "recorded_at"]
    list_filter = ["category"]
    search_fields = ["note", "user__email"]