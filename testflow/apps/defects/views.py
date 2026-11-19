from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from apps.audit.services import record_action
from .models import Defect
from .serializers import DefectSerializer


class DefectViewSet(viewsets.ModelViewSet):
    serializer_class = DefectSerializer
    filterset_fields = ["project", "requirement", "status", "test_case"]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "status", "title"]
    def get_queryset(self):
        qs = Defect.objects.select_related("test_case", "reported_by")
        return qs if self.request.user.role in {"ADMIN", "MANAGER"} else qs.filter(test_case__assigned_to=self.request.user)
    def perform_create(self, serializer):
        case = serializer.validated_data["test_case"]
        if self.request.user.role == "TESTER" and case.assigned_to_id != self.request.user.id:
            raise PermissionDenied('Ви можете повідомляти про дефекти лише призначених вам тесткейсів.')
        defect = serializer.save(reported_by=self.request.user)
        record_action(user=self.request.user, action="DEFECT_CREATED", entity_type="Defect", entity_id=defect.id, metadata={"test_case_id": defect.test_case_id, "status": defect.status})
    def perform_update(self, serializer):
        if self.request.user.role == "TESTER":
            raise PermissionDenied('Оновлювати дефекти можуть лише менеджери й адміністратори.')
        before_status = self.get_object().status
        defect = serializer.save()
        if before_status != defect.status:
            record_action(user=self.request.user, action="DEFECT_STATUS_CHANGED", entity_type="Defect", entity_id=defect.id, metadata={"from": before_status, "to": defect.status})
    def perform_destroy(self, instance):
        if self.request.user.role not in {"ADMIN", "MANAGER"}:
            raise PermissionDenied('Видаляти дефекти можуть лише менеджери й адміністратори.')
        instance.delete()
