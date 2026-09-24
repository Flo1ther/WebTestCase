from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from .models import TestExecution
from .serializers import ExecutionSerializer


class ExecutionViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = ExecutionSerializer
    filterset_fields = ["status", "test_case"]
    ordering_fields = ["executed_at", "status"]
    def get_queryset(self):
        qs = TestExecution.objects.select_related("test_case", "tester")
        return qs if self.request.user.role in {"ADMIN", "MANAGER"} else qs.filter(tester=self.request.user)
    def perform_create(self, serializer):
        execution = serializer.save(tester=self.request.user)
        execution.test_case.status = execution.status
        execution.test_case.save(update_fields=["status", "updated_at"])
