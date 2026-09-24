from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from .models import Defect
from .serializers import DefectSerializer


class DefectViewSet(viewsets.ModelViewSet):
    serializer_class = DefectSerializer
    filterset_fields = ["status", "test_case"]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "status", "title"]
    def get_queryset(self):
        qs = Defect.objects.select_related("test_case", "reported_by")
        return qs if self.request.user.role in {"ADMIN", "MANAGER"} else qs.filter(test_case__assigned_to=self.request.user)
    def perform_create(self, serializer):
        case = serializer.validated_data["test_case"]
        if self.request.user.role == "TESTER" and case.assigned_to_id != self.request.user.id:
            raise PermissionDenied("You can report defects only for assigned test cases.")
        serializer.save(reported_by=self.request.user)
    def perform_update(self, serializer):
        if self.request.user.role == "TESTER":
            raise PermissionDenied("Only a manager or administrator can update a defect.")
        serializer.save()
    def perform_destroy(self, instance):
        if self.request.user.role not in {"ADMIN", "MANAGER"}:
            raise PermissionDenied("Only a manager or administrator can delete a defect.")
        instance.delete()
