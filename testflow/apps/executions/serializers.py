from rest_framework import serializers
from apps.test_cases.models import TestCase
from .models import TestExecution, TestRun, APITest, APIExecution


class TestRunSerializer(serializers.ModelSerializer):
    test_case_ids = serializers.PrimaryKeyRelatedField(many=True, queryset=TestCase.objects.all(), source="test_cases", required=False)
    project_name = serializers.CharField(source="project.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)
    progress = serializers.SerializerMethodField()
    class Meta:
        model = TestRun
        fields = ("id", "project", "project_name", "name", "description", "status", "created_by", "created_by_name", "test_case_ids", "created_at", "updated_at", "progress")
        read_only_fields = ("created_by", "created_at", "updated_at")
    def validate(self, attrs):
        project = attrs.get("project", getattr(self.instance, "project", None))
        cases = attrs.get("test_cases")
        if cases is not None and any(case.project_id != project.id for case in cases):
            raise serializers.ValidationError("Усі тесткейси прогону мають належати вибраному проєкту.")
        if self.instance and "status" in attrs and attrs["status"] != self.instance.status:
            raise serializers.ValidationError({"status": "Статус прогону змінюється лише командами start або complete."})
        return attrs
    def get_progress(self, obj):
        total = obj.test_cases.count()
        done = obj.executions.exclude(status=TestCase.Status.NOT_RUN).values("test_case_id").distinct().count()
        return {"total": total, "completed": done, "percent": round(done * 100 / total) if total else 0}


class APITestSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    requirement_key = serializers.CharField(source="requirement.key", read_only=True)
    class Meta:
        model = APITest
        fields = "__all__"
        read_only_fields = ("created_by", "created_at")
    def validate_url(self, value):
        from urllib.parse import urlparse
        parsed = urlparse(value)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
            raise serializers.ValidationError("Для безпечного запуску дозволені лише локальні HTTP-сервіси.")
        return value
    def validate_json_assertions(self, value):
        if not isinstance(value, list) or len(value) > 20 or not all(isinstance(item, dict) and isinstance(item.get("path"), str) and "equals" in item for item in value):
            raise serializers.ValidationError("Assertions мають бути списком об’єктів path та equals.")
        return value
    def validate(self, attrs):
        project = attrs.get("project", getattr(self.instance, "project", None))
        requirement = attrs.get("requirement", getattr(self.instance, "requirement", None))
        if requirement and project and requirement.project_id != project.id:
            raise serializers.ValidationError({"requirement": "API-тест може тестувати лише вимогу свого проєкту."})
        return attrs


class APIExecutionSerializer(serializers.ModelSerializer):
    api_test_name = serializers.CharField(source="api_test.name", read_only=True)
    class Meta:
        model = APIExecution
        fields = "__all__"
        read_only_fields = ("id", "api_test", "started_by", "status", "actual_status", "duration_ms", "response_preview", "assertion_results", "executed_at")


class ExecutionSerializer(serializers.ModelSerializer):
    test_case_title = serializers.CharField(source="test_case.title", read_only=True)
    tester_name = serializers.SerializerMethodField()
    class Meta:
        model = TestExecution
        fields = "__all__"
        read_only_fields = ("project", "tester", "test_case_snapshot", "executed_at")
    def get_tester_name(self, obj):
        return obj.tester.get_full_name() or obj.tester.username
    def validate(self, attrs):
        case = attrs["test_case"]
        run = attrs.get("test_run")
        user = self.context["request"].user
        if user.role == "TESTER" and case.assigned_to_id != user.id:
            raise serializers.ValidationError('Цей тесткейс вам не призначено.')
        if run and (run.project_id != case.project_id or not run.test_cases.filter(pk=case.pk).exists()):
            raise serializers.ValidationError('Тесткейс не входить до вибраного тестового прогону.')
        if run and run.status != TestRun.Status.ACTIVE:
            raise serializers.ValidationError('Виконання можна додавати лише до активного тестового прогону.')
        return attrs
