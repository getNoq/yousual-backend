from django.contrib import admin
from .models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ["category", "amount", "user", "expense_date", "is_deleted", "recorded_at"]
    list_filter = ["category", "is_deleted"]
    search_fields = ["note", "user__email"]

    def get_queryset(self, request):
        return Expense.all_objects.all()