"""Idempotent, click-to-prepare records for the guided QA platform demonstration."""
from apps.projects.models import Project
from apps.requirements.models import Requirement
from apps.test_cases.models import TestCase, TestStep, TestSuite
from apps.executions.models import TestRun, APITest


def prepare_guided_demo(user):
    """Create only missing demo records and return their identifiers; never reset user data."""
    store, _ = Project.objects.get_or_create(
        name="Demo Store API",
        defaults={"description": "Керований сценарій реального локального API-тестування.", "created_by": user},
    )
    checkout_requirement, _ = Requirement.objects.get_or_create(
        project=store, key="REQ-CHECKOUT-01",
        defaults={"title": "Безпечна оплата замовлення", "description": "Система не повинна створювати оплачене замовлення за невалідним платіжним токеном.", "priority": "CRITICAL", "status": "APPROVED", "created_by": user},
    )
    checkout_case, created = TestCase.objects.get_or_create(
        project=store, title="Відхилити невалідний payment token",
        defaults={"description": "Перевірити API checkout з невалідним токеном.", "preconditions": "Demo API запущено локально.", "expected_result": "HTTP 400; замовлення не створено.", "priority": "CRITICAL", "status": "NOT_RUN", "created_by": user},
    )
    if created:
        TestStep.objects.create(test_case=checkout_case, step_number=1, action="POST checkout з invalid-token", expected_result="HTTP 400")
    checkout_requirement.test_cases.add(checkout_case)
    suite, _ = TestSuite.objects.get_or_create(project=store, name="Checkout API", defaults={"description": "Критичні API-перевірки checkout.", "created_by": user})
    suite.test_cases.add(checkout_case)
    run, _ = TestRun.objects.get_or_create(project=store, name="Demo Store release 1.0", defaults={"description": "Local demo API · intentional defect DEMO-API-01", "status": "ACTIVE", "created_by": user})
    run.test_cases.add(checkout_case)
    api_test, _ = APITest.objects.get_or_create(
        project=store, name="Checkout rejects invalid token",
        defaults={"method": "POST", "url": "http://127.0.0.1:8000/api/demo-store/checkout/", "request_body": {"items": [{"price": 100, "quantity": 1}], "payment_token": "invalid-token"}, "expected_status": 400, "json_assertions": [], "created_by": user},
    )

    copilot, _ = Project.objects.get_or_create(name="AI Copilot Registration Demo", defaults={"description": "Сценарій review за формальною Requirement.", "created_by": user})
    password_requirement, _ = Requirement.objects.get_or_create(
        project=copilot, key="REQ-REG-PASSWORD",
        defaults={"title": "Валідація пароля при реєстрації", "description": "Пароль повинен містити щонайменше 8 символів. За короткого пароля реєстрація не виконується.", "priority": "HIGH", "status": "APPROVED", "created_by": user},
    )
    password_case, created = TestCase.objects.get_or_create(
        project=copilot, title="Реєстрація з коротким паролем",
        defaults={"description": "Перевірити валідацію мінімальної довжини пароля.", "preconditions": "Відкрита форма реєстрації.", "expected_result": "Користувача успішно зареєстровано.", "priority": "HIGH", "status": "NOT_RUN", "created_by": user},
    )
    if created:
        TestStep.objects.create(test_case=password_case, step_number=1, action="Ввести пароль з 5 символів і натиснути Register.", expected_result="Форма надсилається.")
    password_requirement.test_cases.add(password_case)
    registration_suite, _ = TestSuite.objects.get_or_create(project=copilot, name="Registration validation", defaults={"description": "Перевірки полів реєстрації.", "created_by": user})
    registration_suite.test_cases.add(password_case)
    return {"store_project_id": store.id, "checkout_case_id": checkout_case.id, "run_id": run.id, "api_test_id": api_test.id, "copilot_project_id": copilot.id, "password_requirement_id": password_requirement.id, "password_case_id": password_case.id}
