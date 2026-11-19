from django.db.models import Count, Q
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from apps.defects.models import Defect
from apps.executions.models import TestExecution
from apps.projects.models import Project
from apps.test_cases.models import TestCase
from apps.requirements.models import Requirement
from apps.executions.models import TestRun


def stats_for(user):
    cases = TestCase.objects.all() if user.role in {"ADMIN", "MANAGER"} else TestCase.objects.filter(assigned_to=user)
    counts = cases.aggregate(total=Count("id"), passed=Count("id", filter=Q(status="PASSED")), failed=Count("id", filter=Q(status="FAILED")), blocked=Count("id", filter=Q(status="BLOCKED")), not_run=Count("id", filter=Q(status="NOT_RUN")))
    total = counts["total"] or 0
    completed = total - (counts["not_run"] or 0)
    return {**counts, "executed": completed, "progress": round((completed / total * 100) if total else 0, 1), "defects": Defect.objects.filter(test_case__in=cases).count(), "projects": Project.objects.count()}


@extend_schema(responses=OpenApiTypes.OBJECT)
class DashboardView(APIView):
    def get(self, request):
        cases = TestCase.objects.all() if request.user.role in {"ADMIN", "MANAGER"} else TestCase.objects.filter(assigned_to=request.user)
        execution_qs = TestExecution.objects.select_related("test_case", "tester")
        if request.user.role == "TESTER": execution_qs = execution_qs.filter(tester=request.user)
        requirements = Requirement.objects.all() if request.user.role in {"ADMIN", "MANAGER"} else Requirement.objects.filter(test_cases__assigned_to=request.user).distinct()
        requirement_total = requirements.count()
        uncovered = requirements.filter(test_cases__isnull=True).count()
        critical_defects = Defect.objects.filter(test_case__in=cases, status__in=[Defect.Status.OPEN, Defect.Status.IN_PROGRESS], test_case__priority="CRITICAL").count()
        runs = TestRun.objects.select_related("project").prefetch_related("test_cases")
        if request.user.role == "TESTER": runs = runs.filter(test_cases__assigned_to=request.user).distinct()
        return Response({"stats": stats_for(request.user), "quality": {"requirements_total": requirement_total, "requirements_covered": requirement_total-uncovered, "requirements_coverage": round((requirement_total-uncovered)*100/requirement_total) if requirement_total else 0, "uncovered_requirements": uncovered, "active_critical_defects": critical_defects}, "recent_runs": [{"id":run.id,"name":run.name,"project":run.project.name,"status":run.status,"total":run.test_cases.count()} for run in runs.order_by("-updated_at")[:5]], "recent_executions": execution_qs.order_by("-executed_at")[:6].values("id", "status", "actual_result", "executed_at", "test_case__title", "tester__username"), "recent_test_cases": cases.select_related("project", "assigned_to").order_by("-created_at")[:6].values("id", "title", "status", "priority", "created_at", "project__name", "assigned_to__username")})


@extend_schema(responses=OpenApiTypes.OBJECT)
class ReportsView(APIView):
    def get(self, request):
        return Response({"stats": stats_for(request.user), "by_priority": list((TestCase.objects.all() if request.user.role in {"ADMIN", "MANAGER"} else TestCase.objects.filter(assigned_to=request.user)).values("priority").annotate(count=Count("id")).order_by("priority"))})
