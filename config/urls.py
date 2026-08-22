from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from invoices.views import public_invoice_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/invoices/", include("invoices.urls")),
    path("api/expenses/", include("expenses.urls")),
    path("api/overview/", include("expenses.overview_urls")),
    path("i/<uuid:share_id>/", public_invoice_view, name="public-invoice"),
    path("api/customers/", include("customers.urls")),
    path("api/teams/", include("teams.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)