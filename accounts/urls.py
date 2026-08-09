from django.urls import path

from .views import ForgotPasswordView, LoginView, MeView, ResetPasswordView, SignUpView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path("login/", LoginView.as_view(), name="login"),
    path("me/", MeView.as_view(), name="me"),
    path("password/forgot/", ForgotPasswordView.as_view(), name="password-forgot"),
    path("password/reset/", ResetPasswordView.as_view(), name="password-reset"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
]