from copy import deepcopy
from dataclasses import dataclass, field
from math import isfinite
from typing import Any, Callable, Mapping

TaskFunction = Callable[[Mapping[str, Any], Mapping[str, Any]], Any]


class WorkflowValidationError(ValueError):
    """Błąd niepoprawnej definicji workflow."""


@dataclass(frozen=True)
class Task:
    name: str
    function: TaskFunction
    dependencies: frozenset[str] = field(default_factory=frozenset)
    params: Mapping[str, Any] = field(default_factory=dict)
    description: str = ""
    retries: int = 0
    timeout: float | None = None

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise WorkflowValidationError(
                "Nazwa zadania nie może być pusta."
            )

        object.__setattr__(
            self, "dependencies", frozenset(self.dependencies)
        )
        object.__setattr__(
            self, "params", deepcopy(dict(self.params))
        )

        if self.name in self.dependencies:
            raise WorkflowValidationError(
                f"Zadanie '{self.name}' nie może zależeć od samego siebie."
            )

        if isinstance(self.retries, bool) or not isinstance(self.retries, int):
            raise WorkflowValidationError(
                "Liczba ponowień musi być liczbą całkowitą."
            )

        if self.retries < 0:
            raise WorkflowValidationError(
                "Liczba ponowień nie może być ujemna."
            )

        if self.timeout is not None:
            if (
                isinstance(self.timeout, bool)
                or not isinstance(self.timeout, (int, float))
                or not isfinite(self.timeout)
                or self.timeout <= 0
            ):
                raise WorkflowValidationError(
                    "Timeout musi być dodatnią, skończoną liczbą sekund lub None."
                )


class Workflow:
    def __init__(self) -> None:
        self.tasks: dict[str, Task] = {}

    def add_task(self, task: Task) -> None:
        if task.name in self.tasks:
            raise WorkflowValidationError(
                f"Zadanie '{task.name}' zostało już dodane."
            )

        self.tasks[task.name] = task

    def validate(self) -> None:
        for task in self.tasks.values():
            missing = task.dependencies - self.tasks.keys()

            if missing:
                names = ", ".join(sorted(missing))
                raise WorkflowValidationError(
                    f"Zadanie '{task.name}' ma brakujące zależności: {names}."
                )

        from .graph import topological_order
        topological_order(self)
