from decimal import Decimal

from accounts.phone import normalize_ng_phone
from customers.models import Customer
from django.db import IntegrityError
from django.utils import timezone
from rest_framework import serializers
from teams.services import get_active_team
from activity.services import get_edit_history

from .models import Invoice, InvoiceShare, Payment
from .utils import extract_invoice_seq

ALLOWED_BRAND_COLORS = {"#2E8F63", "#3B82F6", "#141414", "#7C3AED", "#F97316"}


def validate_brand_color(value: str) -> str:
    if not value:
        return ""
    if value not in ALLOWED_BRAND_COLORS:
        raise serializers.ValidationError("Invalid brand color.")
    return value


def _compute_total(items) -> Decimal:
    return sum(Decimal(str(i["qty"])) * Decimal(str(i["unit_price"])) for i in items)


def _clean_items(value):
    cleaned = []
    for item in value:
        description = (item.get("description") or "").strip()
        if not description:
            continue
        try:
            qty = float(item.get("qty"))
            unit_price = float(item.get("unit_price"))
        except (TypeError, ValueError):
            raise serializers.ValidationError("Each item needs a valid quantity and price.")
        if qty <= 0 or unit_price <= 0:
            raise serializers.ValidationError("Quantity and price must be greater than zero.")
        cleaned.append({"description": description, "qty": qty, "unit_price": unit_price})
    if not cleaned:
        raise serializers.ValidationError("Add at least one item with a description, quantity, and price.")
    return cleaned


class PaymentSerializer(serializers.ModelSerializer):
    paid_date = serializers.CharField(source="paid_date_display")

    class Meta:
        model = Payment
        fields = ["id", "amount", "paid_date"]


class InvoiceSerializer(serializers.ModelSerializer):
    created_at = serializers.CharField(source="created_at_display")
    paid_date = serializers.CharField(source="paid_date_display", allow_null=True, required=False)
    amount_paid = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    amount_due = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id", "invoice_number", "business_name", "customer_name",
            "customer_phone", "items", "total", "status", "created_at", "paid_date",
            "note", "brand_color", "amount_paid", "amount_due",
        ]


class InvoiceDetailSerializer(InvoiceSerializer):
    payments = PaymentSerializer(many=True, read_only=True)
    edit_history = serializers.SerializerMethodField()
    last_edited_by_email = serializers.SerializerMethodField()

    class Meta(InvoiceSerializer.Meta):
        fields = InvoiceSerializer.Meta.fields + [
            "payments", "edit_history", "last_edited_by_email", "last_edited_at",
        ]

    def get_edit_history(self, obj):
        return [
            {
                "id": str(log.id),
                "action": log.action,
                "changed_by": log.changed_by.email if log.changed_by else "Unknown",
                "changes": log.changes,
                "created_at": log.created_at,
            }
            for log in get_edit_history(obj)
        ]

    def get_last_edited_by_email(self, obj):
        return obj.last_edited_by.email if obj.last_edited_by else None


class CreateInvoiceSerializer(serializers.Serializer):
    customer_name = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    customer_phone = serializers.CharField(required=False, allow_blank=True, default="")
    items = serializers.ListField(child=serializers.DictField())
    amount_paid_now = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal("0"))
    note = serializers.CharField(required=False, allow_blank=True, max_length=280, default="")
    brand_color = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_customer_name(self, value):
        return value.strip()

    def validate_customer_phone(self, value):
        if not value:
            return ""
        return normalize_ng_phone(value)

    def validate_brand_color(self, value):
        return validate_brand_color(value)

    def validate_amount_paid_now(self, value):
        if value < 0:
            raise serializers.ValidationError("Amount received can't be negative.")
        return value

    def validate_items(self, value):
        return _clean_items(value)

    def validate(self, attrs):
        total = _compute_total(attrs.get("items", []))
        amount_paid_now = attrs.get("amount_paid_now", Decimal("0"))
        if amount_paid_now > total:
            raise serializers.ValidationError({"amount_paid_now": f"That's more than the sale total (₦{total})."})

        fully_paid = amount_paid_now >= total
        if not fully_paid and not attrs.get("customer_name", "").strip():
            raise serializers.ValidationError({"customer_name": "Customer name is required unless the sale is paid in full."})

        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        team = get_active_team(user)
        items = validated_data["items"]
        total = _compute_total(items)
        amount_paid_now = validated_data.get("amount_paid_now", Decimal("0"))
        now_display = timezone.now().strftime("%d %b %Y")

        customer_name = validated_data["customer_name"].strip() or "Unknown"

        invoice = None
        for _ in range(3):
            invoice_number = team.next_invoice_number()
            try:
                invoice = Invoice.objects.create(
                    user=user,
                    team=team,
                    invoice_number=invoice_number,
                    business_name=team.name,
                    customer_name=customer_name,
                    customer_phone=validated_data.get("customer_phone", ""),
                    items=items,
                    total=total,
                    status=Invoice.Status.DUE,
                    created_at_display=now_display,
                    note=validated_data.get("note", ""),
                    brand_color=validated_data.get("brand_color", ""),
                )
                break
            except IntegrityError:
                continue
        if invoice is None:
            raise serializers.ValidationError({"non_field_errors": ["Couldn't generate an invoice number. Try again."]})

        if customer_name != "Unknown":
            customer = Customer.objects.upsert_from_sale(team, user, customer_name, validated_data.get("customer_phone", ""))
            if customer:
                invoice.customer = customer
                invoice.save(update_fields=["customer"])

        if amount_paid_now > 0:
            Payment.objects.create(invoice=invoice, amount=amount_paid_now, paid_date_display=now_display)
            invoice.recompute_status()

        return invoice


