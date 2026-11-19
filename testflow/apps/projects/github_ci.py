"""GitHub Actions callback processing.

The public callback deliberately accepts only a signed, small JSON contract.
GitHub Actions owns the build; WebTestCase only stores traceable QA results.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.executions.models import TestExecution, TestRun
from apps.test_cases.models import TestCase
from .models import GitHubIntegration, GitHubWorkflowRun


STATUS_MAP = {
    "PASSED": TestCase.Status.PASSED, "PASS": TestCase.Status.PASSED, "SUCCESS": TestCase.Status.PASSED,
    "FAILED": TestCase.Status.FAILED, "FAIL": TestCase.Status.FAILED, "FAILURE": TestCase.Status.FAILED,
    "BLOCKED": TestCase.Status.BLOCKED, "NOT_RUN": TestCase.Status.NOT_RUN, "SKIPPED": TestCase.Status.NOT_RUN,
}
CONCLUSION_MAP = {
    "SUCCESS": GitHubWorkflowRun.Conclusion.SUCCESS, "FAILURE": GitHubWorkflowRun.Conclusion.FAILURE,
    "CANCELLED": GitHubWorkflowRun.Conclusion.CANCELLED, "SKIPPED": GitHubWorkflowRun.Conclusion.SKIPPED,
    "TIMED_OUT": GitHubWorkflowRun.Conclusion.TIMED_OUT, "NEUTRAL": GitHubWorkflowRun.Conclusion.NEUTRAL,
}


def _text(value: Any, length: int = 500) -> str:
    return str(value or "").strip()[:length]


def _parse_time(value: Any):
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if timezone.is_aware(parsed) else timezone.make_aware(parsed)
    except ValueError:
        return None


def build_snapshot(case: TestCase) -> dict[str, Any]:
    return {
        "id": case.id, "title": case.title, "description": case.description,
        "preconditions": case.preconditions, "expected_result": case.expected_result,
        "priority": case.priority, "automation_key": case.automation_key,
        "steps": [{"number": step.step_number, "action": step.action, "expected_result": step.expected_result}
                  for step in case.steps.order_by("step_number")],
    }


def process_ci_callback(
    payload: dict[str, Any], *, source: str = GitHubWorkflowRun.Source.GITHUB_ACTIONS,
    actor=None, integration: GitHubIntegration | None = None,
) -> tuple[GitHubWorkflowRun, bool]:
    """Persist one delivery and its mapped per-test execution history.

    GitHub retries webhooks. ``processed_at`` makes the method idempotent: an
    already processed provider run may refresh metadata but cannot duplicate
    executions.
    """
    repository = _text(payload.get("repository"), 240)
    run_id = _text(payload.get("run_id"), 160)
    if not run_id:
        raise ValueError("Payload повинен містити run_id.")
    if integration is None:
        integration = GitHubIntegration.objects.select_related("project", "project__created_by").filter(
            repository_full_name__iexact=repository, is_enabled=True
        ).first()
    if not integration:
        raise LookupError("Активну інтеграцію для цього GitHub-репозиторію не знайдено.")

    project = integration.project
    status = _text(payload.get("status")).upper()
    if status not in GitHubWorkflowRun.Status.values:
        status = GitHubWorkflowRun.Status.COMPLETED if payload.get("conclusion") else GitHubWorkflowRun.Status.QUEUED
    conclusion = CONCLUSION_MAP.get(_text(payload.get("conclusion")).upper(), GitHubWorkflowRun.Conclusion.UNKNOWN)
    tests = payload.get("tests", [])
    if not isinstance(tests, list):
        raise ValueError("Поле tests повинно бути списком результатів.")

    with transaction.atomic():
        workflow_run, created = GitHubWorkflowRun.objects.select_for_update().get_or_create(
            provider_run_id=run_id,
            defaults={"integration": integration, "source": source},
        )
        if workflow_run.integration_id != integration.id:
            raise ValueError("run_id уже належить іншому GitHub-репозиторію.")
        workflow_run.source = source
        workflow_run.workflow_name = _text(payload.get("workflow"), 240)
        workflow_run.branch = _text(payload.get("branch"), 240)
        workflow_run.commit_sha = _text(payload.get("commit_sha"), 64)
        workflow_run.commit_message = _text(payload.get("commit_message"), 500)
        workflow_run.run_url = _text(payload.get("run_url"), 200)
        workflow_run.status = status
        workflow_run.conclusion = conclusion
        workflow_run.received_payload = payload
        workflow_run.started_at = _parse_time(payload.get("started_at")) or workflow_run.started_at
        workflow_run.completed_at = _parse_time(payload.get("completed_at")) or workflow_run.completed_at

        # Metadata-only progress messages can arrive before the final test list.
        if workflow_run.processed_at or not tests:
            workflow_run.save()
            return workflow_run, created

        test_run = TestRun.objects.create(
            project=project,
            name=f"CI · {workflow_run.workflow_name or 'GitHub Actions'} · #{run_id}",
            description="Результати автоматично передані GitHub Actions.",
            status=TestRun.Status.COMPLETED,
            created_by=actor or project.created_by,
        )
        mapped_cases: list[TestCase] = []
        unmatched: list[str] = []
        seen_case_ids: set[int] = set()
        for item in tests:
            if not isinstance(item, dict):
                continue
            key = _text(item.get("automation_key"), 120).upper()
            if not key:
                continue
            case = TestCase.objects.filter(project=project, automation_key__iexact=key).first()
            if not case:
                unmatched.append(key)
                continue
            if case.id not in seen_case_ids:
                mapped_cases.append(case)
                seen_case_ids.add(case.id)
            result_status = STATUS_MAP.get(_text(item.get("status")).upper(), TestCase.Status.NOT_RUN)
            actual_result = _text(item.get("actual_result") or f"GitHub Actions: {result_status}", 4000)
            comment = _text(item.get("comment") or f"CI run #{run_id}", 4000)
            TestExecution.objects.create(
                project=project, test_run=test_run, test_case=case,
                tester=actor or project.created_by, status=result_status,
                actual_result=actual_result, comment=comment,
                test_case_snapshot=build_snapshot(case),
            )
            case.status = result_status
            case.save(update_fields=["status", "updated_at"])
        test_run.test_cases.set(mapped_cases)
        workflow_run.test_run = test_run
        workflow_run.unmatched_automation_keys = sorted(set(unmatched))
        workflow_run.processed_at = timezone.now()
        workflow_run.save()
    return workflow_run, created
