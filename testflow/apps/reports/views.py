from django.db.models import Count, Q
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.defects.models import Defect
from apps.executions.models import TestExecution
from apps.projects.models import Project
from apps.test_cases.models import TestCase


def stats_for(user):
    cases = TestCase.objects.all() if user.role in {"ADMIN", "MANAGER"} else TestCase.objects.filter(assigned_to=user)
    counts = cases.aggregate(total=Count("id"), passed=Count("id", filter=Q(status="PASSED")), failed=Count("id", filter=Q(status="FAILED")), blocked=Count("id", filter=Q(status="BLOCKED")), not_run=Count("id", filter=Q(status="NOT_RUN")))
    total = counts["total"] or 0
    completed = total - (counts["not_run"] or 0)
    return {**counts, "executed": completed, "progress": round((completed / total * 100) if total else 0, 1), "defects": Defect.objects.filter(test_case__in=cases).count(), "projects": Project.objects.count()}


class DashboardView(APIView):
    def get(self, request):
        cases = TestCase.objects.all() if request.user.role in {"ADMIN", "MANAGER"} else TestCase.objects.filter(assigned_to=request.user)
        execution_qs = TestExecution.objects.select_related("test_case", "tester")
        if request.user.role == "TESTER": execution_qs = execution_qs.filter(tester=request.user)
        return Response({"stats": stats_for(request.user), "recent_executions": execution_qs.order_by("-executed_at")[:6].values("id", "status", "actual_result", "executed_at", "test_case__title", "tester__username"), "recent_test_cases": cases.select_related("project", "assigned_to").order_by("-created_at")[:6].values("id", "title", "status", "priority", "created_at", "project__name", "assigned_to__username")})


class ReportsView(APIView):
    def get(self, request):
        return Response({"stats": stats_for(request.user), "by_priority": list((TestCase.objects.all() if request.user.role in {"ADMIN", "MANAGER"} else TestCase.objects.filter(assigned_to=request.user)).values("priority").annotate(count=Count("id")).order_by("priority"))})