class UpdateInvoiceSerializer(serializers.Serializer):
    """
    All fields optional (partial update). invoice_number, status, and
    team/user ownership are deliberately not editable here — status is
    derived from the payment ledger, never set directly, and
    invoice_number is a permanent identifier once issued.
    """
    customer_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    customer_phone = serializers.CharField(required=False, allow_blank=True)
    items = serializers.ListField(child=serializers.DictField(), required=False)
    note = serializers.CharField(required=False, allow_blank=True, max_length=280)
    brand_color = serializers.CharField(required=False, allow_blank=True)

    def validate_customer_phone(self, value):
        if not value:
            return ""
        return normalize_ng_phone(value)

    def validate_brand_color(self, value):
        return validate_brand_color(value)

    def validate_items(self, value):
        return _clean_items(value)


class RecordPaymentSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    paid_date = serializers.CharField(required=False, allow_blank=True)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Enter an amount greater than zero.")
        return value

    def validate(self, attrs):
        invoice = self.context["invoice"]
        if attrs["amount"] > invoice.amount_due:
            raise serializers.ValidationError(
                {"amount": f"That's more than what's outstanding (₦{invoice.amount_due})."}
            )
        return attrs

    def create(self, validated_data):
        invoice = self.context["invoice"]
        paid_date = validated_data.get("paid_date") or timezone.now().strftime("%d %b %Y")
        payment = Payment.objects.create(invoice=invoice, amount=validated_data["amount"], paid_date_display=paid_date)
        invoice.recompute_status()
        return payment


class ImportGuestInvoicesSerializer(serializers.Serializer):
    invoices = serializers.ListField(child=serializers.DictField())

    def create(self, validated_data):
        user = self.context["request"].user
        team = get_active_team(user)
        created = []
        for raw in validated_data["invoices"]:
            invoice_number = raw.get("invoice_number")
            if not invoice_number:
                continue
            if Invoice.objects.filter(team=team, invoice_number=invoice_number).exists():
                continue
            invoice = Invoice.objects.create(
                user=user,
                team=team,
                invoice_number=invoice_number,
                business_name=raw.get("business_name", ""),
                customer_name=raw.get("customer_name", ""),
                customer_phone=raw.get("customer_phone") or "",
                items=raw.get("items", []),
                total=raw.get("total", 0),
                status=Invoice.Status.DUE,
                created_at_display=raw.get("created_at", ""),
                note=raw.get("note") or "",
                brand_color=raw.get("brand_color") or "",
            )
            if raw.get("customer_name", "").strip():
                customer = Customer.objects.upsert_from_sale(team, user, raw.get("customer_name", ""), raw.get("customer_phone") or "")
                if customer:
                    invoice.customer = customer
                    invoice.save(update_fields=["customer"])
            if raw.get("status") == "paid":
                Payment.objects.create(
                    invoice=invoice,
                    amount=invoice.total,
                    paid_date_display=raw.get("paid_date") or invoice.created_at_display,
                )
                invoice.recompute_status()
            created.append(invoice)

        if created:
            max_seq = max(extract_invoice_seq(inv.invoice_number) for inv in created)
            if max_seq > team.invoice_counter:
                team.invoice_counter = max_seq
                team.save(update_fields=["invoice_counter"])

        return created


class CreateInvoiceShareSerializer(serializers.Serializer):
    business_name = serializers.CharField(max_length=255)
    customer_name = serializers.CharField(max_length=255)
    invoice_number = serializers.CharField(max_length=32)
    items = serializers.ListField(child=serializers.DictField())
    total = serializers.DecimalField(max_digits=12, decimal_places=2)
    status = serializers.ChoiceField(choices=Invoice.Status.choices)
    amount_paid = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal("0"))
    created_at = serializers.CharField(source="created_at_display")
    paid_date = serializers.CharField(source="paid_date_display", required=False, allow_null=True)
    note = serializers.CharField(required=False, allow_blank=True, max_length=280, default="")
    brand_color = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_brand_color(self, value):
        return validate_brand_color(value)

    def create(self, validated_data):
        request = self.context["request"]
        user = request.user if request.user.is_authenticated else None
        return InvoiceShare.objects.create(user=user, **validated_data)