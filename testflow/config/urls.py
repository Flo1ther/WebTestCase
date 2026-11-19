from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("", include("apps.security.urls")),

    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/", include("apps.accounts.urls")), path("api/", include("apps.projects.urls")), path("api/", include("apps.requirements.urls")),
    path("api/", include("apps.test_cases.urls")), path("api/", include("apps.executions.urls")),
    path("api/", include("apps.defects.urls")), path("api/", include("apps.reports.urls")),
    path("api/", include("apps.analytics.urls")), path("api/", include("apps.ai_assistant.urls")),
    path("api/", include("apps.audit.urls")),
    path("api/", include("apps.demo_api.urls")),
]
