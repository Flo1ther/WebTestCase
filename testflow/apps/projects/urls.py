from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import ProjectViewSet
from .workspace import ProjectWorkspaceView, ProjectAnalyticsView, ProjectReportView, ProjectAICoverageSummaryView
from .github_views import ProjectGitHubIntegrationView, ProjectGitHubSimulateView, GitHubActionsCallbackView
router = DefaultRouter()
router.register("projects", ProjectViewSet, basename="project")
urlpatterns = [
    path("projects/<int:project_id>/workspace/", ProjectWorkspaceView.as_view()),
    path("projects/<int:project_id>/analytics/", ProjectAnalyticsView.as_view()),
    path("projects/<int:project_id>/reports/", ProjectReportView.as_view()),
    path("projects/<int:project_id>/ai/coverage-summary/", ProjectAICoverageSummaryView.as_view()),
    path("projects/<int:project_id>/github/", ProjectGitHubIntegrationView.as_view()),
    path("projects/<int:project_id>/github/simulate/", ProjectGitHubSimulateView.as_view()),
    path("integrations/github/callback/", GitHubActionsCallbackView.as_view()),
    path("", include(router.urls)),
]
