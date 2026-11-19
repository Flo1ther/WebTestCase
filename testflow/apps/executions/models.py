from django.conf import settings
from django.db import models
from apps.test_cases.models import TestCase


class TestRun(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Чернетка"
        ACTIVE = "ACTIVE", "Активний"
        COMPLETED = "COMPLETED", "Завершений"

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="test_runs")
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_test_runs")
    test_cases = models.ManyToManyField(TestCase, related_name="test_runs", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [models.Index(fields=["project", "status"])]


class TestExecution(models.Model):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="executions")
    test_run = models.ForeignKey(TestRun, null=True, blank=True, on_delete=models.SET_NULL, related_name="executions")
    test_case = models.ForeignKey(TestCase, on_delete=models.CASCADE, related_name="executions")
    tester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="executions")
    status = models.CharField(max_length=10, choices=TestCase.Status.choices, default=TestCase.Status.NOT_RUN)
    actual_result = models.TextField()
    comment = models.TextField(blank=True)
    # An execution must remain understandable even after a test case is edited.
    test_case_snapshot = models.JSONField(default=dict, blank=True)
    executed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-executed_at"]
        indexes = [models.Index(fields=["tester", "executed_at"]), models.Index(fields=["test_case", "executed_at"])]

    def save(self, *args, **kwargs):
        if not self.project_id and self.test_case_id:
            self.project_id = self.test_case.project_id
        super().save(*args, **kwargs)


class APITest(models.Model):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="api_tests")
    requirement = models.ForeignKey("requirements.Requirement", null=True, blank=True, on_delete=models.SET_NULL, related_name="api_tests")
    name = models.CharField(max_length=180)
    method = models.CharField(max_length=8, default="GET")
    url = models.URLField(max_length=500)
    headers = models.JSONField(default=dict, blank=True)
    request_body = models.JSONField(default=dict, blank=True)
    expected_status = models.PositiveSmallIntegerField(default=200)
    json_assertions = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_api_tests")
    created_at = models.DateTimeField(auto_now_add=True)


class APIExecution(models.Model):
    api_test = models.ForeignKey(APITest, on_delete=models.CASCADE, related_name="executions")
    started_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    status = models.CharField(max_length=8, choices=[("PASSED", "Passed"), ("FAILED", "Failed"), ("ERROR", "Error")])
    actual_status = models.PositiveSmallIntegerField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(default=0)
    response_preview = models.TextField(blank=True)
    assertion_results = models.JSONField(default=list)
    executed_at = models.DateTimeField(auto_now_add=True)
