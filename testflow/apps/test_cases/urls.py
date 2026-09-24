from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import TestCaseViewSet
router = DefaultRouter()
router.register("test-cases", TestCaseViewSet, basename="test-case")
urlpatterns = [path("", include(router.urls))]
