from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import ExecutionViewSet
router = DefaultRouter()
router.register("executions", ExecutionViewSet, basename="execution")
urlpatterns = [path("", include(router.urls))]
