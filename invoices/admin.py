from django.contrib import admin
from .models import Invoice, InvoiceShare, Payment


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ["id", "recorded_at"]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ["invoice_number", "user", "customer_name", "total", "status", "is_deleted", "recorded_at"]
    list_filter = ["status", "is_deleted"]
    search_fields = ["invoice_number", "customer_name", "business_name"]
    inlines = [PaymentInline]

    def get_queryset(self, request):
        return Invoice.all_objects.all()


@admin.register(InvoiceShare)
class InvoiceShareAdmin(admin.ModelAdmin):
    list_display = ["invoice_number", "user", "customer_name", "total", "status", "recorded_at"]
    search_fields = ["invoice_number", "customer_name", "business_name"]