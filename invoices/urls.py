from django.urls import path
from .views import ImportGuestInvoicesView, InvoiceListView, MarkInvoicePaidView

urlpatterns = [
    path("", InvoiceListView.as_view(), name="invoice-list"),
    path("<uuid:invoice_id>/mark-paid/", MarkInvoicePaidView.as_view(), name="invoice-mark-paid"),
    path("import-guest/", ImportGuestInvoicesView.as_view(), name="invoice-import-guest"),
]