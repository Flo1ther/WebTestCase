from django.contrib import admin
from django.urls import include, path

urlpatterns = [path("admin/", admin.site.urls), path("api/", include("apps.accounts.urls")), path("api/", include("apps.projects.urls")), path("api/", include("apps.test_cases.urls")), path("api/", include("apps.executions.urls")), path("api/", include("apps.defects.urls")), path("api/", include("apps.reports.urls"))]
