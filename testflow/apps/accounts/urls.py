from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import EmailOrUsernameTokenView, MeView, RegisterView, UserViewSet, AssignableTestersView

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
urlpatterns = [path('assignable-testers/', AssignableTestersView.as_view()),path("auth/register/", RegisterView.as_view()), path("auth/login/", EmailOrUsernameTokenView.as_view()), path("auth/me/", MeView.as_view()), path("", include(router.urls))]
