
import asyncio
import inspect
from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from time import perf_counter
from typing import Any

from .graph import execution_layers, topological_order
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
    attempts: int = 0
    attempt_errors: list[str] = field(default_factory=list)


@dataclass
class RunResult:
    outputs: dict[str, Any] = field(default_factory=dict)
    task_states: dict[str, TaskState] = field(default_factory=dict)
    succeeded: bool = False
    duration: float = 0.0
    errors: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RetryPolicy:
    """Strategia obliczania opóźnienia pomiędzy próbami."""

    strategy: str = "exponential"

    def __post_init__(self) -> None:
        if self.strategy not in {"exponential", "fixed"}:
            raise ValueError(
                "Strategia retry musi mieć wartość "
                "'exponential' albo 'fixed'."
            )

    def get_delay(self, base_delay: float, attempt: int) -> float:
        """Zwraca opóźnienie przed kolejną próbą."""

        if self.strategy == "fixed":
            return base_delay

        return base_delay * (2 ** attempt)


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

    workflow.validate()
    run_started_at = perf_counter()

    result = RunResult(
        task_states={
            name: TaskState()
            for name in workflow.tasks
        }
    )

    first_error: tuple[str, Exception] | None = None

    for task_name in topological_order(workflow):
        task = workflow.tasks[task_name]
        state = result.task_states[task_name]

        dependencies_succeeded = all(
            result.task_states[dependency].status == TaskStatus.SUCCEEDED
            for dependency in task.dependencies
        )

        if not dependencies_succeeded:
            state.status = TaskStatus.SKIPPED
            continue

        state.status = TaskStatus.RUNNING
        state.started_at = perf_counter()
        state.attempts = 1

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
            state.attempt_errors.append(str(exc))
            result.errors[task_name] = str(exc)

            if first_error is None:
                first_error = (task_name, exc)

        finally:
            state.finished_at = perf_counter()
            state.duration = state.finished_at - state.started_at

    result.duration = perf_counter() - run_started_at
    result.succeeded = len(result.errors) == 0

    if first_error is not None:
        task_name, original_exception = first_error

        raise TaskExecutionError(
            task_name,
            original_exception,
            result,
        ) from original_exception

    return result


async def _call_task(task: Any, inputs: dict[str, Any]) -> Any:
    """
    Uruchamia funkcję synchroniczną lub asynchroniczną.

    Funkcje synchroniczne są wykonywane poza pętlą zdarzeń.
    Funkcje zwracające obiekty awaitable również są obsługiwane.
    """

    if inspect.iscoroutinefunction(task.function):
        output = task.function(inputs, task.params)
    else:
        output = await asyncio.to_thread(
            task.function,
            inputs,
            task.params,
        )

    if inspect.isawaitable(output):
        output = await output

    return output


async def _execute_async_task(
    task: Any,
    inputs: dict[str, Any],
    state: TaskState,
    semaphore: asyncio.Semaphore,
    base_delay: float,
    retry_policy: RetryPolicy,
) -> Exception | None:
    """Wykonuje zadanie z obsługą retry, timeout i limitu współbieżności."""

    async with semaphore:
        state.status = TaskStatus.RUNNING
        state.started_at = perf_counter()

        try:
            for attempt in range(task.retries + 1):
                state.attempts = attempt + 1

                try:
                    call = _call_task(task, inputs)

                    if task.timeout is None:
                        output = await call
                    else:
                        output = await asyncio.wait_for(
                            call,
                            timeout=task.timeout,
                        )

                    state.output = output
                    state.error = None
                    state.status = TaskStatus.SUCCEEDED
                    return None

                except asyncio.CancelledError:
                    raise

                except asyncio.TimeoutError:
                    exc = TimeoutError(
                        f"Przekroczono timeout {task.timeout} s."
                    )
                    state.attempt_errors.append(str(exc))
                    state.error = str(exc)

                    if attempt >= task.retries:
                        state.status = TaskStatus.FAILED
                        return exc

                except Exception as exc:
                    state.attempt_errors.append(str(exc))
                    state.error = str(exc)

                    if attempt >= task.retries:
                        state.status = TaskStatus.FAILED
                        return exc

                delay = retry_policy.get_delay(base_delay, attempt)

                if delay > 0:
                    await asyncio.sleep(delay)

        finally:
            state.finished_at = perf_counter()
            state.duration = state.finished_at - state.started_at

    return None


async def async_run(
    workflow: Workflow,
    max_concurrency: int = 5,
    base_delay: float = 0.1,
    retry_policy: RetryPolicy | None = None,
) -> RunResult:
    """
    Asynchronicznie wykonuje workflow warstwami.

    Niezależne zadania w jednej warstwie mogą działać równolegle.
    Liczba aktywnych zadań jest ograniczona semaforem.
    Kolejna warstwa rozpoczyna się po zakończeniu poprzedniej.
    """

    workflow.validate()

    if (
        isinstance(max_concurrency, bool)
        or not isinstance(max_concurrency, int)
        or max_concurrency < 1
    ):
        raise ValueError("max_concurrency musi być liczbą całkowitą >= 1.")

    if (
        isinstance(base_delay, bool)
        or not isinstance(base_delay, (int, float))
        or not isfinite(base_delay)
        or base_delay < 0
    ):
        raise ValueError("base_delay musi być nieujemną, skończoną liczbą.")

    if retry_policy is None:
        retry_policy = RetryPolicy()

    if not isinstance(retry_policy, RetryPolicy):
        raise TypeError("retry_policy musi być obiektem RetryPolicy.")

    run_started_at = perf_counter()

    result = RunResult(
        task_states={
            name: TaskState()
            for name in workflow.tasks
        }
    )

    semaphore = asyncio.Semaphore(max_concurrency)
    first_error: tuple[str, Exception] | None = None

    for layer in execution_layers(workflow):
        ready_tasks = [
            name
            for name in layer
            if all(
                result.task_states[dependency].status == TaskStatus.SUCCEEDED
                for dependency in workflow.tasks[name].dependencies
            )
        ]

        for name in layer:
            if name not in ready_tasks:
                result.task_states[name].status = TaskStatus.SKIPPED

        async def execute(name: str) -> tuple[str, Exception | None]:
            task = workflow.tasks[name]

            inputs = {
                dependency: result.outputs[dependency]
                for dependency in task.dependencies
            }

            error = await _execute_async_task(
                task,
                inputs,
                result.task_states[name],
                semaphore,
                float(base_delay),
                retry_policy,
            )

            return name, error

        outcomes = await asyncio.gather(
            *(execute(name) for name in ready_tasks)
        )

        for name, error in outcomes:
            if error is not None:
                result.errors[name] = str(error)

                if first_error is None:
                    first_error = (name, error)
            else:
                result.outputs[name] = result.task_states[name].output

    result.duration = perf_counter() - run_started_at
    result.succeeded = len(result.errors) == 0

    if first_error is not None:
        task_name, original_exception = first_error

        raise TaskExecutionError(
            task_name,
            original_exception,
            result,
        ) from original_exception

    return result
