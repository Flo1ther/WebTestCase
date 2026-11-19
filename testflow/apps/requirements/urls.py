from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import RequirementViewSet
router = DefaultRouter()
router.register("requirements", RequirementViewSet, basename="requirement")
urlpatterns = [path("", include(router.urls))]
