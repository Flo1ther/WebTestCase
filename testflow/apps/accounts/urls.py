from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import EmailOrUsernameTokenView, MeView, RegisterView, UserViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
urlpatterns = [path("auth/register/", RegisterView.as_view()), path("auth/login/", EmailOrUsernameTokenView.as_view()), path("auth/refresh/", TokenRefreshView.as_view()), path("auth/me/", MeView.as_view()), path("", include(router.urls))]
