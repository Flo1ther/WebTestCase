from datetime import timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncDay
from django.utils import timezone

from apps.defects.models import Defect
from apps.executions.models import TestExecution
from apps.projects.models import Project
from apps.test_cases.models import TestCase


class AnalyticsService:
    """Database-backed analytical aggregates scoped to the requesting user's visibility."""

    def __init__(self, user, filters):
        self.user = user
        self.filters = filters

    def cases(self):
        qs = TestCase.objects.all() if self.user.role in {"ADMIN", "MANAGER"} else TestCase.objects.filter(assigned_to=self.user)
        if project_id := self.filters.get("project_id"):
            qs = qs.filter(project_id=project_id)
        if tester_id := self.filters.get("tester_id"):
            qs = qs.filter(assigned_to_id=tester_id)
        if status := self.filters.get("status"):
            qs = qs.filter(status=status)
        return qs

    def executions(self):
        qs = TestExecution.objects.filter(test_case__in=self.cases())
        if self.user.role == "TESTER":
            qs = qs.filter(tester=self.user)
        if start := self.filters.get("date_from"):
            qs = qs.filter(executed_at__date__gte=start)
        if end := self.filters.get("date_to"):
            qs = qs.filter(executed_at__date__lte=end)
        if tester_id := self.filters.get("tester_id"):
            qs = qs.filter(tester_id=tester_id)
        if status := self.filters.get("status"):
            qs = qs.filter(status=status)
        return qs

    def overview(self):
        cases, executions = self.cases(), self.executions()
        execution_counts = executions.aggregate(
            total_executions=Count("id"), passed=Count("id", filter=Q(status="PASSED")),
            failed=Count("id", filter=Q(status="FAILED")), blocked=Count("id", filter=Q(status="BLOCKED")),
            not_run=Count("id", filter=Q(status="NOT_RUN")),
        )
        total_cases = cases.count()
        completed_cases = cases.filter(executions__status__in=["PASSED", "FAILED", "BLOCKED"]).distinct().count()
        decisive = (execution_counts["passed"] or 0) + (execution_counts["failed"] or 0)
        passed, failed = execution_counts["passed"] or 0, execution_counts["failed"] or 0
        return {
            "total_test_cases": total_cases, **{key: value or 0 for key, value in execution_counts.items()},
            "pass_rate": round(passed / decisive * 100, 1) if decisive else 0,
            "failure_rate": round(failed / decisive * 100, 1) if decisive else 0,
            "execution_coverage": round(completed_cases / total_cases * 100, 1) if total_cases else 0,
            "open_defects": Defect.objects.filter(test_case__in=cases, status__in=["OPEN", "IN_PROGRESS"]).count(),
        }

    def execution_trends(self):
        return list(self.executions().annotate(day=TruncDay("executed_at")).values("day").annotate(
            total=Count("id"), passed=Count("id", filter=Q(status="PASSED")), failed=Count("id", filter=Q(status="FAILED")),
            blocked=Count("id", filter=Q(status="BLOCKED")), not_run=Count("id", filter=Q(status="NOT_RUN")),
        ).order_by("day"))

    def project_comparison(self):
        project_ids = self.cases().values("project_id")
        projects = Project.objects.filter(id__in=project_ids).annotate(
            total_cases=Count("test_cases", filter=Q(test_cases__in=self.cases()), distinct=True),
            completed_cases=Count("test_cases", filter=Q(test_cases__in=self.cases(), test_cases__status__in=["PASSED", "FAILED", "BLOCKED"]), distinct=True),
            failed_cases=Count("test_cases", filter=Q(test_cases__in=self.cases(), test_cases__status="FAILED"), distinct=True),
        ).values("id", "name", "total_cases", "completed_cases", "failed_cases").order_by("name")
        return [{**row, "progress": round(row["completed_cases"] / row["total_cases"] * 100, 1) if row["total_cases"] else 0} for row in projects]

    def defect_trends(self):
        qs = Defect.objects.filter(test_case__in=self.cases())
        if start := self.filters.get("date_from"):
            qs = qs.filter(created_at__date__gte=start)
        if end := self.filters.get("date_to"):
            qs = qs.filter(created_at__date__lte=end)
        return list(qs.annotate(day=TruncDay("created_at")).values("day").annotate(
            total=Count("id"), open=Count("id", filter=Q(status="OPEN")), in_progress=Count("id", filter=Q(status="IN_PROGRESS")), resolved=Count("id", filter=Q(status__in=["RESOLVED", "CLOSED"])),
        ).order_by("day"))

    def tester_performance(self):
        qs = self.executions()
        return list(qs.values("tester_id", "tester__username", "tester__first_name", "tester__last_name").annotate(
            total=Count("id"), passed=Count("id", filter=Q(status="PASSED")), failed=Count("id", filter=Q(status="FAILED")), blocked=Count("id", filter=Q(status="BLOCKED")),
        ).order_by("tester__username"))

    def test_stability(self, history_size=6):
        stale_before = timezone.now() - timedelta(days=30)
        cases = self.cases().prefetch_related("executions").select_related("project")
        result = []
        for case in cases:
            history = list(case.executions.all().order_by("-executed_at")[:history_size])
            statuses = [item.status for item in reversed(history)]
            failures = statuses.count("FAILED")
            blocked = statuses.count("BLOCKED")
            switched_to_failed = any(left == "PASSED" and right == "FAILED" for left, right in zip(statuses, statuses[1:]))
            latest = history[0].executed_at if history else None
            stale = not latest or latest < stale_before
            if (len(statuses) >= 3 and failures / len(statuses) >= 0.5) or switched_to_failed:
                stability, reason = "Unstable", 'Виявлено останні невдалі виконання або перехід від успіху до невдачі.'
            elif stale or blocked >= 2:
                stability, reason = "Needs Attention", 'Тесткейс застарів або неодноразово блокувався.'
            else:
                stability, reason = "Stable", 'В останніх виконаннях не виявлено ознак регресії.'
            result.append({"test_case_id": case.id, "title": case.title, "project": case.project.name, "stability": stability, "reason": reason, "history_size": len(statuses), "latest_execution": latest})
        return result
