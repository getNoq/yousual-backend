from django.urls import path
from .views import ExpenseDetailView, ExpenseListCreateView

urlpatterns = [
    path("", ExpenseListCreateView.as_view(), name="expense-list-create"),
    path("<uuid:expense_id>/", ExpenseDetailView.as_view(), name="expense-detail"),
]