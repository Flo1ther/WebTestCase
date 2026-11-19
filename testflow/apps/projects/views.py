from django.db import models
from django.db.models import Count, Q
from rest_framework import viewsets
from apps.security.permissions import VerifiedUser as IsAuthenticated
from apps.accounts.permissions import IsManagerOrAdmin
from apps.audit.services import record_action
from .models import Project
from .serializers import ProjectSerializer


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at", "updated_at"]

    def get_queryset(self):
        qs = Project.objects.select_related("created_by")
        if self.request.user.role == "TESTER":
            qs = qs.filter(test_cases__assigned_to=self.request.user).distinct()
        return qs.annotate(
            test_case_count=Count("test_cases", distinct=True),
            requirements_count=Count("requirements", distinct=True),
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
        project = serializer.save(created_by=self.request.user)
        record_action(user=self.request.user, action="PROJECT_CREATED", entity_type='Проєкт', entity_id=project.id, metadata={"name": project.name})

    def perform_update(self, serializer):
        project = serializer.save()
        record_action(user=self.request.user, action="PROJECT_UPDATED", entity_type='Проєкт', entity_id=project.id)

    def perform_destroy(self, instance):
        record_action(user=self.request.user, action="PROJECT_DELETED", entity_type='Проєкт', entity_id=instance.id, metadata={"name": instance.name})
        instance.delete()
