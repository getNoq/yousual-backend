from django.db.models import Sum
from django.http import Http404
from django.shortcuts import render
from rest_framework import permissions, status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Invoice, InvoiceShare, Payment
from .pagination import InvoicePagination
from .serializers import (
    CreateInvoiceSerializer,
    CreateInvoiceShareSerializer,
    ImportGuestInvoicesSerializer,
    InvoiceDetailSerializer,
    InvoiceSerializer,
    RecordPaymentSerializer,
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
        return Response(InvoiceDetailSerializer(invoice).data, status=status.HTTP_201_CREATED)


class InvoiceDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, invoice_id):
        try:
            invoice = Invoice.objects.get(id=invoice_id, user=request.user)
        except Invoice.DoesNotExist:
            return Response({"message": "Invoice not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(InvoiceDetailSerializer(invoice).data)


class RecordPaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, invoice_id):
        try:
            invoice = Invoice.objects.get(id=invoice_id, user=request.user)
        except Invoice.DoesNotExist:
            return Response({"message": "Invoice not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = RecordPaymentSerializer(data=request.data, context={"invoice": invoice})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        invoice.refresh_from_db()
        return Response(InvoiceDetailSerializer(invoice).data, status=status.HTTP_201_CREATED)


class InvoiceSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        invoices = Invoice.objects.filter(user=request.user)
        total_count = invoices.count()
        total_all = invoices.aggregate(s=Sum("total"))["s"] or 0
        total_received = Payment.objects.filter(invoice__user=request.user).aggregate(s=Sum("amount"))["s"] or 0
        total_outstanding = total_all - total_received
        return Response(
            {
                "total_count": total_count,
                "total_received": float(total_received),
                "total_outstanding": float(total_outstanding),
            }
        )


class ImportGuestInvoicesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ImportGuestInvoicesSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        created = serializer.save()
        return Response({"imported": InvoiceSerializer(created, many=True).data}, status=status.HTTP_201_CREATED)


class CreateInvoiceShareView(APIView):
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
        items_with_subtotal.append({"description": item.get("description", ""), "qty": qty, "subtotal": subtotal})

    return render(
        request,
        "invoices/public_invoice.html",
        {
            "share": share,
            "doc_label": doc_label,
            "items": items_with_subtotal,
            "accent_color": accent_color,
            "amount_due": share.amount_due,
        },
    )