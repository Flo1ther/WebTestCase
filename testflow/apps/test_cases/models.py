from django.conf import settings
from django.db import models
from apps.projects.models import Project


class TestCase(models.Model):
    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"
    class Status(models.TextChoices):
        PASSED = "PASSED", "Passed"
        FAILED = "FAILED", "Failed"
        BLOCKED = "BLOCKED", "Blocked"
        NOT_RUN = "NOT_RUN", "Not Run"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="test_cases")
    title = models.CharField(max_length=240, db_index=True)
    description = models.TextField()
    preconditions = models.TextField(blank=True)
    expected_result = models.TextField()
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM, db_index=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.NOT_RUN, db_index=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_test_cases", limit_choices_to={"role": "TESTER"})
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_test_cases")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [models.Index(fields=["project", "status"]), models.Index(fields=["assigned_to", "status"])]

    def __str__(self):
        return self.title


class TestStep(models.Model):
    test_case = models.ForeignKey(TestCase, on_delete=models.CASCADE, related_name="steps")
    step_number = models.PositiveIntegerField()
    action = models.TextField()
    expected_result = models.TextField()

    class Meta:
        ordering = ["step_number"]
        constraints = [models.UniqueConstraint(fields=["test_case", "step_number"], name="unique_step_number_per_case")]
