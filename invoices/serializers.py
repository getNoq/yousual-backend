from accounts.phone import normalize_ng_phone
from rest_framework import serializers

from .models import Invoice, InvoiceShare
from .utils import extract_invoice_seq

ALLOWED_BRAND_COLORS = {"#2E8F63", "#3B82F6", "#141414", "#7C3AED", "#F97316"}

def validate_brand_color(value: str) -> str:
    if not value:
        return ""
    if value not in ALLOWED_BRAND_COLORS:
        raise serializers.ValidationError("Invalid brand color.")
    return value


class InvoiceSerializer(serializers.ModelSerializer):
    created_at = serializers.CharField(source="created_at_display")
    paid_date = serializers.CharField(source="paid_date_display", allow_null=True, required=False)

    class Meta:
        model = Invoice
        fields = [
            "id", "invoice_number", "business_name", "customer_name",
            "customer_phone", "items", "total", "status", "note", "brand_color", "created_at", "paid_date",
        ]


class CreateInvoiceSerializer(serializers.Serializer):
    """
    Used by the dashboard's "New invoice" form. business_name isn't
    accepted here at all — it's always the signed-in user's own
    account name, set server-side in create().
    """

    customer_name = serializers.CharField(max_length=255)
    customer_phone = serializers.CharField(required=False, allow_blank=True, default="")
    items = serializers.ListField(child=serializers.DictField())
    status = serializers.ChoiceField(choices=Invoice.Status.choices, default=Invoice.Status.DUE)
    note = serializers.CharField(required=False, allow_blank=True, max_length=280, default="")
    brand_color = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_brand_color(self, value):
        return validate_brand_color(value)

    def validate_customer_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Customer name is required.")
        return value

    def validate_customer_phone(self, value):
        if not value:
            return ""
        return normalize_ng_phone(value)

    def validate_items(self, value):
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

    def create(self, validated_data):
        from django.db import IntegrityError
        from django.utils import timezone

        user = self.context["request"].user
        items = validated_data["items"]
        total = sum(i["qty"] * i["unit_price"] for i in items)
        status = validated_data["status"]
        now_display = timezone.now().strftime("%d %b %Y")

        for _ in range(3):
            invoice_number = user.next_invoice_number()
            try:
                return Invoice.objects.create(
                    user=user,
                    invoice_number=invoice_number,
                    business_name=user.business_name,
                    customer_name=validated_data["customer_name"],
                    customer_phone=validated_data.get("customer_phone", ""),
                    items=items,
                    total=total,
                    status=status,
                    created_at_display=now_display,
                    paid_date_display=now_display if status == Invoice.Status.PAID else None,
                    note=validated_data.get("note", ""),
                    brand_color=validated_data.get("brand_color", ""),
                )
            except IntegrityError:
                continue
        raise serializers.ValidationError({"non_field_errors": ["Couldn't generate an invoice number. Try again."]})


class ImportGuestInvoicesSerializer(serializers.Serializer):
    """
    Takes the exact shape GuestInvoiceFlow stores in localStorage and
    creates one Invoice per entry. Also bumps the user's server-side
    invoice_counter past the highest imported number, so dashboard-
    created invoices never collide with guest-mode numbering.
    """

    invoices = serializers.ListField(child=serializers.DictField())

    def create(self, validated_data):
        user = self.context["request"].user
        created = []
        for raw in validated_data["invoices"]:
            invoice_number = raw.get("invoice_number")
            if not invoice_number:
                continue
            if Invoice.objects.filter(user=user, invoice_number=invoice_number).exists():
                continue
            invoice = Invoice.objects.create(
                user=user,
                invoice_number=invoice_number,
                business_name=raw.get("business_name", ""),
                customer_name=raw.get("customer_name", ""),
                customer_phone=raw.get("customer_phone") or "",
                items=raw.get("items", []),
                total=raw.get("total", 0),
                status=raw.get("status", "due"),
                created_at_display=raw.get("created_at", ""),
                paid_date_display=raw.get("paid_date"),
            )
            created.append(invoice)

        if created:
            max_seq = max(extract_invoice_seq(inv.invoice_number) for inv in created)
            if max_seq > user.invoice_counter:
                user.invoice_counter = max_seq
                user.save(update_fields=["invoice_counter"])

        return created


class CreateInvoiceShareSerializer(serializers.Serializer):
    business_name = serializers.CharField(max_length=255)
    customer_name = serializers.CharField(max_length=255)
    invoice_number = serializers.CharField(max_length=32)
    items = serializers.ListField(child=serializers.DictField())
    total = serializers.DecimalField(max_digits=12, decimal_places=2)
    status = serializers.ChoiceField(choices=Invoice.Status.choices)
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