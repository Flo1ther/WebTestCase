from rest_framework.permissions import BasePermission
class VerifiedUser(BasePermission):
    message = 'Спочатку підтвердьте email.'
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.email_verified and not request.user.manual_blocked)
class Administrator(VerifiedUser):
    message = 'Потрібна роль адміністратора.'
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == 'ADMIN'
