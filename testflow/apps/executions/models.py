from django.conf import settings
from django.db import models
from apps.test_cases.models import TestCase


class TestExecution(models.Model):
    test_case = models.ForeignKey(TestCase, on_delete=models.CASCADE, related_name="executions")
    tester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="executions")
    status = models.CharField(max_length=10, choices=TestCase.Status.choices, default=TestCase.Status.NOT_RUN)
    actual_result = models.TextField()
    comment = models.TextField(blank=True)
    executed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-executed_at"]
        indexes = [models.Index(fields=["tester", "executed_at"]), models.Index(fields=["test_case", "executed_at"])]
