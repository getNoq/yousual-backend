from django.urls import path

from .views import (
    CreateInvoiceShareView,
    ImportGuestInvoicesView,
    InvoiceListCreateView,
    InvoiceSummaryView,
    MarkInvoicePaidView,
)

urlpatterns = [
    path("", InvoiceListCreateView.as_view(), name="invoice-list-create"),
    path("summary/", InvoiceSummaryView.as_view(), name="invoice-summary"),
    path("<uuid:invoice_id>/mark-paid/", MarkInvoicePaidView.as_view(), name="invoice-mark-paid"),
    path("import-guest/", ImportGuestInvoicesView.as_view(), name="invoice-import-guest"),
    path("share/", CreateInvoiceShareView.as_view(), name="invoice-share"),
]