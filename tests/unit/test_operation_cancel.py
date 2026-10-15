"""Cancelling operations through the ledger (spec contract W2-3).

``core.operations.register_cancel_handler`` / ``register_op_cancel`` and
``POST /api/v1/operations/{id}/cancel``: 200 ``{"operation"}`` once it has
ended, 404 for an unknown id, 409 when it is finished or nothing can stop it.
"""

import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.v1.endpoints import operations as operations_endpoint
from core import operations


@pytest.fixture(autouse=True)
def isolated_ledger(tmp_path, monkeypatch):
    db = tmp_path / "ops.db"
    monkeypatch.setattr(operations, "get_db_path", lambda: str(db))
    monkeypatch.setattr(operations, "_cancel_handlers", {})
    monkeypatch.setattr(operations, "_op_cancellers", {})
    yield db


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(operations_endpoint.router, prefix="/api/v1")
    return TestClient(app)


def _running(kind: str = "other", title: str = "Work") -> str:
    op = operations.create_operation(kind, title)
    operations.start_operation(op["id"])
    return op["id"]


# ---------------------------------------------------------------------------
# Route matrix
# ---------------------------------------------------------------------------


def test_unknown_operation_is_404(client):
    response = client.post("/api/v1/operations/does-not-exist/cancel")
    assert response.status_code == 404


@pytest.mark.parametrize("finish", ["complete", "fail", "cancel"])
def test_finished_operation_is_409(client, finish):
    op_id = _running()
    operations.register_cancel_handler("other", lambda _id: None)
    {
        "complete": lambda: operations.complete_operation(op_id),
        "fail": lambda: operations.fail_operation(op_id, "boom"),
        "cancel": lambda: operations.cancel_operation(op_id),
    }[finish]()

    response = client.post(f"/api/v1/operations/{op_id}/cancel")

    assert response.status_code == 409
    assert "already" in response.json()["detail"]


def test_kind_without_a_handler_is_409(client):
    op_id = _running("video")

    response = client.post(f"/api/v1/operations/{op_id}/cancel")

    assert response.status_code == 409
    assert "no cancel handler" in response.json()["detail"]
    assert operations.get_operation(op_id)["status"] == "running"


def test_kind_handler_that_records_the_cancel_returns_200(client):
    calls = []

    def handler(op_id):
        calls.append(op_id)
        operations.cancel_operation(op_id)

    operations.register_cancel_handler("other", handler)
    op_id = _running()

    response = client.post(f"/api/v1/operations/{op_id}/cancel")

    assert response.status_code == 200
    op = response.json()["operation"]
    assert op["id"] == op_id and op["status"] == "cancelled"
    assert op["elapsed_seconds"] is not None
    assert calls == [op_id]


def test_async_handler_is_awaited(client):
    async def handler(op_id):
        await asyncio.sleep(0)
        operations.cancel_operation(op_id, result={"stopped_by": "handler"})

    operations.register_cancel_handler("tts", handler)
    op_id = _running("tts")

    response = client.post(f"/api/v1/operations/{op_id}/cancel")

    assert response.status_code == 200
    assert response.json()["operation"]["result"] == {"stopped_by": "handler"}


def test_per_operation_handler_wins_over_the_kind_handler(client):
    operations.register_cancel_handler("other", lambda _id: pytest.fail("kind handler used"))
    op_id = _running()
    operations.register_op_cancel(op_id, operations.cancel_operation)

    response = client.post(f"/api/v1/operations/{op_id}/cancel")

    assert response.status_code == 200
    assert response.json()["operation"]["status"] == "cancelled"


def test_handler_refusal_is_409(client):
    def handler(op_id):
        raise operations.OperationNotCancellable("backend refused")

    operations.register_cancel_handler("other", handler)
    op_id = _running()

    response = client.post(f"/api/v1/operations/{op_id}/cancel")

    assert response.status_code == 409
    assert response.json()["detail"] == "backend refused"


