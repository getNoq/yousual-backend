from django.contrib import admin
from .models import BillingTransaction, Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["team", "gateway", "status", "amount", "current_period_end"]
    list_filter = ["gateway", "status"]


@admin.register(BillingTransaction)
class BillingTransactionAdmin(admin.ModelAdmin):
    list_display = ["team", "gateway", "gateway_reference", "amount", "status", "created_at"]
    list_filter = ["gateway", "status"]
    search_fields = ["gateway_reference"]