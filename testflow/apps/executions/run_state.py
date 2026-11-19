"""State pattern for the lifecycle of a TestRun.

The database stores a compact status value, while these classes own the
business rules for allowed transitions.  This keeps views and serializers from
growing into a collection of status-related ``if`` statements.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class TestRunTransitionError(ValueError):
    """Raised when a requested test-run lifecycle transition is not allowed."""


class TestRunState(ABC):
    """Common interface for every persisted TestRun state."""

    code: str

    @abstractmethod
    def start(self, run) -> str:
        """Return the next status for a start command."""

    @abstractmethod
    def complete(self, run) -> str:
        """Return the next status for a complete command."""


class DraftRunState(TestRunState):
    code = "DRAFT"

    def start(self, run) -> str:
        return "ACTIVE"

    def complete(self, run) -> str:
        raise TestRunTransitionError("Чернетку не можна завершити: спочатку запустіть прогін.")


class ActiveRunState(TestRunState):
    code = "ACTIVE"

    def start(self, run) -> str:
        raise TestRunTransitionError("Тестовий прогін уже активний.")

    def complete(self, run) -> str:
        return "COMPLETED"


class CompletedRunState(TestRunState):
    code = "COMPLETED"

    def start(self, run) -> str:
        raise TestRunTransitionError("Завершений прогін не можна запустити повторно. Створіть новий прогін.")

    def complete(self, run) -> str:
        raise TestRunTransitionError("Тестовий прогін уже завершений.")


_STATES = {
    DraftRunState.code: DraftRunState,
    ActiveRunState.code: ActiveRunState,
    CompletedRunState.code: CompletedRunState,
}


def state_for(status: str) -> TestRunState:
    """Restore the appropriate state object from the status persisted in PostgreSQL."""
    try:
        return _STATES[status]()
    except KeyError as exc:
        raise TestRunTransitionError(f"Невідомий стан тестового прогону: {status}.") from exc


class TestRunWorkflow:
    """Context object of the State pattern used by API command handlers."""

    @classmethod
    def transition(cls, run, command: str) -> str:
        state = state_for(run.status)
        try:
            handler = getattr(state, command)
        except AttributeError as exc:
            raise TestRunTransitionError(f"Невідома команда життєвого циклу: {command}.") from exc
        next_status = handler(run)
        run.status = next_status
        return next_status
