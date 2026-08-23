from django.urls import path
from .views import (
    ReportExpenseBreakdownView,
    ReportExportView,
    ReportSummaryView,
    ReportTopCustomersView,
    ReportTrendView,
)

urlpatterns = [
    path("summary/", ReportSummaryView.as_view(), name="report-summary"),
    path("trend/", ReportTrendView.as_view(), name="report-trend"),
    path("expense-breakdown/", ReportExpenseBreakdownView.as_view(), name="report-expense-breakdown"),
    path("top-customers/", ReportTopCustomersView.as_view(), name="report-top-customers"),
    path("export/", ReportExportView.as_view(), name="report-export"),
]