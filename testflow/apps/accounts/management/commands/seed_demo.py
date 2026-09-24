from django.core.management.base import BaseCommand
from apps.accounts.models import User
from apps.projects.models import Project
from apps.test_cases.models import TestCase, TestStep
from apps.executions.models import TestExecution
from apps.defects.models import Defect


class Command(BaseCommand):
    help = "Create idempotent local demo users and test management data"

    def handle(self, *args, **options):
        users = {}
        for username, email, role, first, last in [
            ("admin", "admin@example.com", "ADMIN", "Olena", "Admin"),
            ("manager", "manager@example.com", "MANAGER", "Maksym", "Manager"),
            ("tester", "tester@example.com", "TESTER", "Taras", "Tester"),
        ]:
            user, created = User.objects.get_or_create(username=username, defaults={"email": email, "role": role, "first_name": first, "last_name": last})
            if created:
                user.set_password("DemoPass123!")
                user.save()
            users[username] = user
        shop, _ = Project.objects.get_or_create(name="Online Store", defaults={"description": "Checkout and customer account regression suite.", "created_by": users["manager"]})
        portal, _ = Project.objects.get_or_create(name="Customer Portal", defaults={"description": "Self-service portal acceptance testing.", "created_by": users["manager"]})
        cases = [
            (shop, "Successful checkout with card", "Verify that an authenticated customer can place an order.", "Customer has an item in the cart.", "Order confirmation is displayed and an order is created.", "HIGH", "PASSED"),
            (shop, "Reject expired payment card", "Verify validation for expired cards.", "Customer has an item in the cart.", "A clear payment validation message is shown.", "CRITICAL", "FAILED"),
            (portal, "Update profile details", "Verify saved contact details.", "Tester is signed in.", "Updated details remain after page refresh.", "MEDIUM", "NOT_RUN"),
        ]
        created_cases = []
        for project, title, description, preconditions, expected, priority, status in cases:
            case, made = TestCase.objects.get_or_create(title=title, project=project, defaults={"description": description, "preconditions": preconditions, "expected_result": expected, "priority": priority, "status": status, "assigned_to": users["tester"], "created_by": users["manager"]})
            if made:
                TestStep.objects.bulk_create([TestStep(test_case=case, step_number=1, action="Open the relevant page.", expected_result="The page is available."), TestStep(test_case=case, step_number=2, action="Complete the scenario using valid data.", expected_result=expected)])
            created_cases.append(case)
        TestExecution.objects.get_or_create(test_case=created_cases[0], tester=users["tester"], status="PASSED", defaults={"actual_result": "Order confirmation was displayed.", "comment": "Smoke test passed."})
        TestExecution.objects.get_or_create(test_case=created_cases[1], tester=users["tester"], status="FAILED", defaults={"actual_result": "Expired-card error does not explain how to correct the data.", "comment": "Defect reported."})
        Defect.objects.get_or_create(test_case=created_cases[1], title="Payment validation message is unclear", defaults={"reported_by": users["tester"], "description": "The expired-card message must explain which field should be corrected.", "status": "OPEN"})
        self.stdout.write(self.style.SUCCESS("Demo data is ready. Password for all accounts: DemoPass123!"))
