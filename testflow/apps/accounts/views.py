from rest_framework import mixins, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import CreateAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import User
from .permissions import IsAdminRole
from .serializers import AdminUserSerializer, RegisterSerializer, UserSerializer


class EmailOrUsernameTokenSerializer(TokenObtainPairSerializer):
    """Allow the login form to accept either the username or unique email."""

    def validate(self, attrs):
        identifier = attrs.get(self.username_field, "").strip()
        if "@" in identifier:
            user = User.objects.filter(email__iexact=identifier).first()
            if user:
                attrs[self.username_field] = user.username
        return super().validate(attrs)


class EmailOrUsernameTokenView(TokenObtainPairView):
    serializer_class = EmailOrUsernameTokenSerializer


class RegisterView(CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer


class MeView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class UserViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAdminRole]
    serializer_class = AdminUserSerializer
    queryset = User.objects.all().order_by("username")
    search_fields = ["username", "email", "first_name", "last_name"]
    filterset_fields = ["role", "is_active"]

    def perform_update(self, serializer):
        target = self.get_object()
        new_active = serializer.validated_data.get("is_active", target.is_active)
        new_role = serializer.validated_data.get("role", target.role)

        if target.pk == self.request.user.pk and (not new_active or new_role != User.Role.ADMIN):
            raise PermissionDenied("You cannot deactivate or change the administrator role of your own account.")

        removes_active_admin = target.role == User.Role.ADMIN and target.is_active and (not new_active or new_role != User.Role.ADMIN)
        if removes_active_admin and not User.objects.filter(role=User.Role.ADMIN, is_active=True).exclude(pk=target.pk).exists():
            raise PermissionDenied("At least one active administrator must remain in the system.")

        serializer.save()
