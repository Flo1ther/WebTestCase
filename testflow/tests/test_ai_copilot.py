import pytest
from apps.projects.models import Project
from apps.requirements.models import Requirement
from apps.test_cases.models import TestCase, TestStep
from apps.executions.models import APITest, APIExecution
from apps.ai_assistant.benchmark import run_benchmark
from apps.ai_assistant.copilot import TextScenarioReviewer
from tests.test_api import client, users


@pytest.fixture(autouse=True)
def local_provider(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "local")


@pytest.mark.django_db
def test_review_finds_requirement_min_length_contradiction_and_applies_fix(client, users):
    project=Project.objects.create(name="Registration", description="Account onboarding", created_by=users["manager"])
    req=Requirement.objects.create(project=project,key="REQ-PASS-8",title="Password length",description="Пароль повинен містити щонайменше 8 символів.",priority="HIGH",status="APPROVED",created_by=users["manager"])
    case=TestCase.objects.create(project=project,title="Short password accepted",description="Перевірка реєстрації.",preconditions="Registration page is open.",expected_result="Користувача успішно зареєстровано.",created_by=users["manager"])
    TestStep.objects.create(test_case=case,step_number=1,action="Ввести пароль з 5 символів і натиснути Register.",expected_result="Форма надсилається.")
    req.test_cases.add(case)
    client.force_authenticate(users["manager"])
    review=client.post("/api/ai/analyze-test-case/",{"test_case_id":case.id},format="json")
    assert review.status_code==201
    finding=next(item for item in review.data["result"]["findings"] if item["id"]=="REQ-MIN-LENGTH")
    assert finding["evidence_type"]=="requirement_match" and review.data["result"]["quality_score"]<100
    proposal=client.post(f"/api/ai/analyses/{review.data['id']}/fixes/",{"finding_id":"REQ-MIN-LENGTH"},format="json")
    assert proposal.status_code==201 and proposal.data["status"]=="PROPOSED"
    applied=client.post(f"/api/ai/fixes/{proposal.data['id']}/apply/",{},format="json")
    assert applied.status_code==200
    case.refresh_from_db(); assert "помилку" in case.expected_result.lower()


@pytest.mark.django_db
def test_fix_refuses_stale_test_case(client, users):
    project=Project.objects.create(name="Stale",created_by=users["manager"])
    case=TestCase.objects.create(project=project,title="Invalid payment",description="d",preconditions="Open checkout",expected_result="Оплату виконано",created_by=users["manager"])
    TestStep.objects.create(test_case=case,step_number=1,action="Ввести невалідний номер картки",expected_result="Оплата успішна")
    client.force_authenticate(users["manager"])
    review=client.post("/api/ai/analyze-test-case/",{"test_case_id":case.id},format="json")
    proposal=client.post(f"/api/ai/analyses/{review.data['id']}/fixes/",{"finding_id":"LOG-INVALID-SUCCESS"},format="json")
    case.description="Changed after review";case.save()
    assert client.post(f"/api/ai/fixes/{proposal.data['id']}/apply/",{},format="json").status_code==400


@pytest.mark.django_db
def test_negative_api_test_with_http_400_is_not_false_positive(client, users):
    project=Project.objects.create(name="API negative",created_by=users["manager"])
    case=TestCase.objects.create(project=project,title="Reject invalid token",description="Negative checkout API test",preconditions="API is available",expected_result="HTTP 400; замовлення не створено.",created_by=users["manager"])
    TestStep.objects.create(test_case=case,step_number=1,action="POST checkout з invalid-token",expected_result="HTTP 400; замовлення не створено.")
    client.force_authenticate(users["manager"])
    review=client.post("/api/ai/analyze-test-case/",{"test_case_id":case.id},format="json")
    assert review.status_code==201
    assert not any(item["id"]=="LOG-INVALID-SUCCESS" for item in review.data["result"]["findings"])


@pytest.mark.django_db
def test_coverage_analysis_and_api_assistant(client, users):
    project=Project.objects.create(name="Coverage",created_by=users["manager"])
    req=Requirement.objects.create(project=project,key="REQ-1",title="Save profile",description="Profile data must be saved.",created_by=users["manager"])
    case=TestCase.objects.create(project=project,title="Successful save",description="positive",preconditions="Signed in",expected_result="Saved",created_by=users["manager"])
    req.test_cases.add(case)
    api_test=APITest.objects.create(project=project,name="Health",method="GET",url="http://127.0.0.1:8000/api/demo-store/health/",expected_status=200,created_by=users["manager"])
    APIExecution.objects.create(api_test=api_test,started_by=users["manager"],status="FAILED",actual_status=500,assertion_results=[{"name":"HTTP status","passed":False,"expected":200,"actual":500}])
    client.force_authenticate(users["manager"])
    coverage=client.post("/api/ai/coverage-analysis/",{"requirement_id":req.id},format="json")
    assert coverage.status_code==201 and coverage.data["result"]["potential_gaps"]
    helper=client.post(f"/api/ai/api-tests/{api_test.id}/assistant/",{},format="json")
    assert helper.status_code==201 and helper.data["result"]["failure_explanation"]["actual_status"]==500


def test_deterministic_benchmark_has_reproducible_metrics():
    metrics, details=run_benchmark()
    assert metrics["precision"]==1.0 and metrics["recall"]==1.0 and metrics["f1"]==1.0
    assert len(details)==6 and not any(item["false_negatives"] for item in details)


def test_requirement_reviewer_detects_generic_consistency_problems():
    text = '''У кошику ноутбук вартістю 30000 грн та миша вартістю 1000 грн.
Промокод дає знижку 10%. Загальна вартість замовлення становить 28000 грн.
Ввести невалідний номер картки. Оплату виконано, замовлення оплачено.
Оновити сторінку. Автоматично створюється ще одне замовлення.'''
    ids = {item['id'] for item in TextScenarioReviewer().review(text)}
    assert {'TEXT-PERCENT', 'TEXT-INVALID-SUCCESS', 'TEXT-REPEAT-SIDE-EFFECT'} <= ids
