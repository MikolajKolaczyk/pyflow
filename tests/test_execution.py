
import pytest

from pyflow import (
    Task,
    Workflow,
    TaskStatus,
    TaskExecutionError,
    run,
)


def test_empty_workflow():
    workflow = Workflow()

    result = run(workflow)

    assert result.outputs == {}
    assert result.task_states == {}
    assert result.succeeded is True
    assert result.duration >= 0


def test_task_execution_and_output_flow():
    workflow = Workflow()

    workflow.add_task(
        Task(
            name="extract",
            function=lambda inputs, params: 10,
        )
    )

    workflow.add_task(
        Task(
            name="report",
            function=lambda inputs, params: inputs["extract"] * 2,
            dependencies=frozenset({"extract"}),
        )
    )

    result = run(workflow)

    assert result.outputs == {
        "extract": 10,
        "report": 20,
    }
    assert result.succeeded is True


def test_execution_order():
    execution_order = []

    def extract(inputs, params):
        execution_order.append("extract")
        return 10

    def clean(inputs, params):
        execution_order.append("clean")
        return inputs["extract"] + 5

    def report(inputs, params):
        execution_order.append("report")
        return inputs["clean"]

    workflow = Workflow()

    workflow.add_task(Task("extract", extract))
    workflow.add_task(
        Task(
            "clean",
            clean,
            dependencies=frozenset({"extract"}),
        )
    )
    workflow.add_task(
        Task(
            "report",
            report,
            dependencies=frozenset({"clean"}),
        )
    )

    run(workflow)

    assert execution_order == ["extract", "clean", "report"]


def test_task_receives_params():
    workflow = Workflow()

    workflow.add_task(
        Task(
            name="calculate",
            function=lambda inputs, params: params["value"] * 3,
            params={"value": 7},
        )
    )

    result = run(workflow)

    assert result.outputs["calculate"] == 21


def test_task_receives_only_direct_dependencies():
    workflow = Workflow()

    workflow.add_task(
        Task(
            name="first",
            function=lambda inputs, params: 10,
        )
    )

    workflow.add_task(
        Task(
            name="second",
            function=lambda inputs, params: inputs["first"] + 5,
            dependencies=frozenset({"first"}),
        )
    )

    workflow.add_task(
        Task(
            name="third",
            function=lambda inputs, params: inputs["second"] * 2,
            dependencies=frozenset({"second"}),
        )
    )

    result = run(workflow)

    assert result.outputs["third"] == 30


def test_successful_task_states_and_times():
    workflow = Workflow()

    workflow.add_task(
        Task(
            name="extract",
            function=lambda inputs, params: "OK",
        )
    )

    result = run(workflow)

    state = result.task_states["extract"]

    assert state.status == TaskStatus.SUCCEEDED
    assert state.output == "OK"
    assert state.started_at is not None
    assert state.finished_at is not None
    assert state.duration >= 0
    assert result.duration >= 0


def test_failed_task_and_error_cause():
    def failing_task(inputs, params):
        raise ValueError("Test error")

    workflow = Workflow()

    workflow.add_task(
        Task(
            name="failing",
            function=failing_task,
        )
    )

    with pytest.raises(TaskExecutionError) as error:
        run(workflow)

    assert error.value.task_name == "failing"
    assert isinstance(error.value.__cause__, ValueError)
    assert str(error.value.__cause__) == "Test error"

    result = error.value.result

    assert result.succeeded is False
    assert result.task_states["failing"].status == TaskStatus.FAILED
    assert "failing" in result.errors


def test_dependent_task_is_skipped():
    def failing_task(inputs, params):
        raise ValueError("Failure")

    workflow = Workflow()

    workflow.add_task(
        Task(
            name="a_fail",
            function=failing_task,
        )
    )

    workflow.add_task(
        Task(
            name="b_dependent",
            function=lambda inputs, params: "Nie powinno się wykonać",
            dependencies=frozenset({"a_fail"}),
        )
    )

    with pytest.raises(TaskExecutionError) as error:
        run(workflow)

    result = error.value.result

    assert result.task_states["a_fail"].status == TaskStatus.FAILED
    assert result.task_states["b_dependent"].status == TaskStatus.SKIPPED
    assert "b_dependent" not in result.outputs


def test_independent_task_runs_after_failure():
    independent_executed = []

    def failing_task(inputs, params):
        raise ValueError("Failure")

    def independent_task(inputs, params):
        independent_executed.append(True)
        return "Independent result"

    workflow = Workflow()

    workflow.add_task(
        Task(
            name="a_fail",
            function=failing_task,
        )
    )

    workflow.add_task(
        Task(
            name="b_dependent",
            function=lambda inputs, params: "Skipped",
            dependencies=frozenset({"a_fail"}),
        )
    )

    workflow.add_task(
        Task(
            name="z_independent",
            function=independent_task,
        )
    )

    with pytest.raises(TaskExecutionError) as error:
        run(workflow)

    result = error.value.result

    assert independent_executed == [True]
    assert result.task_states["z_independent"].status == TaskStatus.SUCCEEDED
    assert result.outputs["z_independent"] == "Independent result"
    assert result.task_states["b_dependent"].status == TaskStatus.SKIPPED
