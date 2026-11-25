
from .models import Workflow, WorkflowValidationError


def topological_order(workflow: Workflow) -> list[str]:
    indegree = {
        name: len(task.dependencies)
        for name, task in workflow.tasks.items()
    }
    dependents: dict[str, list[str]] = {
        name: [] for name in workflow.tasks
    }

    for name, task in workflow.tasks.items():
        for dependency in task.dependencies:
            if dependency not in workflow.tasks:
                raise WorkflowValidationError(
                    f"Brak zadania '{dependency}', wymaganego przez '{name}'."
                )
            dependents[dependency].append(name)

    ready = sorted(
        name for name, degree in indegree.items() if degree == 0
    )
    order: list[str] = []

    while ready:
        name = ready.pop(0)
        order.append(name)

        for dependent in sorted(dependents[name]):
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                ready.append(dependent)
                ready.sort()

    if len(order) != len(workflow.tasks):
        raise WorkflowValidationError("Wykryto cykl w grafie zależności.")

    return order


def execution_layers(workflow: Workflow) -> list[list[str]]:
    remaining = set(workflow.tasks)
    completed: set[str] = set()
    layers: list[list[str]] = []

    while remaining:
        layer = sorted(
            name for name in remaining
            if workflow.tasks[name].dependencies <= completed
        )

        if not layer:
            raise WorkflowValidationError(
                "Nie można wyznaczyć warstw: cykl lub brakujące zależności."
            )

        layers.append(layer)
        completed.update(layer)
        remaining.difference_update(layer)

    return layers
