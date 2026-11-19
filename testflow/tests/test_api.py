import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.executions.models import TestExecution as ExecutionModel
from apps.projects.models import Project
from apps.test_cases.models import TestCase as CaseModel, TestStep as StepModel


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def users():
    return {
        "admin": User.objects.create_user(username="admin", email="admin@test.local", password="DemoPass123!", role="ADMIN"),
        "manager": User.objects.create_user(username="manager", email="manager@test.local", password="DemoPass123!", role="MANAGER"),
        "tester": User.objects.create_user(username="tester", email="tester@test.local", password="DemoPass123!", role="TESTER"),
        "other": User.objects.create_user(username="other", email="other@test.local", password="DemoPass123!", role="TESTER"),
    }


@pytest.fixture
def test_case(users):
    project = Project.objects.create(name="Analytics project", created_by=users["manager"])
    case = CaseModel.objects.create(project=project, title="Valid checkout", description="Customer pays with valid card.", expected_result="Order is confirmed.", assigned_to=users["tester"], created_by=users["manager"])
    StepModel.objects.create(test_case=case, step_number=1, action="Open checkout", expected_result="Checkout opens")
    return case


@pytest.mark.django_db
def test_login_accepts_email(client, users):
    response = client.post("/api/auth/login/", {"username": users["tester"].email, "password": "DemoPass123!"})
    assert response.status_code == 200
    assert response.data["requires_2fa"] is False
    assert "sessionid" in client.cookies


@pytest.mark.django_db
def test_manager_creates_test_case_and_audit_event(client, users):
    client.force_authenticate(users["manager"])
    project = Project.objects.create(name="CRUD project", created_by=users["manager"])
    response = client.post("/api/test-cases/", {"project": project.id, "title": "Registration", "description": "Create an account with valid data.", "expected_result": "Account is created.", "priority": "HIGH", "status": "NOT_RUN", "assigned_to": users["tester"].id, "steps": [{"step_number": 1, "action": "Open registration", "expected_result": "Form is visible"}]}, format="json")
    assert response.status_code == 201
    assert response.data["steps"][0]["step_number"] == 1
    assert client.get("/api/audit-logs/").status_code == 403


@pytest.mark.django_db
def test_tester_execution_updates_case_and_keeps_history(client, users, test_case):
    client.force_authenticate(users["tester"])
    response = client.post("/api/executions/", {"test_case": test_case.id, "status": "PASSED", "actual_result": "Order appeared in account.", "comment": ""}, format="json")
    assert response.status_code == 201
    test_case.refresh_from_db()
    assert test_case.status == "PASSED"
    assert ExecutionModel.objects.filter(test_case=test_case).count() == 1


@pytest.mark.django_db
def test_analytics_is_scoped_to_assigned_cases(client, users, test_case):
    ExecutionModel.objects.create(test_case=test_case, tester=users["tester"], status="PASSED", actual_result="Passed")
    client.force_authenticate(users["tester"])
    response = client.get("/api/analytics/overview/")
    assert response.status_code == 200
    assert response.data["total_test_cases"] == 1
    assert response.data["passed"] == 1
    for endpoint in ("execution-trends", "project-comparison", "test-stability", "defect-trends", "tester-performance"):
        assert client.get(f"/api/analytics/{endpoint}/").status_code == 200


@pytest.mark.django_db
def test_ai_local_demo_allows_assigned_tester_only(client, users, test_case, monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "local")
    client.force_authenticate(users["tester"])
    response = client.post("/api/ai/analyze-test-case/", {"test_case_id": test_case.id}, format="json")
    assert response.status_code == 201
    assert response.data["result"]["mode"] == "local_demo"
    client.force_authenticate(users["other"])
    forbidden = client.post("/api/ai/analyze-test-case/", {"test_case_id": test_case.id}, format="json")
    assert forbidden.status_code == 403
