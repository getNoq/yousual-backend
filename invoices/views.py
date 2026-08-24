import uuid as uuid_lib

from django.conf import settings
from django.db.models import DecimalField, F, Sum, Value
from django.db.models.functions import Coalesce
from django.http import Http404
from django.shortcuts import render
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from teams.models import Membership
from teams.services import get_active_team
from activity.services import diff_fields, log_change
from activity.models import EditLog

from .models import Invoice, InvoiceShare, Payment
from .pagination import InvoicePagination
from .serializers import (
    CreateInvoiceSerializer,
    CreateInvoiceShareSerializer,
    ImportGuestInvoicesSerializer,
    InvoiceDetailSerializer,
    InvoiceSerializer,
    RecordPaymentSerializer,
    UpdateInvoiceSerializer,
    _compute_total,
)


def _lookup_share(identifier):
    share = InvoiceShare.objects.filter(slug=identifier).first()
    if share:
        return share
    try:
        uuid_lib.UUID(identifier)
    except (ValueError, AttributeError, TypeError):
        return None
    return InvoiceShare.objects.filter(id=identifier).first()


class InvoiceListCreateView(ListAPIView):
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = InvoicePagination

    def get_queryset(self):
        team = get_active_team(self.request.user)
        return Invoice.objects.filter(team=team)

    def post(self, request):
        if not request.user.is_email_verified:
            return Response(
                {"message": "Verify your email before recording new sales.", "code": "email_not_verified"},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = CreateInvoiceSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        invoice = serializer.save()
        return Response(InvoiceDetailSerializer(invoice).data, status=status.HTTP_201_CREATED)


class OwedInvoicesView(ListAPIView):
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = InvoicePagination

    def get_queryset(self):
        team = get_active_team(self.request.user)
        qs = (
            Invoice.objects.filter(team=team)
            .exclude(status=Invoice.Status.PAID)
            .annotate(
                paid_sum=Coalesce(
                    Sum("payments__amount"),
                    Value(0),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            )
        )
        qs = qs.annotate(balance=F("total") - F("paid_sum"))

        sort = self.request.query_params.get("sort", "oldest")
        if sort == "largest":
            return qs.order_by("-balance")
        return qs.order_by("recorded_at")


class InvoiceDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, invoice_id):
        team = get_active_team(request.user)
        try:
            invoice = Invoice.objects.get(id=invoice_id, team=team)
        except Invoice.DoesNotExist:
            return Response({"message": "Invoice not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(InvoiceDetailSerializer(invoice).data)

    def patch(self, request, invoice_id):
        team = get_active_team(request.user)
        try:
            invoice = Invoice.objects.get(id=invoice_id, team=team)
        except Invoice.DoesNotExist:
            return Response({"message": "Invoice not found."}, status=status.HTTP_404_NOT_FOUND)

        old_values = {
            "customer_name": invoice.customer_name,
            "customer_phone": invoice.customer_phone,
            "items": invoice.items,
            "note": invoice.note,
            "brand_color": invoice.brand_color,
        }

        serializer = UpdateInvoiceSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        for field in ["customer_name", "customer_phone", "note", "brand_color"]:
            if field in data:
                setattr(invoice, field, data[field])
        if "items" in data:
            invoice.items = data["items"]
            invoice.total = _compute_total(data["items"])

        invoice.last_edited_by = request.user
        invoice.last_edited_at = timezone.now()
        invoice.save()
        invoice.recompute_status()

        new_values = {
            "customer_name": invoice.customer_name,
            "customer_phone": invoice.customer_phone,
            "items": invoice.items,
            "note": invoice.note,
            "brand_color": invoice.brand_color,
        }
        changes = diff_fields(old_values, new_values)
        if changes:
            log_change(invoice, EditLog.Action.EDITED, request.user, changes)

        return Response(InvoiceDetailSerializer(invoice).data)

    def delete(self, request, invoice_id):
        team = get_active_team(request.user)
        membership = Membership.objects.filter(team=team, user=request.user).first()
        if not membership or membership.role != Membership.Role.OWNER:
            return Response({"message": "Only the team owner can delete sales."}, status=status.HTTP_403_FORBIDDEN)

        try:
            invoice = Invoice.objects.get(id=invoice_id, team=team)
        except Invoice.DoesNotExist:
            return Response({"message": "Invoice not found."}, status=status.HTTP_404_NOT_FOUND)

        invoice.is_deleted = True
        invoice.save(update_fields=["is_deleted"])
        log_change(invoice, EditLog.Action.DELETED, request.user)
        return Response({"message": "Sale deleted."})


class RecordPaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, invoice_id):
        team = get_active_team(request.user)
        try:
            invoice = Invoice.objects.get(id=invoice_id, team=team)
        except Invoice.DoesNotExist:
            return Response({"message": "Invoice not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = RecordPaymentSerializer(data=request.data, context={"invoice": invoice})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        invoice.refresh_from_db()
        return Response(InvoiceDetailSerializer(invoice).data, status=status.HTTP_201_CREATED)


class PaymentDetailView(APIView):
    """
    Payments are delete-only, not editable — retroactively changing a
    ledger entry's amount is a genuinely different, riskier operation
    than fixing a typo in a name. If a payment was recorded wrong, the
    correct fix is: delete it, then record a new correct one.
    """
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, invoice_id, payment_id):
        team = get_active_team(request.user)
        membership = Membership.objects.filter(team=team, user=request.user).first()
        if not membership or membership.role != Membership.Role.OWNER:
            return Response({"message": "Only the team owner can delete payments."}, status=status.HTTP_403_FORBIDDEN)

        try:
            invoice = Invoice.objects.get(id=invoice_id, team=team)
            payment = Payment.objects.get(id=payment_id, invoice=invoice)
        except (Invoice.DoesNotExist, Payment.DoesNotExist):
            return Response({"message": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)

        payment.is_deleted = True
        payment.save(update_fields=["is_deleted"])
        log_change(payment, EditLog.Action.DELETED, request.user)
        invoice.recompute_status()

        return Response(InvoiceDetailSerializer(invoice).data)


class InvoiceSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        team = get_active_team(request.user)
        invoices = Invoice.objects.filter(team=team)
        total_count = invoices.count()
        total_all = invoices.aggregate(s=Sum("total"))["s"] or 0
        total_received = Payment.objects.filter(invoice__team=team).aggregate(s=Sum("amount"))["s"] or 0
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
        url = f"{settings.FRONTEND_SHARE_URL}/i/{share.slug}/"
        return Response({"url": url}, status=status.HTTP_201_CREATED)


def public_invoice_view(request, identifier):
    share = _lookup_share(identifier)
    if not share:
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


class PublicShareDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, identifier):
        share = _lookup_share(identifier)
        if not share:
            return Response({"message": "This invoice link doesn't exist or has expired."}, status=status.HTTP_404_NOT_FOUND)

        return Response(
            {
                "business_name": share.business_name,
                "customer_name": share.customer_name,
                "invoice_number": share.invoice_number,
                "items": share.items,
                "total": float(share.total),
                "status": share.status,
                "amount_paid": float(share.amount_paid),
                "amount_due": float(share.amount_due),
                "created_at": share.created_at_display,
                "paid_date": share.paid_date_display,
                "note": share.note,
                "brand_color": share.brand_color,
                "hide_branding": share.hide_branding,
            }
        )