from __future__ import annotations

import hashlib
import hmac
import json
import secrets

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsManagerOrAdmin
from apps.audit.services import record_action
from apps.test_cases.models import TestCase
from .github_ci import process_ci_callback
from .models import GitHubIntegration, GitHubWorkflowRun, Project


class GitHubIntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = GitHubIntegration
        fields = ("id", "project", "repository_full_name", "repository_url", "default_branch", "workflow_file", "is_enabled", "created_at", "updated_at")
        read_only_fields = ("id", "project", "created_at", "updated_at")

    def validate_repository_full_name(self, value):
        value = value.strip().strip("/")
        if len(value.split("/")) != 2 or any(not part for part in value.split("/")):
            raise serializers.ValidationError("Вкажіть репозиторій у форматі owner/repository.")
        return value


class ProjectGitHubIntegrationView(APIView):
    permission_classes = [IsManagerOrAdmin]

    def get_project(self, project_id):
        return get_object_or_404(Project, pk=project_id)

    def get(self, request, project_id):
        project = self.get_project(project_id)
        integration = GitHubIntegration.objects.filter(project=project).first()
        data = GitHubIntegrationSerializer(integration).data if integration else None
        recent_runs = [] if not integration else GitHubWorkflowRun.objects.filter(integration=integration).select_related("test_run")[:12]
        return Response({
            "integration": data,
            "callback_url": f"{settings.PUBLIC_API_URL}/api/integrations/github/callback/",
            "secret_configured": bool(settings.GITHUB_WEBHOOK_SECRET),
            "recent_runs": GitHubWorkflowRunSerializer(recent_runs, many=True).data,
        })

    def post(self, request, project_id):
        project = self.get_project(project_id)
        integration = GitHubIntegration.objects.filter(project=project).first()
        created = integration is None
        serializer = GitHubIntegrationSerializer(integration, data=request.data)
        serializer.is_valid(raise_exception=True)
        integration = serializer.save(project=project)
        record_action(user=request.user, action="GITHUB_INTEGRATION_CONFIGURED", entity_type="Project", entity_id=project.id, metadata={"repository": integration.repository_full_name})
        return Response(GitHubIntegrationSerializer(integration).data, status=201 if created else 200)

    def patch(self, request, project_id):
        project = self.get_project(project_id)
        integration = get_object_or_404(GitHubIntegration, project=project)
        serializer = GitHubIntegrationSerializer(integration, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        integration = serializer.save()
        record_action(user=request.user, action="GITHUB_INTEGRATION_UPDATED", entity_type="Project", entity_id=project.id, metadata={"repository": integration.repository_full_name})
        return Response(GitHubIntegrationSerializer(integration).data)


class GitHubWorkflowRunSerializer(serializers.ModelSerializer):
    test_run_id = serializers.IntegerField(read_only=True)
    test_run_name = serializers.CharField(source="test_run.name", read_only=True)
    class Meta:
        model = GitHubWorkflowRun
        fields = ("id", "provider_run_id", "source", "workflow_name", "branch", "commit_sha", "commit_message", "run_url", "status", "conclusion", "test_run_id", "test_run_name", "unmatched_automation_keys", "started_at", "completed_at", "processed_at", "created_at")


class ProjectGitHubSimulateView(APIView):
    """A transparent local demo using exactly the same result mapper as CI."""
    permission_classes = [IsManagerOrAdmin]

    def post(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        integration = get_object_or_404(GitHubIntegration, project=project, is_enabled=True)
        tests = request.data.get("tests", [])
        if not isinstance(tests, list) or not tests:
            raise ValidationError({"tests": "Додайте хоча б один результат з ключем automation_key."})
        for item in tests:
            if not isinstance(item, dict) or not str(item.get("automation_key", "")).strip():
                raise ValidationError({"tests": "Кожен результат повинен містити automation_key."})
        conclusion = "SUCCESS" if all(str(item.get("status", "")).upper() in {"PASSED", "PASS", "SUCCESS"} for item in tests) else "FAILURE"
        payload = {
            "repository": integration.repository_full_name,
            "run_id": f"local-{secrets.token_hex(8)}",
            "workflow": "Локальна симуляція GitHub Actions",
            "branch": integration.default_branch,
            "commit_sha": "local-demo",
            "commit_message": "Демонстраційне надходження CI-результатів",
            "status": "COMPLETED", "conclusion": conclusion, "tests": tests,
        }
        workflow_run, _ = process_ci_callback(payload, source=GitHubWorkflowRun.Source.LOCAL_SIMULATION, actor=request.user, integration=integration)
        record_action(user=request.user, action="GITHUB_CI_SIMULATED", entity_type="Project", entity_id=project.id, metadata={"workflow_run_id": workflow_run.id, "test_run_id": workflow_run.test_run_id})
        return Response(GitHubWorkflowRunSerializer(workflow_run).data, status=201)


class GitHubActionsCallbackView(APIView):
    """Public, HMAC-protected callback used from a GitHub Actions workflow."""
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        secret = settings.GITHUB_WEBHOOK_SECRET
        if not secret:
            return Response({"detail": "GitHub callback не налаштований на сервері."}, status=503)
        signature = request.headers.get("X-Hub-Signature-256", "")
        expected = "sha256=" + hmac.new(secret.encode(), request.body, hashlib.sha256).hexdigest()
        if not signature or not hmac.compare_digest(signature, expected):
            return Response({"detail": "Некоректний підпис GitHub callback."}, status=401)
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return Response({"detail": "Очікується коректний JSON payload."}, status=400)
        if not isinstance(payload, dict):
            return Response({"detail": "Payload повинен бути JSON-об’єктом."}, status=400)
        try:
            workflow_run, created = process_ci_callback(payload)
        except LookupError as exc:
            return Response({"detail": str(exc)}, status=404)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response({"accepted": True, "created": created, "workflow_run": GitHubWorkflowRunSerializer(workflow_run).data}, status=201 if created else 200)
