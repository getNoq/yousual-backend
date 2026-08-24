from django.urls import path
from .views import PublicShareDetailView, PaymentDetailView

from .views import (
    CreateInvoiceShareView,
    ImportGuestInvoicesView,
    InvoiceDetailView,
    InvoiceListCreateView,
    InvoiceSummaryView,
    OwedInvoicesView,
    RecordPaymentView,
)

urlpatterns = [
    path("", InvoiceListCreateView.as_view(), name="invoice-list-create"),
    path("summary/", InvoiceSummaryView.as_view(), name="invoice-summary"),
    path("owed/", OwedInvoicesView.as_view(), name="invoice-owed"),
    path("import-guest/", ImportGuestInvoicesView.as_view(), name="invoice-import-guest"),
    path("share/", CreateInvoiceShareView.as_view(), name="invoice-share"),
    path("share/<str:identifier>/", PublicShareDetailView.as_view(), name="invoice-share-detail"),
    path("<uuid:invoice_id>/", InvoiceDetailView.as_view(), name="invoice-detail"),
    path("<uuid:invoice_id>/payments/", RecordPaymentView.as_view(), name="invoice-record-payment"),
    path("<uuid:invoice_id>/payments/<uuid:payment_id>/", PaymentDetailView.as_view(), name="invoice-payment-delete"),
]