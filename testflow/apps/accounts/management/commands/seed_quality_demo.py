from django.core.management.base import BaseCommand
from apps.accounts.models import User
from apps.projects.models import Project
from apps.requirements.models import Requirement
from apps.test_cases.models import TestCase, TestStep, TestSuite
from apps.executions.models import TestRun, APITest


class Command(BaseCommand):
    help = "Creates a reproducible QA platform demo for the local demo-store API."

    def handle(self, *args, **options):
        manager, _ = User.objects.get_or_create(username="manager", defaults={"email":"manager@example.com","role":"MANAGER","first_name":"Demo","last_name":"Manager"})
        if not manager.has_usable_password(): manager.set_password("DemoPass123!"); manager.save()
        project, _ = Project.objects.get_or_create(name="Demo Store API", defaults={"description":"Controlled local API testing scenario.","ai_context":"Online store checkout API. A valid payment token is required before an order may be created. API tests must be linked to an explicit business requirement.","created_by":manager})
        requirement, _ = Requirement.objects.get_or_create(project=project,key="REQ-CHECKOUT-01",defaults={"title":"Безпечна оплата замовлення","description":"Система не повинна створювати оплачуване замовлення за невалідним платіжним токеном.","priority":"CRITICAL","status":"APPROVED","created_by":manager})
        case, created = TestCase.objects.get_or_create(project=project,title="Відхилити невалідний payment token",defaults={"requirement":requirement,"description":"Перевірити API checkout з невалідним токеном.","preconditions":"Demo API запущено локально.","expected_result":"HTTP 400; замовлення не створено.","priority":"CRITICAL","status":"NOT_RUN","created_by":manager})
        if case.requirement_id != requirement.id:
            case.requirement = requirement
            case.save(update_fields=["requirement", "updated_at"])
        if created: TestStep.objects.create(test_case=case,step_number=1,action="POST checkout з invalid-token",expected_result="HTTP 400")
        requirement.test_cases.add(case)
        suite, _ = TestSuite.objects.get_or_create(project=project,name="Checkout API",defaults={"description":"Критичні API-перевірки checkout.","created_by":manager})
        suite.test_cases.add(case)
        run, _ = TestRun.objects.get_or_create(project=project,name="Demo Store release 1.0",defaults={"description":"Local demo API · intentional defect DEMO-API-01","status":"ACTIVE","created_by":manager})
        run.test_cases.add(case)
        APITest.objects.get_or_create(project=project,name="Checkout rejects invalid token",defaults={"requirement":requirement,"method":"POST","url":"http://127.0.0.1:8000/api/demo-store/checkout/","request_body":{"items":[{"price":100,"quantity":1}],"payment_token":"invalid-token"},"expected_status":400,"json_assertions":[],"created_by":manager})
        self.stdout.write(self.style.SUCCESS(f"Quality demo ready: project={project.id}, requirement={requirement.key}, run={run.id}."))
