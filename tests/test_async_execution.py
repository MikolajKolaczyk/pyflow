
import asyncio
import time

import pytest

from pyflow import (
    Task,
    Workflow,
    TaskStatus,
    TaskExecutionError,
    async_run,
)


def test_async_and_sync_tasks():
    async def scenario():
        workflow = Workflow()

        workflow.add_task(
            Task(
                name="sync",
                function=lambda inputs, params: 10,
            )
        )

        async def async_function(inputs, params):
            await asyncio.sleep(0.01)
            return 20

        workflow.add_task(
            Task(
                name="async",
                function=async_function,
            )
        )

        result = await async_run(workflow)

        assert result.succeeded is True
        assert result.outputs["sync"] == 10
        assert result.outputs["async"] == 20

    asyncio.run(scenario())


def test_max_concurrency_limit():
    async def scenario():
        workflow = Workflow()

        active = 0
        maximum_active = 0
        lock = asyncio.Lock()

        async def task_function(inputs, params):
            nonlocal active, maximum_active

            async with lock:
                active += 1
                maximum_active = max(maximum_active, active)

            await asyncio.sleep(0.03)

            async with lock:
                active -= 1

            return "done"

        for number in range(6):
            workflow.add_task(
                Task(
                    name=f"task_{number}",
                    function=task_function,
                )
            )

        result = await async_run(workflow, max_concurrency=2)

        assert result.succeeded is True
        assert maximum_active == 2

    asyncio.run(scenario())


def test_dependent_layer_starts_after_previous_layer():
    async def scenario():
        workflow = Workflow()
        execution_order = []

        async def first(inputs, params):
            await asyncio.sleep(0.02)
            execution_order.append("first")
            return 10

        async def second(inputs, params):
            execution_order.append("second")
            return inputs["first"] + 5

        workflow.add_task(Task(name="first", function=first))
        workflow.add_task(
            Task(
                name="second",
                function=second,
                dependencies=frozenset({"first"}),
            )
        )

        result = await async_run(workflow)

        assert result.succeeded is True
        assert execution_order == ["first", "second"]
        assert result.outputs["second"] == 15

    asyncio.run(scenario())


def test_retry_succeeds_after_failure():
    async def scenario():
        workflow = Workflow()
        attempts = 0

        async def unstable_task(inputs, params):
            nonlocal attempts
            attempts += 1

            if attempts < 3:
                raise ValueError("Temporary error")

            return "success"

        workflow.add_task(
            Task(
                name="unstable",
                function=unstable_task,
                retries=2,
            )
        )

        result = await async_run(workflow, base_delay=0)

        assert result.succeeded is True
        assert result.outputs["unstable"] == "success"
        assert result.task_states["unstable"].attempts == 3
        assert result.task_states["unstable"].status == TaskStatus.SUCCEEDED

    asyncio.run(scenario())


def test_retry_exhaustion_marks_task_failed():
    async def scenario():
        workflow = Workflow()
        attempts = 0

        async def failing_task(inputs, params):
            nonlocal attempts
            attempts += 1
            raise ValueError("Permanent error")

        workflow.add_task(
            Task(
                name="failing",
                function=failing_task,
                retries=2,
            )
        )

        with pytest.raises(TaskExecutionError) as error:
            await async_run(workflow, base_delay=0)

        result = error.value.result

        assert attempts == 3
        assert result.task_states["failing"].attempts == 3
        assert result.task_states["failing"].status == TaskStatus.FAILED
        assert "Permanent error" in result.errors["failing"]

    asyncio.run(scenario())


def test_timeout_triggers_retry():
    async def scenario():
        workflow = Workflow()
        attempts = 0

        async def slow_task(inputs, params):
            nonlocal attempts
            attempts += 1

            if attempts == 1:
                await asyncio.sleep(0.1)

            return "success"

        workflow.add_task(
            Task(
                name="slow",
                function=slow_task,
                retries=1,
                timeout=0.02,
            )
        )

        result = await async_run(workflow, base_delay=0)

        assert result.succeeded is True
        assert result.outputs["slow"] == "success"
        assert result.task_states["slow"].attempts == 2

    asyncio.run(scenario())


def test_failed_task_skips_dependent_task():
    async def scenario():
        workflow = Workflow()
        dependent_called = False

        async def failing_task(inputs, params):
            raise ValueError("Task failed")

        async def dependent_task(inputs, params):
            nonlocal dependent_called
            dependent_called = True
            return "done"

        workflow.add_task(
            Task(
                name="first",
                function=failing_task,
            )
        )

        workflow.add_task(
            Task(
                name="second",
                function=dependent_task,
                dependencies=frozenset({"first"}),
            )
        )

        with pytest.raises(TaskExecutionError) as error:
            await async_run(workflow, base_delay=0)

        result = error.value.result

        assert result.task_states["first"].status == TaskStatus.FAILED
        assert result.task_states["second"].status == TaskStatus.SKIPPED
        assert dependent_called is False

    asyncio.run(scenario())


def test_cancellation_is_not_converted_to_failure():
    async def scenario():
        workflow = Workflow()
        started = asyncio.Event()

        async def long_task(inputs, params):
            started.set()
            await asyncio.sleep(10)

        workflow.add_task(
            Task(
                name="long",
                function=long_task,
            )
        )

        running_task = asyncio.create_task(async_run(workflow))

        await started.wait()
        running_task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await running_task

    asyncio.run(scenario())


def test_invalid_max_concurrency_is_rejected():
    async def scenario():
        workflow = Workflow()

        with pytest.raises(ValueError):
            await async_run(workflow, max_concurrency=0)

    asyncio.run(scenario())


def test_sync_function_does_not_block_event_loop():
    async def scenario():
        workflow = Workflow()

        def slow_sync_task(inputs, params):
            time.sleep(0.05)
            return "done"

        workflow.add_task(
            Task(
                name="sync",
                function=slow_sync_task,
            )
        )

        heartbeat = asyncio.Event()

        async def mark_heartbeat():
            await asyncio.sleep(0.005)
            heartbeat.set()

        heartbeat_task = asyncio.create_task(mark_heartbeat())

        result = await async_run(workflow)

        await heartbeat_task

        assert result.succeeded is True
        assert heartbeat.is_set()

    asyncio.run(scenario())