def test_render_wrapper_maps_job_errors_to_404_and_409(client, monkeypatch):
    from backend.app.main import register_cancel_handlers
    from backend.core.services.render import jobs

    register_cancel_handlers()
    op_id = _running("render")

    async def not_found(_op_id):
        raise jobs.JobNotFound(_op_id)

    monkeypatch.setattr(jobs, "cancel_job", not_found)
    assert client.post(f"/api/v1/operations/{op_id}/cancel").status_code == 404

    async def refused(_op_id):
        raise jobs.JobNotCancellable("backend busy")

    monkeypatch.setattr(jobs, "cancel_job", refused)
    response = client.post(f"/api/v1/operations/{op_id}/cancel")
    assert response.status_code == 409
    assert response.json()["detail"] == "backend busy"


def test_queued_operation_can_be_cancelled(client):
    operations.register_cancel_handler("other", operations.cancel_operation)
    op = operations.create_operation("other", "Waiting")

    response = client.post(f"/api/v1/operations/{op['id']}/cancel")

    assert response.status_code == 200
    cancelled = response.json()["operation"]
    assert cancelled["status"] == "cancelled"
    assert cancelled["elapsed_seconds"] is None  # never started


# ---------------------------------------------------------------------------
# No race leaves it running
# ---------------------------------------------------------------------------


async def test_worker_that_stops_on_its_next_tick_records_the_cancel():
    """The handler only signals; the worker records ``cancelled`` a tick later."""
    op_id = _running()
    stop = asyncio.Event()

    async def worker():
        await stop.wait()
        await asyncio.sleep(0.1)  # the rest of the current tick
        operations.cancel_operation(op_id, result={"ticks": 3})

    task = asyncio.create_task(worker())
    operations.register_op_cancel(op_id, lambda _id: stop.set())

    op = await operations.request_cancel(op_id)
    await task

    assert op["status"] == "cancelled"
    assert op["result"] == {"ticks": 3}
    assert op["elapsed_seconds"] >= 0.1


async def test_handler_that_never_settles_is_recorded_cancelled_by_the_route():
    op_id = _running()
    operations.register_op_cancel(op_id, lambda _id: None)  # signals nothing

    op = await operations.request_cancel(op_id, settle_seconds=0.1)

    assert op["status"] == "cancelled"
    assert op["elapsed_seconds"] is not None
    # A worker that ends late finds the operation already closed.
    with pytest.raises(operations.OperationError):
        operations.complete_operation(op_id)


async def test_work_that_finishes_while_the_cancel_is_in_flight_is_409():
    op_id = _running()

    def handler(op_id):
        operations.complete_operation(op_id)  # the work ended on its own just now
        raise operations.OperationError("too late")

    operations.register_op_cancel(op_id, handler)

    with pytest.raises(operations.OperationNotCancellable, match="already success"):
        await operations.request_cancel(op_id)


def test_register_cancel_handler_rejects_unknown_kinds():
    with pytest.raises(operations.OperationError):
        operations.register_cancel_handler("mops", lambda _id: None)


def test_interrupt_operation_records_the_reason_and_elapsed_time():
    op_id = _running()
    op = operations.interrupt_operation(op_id, "server shut down", result={"partial": True})
    assert op["status"] == "interrupted"
    assert op["error"] == "server shut down"
    assert op["result"] == {"partial": True}
    assert op["elapsed_seconds"] is not None


# ---------------------------------------------------------------------------
# Render registers its existing cancel through the ledger
# ---------------------------------------------------------------------------


def test_render_cancel_is_registered_and_reachable_through_the_ledger(client):
    from backend.app.main import register_cancel_handlers

    register_cancel_handlers()
    queued = operations.create_operation("render", "Witness", params={"backend": "comfyui-qwen-image-2.1"})
    assert operations.get_cancel_handler(queued) is not None

    response = client.post(f"/api/v1/operations/{queued['id']}/cancel")

    assert response.status_code == 200
    assert response.json()["operation"]["status"] == "cancelled"
    # Already finished: render's own refusal comes back as 409.
    again = client.post(f"/api/v1/operations/{queued['id']}/cancel")
    assert again.status_code == 409
