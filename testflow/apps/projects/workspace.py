from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.defects.models import Defect
from apps.executions.models import APITest, TestExecution, TestRun
from apps.requirements.models import Requirement
from apps.test_cases.models import TestCase
from apps.reports.factories import creator_for
from .models import Project


def project_for_user(user, project_id):
    """Return a project only when the current role is allowed to see its QA data."""
    projects = Project.objects.all()
    if user.role == "TESTER":
        projects = projects.filter(test_cases__assigned_to=user).distinct()
    return get_object_or_404(projects, pk=project_id)


def project_quality_snapshot(project):
    cases = TestCase.objects.filter(project=project)
    requirements = Requirement.objects.filter(project=project).prefetch_related("primary_test_cases", "test_cases", "api_tests")
    executions = TestExecution.objects.filter(project=project)
    defects = Defect.objects.filter(project=project)
    total_cases = cases.count()
    result_counts = cases.aggregate(
        passed=Count("id", filter=Q(status=TestCase.Status.PASSED)),
        failed=Count("id", filter=Q(status=TestCase.Status.FAILED)),
        blocked=Count("id", filter=Q(status=TestCase.Status.BLOCKED)),
        not_run=Count("id", filter=Q(status=TestCase.Status.NOT_RUN)),
    )
    coverage = []
    for requirement in requirements:
        manual_ids = {case.id for case in requirement.primary_test_cases.all()} | {case.id for case in requirement.test_cases.all()}
        api_count = requirement.api_tests.count()
        coverage.append({
            "id": requirement.id,
            "key": requirement.key,
            "title": requirement.title,
            "status": requirement.status,
            "manual_test_cases": len(manual_ids),
            "api_tests": api_count,
            "covered": bool(manual_ids or api_count),
        })
    covered = sum(1 for item in coverage if item["covered"])
    total_requirements = len(coverage)
    completed = total_cases - result_counts["not_run"]
    return {
        "project": {"id": project.id, "name": project.name, "description": project.description, "ai_context": project.ai_context, "status": project.status},
        "summary": {
            "requirements": total_requirements,
            "requirements_covered": covered,
            "requirements_coverage": round(covered * 100 / total_requirements, 1) if total_requirements else 0,
            "test_cases": total_cases,
            "api_tests": APITest.objects.filter(project=project).count(),
            "test_runs": TestRun.objects.filter(project=project).count(),
            "executions": executions.count(),
            "progress": round(completed * 100 / total_cases, 1) if total_cases else 0,
            "passed": result_counts["passed"], "failed": result_counts["failed"],
            "blocked": result_counts["blocked"], "not_run": result_counts["not_run"],
            "open_defects": defects.filter(status__in=[Defect.Status.OPEN, Defect.Status.IN_PROGRESS]).count(),
        },
        "coverage": coverage,
        "recent_executions": list(executions.select_related("test_case", "tester").values("id", "status", "actual_result", "executed_at", "test_case__id", "test_case__title", "tester__username")[:8]),
        "recent_defects": list(defects.values("id", "title", "status", "severity", "test_case__title", "requirement__key")[:8]),
    }


class ProjectWorkspaceView(APIView):
    def get(self, request, project_id):
        return Response(project_quality_snapshot(project_for_user(request.user, project_id)))


class ProjectAnalyticsView(APIView):
    def get(self, request, project_id):
        project = project_for_user(request.user, project_id)
        snapshot = project_quality_snapshot(project)
        return Response({
            "project": snapshot["project"], "summary": snapshot["summary"], "coverage": snapshot["coverage"],
            "by_priority": list(TestCase.objects.filter(project=project).values("priority").annotate(count=Count("id")).order_by("priority")),
            "by_defect_severity": list(Defect.objects.filter(project=project).values("severity").annotate(count=Count("id")).order_by("severity")),
        })


class ProjectReportView(APIView):
    def get(self, request, project_id):
        project = project_for_user(request.user, project_id)
        snapshot = project_quality_snapshot(project)
        report_type = request.query_params.get("type", "quality")
        try:
            report = creator_for(report_type).generate_report(project, snapshot)
        except ValueError as exc:
            raise ValidationError({"type": str(exc)}) from exc
        return Response(report)


class ProjectAICoverageSummaryView(APIView):
    """Deterministic project summary. It is useful even when the optional LLM is offline."""
    def get(self, request, project_id):
        project = project_for_user(request.user, project_id)
        snapshot = project_quality_snapshot(project)
        uncovered = [item for item in snapshot["coverage"] if not item["covered"]]
        summary = snapshot["summary"]
        parts = [
            f"Проєкт {project.name}: покрито {summary['requirements_covered']} з {summary['requirements']} вимог ({summary['requirements_coverage']}%).",
            f"Ручних тесткейсів: {summary['test_cases']}; API-тестів: {summary['api_tests']}; відкритих дефектів: {summary['open_defects']}.",
        ]
        if uncovered:
            parts.append("Непокриті вимоги: " + ", ".join(item["key"] for item in uncovered) + ".")
        else:
            parts.append("Усі наявні вимоги мають щонайменше один ручний або API-тест.")
        return Response({"project_id": project.id, "provider": "deterministic-project-summary", "summary": " ".join(parts), "coverage": snapshot["coverage"]})
