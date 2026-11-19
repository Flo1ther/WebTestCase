from django.urls import path

from .views import DefectTrendsView, ExecutionTrendsView, OverviewView, ProjectComparisonView, TesterPerformanceView, TestStabilityView

urlpatterns = [
    path("analytics/overview/", OverviewView.as_view()),
    path("analytics/execution-trends/", ExecutionTrendsView.as_view()),
    path("analytics/project-comparison/", ProjectComparisonView.as_view()),
    path("analytics/test-stability/", TestStabilityView.as_view()),
    path("analytics/defect-trends/", DefectTrendsView.as_view()),
    path("analytics/tester-performance/", TesterPerformanceView.as_view()),
]
