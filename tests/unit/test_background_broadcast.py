"""POST /radionics/broadcast no longer blocks the event loop (spec contract W2-3).

The scalar loop runs on the broadcast worker pool as a ``broadcast`` ledger
operation; the request returns straight away. Cancelling stops the loop at its
next tick (``cancelled``, measured elapsed); completion records the full
response the synchronous route used to return; shutdown ends runs
``interrupted``. No audio hardware: the crystal service is absent and the
scalar generator is a fake.
"""

import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import core.integrated_scalar_radionics as scalar_mod
from backend.app.api.v1.endpoints import operations as operations_endpoint
from backend.app.api.v1.endpoints import radionics as radionics_endpoint
from core import operations

BROADCAST = {"intention": "healing", "target_names": ["all beings"], "duration_minutes": 1, "rate_values": [42, 60, 77]}


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    db = tmp_path / "ops.db"
    monkeypatch.setattr(operations, "get_db_path", lambda: str(db))
    monkeypatch.setattr(operations, "_cancel_handlers", {})
    monkeypatch.setattr(operations, "_op_cancellers", {})
    monkeypatch.setattr(scalar_mod, "TICK_PAUSE_SECONDS", 0.005)
    yield db
    scalar_mod.shutdown_broadcasts(timeout=2.0)  # never leak a worker into other tests


@pytest.fixture
def radionics_service(monkeypatch):
    """A real RadionicsService with no DBs, no crystal audio and a fake scalar generator."""
    monkeypatch.setattr(scalar_mod, "HAS_SCALAR", False)
    monkeypatch.setattr(scalar_mod, "HAS_BLESSINGS", False)
    monkeypatch.setattr(scalar_mod, "HAS_ANATOMY", False)
    from container import container
    from modules.radionics import RadionicsService

    service = RadionicsService(event_bus=None, crystal_service=None)
    gen = MagicMock()
    gen.generate_hybrid_stream.side_effect = lambda n: [0.5] * n
    gen.thermal.state.temperature = 40.0
    service.broadcaster.scalar_gen = gen
    monkeypatch.setattr(container, "_radionics", service)
    monkeypatch.setattr(radionics_endpoint.orchestrator_bridge, "create_session", AsyncMock(return_value="session-1"))
    return service


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(radionics_endpoint.router, prefix="/api/v1/radionics")
    app.include_router(operations_endpoint.router, prefix="/api/v1")
    return TestClient(app)


