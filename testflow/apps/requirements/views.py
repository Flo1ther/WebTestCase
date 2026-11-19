from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from apps.audit.services import record_action
from apps.security.permissions import VerifiedUser
from .models import Requirement
from .serializers import RequirementSerializer


class RequirementViewSet(viewsets.ModelViewSet):
    serializer_class = RequirementSerializer
    filterset_fields = ["project", "priority", "status"]
    search_fields = ["key", "title", "description"]
    ordering_fields = ["key", "priority", "created_at", "updated_at"]
    def get_queryset(self):
        qs = Requirement.objects.select_related("project", "created_by").prefetch_related("test_cases")
        return qs if self.request.user.role in {"ADMIN", "MANAGER"} else qs.filter(test_cases__assigned_to=self.request.user).distinct()
    def get_permissions(self):
        return [VerifiedUser()]
    def _require_manager(self):
        if self.request.user.role not in {"ADMIN", "MANAGER"}:
            raise PermissionDenied("Керувати вимогами можуть лише менеджери й адміністратори.")
    def perform_create(self, serializer):
        self._require_manager()
        item = serializer.save(created_by=self.request.user)
        record_action(user=self.request.user, action="REQUIREMENT_CREATED", entity_type="Requirement", entity_id=item.id, metadata={"project_id": item.project_id, "key": item.key})
    def perform_update(self, serializer):
        self._require_manager()
        serializer.save()
    def perform_destroy(self, instance):
        self._require_manager()
        instance.delete()
