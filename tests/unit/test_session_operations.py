"""vajra_service sessions and sigil broadcasts are timed ledger operations (spec contract W2-3).

A started session is one ``audio`` operation (``broadcast`` for a sigil
broadcast) from start to its measured end: ``stop_session`` ends it
``success``, the ledger cancel route stops the audio and ends it
``cancelled``, a sigil broadcast ends itself after its duration, and server
shutdown records ``interrupted``. No audio hardware: generation and playback
are replaced by fakes on a service built with ``__new__`` (see
test_vajra_service_stop.py).
"""

import asyncio
import threading
import time

import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.v1.endpoints import operations as operations_endpoint
from backend.app.api.v1.endpoints import sigils as sigils_endpoint
from backend.core.services.vajra_service import SESSION_INTERRUPT_REASON, VajraStreamService
from core import operations


@pytest.fixture(autouse=True)
def isolated_ledger(tmp_path, monkeypatch):
    # vajra_service imports these from the sessions endpoint inside a
    # try/except that leaves them None when it loses the circular-import race
    # (import order in a full run); pin the real classes.
    import backend.core.services.vajra_service as vajra_service_module
    from backend.core.services.session_models import AudioConfig, SessionConfig

    monkeypatch.setattr(vajra_service_module, "AudioConfig", AudioConfig)
    monkeypatch.setattr(vajra_service_module, "SessionConfig", SessionConfig)
    db = tmp_path / "ops.db"
    monkeypatch.setattr(operations, "get_db_path", lambda: str(db))
    monkeypatch.setattr(operations, "_op_cancellers", {})
    yield db


def make_service(tmp_path) -> VajraStreamService:
    svc = VajraStreamService.__new__(VajraStreamService)
    svc.active_sessions = {}
    svc.session_history = []
    svc._history_path = str(tmp_path / "history.json")
    svc.event_bus = None
    svc._broadcast_task = None
    svc._session_timers = {}
    svc._playback_lock = threading.RLock()
    svc._playback_epoch = 0
    svc._playback_pending = 0
    svc._playback_active = 0
    svc.stops = []

    async def generate(_config):
        return np.zeros(16)

    async def broadcast(_audio, *_args, **_kwargs):
        return True

    async def visuals(_audio):
        return {}

    svc.generate_prayer_bowl_audio = generate
    svc.broadcast_audio = broadcast
    svc._generate_visuals = visuals
    svc._start_broadcast_loop = lambda: None
    svc.stop_playback = lambda: svc.stops.append(time.monotonic()) or {"was_playing": True}
    return svc


async def _start(svc, **kwargs) -> tuple[str, str]:
    session_id = await svc.create_session(name="Evening", intention="peace", duration=600, astrology_enabled=False)
    assert await svc.start_session(session_id, **kwargs)
    return session_id, svc.active_sessions[session_id]["operation_id"]


async def test_session_is_one_audio_operation_from_start_to_stop(tmp_path):
    svc = make_service(tmp_path)
    session_id, op_id = await _start(svc)

    op = operations.get_operation(op_id)
    assert op["kind"] == "audio" and op["status"] == "running"
    assert op["title"] == "Session: Evening"
    assert op["params"]["session_id"] == session_id
    assert op["params"]["duration_seconds"] == 600

    await asyncio.sleep(0.05)
    assert await svc.stop_session(session_id)

    op = operations.get_operation(op_id)
    assert op["status"] == "success"
    assert op["elapsed_seconds"] >= 0.05
    assert op["result"]["session_id"] == session_id
    assert operations.get_cancel_handler(op) is None


async def test_starting_a_running_session_again_keeps_one_operation(tmp_path):
    svc = make_service(tmp_path)
    session_id, op_id = await _start(svc)
    assert await svc.start_session(session_id)
    assert svc.active_sessions[session_id]["operation_id"] == op_id
    assert len(operations.list_operations(kind="audio")) == 1


async def test_ledger_cancel_stops_the_audio_and_records_cancelled(tmp_path):
    svc = make_service(tmp_path)
    session_id, op_id = await _start(svc)

    op = await operations.request_cancel(op_id)

    assert op["status"] == "cancelled"
    assert op["elapsed_seconds"] is not None
    assert svc.stops, "the cancel must cut the audio"
    assert session_id not in svc.active_sessions
    assert svc.session_history[-1]["operation_id"] == op_id


async def test_timed_session_ends_itself_with_success(tmp_path):
    svc = make_service(tmp_path)
    session_id, op_id = await _start(svc, operation_kind="broadcast", end_after_seconds=0.1)

    await asyncio.sleep(0.4)

    op = operations.get_operation(op_id)
    assert op["kind"] == "broadcast"
    assert op["status"] == "success"
    assert op["elapsed_seconds"] >= 0.1
    assert session_id not in svc.active_sessions
    assert svc._session_timers == {}


async def test_shutdown_records_running_sessions_interrupted(tmp_path):
    svc = make_service(tmp_path)
    _, op_id = await _start(svc, end_after_seconds=60)

    assert svc.interrupt_session_operations() == 1

    op = operations.get_operation(op_id)
    assert op["status"] == "interrupted"
    assert op["error"] == SESSION_INTERRUPT_REASON
    assert svc._session_timers == {}


async def test_failed_start_records_error(tmp_path):
    svc = make_service(tmp_path)

    async def broken(_config):
        raise RuntimeError("no audio device")

    svc.generate_prayer_bowl_audio = broken
    session_id = await svc.create_session(name="Broken", intention="peace", astrology_enabled=False)

    with pytest.raises(RuntimeError):
        await svc.start_session(session_id)

    [op] = operations.list_operations(kind="audio")
    assert op["status"] == "error"
    assert "no audio device" in op["error"]


def test_sigil_broadcast_is_a_cancellable_broadcast_operation(tmp_path, monkeypatch):
    svc = make_service(tmp_path)
    monkeypatch.setattr(sigils_endpoint, "vajra_service", svc)
    app = FastAPI()
    app.include_router(sigils_endpoint.router, prefix="/api/v1")
    app.include_router(operations_endpoint.router, prefix="/api/v1")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/sigils/broadcast", json={"intention": "May all beings be free", "duration_minutes": 5}
        )
        assert response.status_code == 200
        op_id = response.json()["operation_id"]
        op = operations.get_operation(op_id)
        assert op["kind"] == "broadcast"
        assert op["status"] == "running"
        assert op["title"] == "Sigil broadcast: May all beings be free"
        assert op["params"]["duration_seconds"] == 300

        cancelled = client.post(f"/api/v1/operations/{op_id}/cancel")

    assert cancelled.status_code == 200
    assert cancelled.json()["operation"]["status"] == "cancelled"
    assert svc.stops
    assert svc._session_timers == {}
