from django.conf import settings
from django.db import models
from apps.test_cases.models import TestCase


class Defect(models.Model):
    class Severity(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        IN_PROGRESS = "IN_PROGRESS", 'У процесі'
        RESOLVED = "RESOLVED", "Resolved"
        CLOSED = "CLOSED", "Closed"
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="defects")
    requirement = models.ForeignKey("requirements.Requirement", null=True, blank=True, on_delete=models.SET_NULL, related_name="defects")
    test_case = models.ForeignKey(TestCase, on_delete=models.CASCADE, related_name="defects")
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reported_defects")
    title = models.CharField(max_length=220, db_index=True)
    description = models.TextField()
    reproduction_steps = models.TextField(blank=True)
    expected_result = models.TextField(blank=True)
    actual_result = models.TextField(blank=True)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.MEDIUM)
    priority = models.CharField(max_length=10, choices=Severity.choices, default=Severity.MEDIUM)
    product_version = models.CharField(max_length=80, blank=True)
    environment = models.CharField(max_length=120, blank=True)
    test_run = models.ForeignKey("executions.TestRun", null=True, blank=True, on_delete=models.SET_NULL, related_name="defects")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.project_id and self.test_case_id:
            self.project_id = self.test_case.project_id
        if not self.requirement_id and self.test_case_id:
            self.requirement_id = self.test_case.requirement_id
        super().save(*args, **kwargs)
