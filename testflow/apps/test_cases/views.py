from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from apps.security.permissions import VerifiedUser as IsAuthenticated
from apps.accounts.permissions import IsManagerOrAdmin
from apps.audit.services import record_action
from .models import TestCase, TestSuite
from .serializers import TestCaseSerializer, TestSuiteSerializer


class TestSuiteViewSet(viewsets.ModelViewSet):
    serializer_class=TestSuiteSerializer
    filterset_fields=["project"]
    search_fields=["name","description"]
    def get_queryset(self):
        qs=TestSuite.objects.select_related("project","created_by").prefetch_related("test_cases")
        return qs if self.request.user.role in {"ADMIN","MANAGER"} else qs.filter(test_cases__assigned_to=self.request.user).distinct()
    def get_permissions(self): return [IsAuthenticated()] if self.action in {"list","retrieve"} else [IsManagerOrAdmin()]
    def perform_create(self,serializer):
        suite=serializer.save(created_by=self.request.user)
        record_action(user=self.request.user,action="TEST_SUITE_CREATED",entity_type="TestSuite",entity_id=suite.id,metadata={"project_id":suite.project_id})


class TestCaseViewSet(viewsets.ModelViewSet):
    serializer_class = TestCaseSerializer
    filterset_fields = ["status", "priority", "project", "requirement", "assigned_to"]
    search_fields = ["title", "description", "preconditions"]
    ordering_fields = ["title", "priority", "status", "created_at", "updated_at"]

    def get_queryset(self):
        qs = TestCase.objects.select_related("project", "assigned_to", "created_by").prefetch_related("steps")
        return qs if self.request.user.role in {"ADMIN", "MANAGER"} else qs.filter(assigned_to=self.request.user)
    def get_permissions(self):
        return [IsAuthenticated()] if self.action in {"list", "retrieve"} else [IsManagerOrAdmin()]
    def perform_create(self, serializer):
        test_case = serializer.save(created_by=self.request.user)
        record_action(user=self.request.user, action="TEST_CASE_CREATED", entity_type="TestCase", entity_id=test_case.id, metadata={"project_id": test_case.project_id, "assigned_to": test_case.assigned_to_id})

    def perform_update(self, serializer):
        before_assignee = self.get_object().assigned_to_id
        test_case = serializer.save()
        action = "TEST_CASE_ASSIGNED" if before_assignee != test_case.assigned_to_id else "TEST_CASE_UPDATED"
        record_action(user=self.request.user, action=action, entity_type="TestCase", entity_id=test_case.id, metadata={"project_id": test_case.project_id, "assigned_to": test_case.assigned_to_id})

    def perform_destroy(self, instance):
        record_action(user=self.request.user, action="TEST_CASE_DELETED", entity_type="TestCase", entity_id=instance.id, metadata={"title": instance.title})
        instance.delete()
