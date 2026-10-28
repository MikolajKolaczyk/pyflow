import pytest

from pyflow import (
    Task,
    Workflow,
    WorkflowValidationError,
    topological_order,
    execution_layers,
)


def make_task(name, dependencies=()):
    return Task(
        name=name,
        function=lambda inputs, params: None,
        dependencies=frozenset(dependencies),
    )


def test_empty_workflow():
    workflow = Workflow()
    assert topological_order(workflow) == []
    assert execution_layers(workflow) == []


def test_single_task():
    workflow = Workflow()
    workflow.add_task(make_task("extract"))
    assert topological_order(workflow) == ["extract"]
    assert execution_layers(workflow) == [["extract"]]


def test_chain():
    workflow = Workflow()
    workflow.add_task(make_task("extract"))
    workflow.add_task(make_task("clean", ["extract"]))
    workflow.add_task(make_task("report", ["clean"]))

    assert topological_order(workflow) == ["extract", "clean", "report"]
    assert execution_layers(workflow) == [
        ["extract"], ["clean"], ["report"]
    ]


def test_independent_tasks_are_deterministic():
    workflow = Workflow()
    workflow.add_task(make_task("z_task"))
    workflow.add_task(make_task("a_task"))
    workflow.add_task(make_task("m_task"))

    assert topological_order(workflow) == ["a_task", "m_task", "z_task"]
    assert execution_layers(workflow) == [
        ["a_task", "m_task", "z_task"]
    ]


def test_parallel_layers():
    workflow = Workflow()
    workflow.add_task(make_task("extract"))
    workflow.add_task(make_task("clean_b", ["extract"]))
    workflow.add_task(make_task("clean_a", ["extract"]))
    workflow.add_task(make_task("report", ["clean_a", "clean_b"]))

    assert execution_layers(workflow) == [
        ["extract"], ["clean_a", "clean_b"], ["report"]
    ]


def test_missing_dependency_in_graph():
    workflow = Workflow()
    workflow.add_task(make_task("report", ["missing"]))

    with pytest.raises(WorkflowValidationError):
        topological_order(workflow)


def test_cycle_is_rejected():
    workflow = Workflow()
    workflow.add_task(make_task("a", ["b"]))
    workflow.add_task(make_task("b", ["a"]))

    with pytest.raises(WorkflowValidationError):
        topological_order(workflow)


def test_workflow_validation_rejects_cycle():
    workflow = Workflow()
    workflow.add_task(make_task("a", ["b"]))
    workflow.add_task(make_task("b", ["a"]))

    with pytest.raises(WorkflowValidationError):
        workflow.validate()