def _wait_for(op_id: str, statuses: set[str], timeout: float = 5.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        op = operations.get_operation(op_id)
        if op is not None and op["status"] in statuses:
            return op
        time.sleep(0.01)
    raise AssertionError(f"operation {op_id} never reached {statuses}: {operations.get_operation(op_id)}")


def test_broadcast_returns_immediately_with_the_operation_id(client, radionics_service):
    start = time.monotonic()
    response = client.post("/api/v1/radionics/broadcast", json=BROADCAST)
    took = time.monotonic() - start

    assert response.status_code == 200
    assert took < 5.0, "the request must not wait out the 60 s broadcast"
    body = response.json()
    # Same fields as before; run-only ones are null until the operation ends.
    assert set(body) >= set(radionics_endpoint.BroadcastResponse.model_fields)
    assert body["status"] == "started"
    assert body["session_id"] == "session-1"
    assert body["duration_seconds"] == 60
    assert body["operation_id"]
    assert body["scalar_output"] is None and body["crystal_output"] is None and body["frequencies"] is None

    op = _wait_for(body["operation_id"], {"running"})
    assert op["kind"] == "broadcast"
    assert op["params"]["duration_seconds"] == 60
    assert op["params"]["rate_values"] == [42, 60, 77]
    assert body["operation_id"] in scalar_mod.active_broadcasts()


def test_cancel_stops_the_loop_and_records_cancelled_with_elapsed(client, radionics_service):
    op_id = client.post("/api/v1/radionics/broadcast", json=BROADCAST).json()["operation_id"]
    _wait_for(op_id, {"running"})
    time.sleep(0.1)

    response = client.post(f"/api/v1/operations/{op_id}/cancel")

    assert response.status_code == 200
    op = response.json()["operation"]
    assert op["status"] == "cancelled"
    assert 0.1 <= op["elapsed_seconds"] < 5.0  # measured, not the requested 60 s
    assert op["result"]["status"] == "cancelled"
    assert op["result"]["scalar_output"]["stopped"] == "cancelled"
    assert op["result"]["scalar_output"]["values_generated"] > 0
    assert op_id not in scalar_mod.active_broadcasts()
    # Finished now: a second cancel is a conflict.
    assert client.post(f"/api/v1/operations/{op_id}/cancel").status_code == 409


def test_completion_records_success_with_the_old_response_fields(client, radionics_service, monkeypatch):
    # Each read of the loop clock advances 7 s: the 60 s broadcast runs ~9 ticks.
    fake_now = [0.0]

    def clock():
        fake_now[0] += 7.0
        return fake_now[0]

    monkeypatch.setattr(scalar_mod, "_clock", clock)
    body = client.post("/api/v1/radionics/broadcast", json=BROADCAST).json()

    op = _wait_for(body["operation_id"], {"success", "error", "cancelled", "interrupted"})

    assert op["status"] == "success", op
    result = op["result"]
    assert set(result) >= set(radionics_endpoint.BroadcastResponse.model_fields)
    assert result["status"] == "success"
    assert result["operation_id"] == body["operation_id"]
    assert result["session_id"] == "session-1"
    assert result["frequencies"] and result["solfeggio_names"]
    assert result["scalar_output"]["values_generated"] > 0
    assert result["scalar_output"]["stopped"] is None


def test_scalar_failure_records_error_and_keeps_the_partial_result(client, radionics_service):
    radionics_service.broadcaster.scalar_gen.generate_hybrid_stream.side_effect = RuntimeError("generator exploded")
    body = client.post("/api/v1/radionics/broadcast", json=BROADCAST).json()

    op = _wait_for(body["operation_id"], {"success", "error"})

    assert op["status"] == "error"
    assert op["error"] == "generator exploded"
    assert op["result"]["scalar_output"]["status"] == "failed"


def test_queued_broadcast_can_be_cancelled_before_it_runs(client, radionics_service, monkeypatch):
    scalar_mod.shutdown_broadcasts(timeout=1.0)  # fresh pool with the patched size
    monkeypatch.setattr(scalar_mod, "MAX_CONCURRENT_BROADCASTS", 1)
    first = client.post("/api/v1/radionics/broadcast", json=BROADCAST).json()["operation_id"]
    _wait_for(first, {"running"})
    second = client.post("/api/v1/radionics/broadcast", json=BROADCAST).json()["operation_id"]
    assert operations.get_operation(second)["status"] == "queued"

    response = client.post(f"/api/v1/operations/{second}/cancel")

    assert response.status_code == 200
    op = response.json()["operation"]
    assert op["status"] == "cancelled"
    assert op["started_at"] is None and op["elapsed_seconds"] is None
    assert client.post(f"/api/v1/operations/{first}/cancel").json()["operation"]["status"] == "cancelled"


def test_shutdown_interrupts_running_broadcasts(client, radionics_service):
    op_id = client.post("/api/v1/radionics/broadcast", json=BROADCAST).json()["operation_id"]
    _wait_for(op_id, {"running"})

    stopped = scalar_mod.shutdown_broadcasts(timeout=5.0)

    assert stopped == 1
    op = operations.get_operation(op_id)
    assert op["status"] == "interrupted"
    assert op["error"] == scalar_mod.SHUTDOWN_REASON
    assert op["elapsed_seconds"] is not None
    assert scalar_mod.active_broadcasts() == []


def test_synchronous_broadcast_is_cancellable_too(radionics_service):
    """Callers that still run broadcast_to_targets inline (CLI, LLM tools) own their op; cancel still works."""
    import threading

    from core.integrated_scalar_radionics import BroadcastConfiguration, IntentionType

    config = BroadcastConfiguration(
        intention=IntentionType.PEACE,
        target_count=1,
        duration_seconds=60,
        scalar_intensity=0.5,
        frequency_hz=None,
        mantra="Om",
    )
    box: dict = {}
    worker = threading.Thread(
        target=lambda: box.update(radionics_service.broadcaster.broadcast_to_targets(config)), daemon=True
    )
    worker.start()
    deadline = time.monotonic() + 5
    while not scalar_mod.active_broadcasts() and time.monotonic() < deadline:
        time.sleep(0.01)
    [op_id] = scalar_mod.active_broadcasts()

    operations.get_cancel_handler(operations.get_operation(op_id))(op_id)
    worker.join(timeout=5)

    assert not worker.is_alive()
    assert box["stopped"] == "cancelled"
    op = operations.get_operation(op_id)
    assert op["status"] == "cancelled"
    assert op["result"]["values_generated"] == box["values_generated"]
