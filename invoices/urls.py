from django.urls import path

from .views import (
    CreateInvoiceShareView,
    ImportGuestInvoicesView,
    InvoiceDetailView,
    InvoiceListCreateView,
    InvoiceSummaryView,
    RecordPaymentView,
)

urlpatterns = [
    path("", InvoiceListCreateView.as_view(), name="invoice-list-create"),
    path("summary/", InvoiceSummaryView.as_view(), name="invoice-summary"),
    path("import-guest/", ImportGuestInvoicesView.as_view(), name="invoice-import-guest"),
    path("share/", CreateInvoiceShareView.as_view(), name="invoice-share"),
    path("<uuid:invoice_id>/", InvoiceDetailView.as_view(), name="invoice-detail"),
    path("<uuid:invoice_id>/payments/", RecordPaymentView.as_view(), name="invoice-record-payment"),
]