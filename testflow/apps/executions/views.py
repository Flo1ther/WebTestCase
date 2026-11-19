from rest_framework import mixins, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from apps.security.permissions import VerifiedUser as IsAuthenticated
from django.db import transaction
from apps.audit.services import record_action
import json, time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import TestExecution, TestRun, APITest, APIExecution
from .serializers import ExecutionSerializer, TestRunSerializer, APITestSerializer, APIExecutionSerializer
from .run_state import TestRunTransitionError, TestRunWorkflow


class TestRunViewSet(viewsets.ModelViewSet):
    serializer_class = TestRunSerializer
    filterset_fields = ["project", "status"]
    search_fields = ["name", "description"]
    ordering_fields = ["created_at", "updated_at", "name"]
    def get_queryset(self):
        qs = TestRun.objects.select_related("project", "created_by").prefetch_related("test_cases")
        return qs if self.request.user.role in {"ADMIN", "MANAGER"} else qs.filter(test_cases__assigned_to=self.request.user).distinct()
    def get_permissions(self):
        # Testers may see runs containing their assignments, but cannot alter the plan.
        if self.action in {"list", "retrieve"}:
            return [IsAuthenticated()]
        return [IsAuthenticated()]
    def _require_manager(self):
        if self.request.user.role not in {"ADMIN", "MANAGER"}:
            raise PermissionDenied("Керувати тестовими прогонами можуть лише менеджери й адміністратори.")
    def perform_create(self, serializer):
        self._require_manager()
        run = serializer.save(created_by=self.request.user)
        record_action(user=self.request.user, action="TEST_RUN_CREATED", entity_type="TestRun", entity_id=run.id, metadata={"project_id":run.project_id})
    def perform_update(self, serializer):
        self._require_manager()
        serializer.save()
    def perform_destroy(self, instance):
        self._require_manager()
        instance.delete()

    def _transition(self, request, pk, command):
        self._require_manager()
        # get_object preserves visibility checks before acquiring a row lock.
        self.get_object()
        with transaction.atomic():
            run = TestRun.objects.select_for_update().get(pk=pk)
            try:
                next_status = TestRunWorkflow.transition(run, command)
            except TestRunTransitionError as exc:
                raise ValidationError({"status": str(exc)}) from exc
            run.save(update_fields=["status", "updated_at"])
        action_names = {"start": "TEST_RUN_STARTED", "complete": "TEST_RUN_COMPLETED"}
        record_action(
            user=request.user,
            action=action_names[command],
            entity_type="TestRun",
            entity_id=run.id,
            metadata={"project_id": run.project_id, "status": next_status},
        )
        return Response(self.get_serializer(run).data)

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        """State command: DRAFT -> ACTIVE."""
        return self._transition(request, pk, "start")

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """State command: ACTIVE -> COMPLETED."""
        return self._transition(request, pk, "complete")


class APITestViewSet(viewsets.ModelViewSet):
    serializer_class = APITestSerializer
    filterset_fields = ["project", "requirement", "method"]
    def get_queryset(self):
        return APITest.objects.select_related("project", "created_by") if self.request.user.role in {"ADMIN", "MANAGER"} else APITest.objects.none()
    def perform_create(self, serializer):
        if self.request.user.role not in {"ADMIN", "MANAGER"}: raise PermissionDenied("Керувати API-тестами можуть лише менеджери й адміністратори.")
        serializer.save(created_by=self.request.user)
    def perform_update(self, serializer):
        if self.request.user.role not in {"ADMIN", "MANAGER"}: raise PermissionDenied("Керувати API-тестами можуть лише менеджери й адміністратори.")
        serializer.save()
    def perform_destroy(self, instance):
        if self.request.user.role not in {"ADMIN", "MANAGER"}: raise PermissionDenied("Керувати API-тестами можуть лише менеджери й адміністратори.")
        instance.delete()
    @action(detail=True, methods=["post"])
    def run(self, request, pk=None):
        test = self.get_object()
        if request.user.role not in {"ADMIN", "MANAGER"}: raise PermissionDenied("Запускати API-тести можуть лише менеджери й адміністратори.")
        started = time.monotonic(); actual_status = None; preview = ""; checks = []
        try:
            data = json.dumps(test.request_body).encode() if test.method in {"POST", "PUT", "PATCH"} else None
            headers = {str(k): str(v) for k, v in test.headers.items() if str(k).lower() not in {"authorization", "cookie"}}
            headers.setdefault("Content-Type", "application/json")
            req = Request(test.url, data=data, headers=headers, method=test.method)
            try:
                with urlopen(req, timeout=10) as response:
                    actual_status = response.status; raw = response.read(65536)
            except HTTPError as error:
                actual_status = error.code; raw = error.read(65536)
            preview = raw.decode("utf-8", errors="replace")[:4000]
            try: body = json.loads(preview)
            except json.JSONDecodeError: body = None
            checks.append({"name": "HTTP status", "passed": actual_status == test.expected_status, "expected": test.expected_status, "actual": actual_status})
            for assertion in test.json_assertions:
                value = body
                for key in assertion["path"].strip(".").split("."):
                    value = value.get(key) if isinstance(value, dict) else None
                checks.append({"name": assertion["path"], "passed": value == assertion["equals"], "expected": assertion["equals"], "actual": value})
            status = "PASSED" if all(item["passed"] for item in checks) else "FAILED"
        except (URLError, TimeoutError, ValueError) as exc:
            preview = str(exc); status = "ERROR"; checks.append({"name":"request", "passed":False, "actual":preview})
        execution = APIExecution.objects.create(api_test=test, started_by=request.user, status=status, actual_status=actual_status, duration_ms=round((time.monotonic()-started)*1000), response_preview=preview, assertion_results=checks)
        record_action(user=request.user, action="API_TEST_EXECUTED", entity_type="APIExecution", entity_id=execution.id, metadata={"api_test_id":test.id,"status":status})
        return Response(APIExecutionSerializer(execution).data, status=201)

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        return Response(APIExecutionSerializer(self.get_object().executions.order_by("-executed_at")[:50], many=True).data)


class ExecutionViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = ExecutionSerializer
    filterset_fields = ["project", "status", "test_case"]
    ordering_fields = ["executed_at", "status"]
    def get_queryset(self):
        qs = TestExecution.objects.select_related("test_case", "tester")
        return qs if self.request.user.role in {"ADMIN", "MANAGER"} else qs.filter(tester=self.request.user)
    def perform_create(self, serializer):
        with transaction.atomic():
            case = serializer.validated_data["test_case"]
            snapshot = {
                "id": case.id,
                "title": case.title,
                "description": case.description,
                "preconditions": case.preconditions,
                "expected_result": case.expected_result,
                "priority": case.priority,
                "steps": [
                    {"number": step.step_number, "action": step.action, "expected_result": step.expected_result}
                    for step in case.steps.order_by("step_number")
                ],
            }
            execution = serializer.save(tester=self.request.user, test_case_snapshot=snapshot)
            execution.test_case.status = execution.status
            execution.test_case.save(update_fields=["status", "updated_at"])
            record_action(user=self.request.user, action="TEST_EXECUTED", entity_type="TestExecution", entity_id=execution.id, metadata={"test_case_id": execution.test_case_id, "status": execution.status})
