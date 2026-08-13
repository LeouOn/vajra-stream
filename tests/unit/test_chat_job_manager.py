"""In-memory async chat job store — create, cancel, public view."""

from __future__ import annotations

import asyncio

import pytest

from backend.app.api.v1.chat_job_manager import (
    cancel_job,
    create_job,
    get_job,
    is_cancelled,
    job_public_view,
    register_task,
    update_job,
)


@pytest.mark.unit
def test_create_and_get_job():
    job_id = create_job(connection_id="conn-1")
    job = get_job(job_id)
    assert job is not None
    assert job["status"] == "pending"
    assert job["connection_id"] == "conn-1"
    assert "task" not in job_public_view(job)


@pytest.mark.unit
def test_cancel_unknown_job_returns_false():
    assert cancel_job("chat_does_not_exist") is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cancel_running_job_cancels_task():
    job_id = create_job()

    async def _hang() -> None:
        await asyncio.sleep(30)

    task = asyncio.create_task(_hang())
    register_task(job_id, task)
    update_job(job_id, status="running")

    assert cancel_job(job_id) is True
    assert is_cancelled(job_id) is True
    await asyncio.sleep(0)
    assert task.cancelled() or task.done()


@pytest.mark.unit
def test_cancel_completed_job_is_noop():
    job_id = create_job()
    update_job(job_id, status="completed")
    assert cancel_job(job_id) is True
    assert get_job(job_id)["status"] == "completed"
