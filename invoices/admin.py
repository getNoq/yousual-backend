from django.contrib import admin
from .models import Invoice, InvoiceShare


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ["invoice_number", "user", "customer_name", "total", "status", "recorded_at"]
    list_filter = ["status"]
    search_fields = ["invoice_number", "customer_name", "business_name"]


@admin.register(InvoiceShare)
class InvoiceShareAdmin(admin.ModelAdmin):
    list_display = ["invoice_number", "user", "customer_name", "total", "status", "recorded_at"]
    search_fields = ["invoice_number", "customer_name", "business_name"]