from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers
from .tokens import email_verification_token

from .phone import normalize_ng_phone

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "phone", "business_name", "first_name", "last_name", "is_email_verified"]


class SignUpSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    phone = serializers.CharField()
    business_name = serializers.CharField(max_length=255)

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate_phone(self, value):
        return normalize_ng_phone(value)

    def validate_business_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Business name is required.")
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email", "").strip().lower()
        password = attrs.get("password")

        user = authenticate(request=self.context.get("request"), username=email, password=password)
        if user is None:
            raise serializers.ValidationError({"non_field_errors": ["Incorrect email or password."]})
        if not user.is_active:
            raise serializers.ValidationError({"non_field_errors": ["This account is inactive."]})

        attrs["user"] = user
        return attrs


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        token = attrs.get("token", "")
        try:
            uidb64, raw_token = token.split(".", 1)
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (ValueError, TypeError, User.DoesNotExist):
            raise serializers.ValidationError({"non_field_errors": ["That reset link is invalid."]})

        if not default_token_generator.check_token(user, raw_token):
            raise serializers.ValidationError(
                {"non_field_errors": ["That reset link has expired. Request a new one."]}
            )

        validate_password(attrs["password"], user=user)
        attrs["user"] = user
        return attrs


class UpdateProfileSerializer(serializers.ModelSerializer):
    """
    Deliberately excludes email — changing a login credential needs its
    own careful, verified flow (confirming the new address, possibly
    re-auth), not a plain profile field edit. Not built this pass.
    """

    class Meta:
        model = User
        fields = ["business_name", "first_name", "last_name", "phone"]

    def validate_business_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Business name is required.")
        return value

    def validate_phone(self, value):
        return normalize_ng_phone(value)

    def validate_first_name(self, value):
        return value.strip()

    def validate_last_name(self, value):
        return value.strip()


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value):
        user = self.context["request"].user
        validate_password(value, user=user)
        return value

    def save(self):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user

class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.CharField()

    def validate(self, attrs):
        token = attrs.get("token", "")
        try:
            uidb64, raw_token = token.split(".", 1)
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (ValueError, TypeError, User.DoesNotExist):
            raise serializers.ValidationError({"non_field_errors": ["That verification link is invalid."]})

        if not email_verification_token.check_token(user, raw_token):
            raise serializers.ValidationError({"non_field_errors": ["That verification link has expired. Request a new one."]})

        attrs["user"] = user
        return attrs