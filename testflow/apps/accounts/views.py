from rest_framework import mixins, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import CreateAPIView, RetrieveAPIView, ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import User
from .permissions import IsAdminRole, IsManagerOrAdmin
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

class AssignableTestersView(ListAPIView):
    permission_classes=[IsManagerOrAdmin]
    def get(self, request):
        from rest_framework.response import Response
        users=User.objects.filter(role='TESTER',is_active=True,email_verified=True,manual_blocked=False).order_by('last_name','id')
        paginator=self.paginator
        page=paginator.paginate_queryset(users,request)
        return paginator.get_paginated_response([{'id':u.pk,'username':u.username,'full_name':u.get_full_name() or u.username,'role':u.role} for u in page])


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
            raise PermissionDenied('Не можна вимкнути власний обліковий запис адміністратора або змінити його роль.')

        removes_active_admin = target.role == User.Role.ADMIN and target.is_active and (not new_active or new_role != User.Role.ADMIN)
        if removes_active_admin and not User.objects.filter(role=User.Role.ADMIN, is_active=True).exclude(pk=target.pk).exists():
            raise PermissionDenied('У системі має залишатися хоча б один активний адміністратор.')

        from apps.security.services import audit
        serializer.save(manual_blocked=not new_active, auth_version=target.auth_version+1)
        if new_active:
            from apps.security.models import AttemptBucket
            AttemptBucket.objects.filter(user=target).update(count=0, blocked_until=None)
        audit(self.request, 'UNBLOCK' if new_active else 'MANUAL_BLOCK', True, target, actor=self.request.user)
