
import asyncio

import pytest

from pyflow import (
    RetryPolicy,
    Task,
    Workflow,
    TaskStatus,
    TaskExecutionError,
    async_run,
)


def test_exponential_retry_policy():
    policy = RetryPolicy("exponential")

    assert policy.get_delay(0.1, 0) == pytest.approx(0.1)
    assert policy.get_delay(0.1, 1) == pytest.approx(0.2)
    assert policy.get_delay(0.1, 2) == pytest.approx(0.4)


def test_fixed_retry_policy():
    policy = RetryPolicy("fixed")

    assert policy.get_delay(0.1, 0) == pytest.approx(0.1)
    assert policy.get_delay(0.1, 1) == pytest.approx(0.1)
    assert policy.get_delay(0.1, 2) == pytest.approx(0.1)


def test_invalid_retry_policy_is_rejected():
    with pytest.raises(ValueError):
        RetryPolicy("random")


def test_retry_history_is_recorded_after_success():
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

        result = await async_run(
            workflow,
            base_delay=0,
            retry_policy=RetryPolicy("fixed"),
        )

        state = result.task_states["unstable"]

        assert state.status == TaskStatus.SUCCEEDED
        assert state.attempts == 3
        assert len(state.attempt_errors) == 2
        assert state.error is None
        assert result.outputs["unstable"] == "success"

    asyncio.run(scenario())


def test_retry_exhaustion_preserves_attempt_history():
    async def scenario():
        workflow = Workflow()

        async def failing_task(inputs, params):
            raise ValueError("Permanent error")

        workflow.add_task(
            Task(
                name="failing",
                function=failing_task,
                retries=2,
            )
        )

        with pytest.raises(TaskExecutionError) as error:
            await async_run(
                workflow,
                base_delay=0,
                retry_policy=RetryPolicy("exponential"),
            )

        state = error.value.result.task_states["failing"]

        assert state.status == TaskStatus.FAILED
        assert state.attempts == 3
        assert len(state.attempt_errors) == 3
        assert "Permanent error" in state.error

    asyncio.run(scenario())
