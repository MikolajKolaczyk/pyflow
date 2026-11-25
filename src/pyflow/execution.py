
from dataclasses import dataclass, field
from enum import Enum
from time import perf_counter
from typing import Any

from .graph import topological_order
from .models import Workflow


class TaskStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass
class TaskState:
    status: TaskStatus = TaskStatus.PENDING
    output: Any = None
    started_at: float | None = None
    finished_at: float | None = None
    duration: float = 0.0
    error: str | None = None


@dataclass
class RunResult:
    outputs: dict[str, Any] = field(default_factory=dict)
    task_states: dict[str, TaskState] = field(default_factory=dict)
    succeeded: bool = False
    duration: float = 0.0
    errors: dict[str, str] = field(default_factory=dict)


class TaskExecutionError(RuntimeError):
    """Błąd wykonania zadania w workflow."""

    def __init__(
        self,
        task_name: str,
        original_exception: Exception,
        result: RunResult,
    ) -> None:
        self.task_name = task_name
        self.original_exception = original_exception
        self.result = result

        super().__init__(
            f"Zadanie '{task_name}' zakończyło się błędem: "
            f"{original_exception}"
        )


def run(workflow: Workflow) -> RunResult:
    """Synchronicznie wykonuje zadania workflow w kolejności topologicznej."""

    # Najpierw sprawdzamy poprawność całego workflow.
    workflow.validate()

    run_started_at = perf_counter()

    result = RunResult(
        task_states={
            name: TaskState()
            for name in workflow.tasks
        }
    )

    first_error: tuple[str, Exception] | None = None

    # Wykonujemy zadania zgodnie z planem z Laboratorium 1.
    for task_name in topological_order(workflow):
        task = workflow.tasks[task_name]
        state = result.task_states[task_name]

        # Pomijamy zadanie, jeśli któraś z jego zależności nie powiodła się.
        dependencies_succeeded = all(
            result.task_states[dependency].status == TaskStatus.SUCCEEDED
            for dependency in task.dependencies
        )

        if not dependencies_succeeded:
            state.status = TaskStatus.SKIPPED
            continue

        state.status = TaskStatus.RUNNING
        state.started_at = perf_counter()

        # Przekazujemy wyłącznie wyniki bezpośrednich zależności.
        inputs = {
            dependency: result.outputs[dependency]
            for dependency in task.dependencies
        }

        try:
            output = task.function(inputs, task.params)

            result.outputs[task_name] = output
            state.output = output
            state.status = TaskStatus.SUCCEEDED

        except Exception as exc:
            state.status = TaskStatus.FAILED
            state.error = str(exc)
            result.errors[task_name] = str(exc)

            if first_error is None:
                first_error = (task_name, exc)

        finally:
            state.finished_at = perf_counter()
            state.duration = state.finished_at - state.started_at

    result.duration = perf_counter() - run_started_at
    result.succeeded = len(result.errors) == 0

    # Zachowujemy oryginalny wyjątek jako przyczynę.
    if first_error is not None:
        task_name, original_exception = first_error

        raise TaskExecutionError(
            task_name,
            original_exception,
            result,
        ) from original_exception

    return result
