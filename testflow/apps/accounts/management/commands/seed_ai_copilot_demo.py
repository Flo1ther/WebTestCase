from django.core.management.base import BaseCommand
from apps.accounts.models import User
from apps.projects.models import Project
from apps.requirements.models import Requirement
from apps.test_cases.models import TestCase, TestStep, TestSuite


class Command(BaseCommand):
    help = "Creates a reproducible AI QA Copilot demonstration scenario."

    def handle(self, *args, **options):
        manager, _ = User.objects.get_or_create(username="manager", defaults={"email":"manager@example.com", "role":"MANAGER", "first_name":"Demo", "last_name":"Manager"})
        if not manager.has_usable_password(): manager.set_password("DemoPass123!"); manager.save()
        tester, _ = User.objects.get_or_create(username="tester", defaults={"email":"tester@example.com", "role":"TESTER", "first_name":"Taras", "last_name":"Тестувальник", "email_verified":True})
        if not tester.has_usable_password(): tester.set_password("DemoPass123!"); tester.save()
        project, _ = Project.objects.get_or_create(name="AI Copilot Registration Demo", defaults={"description":"Demo for requirement-aware QA review.","created_by":manager})
        requirement, _ = Requirement.objects.get_or_create(project=project,key="REQ-REG-PASSWORD",defaults={"title":"Валідація пароля при реєстрації","description":"Пароль повинен містити щонайменше 8 символів. За короткого пароля реєстрація не виконується.","priority":"HIGH","status":"APPROVED","created_by":manager})
        case, created = TestCase.objects.get_or_create(project=project,title="Реєстрація з коротким паролем",defaults={"description":"Перевірити валідацію мінімальної довжини пароля.","preconditions":"Відкрита форма реєстрації.","expected_result":"Користувача успішно зареєстровано.","priority":"HIGH","status":"NOT_RUN","assigned_to":tester,"created_by":manager})
        if case.assigned_to_id is None:
            case.assigned_to = tester
            case.save(update_fields=["assigned_to", "updated_at"])
        if created: TestStep.objects.create(test_case=case,step_number=1,action="Ввести пароль з 5 символів і натиснути Register.",expected_result="Форма надсилається.")
        requirement.test_cases.add(case)
        suite, _ = TestSuite.objects.get_or_create(project=project,name="Registration validation",defaults={"description":"Перевірки полів реєстрації.","created_by":manager})
        suite.test_cases.add(case)
        self.stdout.write(self.style.SUCCESS(f"AI Copilot demo ready: project={project.id}, requirement={requirement.key}, case={case.id}."))
