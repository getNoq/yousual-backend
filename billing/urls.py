from django.urls import path
from .views import PlanPricesView

from .views import (
    BillingHistoryView,
    BillingStatusView,
    CancelSubscriptionView,
    FlutterwaveWebhookView,
    PaystackWebhookView,
    SubscribeView,
    VerifyCallbackView,
)

urlpatterns = [
    path("subscribe/", SubscribeView.as_view(), name="billing-subscribe"),
    path("status/", BillingStatusView.as_view(), name="billing-status"),
    path("cancel/", CancelSubscriptionView.as_view(), name="billing-cancel"),
    path("verify/", VerifyCallbackView.as_view(), name="billing-verify"),
    path("history/", BillingHistoryView.as_view(), name="billing-history"),
    path("webhook/paystack/", PaystackWebhookView.as_view(), name="billing-webhook-paystack"),
    path("webhook/flutterwave/", FlutterwaveWebhookView.as_view(), name="billing-webhook-flutterwave"),
    path("prices/", PlanPricesView.as_view(), name="billing-prices"),
]