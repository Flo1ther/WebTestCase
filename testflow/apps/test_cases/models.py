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
        PASSED = "PASSED", 'Пройдено'
        FAILED = "FAILED", 'Не пройдено'
        BLOCKED = "BLOCKED", 'Заблоковано'
        NOT_RUN = "NOT_RUN", 'Не виконано'

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="test_cases")
    requirement = models.ForeignKey("requirements.Requirement", null=True, blank=True, on_delete=models.SET_NULL, related_name="primary_test_cases")
    title = models.CharField(max_length=240, db_index=True)
    # A stable key used by CI reports, e.g. TC-AUTH-LOGIN.  It is optional
    # because a manual-only scenario does not need an automated counterpart.
    automation_key = models.CharField(max_length=120, blank=True, db_index=True)
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


class TestSuite(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="test_suites")
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_test_suites")
    test_cases = models.ManyToManyField(TestCase, related_name="suites", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["project_id", "name"]
        constraints = [models.UniqueConstraint(fields=["project", "name"], name="unique_suite_name_per_project")]


class TestStep(models.Model):
    test_case = models.ForeignKey(TestCase, on_delete=models.CASCADE, related_name="steps")
    step_number = models.PositiveIntegerField()
    action = models.TextField()
    expected_result = models.TextField()

    class Meta:
        ordering = ["step_number"]
        constraints = [models.UniqueConstraint(fields=["test_case", "step_number"], name="unique_step_number_per_case")]
