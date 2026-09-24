from django.urls import path
from .views import DashboardView, ReportsView
urlpatterns = [path("dashboard/", DashboardView.as_view()), path("reports/", ReportsView.as_view())]
