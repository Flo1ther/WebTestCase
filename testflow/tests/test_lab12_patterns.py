import pytest

from apps.executions.models import TestRun as RunModel
from apps.projects.models import Project
from apps.requirements.models import Requirement
from apps.test_cases.models import TestCase as CaseModel, TestStep as StepModel
from tests.test_api import client, users


@pytest.mark.django_db
def test_state_pattern_controls_test_run_lifecycle_and_execution(client, users):
    project = Project.objects.create(name="State lifecycle", created_by=users["manager"])
    case = CaseModel.objects.create(
        project=project,
        title="Run state case",
        description="d",
        expected_result="r",
        assigned_to=users["tester"],
        created_by=users["manager"],
    )
    StepModel.objects.create(test_case=case, step_number=1, action="a", expected_result="r")
    run = RunModel.objects.create(project=project, name="Release candidate", created_by=users["manager"])
    run.test_cases.add(case)

    client.force_authenticate(users["manager"])
    assert client.post(f"/api/test-runs/{run.id}/complete/", {}, format="json").status_code == 400
    started = client.post(f"/api/test-runs/{run.id}/start/", {}, format="json")
    assert started.status_code == 200 and started.data["status"] == "ACTIVE"
    assert client.patch(f"/api/test-runs/{run.id}/", {"status": "COMPLETED"}, format="json").status_code == 400

    client.force_authenticate(users["tester"])
    execution = client.post(
        "/api/executions/",
        {"test_case": case.id, "test_run": run.id, "status": "PASSED", "actual_result": "ok"},
        format="json",
    )
    assert execution.status_code == 201

    client.force_authenticate(users["manager"])
    completed = client.post(f"/api/test-runs/{run.id}/complete/", {}, format="json")
    assert completed.status_code == 200 and completed.data["status"] == "COMPLETED"
    assert client.post(f"/api/test-runs/{run.id}/start/", {}, format="json").status_code == 400

    client.force_authenticate(users["tester"])
    rejected = client.post(
        "/api/executions/",
        {"test_case": case.id, "test_run": run.id, "status": "PASSED", "actual_result": "second attempt"},
        format="json",
    )
    assert rejected.status_code == 400


@pytest.mark.django_db
def test_factory_method_creates_requested_project_report(client, users):
    project = Project.objects.create(name="Factory reports", created_by=users["manager"])
    Requirement.objects.create(
        project=project,
        key="REQ-REPORT-1",
        title="Traceability",
        description="A requirement for the report factory test.",
        created_by=users["manager"],
    )
    client.force_authenticate(users["manager"])

    quality = client.get(f"/api/projects/{project.id}/reports/?type=quality")
    traceability = client.get(f"/api/projects/{project.id}/reports/?type=traceability")
    execution = client.get(f"/api/projects/{project.id}/reports/?type=execution")
    invalid = client.get(f"/api/projects/{project.id}/reports/?type=pdf")

    assert quality.status_code == 200 and quality.data["report_type"] == "project-quality-summary"
    assert traceability.status_code == 200 and traceability.data["report_type"] == "project-traceability"
    assert traceability.data["uncovered"][0]["key"] == "REQ-REPORT-1"
    assert execution.status_code == 200 and execution.data["report_type"] == "project-execution-progress"
    assert invalid.status_code == 400
