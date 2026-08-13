from django.urls import path
from .views import OverviewFeedView, OverviewSummaryView

urlpatterns = [
    path("summary/", OverviewSummaryView.as_view(), name="overview-summary"),
    path("feed/", OverviewFeedView.as_view(), name="overview-feed"),
]