from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import ExecutionViewSet, TestRunViewSet, APITestViewSet
router = DefaultRouter()
router.register("test-runs", TestRunViewSet, basename="test-run")
router.register("api-tests", APITestViewSet, basename="api-test")
router.register("executions", ExecutionViewSet, basename="execution")
urlpatterns = [path("", include(router.urls))]
