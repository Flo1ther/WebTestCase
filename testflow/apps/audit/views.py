from rest_framework import mixins, viewsets

from apps.accounts.permissions import IsAdminRole
from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAdminRole]
    serializer_class = AuditLogSerializer
    queryset = AuditLog.objects.select_related("user")
    filterset_fields = ["action", "entity_type", "user"]
    ordering_fields = ["created_at", "action", "entity_type"]
