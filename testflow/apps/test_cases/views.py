from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from apps.accounts.permissions import IsManagerOrAdmin
from .models import TestCase
from .serializers import TestCaseSerializer


class TestCaseViewSet(viewsets.ModelViewSet):
    serializer_class = TestCaseSerializer
    filterset_fields = ["status", "priority", "project", "assigned_to"]
    search_fields = ["title", "description", "preconditions"]
    ordering_fields = ["title", "priority", "status", "created_at", "updated_at"]

    def get_queryset(self):
        qs = TestCase.objects.select_related("project", "assigned_to", "created_by").prefetch_related("steps")
        return qs if self.request.user.role in {"ADMIN", "MANAGER"} else qs.filter(assigned_to=self.request.user)
    def get_permissions(self):
        return [IsAuthenticated()] if self.action in {"list", "retrieve"} else [IsManagerOrAdmin()]
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
