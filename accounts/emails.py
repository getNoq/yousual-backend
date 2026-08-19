from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .tokens import email_verification_token


def send_password_reset_email(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    raw_token = default_token_generator.make_token(user)
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={uid}.{raw_token}"
    send_mail(
        subject="Reset your Yousual password",
        message=f"Reset your password here: {reset_link}\n\nIf you didn't request this, you can ignore this email.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )


def send_verification_email(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    raw_token = email_verification_token.make_token(user)
    verify_link = f"{settings.FRONTEND_URL}/verify-email?token={uid}.{raw_token}"
    send_mail(
        subject="Verify your Yousual email",
        message=f"Welcome to Yousual! Verify your email to start recording sales and expenses:\n\n{verify_link}\n\nIf you didn't create this account, you can ignore this email.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )