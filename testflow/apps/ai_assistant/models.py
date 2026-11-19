from django.conf import settings
from django.db import models


class AIAnalysis(models.Model):
    class AnalysisType(models.TextChoices):
        ANALYZE = "ANALYZE", "Analyze test case"
        GENERATE = "GENERATE", 'Підготувати пропозиції'
        COVERAGE = "COVERAGE", "Coverage analysis"
        API = "API", "API assistant"

    test_case = models.ForeignKey("test_cases.TestCase", null=True, blank=True, on_delete=models.SET_NULL, related_name="ai_analyses")
    requirement = models.ForeignKey("requirements.Requirement", null=True, blank=True, on_delete=models.SET_NULL, related_name="ai_analyses")
    project = models.ForeignKey("projects.Project", null=True, blank=True, on_delete=models.SET_NULL, related_name="ai_analyses")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ai_analyses")
    analysis_type = models.CharField(max_length=16, choices=AnalysisType.choices)
    provider = models.CharField(max_length=40)
    model_name = models.CharField(max_length=120)
    result = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["requested_by", "created_at"]), models.Index(fields=["test_case", "created_at"])]


class AIFixProposal(models.Model):
    class Status(models.TextChoices):
        PROPOSED = "PROPOSED", "Proposed"
        APPLIED = "APPLIED", "Applied"
        REJECTED = "REJECTED", "Rejected"

    analysis = models.ForeignKey(AIAnalysis, on_delete=models.CASCADE, related_name="fixes")
    finding_id = models.CharField(max_length=80)
    target_field = models.CharField(max_length=80)
    before = models.TextField()
    after = models.TextField()
    rationale = models.TextField()
    related_fields = models.JSONField(default=list, blank=True)
    test_case_updated_at = models.DateTimeField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PROPOSED)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="ai_fix_decisions")
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["analysis", "finding_id"], name="unique_ai_fix_per_finding")]


class AIBenchmarkRun(models.Model):
    provider = models.CharField(max_length=40)
    model_name = models.CharField(max_length=120)
    dataset_version = models.CharField(max_length=40, default="qa-copilot-v1")
    metrics = models.JSONField(default=dict)
    details = models.JSONField(default=list)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
