from django.db import models
from django.db.models import Count, Q
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from apps.accounts.permissions import IsManagerOrAdmin
from .models import Project
from .serializers import ProjectSerializer


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at", "updated_at"]

    def get_queryset(self):
        return Project.objects.select_related("created_by").annotate(
            test_case_count=Count("test_cases", distinct=True),
            completed=Count("test_cases", filter=~Q(test_cases__status="NOT_RUN"), distinct=True),
        ).annotate(progress=100.0 * models.F("completed") / models.functions.Greatest(models.F("test_case_count"), 1))

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [IsAuthenticated()]
        if self.action == "destroy":
            from apps.accounts.permissions import IsAdminRole
            return [IsAdminRole()]
        return [IsManagerOrAdmin()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
