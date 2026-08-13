from rest_framework import serializers
from .models import Expense

ALLOWED_RECEIPT_EXTENSIONS = {"jpg", "jpeg", "png", "pdf"}
MAX_RECEIPT_SIZE_BYTES = 5 * 1024 * 1024  # 5MB — keeps free-tier disk usage in check


class ExpenseSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    receipt_url = serializers.SerializerMethodField()

    class Meta:
        model = Expense
        fields = ["id", "amount", "category", "category_display", "note", "expense_date", "receipt_url", "recorded_at"]

    def get_receipt_url(self, obj):
        request = self.context.get("request")
        if obj.receipt and request:
            return request.build_absolute_uri(obj.receipt.url)
        return None


class CreateExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = ["amount", "category", "note", "expense_date", "receipt"]
        extra_kwargs = {
            "expense_date": {"required": False},
            "note": {"required": False},
        }

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Enter an amount greater than zero.")
        return value

    def validate_receipt(self, value):
        if not value:
            return value
        ext = value.name.rsplit(".", 1)[-1].lower() if "." in value.name else ""
        if ext not in ALLOWED_RECEIPT_EXTENSIONS:
            raise serializers.ValidationError("Attach a JPG, PNG, or PDF file.")
        if value.size > MAX_RECEIPT_SIZE_BYTES:
            raise serializers.ValidationError("Receipt file is too large — max 5MB.")
        return value

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return Expense.objects.create(**validated_data)