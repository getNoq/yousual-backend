from django.urls import path
from .views import CustomerDetailView, CustomerListView

urlpatterns = [
    path("", CustomerListView.as_view(), name="customer-list"),
    path("<uuid:customer_id>/", CustomerDetailView.as_view(), name="customer-detail"),
]