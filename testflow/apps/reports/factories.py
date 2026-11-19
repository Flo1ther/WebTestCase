"""Factory Method implementations for project-level QA reports."""

from __future__ import annotations

from abc import ABC, abstractmethod

from apps.defects.models import Defect
from apps.executions.models import TestExecution, TestRun
from apps.test_cases.models import TestCase


class ProjectReport(ABC):
    """Product returned by every project-report creator."""

    @abstractmethod
    def generate(self, project, snapshot: dict) -> dict:
        """Build a JSON-safe report payload."""


class QualitySummaryReport(ProjectReport):
    def generate(self, project, snapshot: dict) -> dict:
        return {
            "report_type": "project-quality-summary",
            "generated_for": project.name,
            "summary": snapshot["summary"],
            "coverage": snapshot["coverage"],
            "failed_test_cases": list(
                TestCase.objects.filter(project=project, status=TestCase.Status.FAILED).values(
                    "id", "title", "requirement__key", "updated_at"
                )
            ),
            "open_defects": list(
                Defect.objects.filter(
                    project=project,
                    status__in=[Defect.Status.OPEN, Defect.Status.IN_PROGRESS],
                ).values("id", "title", "severity", "status", "requirement__key", "test_case__title")
            ),
        }


class TraceabilityReport(ProjectReport):
    def generate(self, project, snapshot: dict) -> dict:
        uncovered = [item for item in snapshot["coverage"] if not item["covered"]]
        return {
            "report_type": "project-traceability",
            "generated_for": project.name,
            "summary": {
                "requirements": snapshot["summary"]["requirements"],
                "requirements_covered": snapshot["summary"]["requirements_covered"],
                "requirements_coverage": snapshot["summary"]["requirements_coverage"],
                "uncovered_requirements": len(uncovered),
            },
            "coverage_matrix": snapshot["coverage"],
            "uncovered": uncovered,
        }


class ExecutionProgressReport(ProjectReport):
    def generate(self, project, snapshot: dict) -> dict:
        runs = TestRun.objects.filter(project=project).prefetch_related("test_cases", "executions")
        run_rows = []
        for run in runs:
            total = run.test_cases.count()
            completed = run.executions.exclude(status=TestCase.Status.NOT_RUN).values("test_case_id").distinct().count()
            run_rows.append({
                "id": run.id,
                "name": run.name,
                "status": run.status,
                "total_test_cases": total,
                "completed_test_cases": completed,
                "progress": round(completed * 100 / total) if total else 0,
                "updated_at": run.updated_at,
            })
        return {
            "report_type": "project-execution-progress",
            "generated_for": project.name,
            "summary": {
                "test_runs": snapshot["summary"]["test_runs"],
                "executions": snapshot["summary"]["executions"],
                "progress": snapshot["summary"]["progress"],
                "passed": snapshot["summary"]["passed"],
                "failed": snapshot["summary"]["failed"],
                "blocked": snapshot["summary"]["blocked"],
                "not_run": snapshot["summary"]["not_run"],
            },
            "test_runs": run_rows,
            "recent_executions": list(
                TestExecution.objects.filter(project=project)
                .select_related("test_case", "tester")
                .values("id", "status", "actual_result", "executed_at", "test_case__title", "tester__username")[:20]
            ),
        }


class ProjectReportCreator(ABC):
    """Creator in Factory Method: subclasses choose a concrete report product."""

    @abstractmethod
    def create_report(self) -> ProjectReport:
        """Return the report implementation owned by this creator."""

    def generate_report(self, project, snapshot: dict) -> dict:
        return self.create_report().generate(project, snapshot)


class QualitySummaryReportCreator(ProjectReportCreator):
    def create_report(self) -> ProjectReport:
        return QualitySummaryReport()


class TraceabilityReportCreator(ProjectReportCreator):
    def create_report(self) -> ProjectReport:
        return TraceabilityReport()


class ExecutionProgressReportCreator(ProjectReportCreator):
    def create_report(self) -> ProjectReport:
        return ExecutionProgressReport()


_CREATORS = {
    "quality": QualitySummaryReportCreator,
    "traceability": TraceabilityReportCreator,
    "execution": ExecutionProgressReportCreator,
}


def creator_for(report_type: str) -> ProjectReportCreator:
    """Choose a report creator without exposing concrete report classes to views."""
    try:
        return _CREATORS[report_type]()
    except KeyError as exc:
        choices = ", ".join(_CREATORS)
        raise ValueError(f"Невідомий тип звіту '{report_type}'. Доступні типи: {choices}.") from exc
