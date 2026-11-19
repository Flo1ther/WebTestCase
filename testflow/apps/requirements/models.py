from django.conf import settings
from django.db import models


class Requirement(models.Model):
    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        APPROVED = "APPROVED", "Approved"
        IMPLEMENTED = "IMPLEMENTED", "Implemented"
        DEPRECATED = "DEPRECATED", "Deprecated"

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="requirements")
    key = models.CharField(max_length=40)
    title = models.CharField(max_length=240)
    description = models.TextField()
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=14, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_requirements")
    test_cases = models.ManyToManyField("test_cases.TestCase", related_name="requirements", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["project_id", "key"]
        constraints = [models.UniqueConstraint(fields=["project", "key"], name="unique_requirement_key_per_project")]
        indexes = [models.Index(fields=["project", "status"])]
