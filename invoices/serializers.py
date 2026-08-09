from rest_framework import serializers
from .models import Invoice


class InvoiceSerializer(serializers.ModelSerializer):
    created_at = serializers.CharField(source="created_at_display")
    paid_date = serializers.CharField(source="paid_date_display", allow_null=True, required=False)

    class Meta:
        model = Invoice
        fields = [
            "id", "invoice_number", "business_name", "customer_name",
            "customer_phone", "items", "total", "status", "created_at", "paid_date",
        ]


class ImportGuestInvoicesSerializer(serializers.Serializer):
    """
    Takes the exact shape GuestInvoiceFlow stores in localStorage and
    creates one Invoice per entry for the signed-in user. Entries whose
    invoice_number already exists for this user (e.g. a retry after a
    partial failure) are skipped, not errored.

    Note: the global CamelCaseJSONParser has already converted the
    incoming payload's keys to snake_case by the time it reaches here —
    "invoiceNumber" arrives as "invoice_number", "unitPrice" inside each
    item as "unit_price", etc.
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
        return created