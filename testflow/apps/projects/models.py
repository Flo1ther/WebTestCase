from django.conf import settings
from django.db import models


class Project(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        ON_HOLD = "ON_HOLD", "On hold"
        ARCHIVED = "ARCHIVED", "Archived"

    name = models.CharField(max_length=180, unique=True)
    description = models.TextField(blank=True)
    ai_context = models.TextField(blank=True, help_text="Domain, terminology, users, constraints and acceptance context for AI QA.")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_projects")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class GitHubIntegration(models.Model):
    """One GitHub Actions source may report test results to one QA project."""

    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name="github_integration")
    repository_full_name = models.CharField(max_length=240, unique=True, help_text="owner/repository")
    repository_url = models.URLField(blank=True)
    default_branch = models.CharField(max_length=120, default="main")
    workflow_file = models.CharField(max_length=240, blank=True, help_text=".github/workflows/qa.yml")
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "GitHub integration"
        verbose_name_plural = "GitHub integrations"

    def __str__(self):
        return f"{self.project.name} ← {self.repository_full_name}"


class GitHubWorkflowRun(models.Model):
    class Source(models.TextChoices):
        GITHUB_ACTIONS = "GITHUB_ACTIONS", "GitHub Actions"
        LOCAL_SIMULATION = "LOCAL_SIMULATION", "Local simulation"

    class Status(models.TextChoices):
        QUEUED = "QUEUED", "Queued"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        COMPLETED = "COMPLETED", "Completed"

    class Conclusion(models.TextChoices):
        SUCCESS = "SUCCESS", "Success"
        FAILURE = "FAILURE", "Failure"
        CANCELLED = "CANCELLED", "Cancelled"
        SKIPPED = "SKIPPED", "Skipped"
        TIMED_OUT = "TIMED_OUT", "Timed out"
        NEUTRAL = "NEUTRAL", "Neutral"
        UNKNOWN = "UNKNOWN", "Unknown"

    integration = models.ForeignKey(GitHubIntegration, on_delete=models.CASCADE, related_name="workflow_runs")
    test_run = models.ForeignKey("executions.TestRun", null=True, blank=True, on_delete=models.SET_NULL, related_name="github_workflow_runs")
    provider_run_id = models.CharField(max_length=160, unique=True)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.GITHUB_ACTIONS)
    workflow_name = models.CharField(max_length=240, blank=True)
    branch = models.CharField(max_length=240, blank=True)
    commit_sha = models.CharField(max_length=64, blank=True)
    commit_message = models.CharField(max_length=500, blank=True)
    run_url = models.URLField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    conclusion = models.CharField(max_length=20, choices=Conclusion.choices, default=Conclusion.UNKNOWN)
    received_payload = models.JSONField(default=dict, blank=True)
    unmatched_automation_keys = models.JSONField(default=list, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["integration", "status"], name="projects_gi_integr_7fa946_idx")]

    def __str__(self):
        return f"{self.integration.repository_full_name} #{self.provider_run_id}"
