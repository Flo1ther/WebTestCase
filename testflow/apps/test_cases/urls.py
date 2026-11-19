from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import TestCaseViewSet, TestSuiteViewSet
router = DefaultRouter()
router.register("test-cases", TestCaseViewSet, basename="test-case")
router.register("test-suites", TestSuiteViewSet, basename="test-suite")
urlpatterns = [path("", include(router.urls))]
