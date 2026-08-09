from django.contrib import admin
from django.urls import include, path

from invoices.views import public_invoice_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/invoices/", include("invoices.urls")),
    path("i/<uuid:share_id>/", public_invoice_view, name="public-invoice"),
]