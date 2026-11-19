from apps.security.permissions import VerifiedUser as BasePermission


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return bool(super().has_permission(request, view) and request.user.role == "ADMIN")


class IsManagerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(super().has_permission(request, view) and request.user.role in {"ADMIN", "MANAGER"})
