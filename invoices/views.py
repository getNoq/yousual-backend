from django.db.models import Sum
from django.http import Http404
from django.shortcuts import render
from rest_framework import permissions, status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Invoice, InvoiceShare
from .pagination import InvoicePagination
from .serializers import (
    CreateInvoiceSerializer,
    CreateInvoiceShareSerializer,
    ImportGuestInvoicesSerializer,
    InvoiceSerializer,
)


class InvoiceListCreateView(ListAPIView):
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = InvoicePagination

    def get_queryset(self):
        return Invoice.objects.filter(user=self.request.user)

    def post(self, request):
        serializer = CreateInvoiceSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        invoice = serializer.save()
        return Response(InvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED)


class InvoiceSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = Invoice.objects.filter(user=request.user)
        total_received = qs.filter(status=Invoice.Status.PAID).aggregate(s=Sum("total"))["s"] or 0
        total_outstanding = qs.filter(status=Invoice.Status.DUE).aggregate(s=Sum("total"))["s"] or 0
        return Response(
            {
                "total_count": qs.count(),
                "total_received": float(total_received),
                "total_outstanding": float(total_outstanding),
            }
        )


class MarkInvoicePaidView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, invoice_id):
        try:
            invoice = Invoice.objects.get(id=invoice_id, user=request.user)
        except Invoice.DoesNotExist:
            return Response({"message": "Invoice not found."}, status=status.HTTP_404_NOT_FOUND)

        invoice.status = Invoice.Status.PAID
        invoice.paid_date_display = request.data.get("paid_date", "")
        invoice.save(update_fields=["status", "paid_date_display"])
        return Response(InvoiceSerializer(invoice).data)


class ImportGuestInvoicesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ImportGuestInvoicesSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        created = serializer.save()
        return Response({"imported": InvoiceSerializer(created, many=True).data}, status=status.HTTP_201_CREATED)


class CreateInvoiceShareView(APIView):
    # AllowAny — guest mode has no auth at all, and this endpoint only
    # ever stores a snapshot the client already has; it doesn't read
    # or expose anything from any account.
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = CreateInvoiceShareSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        share = serializer.save()
        url = request.build_absolute_uri(f"/i/{share.id}/")
        return Response({"url": url}, status=status.HTTP_201_CREATED)


def public_invoice_view(request, share_id):
    try:
        share = InvoiceShare.objects.get(id=share_id)
    except InvoiceShare.DoesNotExist:
        raise Http404("This invoice link doesn't exist or has expired.")

    doc_label = "Receipt" if share.status == "paid" else "Invoice"
    accent_color = share.brand_color or "#221D17"

    items_with_subtotal = []
    for item in share.items:
        qty = item.get("qty", 0)
        unit_price = item.get("unit_price", 0)
        try:
            subtotal = float(qty) * float(unit_price)
        except (TypeError, ValueError):
            subtotal = 0
        items_with_subtotal.append(
            {"description": item.get("description", ""), "qty": qty, "subtotal": subtotal}
        )

    return render(
        request,
        "invoices/public_invoice.html",
        {"share": share, "doc_label": doc_label, "items": items_with_subtotal, "accent_color": accent_color},
    )

class InvoiceDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, invoice_id):
        try:
            invoice = Invoice.objects.get(id=invoice_id, user=request.user)
        except Invoice.DoesNotExist:
            return Response({"message": "Invoice not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(InvoiceSerializer(invoice).data)