import pytest

from tests.test_api import client, users
from apps.defects.models import Defect
from apps.executions.models import APITest, TestExecution as Execution
from apps.projects.models import Project
from apps.requirements.models import Requirement
from apps.test_cases.models import TestCase as Case, TestStep as Step


@pytest.mark.django_db
def test_project_workspace_tracks_requirement_coverage_and_project_owned_records(client, users):
    project = Project.objects.create(name="Checkout workspace", ai_context="Online checkout. Card payments require valid tokens.", created_by=users["manager"])
    requirement = Requirement.objects.create(project=project, key="REQ-PAY-1", title="Reject invalid token", description="Invalid payment token must not create an order.", created_by=users["manager"])
    case = Case.objects.create(project=project, requirement=requirement, title="Reject invalid token", description="Negative payment test", expected_result="HTTP 400", assigned_to=users["tester"], created_by=users["manager"])
    Step.objects.create(test_case=case, step_number=1, action="Send invalid token", expected_result="Request is rejected")
    execution = Execution.objects.create(test_case=case, tester=users["tester"], status="FAILED", actual_result="HTTP 201")
    defect = Defect.objects.create(test_case=case, reported_by=users["tester"], title="Token accepted", description="Unexpected checkout success")
    api_test = APITest.objects.create(project=project, requirement=requirement, name="Checkout invalid token", method="POST", url="http://127.0.0.1:8000/api/demo-store/checkout/", expected_status=400, created_by=users["manager"])
    assert execution.project_id == project.id
    assert defect.project_id == project.id and defect.requirement_id == requirement.id
    assert api_test.requirement_id == requirement.id

    client.force_authenticate(users["manager"])
    workspace = client.get(f"/api/projects/{project.id}/workspace/")
    assert workspace.status_code == 200
    assert workspace.data["summary"]["requirements_coverage"] == 100
    assert workspace.data["coverage"][0]["manual_test_cases"] == 1
    assert workspace.data["coverage"][0]["api_tests"] == 1
    assert client.get(f"/api/projects/{project.id}/reports/").data["summary"]["open_defects"] == 1
    summary = client.get(f"/api/projects/{project.id}/ai/coverage-summary/")
    assert summary.status_code == 200 and "100" in summary.data["summary"]


@pytest.mark.django_db
def test_test_case_and_api_test_reject_requirement_from_another_project(client, users):
    client.force_authenticate(users["manager"])
    project_a = Project.objects.create(name="A", created_by=users["manager"])
    project_b = Project.objects.create(name="B", created_by=users["manager"])
    requirement = Requirement.objects.create(project=project_a, key="REQ-A", title="A", description="A", created_by=users["manager"])
    case = client.post("/api/test-cases/", {"project": project_b.id, "requirement": requirement.id, "title": "Wrong link", "description": "x", "expected_result": "x", "steps": [{"action": "x", "expected_result": "x"}]}, format="json")
    api = client.post("/api/api-tests/", {"project": project_b.id, "requirement": requirement.id, "name": "Wrong API link", "method": "GET", "url": "http://127.0.0.1:8000/api/demo-store/health/", "expected_status": 200, "json_assertions": []}, format="json")
    assert case.status_code == 400
    assert api.status_code == 400
