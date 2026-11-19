import hashlib
import hmac
import json

import pytest
from django.test import override_settings

from tests.test_api import client, users  # noqa: F401 - shared integration fixtures
from apps.executions.models import TestExecution as ExecutionModel, TestRun as RunModel
from apps.projects.models import GitHubIntegration, GitHubWorkflowRun, Project
from apps.test_cases.models import TestCase as CaseModel, TestStep as StepModel


@pytest.fixture
def github_project(users):
    project = Project.objects.create(name="GitHub CI project", created_by=users["manager"])
    integration = GitHubIntegration.objects.create(project=project, repository_full_name="qa-team/demo-store")
    case = CaseModel.objects.create(
        project=project, title="Reject invalid token", automation_key="TC-PAY-INVALID-TOKEN",
        description="Negative checkout", expected_result="HTTP 400", created_by=users["manager"],
    )
    StepModel.objects.create(test_case=case, step_number=1, action="Send invalid token", expected_result="Rejected")
    return project, integration, case


@pytest.mark.django_db
def test_manager_configures_and_simulates_ci_results(client, users, github_project):
    project, integration, case = github_project
    client.force_authenticate(users["manager"])

    response = client.post(
        f"/api/projects/{project.id}/github/simulate/",
        {"tests": [{"automation_key": case.automation_key, "status": "FAILED", "actual_result": "HTTP 201 returned"}]},
        format="json",
    )
    assert response.status_code == 201
    workflow = GitHubWorkflowRun.objects.get(pk=response.data["id"])
    assert workflow.source == "LOCAL_SIMULATION"
    assert workflow.test_run.status == RunModel.Status.COMPLETED
    assert workflow.test_run.test_cases.get() == case
    assert ExecutionModel.objects.filter(test_run=workflow.test_run, test_case=case, status="FAILED").count() == 1
    case.refresh_from_db()
    assert case.status == "FAILED"


@pytest.mark.django_db
@override_settings(GITHUB_WEBHOOK_SECRET="callback-secret")
def test_signed_github_callback_is_idempotent_and_rejects_bad_signature(client, users, github_project):
    _, integration, case = github_project
    payload = {
        "repository": integration.repository_full_name, "run_id": "987654", "workflow": "Tests",
        "status": "COMPLETED", "conclusion": "SUCCESS",
        "tests": [{"automation_key": case.automation_key, "status": "PASSED", "actual_result": "pytest passed"}],
    }
    raw = json.dumps(payload).encode()
    bad = client.post("/api/integrations/github/callback/", raw, content_type="application/json")
    assert bad.status_code == 401
    signature = "sha256=" + hmac.new(b"callback-secret", raw, hashlib.sha256).hexdigest()
    accepted = client.post("/api/integrations/github/callback/", raw, content_type="application/json", HTTP_X_HUB_SIGNATURE_256=signature)
    assert accepted.status_code == 201
    retried = client.post("/api/integrations/github/callback/", raw, content_type="application/json", HTTP_X_HUB_SIGNATURE_256=signature)
    assert retried.status_code == 200
    assert ExecutionModel.objects.filter(test_case=case).count() == 1


@pytest.mark.django_db
def test_tester_cannot_read_or_simulate_project_ci(client, users, github_project):
    project, _, _ = github_project
    client.force_authenticate(users["tester"])
    assert client.get(f"/api/projects/{project.id}/github/").status_code == 403
    assert client.post(f"/api/projects/{project.id}/github/simulate/", {"tests": []}, format="json").status_code == 403
