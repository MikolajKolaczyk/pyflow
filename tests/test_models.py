import pytest

from pyflow import Task, Workflow, WorkflowValidationError


def dummy_function(inputs, params):
    return None


def test_task_creation():
    task = Task(name="extract", function=dummy_function)
    assert task.name == "extract"
    assert task.dependencies == frozenset()
    assert task.params == {}


def test_task_rejects_empty_name():
    with pytest.raises(WorkflowValidationError):
        Task(name="", function=dummy_function)


def test_task_rejects_self_dependency():
    with pytest.raises(WorkflowValidationError):
        Task(
            name="extract",
            function=dummy_function,
            dependencies=frozenset({"extract"}),
        )


def test_workflow_rejects_duplicate_tasks():
    workflow = Workflow()
    task = Task(name="extract", function=dummy_function)
    workflow.add_task(task)

    with pytest.raises(WorkflowValidationError):
        workflow.add_task(task)


def test_workflow_rejects_missing_dependency():
    workflow = Workflow()
    workflow.add_task(
        Task(
            name="report",
            function=dummy_function,
            dependencies=frozenset({"extract"}),
        )
    )

    with pytest.raises(WorkflowValidationError):
        workflow.validate()
