"""IR-3b: the bridge is safe to receive the events IR-3 now lets through.

RED-first regression tests for two defects that the now-constructible domain
events expose:

  A. The websocket forwarder put the raw ``datetime`` into the forwarded
     payload, so Starlette's ``send_json`` raised ``TypeError`` inside
     ``json.dumps`` and the connection manager treated it as a per-client
     fault and DISCONNECTED EVERY CLIENT.
  B. ``_on_session_started`` started an hour of real crystal audio on every
     session start, with no opt-in.

No audio, no network, no server: the websocket is a fake that serialises
exactly like Starlette's ``send_json``, and the crystal service is a fake.
"""

from __future__ import annotations

import importlib.util
import json
import os
import threading
from typing import Any

import pytest

from backend.core.orchestrator_bridge import OrchestratorBridge
from modules.interfaces import BroadcastStarted, RNGReadingEvent, SessionStarted

# The connection manager is loaded from its file path, and the bridge's
# reference to it is patched per test, so this file depends on NO global
# module state and on no import order. Another test in this suite
# (test_orchestrator_bridge_shutdown.py) deliberately stubs
# backend.websocket.connection_manager in sys.modules, and a module-level
# import here would pick up that stub depending on which file is imported
# first.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_spec = importlib.util.spec_from_file_location(
    "devb_real_connection_manager", os.path.join(_REPO_ROOT, "backend", "websocket", "connection_manager.py")
)
assert _spec is not None and _spec.loader is not None
_connection_manager = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_connection_manager)

# The real manager implementation, one instance for these tests.
REAL_MANAGER = _connection_manager.stable_connection_manager_v2


class FakeWebSocket:
    """A websocket whose send_json serialises exactly like Starlette's.

    The installed ``WebSocket.send_json`` does ``json.dumps(data,
    separators=(",", ":"), ensure_ascii=False)`` - it does NOT pass
    ``allow_nan=False``. This fake therefore mirrors Starlette's own
    behaviour (default allow_nan=True) so that the test exercises the same
    failure mode. The STRICTER ``allow_nan=False`` check is deliberate
    hygiene in the connection manager, not parity with Starlette: it rejects a
    non-finite float before any client is touched instead of letting one NaN
    reach the wire.
    """

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.accepted = False
        self.sent: list[Any] = []

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, data: Any) -> None:
        text = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        if self.fail:
            raise RuntimeError("socket is gone")
        self.sent.append(json.loads(text))

    async def send_text(self, text: str) -> None:
        self.sent.append(text)


class FakeCrystal:
    """Records what the bridge asks of the crystal service."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def broadcast_intention(self, **kwargs: Any) -> None:
        self.calls.append(kwargs)


@pytest.fixture(autouse=True)
def _clean_connection_manager(monkeypatch: pytest.MonkeyPatch):
    """Give the bridge the real manager for these tests, and keep it clean."""
    import backend.core.orchestrator_bridge as bridge_module

    monkeypatch.setattr(bridge_module, "stable_connection_manager_v2", REAL_MANAGER)
    saved_connections = dict(REAL_MANAGER.active_connections)
    saved_metadata = dict(REAL_MANAGER.connection_metadata)
    REAL_MANAGER.active_connections.clear()
    REAL_MANAGER.connection_metadata.clear()
    try:
        yield
    finally:
        REAL_MANAGER.active_connections.clear()
        REAL_MANAGER.active_connections.update(saved_connections)
        REAL_MANAGER.connection_metadata.clear()
        REAL_MANAGER.connection_metadata.update(saved_metadata)


@pytest.fixture
def bridge(monkeypatch: pytest.MonkeyPatch) -> OrchestratorBridge:
    """A bridge whose orchestrator is a stub; the real one is never started."""
    instance = OrchestratorBridge()
    # The bridge is a singleton: every attribute is restored by monkeypatch, so
    # this fixture cannot leak into another test.
    monkeypatch.setattr(instance, "orchestrator", _StubOrchestrator(), raising=False)
    monkeypatch.setattr(instance, "_crystal_thread", None, raising=False)
    monkeypatch.setattr(instance, "_shutdown_event", threading.Event(), raising=False)
    return instance


class _StubOrchestrator:
    def __init__(self) -> None:
        self.services: dict[str, Any] = {}


async def _connect(websocket: FakeWebSocket) -> str:
    """Connect a client and forget the manager's greeting message.

    ``connect()`` sends a ``connection_status`` message, which is not what
    these tests are about; the fake is cleared so only the messages a test
    causes are counted.
    """
    connection_id = await REAL_MANAGER.connect(websocket)
    websocket.sent.clear()
    return connection_id


# ---------------------------------------------------------------------------
# A. the forwarder must produce JSON-safe payloads
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "event",
    [
        SessionStarted(session_id="s", name="n"),
        BroadcastStarted(session_id="s", hardware_level=0, frequencies=[136.1]),
        RNGReadingEvent(session_id="s", coherence=0.5, entropy=0.5, floating_needle_score=0.5),
    ],
    ids=["SessionStarted", "BroadcastStarted", "RNGReadingEvent"],
)
async def test_forwarder_delivers_one_json_safe_message_per_event(bridge: OrchestratorBridge, event: Any) -> None:
    """Each event reaches the client as exactly one JSON message."""
    websocket = FakeWebSocket()
    await _connect(websocket)

    await bridge._forward_event_to_websocket(event)

    assert len(websocket.sent) == 1, f"expected 1 message, got {websocket.sent}"
    message = websocket.sent[0]
    # The message must be JSON-safe: the fake already proved that by parsing it.
    json.dumps(message, allow_nan=False)
    assert isinstance(message["timestamp"], str), "timestamp must be an ISO string"
    assert isinstance(message["data"], dict)
    assert isinstance(message["data"]["timestamp"], str), "the event timestamp must be an ISO string"


@pytest.mark.asyncio
async def test_forwarding_does_not_disconnect_the_client(bridge: OrchestratorBridge) -> None:
    """The whole point: a forwarded event must not drop the connection."""
    websocket = FakeWebSocket()
    connection_id = await _connect(websocket)

    await bridge._forward_event_to_websocket(SessionStarted(session_id="s", name="n"))

    assert connection_id in REAL_MANAGER.active_connections, "the client was disconnected by a forwarded event"


@pytest.mark.asyncio
async def test_forwarded_message_keys_are_unchanged(bridge: OrchestratorBridge) -> None:
    """REGRESSION GUARD: the message shape stays exactly type/timestamp/data."""
    websocket = FakeWebSocket()
    await _connect(websocket)

    await bridge._forward_event_to_websocket(SessionStarted(session_id="s", name="n"))

    assert set(websocket.sent[0].keys()) == {"type", "timestamp", "data"}


# ---------------------------------------------------------------------------
# A2. the connection manager must not disconnect everyone for a bad payload
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_broadcast_does_not_disconnect_clients_for_a_non_serialisable_message(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A message that cannot be serialised is the caller's fault, not the client's."""
    websocket = FakeWebSocket()
    connection_id = await _connect(websocket)

    with caplog.at_level("ERROR"):
        await REAL_MANAGER.broadcast({"type": "x", "when": object()})

    assert connection_id in REAL_MANAGER.active_connections, "a non-serialisable message must not disconnect anybody"
    assert not websocket.sent
    errors = [r for r in caplog.records if r.levelname == "ERROR"]
    assert len(errors) == 1, f"expected exactly one error, got {[r.getMessage() for r in errors]}"
    assert "x" in errors[0].getMessage(), "the error should name the message type"


@pytest.mark.asyncio
async def test_broadcast_still_disconnects_a_client_whose_send_raises() -> None:
    """A REAL send failure keeps today's behaviour: that client is dropped."""
    good = FakeWebSocket()
    bad = FakeWebSocket(fail=True)
    good_id = await _connect(good)
    bad_id = await _connect(bad)

    await REAL_MANAGER.broadcast({"type": "x", "value": 1})

    assert bad_id not in REAL_MANAGER.active_connections, "a client whose send fails must still be disconnected"
    assert good_id in REAL_MANAGER.active_connections
    assert len(good.sent) == 1


# ---------------------------------------------------------------------------
# B. the crystal broadcast on session start must be opt-in
# ---------------------------------------------------------------------------


def test_session_started_does_not_broadcast_crystal_by_default(
    bridge: OrchestratorBridge, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Default OFF: no crystal audio, and no thread, on a session start."""
    monkeypatch.delenv("VAJRA_BRIDGE_CRYSTAL_ON_SESSION_START", raising=False)
    crystal = FakeCrystal()
    bridge.orchestrator.services["crystal"] = crystal

    bridge._on_session_started(SessionStarted(session_id="s", name="n"))

    assert crystal.calls == [], "a disabled bridge must not start crystal audio"
    assert bridge._crystal_thread is None, "a disabled bridge must not start a thread"


def test_session_started_broadcasts_crystal_when_explicitly_enabled(
    bridge: OrchestratorBridge, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Enabled: the crystal broadcast happens exactly as it did before."""
    monkeypatch.setenv("VAJRA_BRIDGE_CRYSTAL_ON_SESSION_START", "1")
    crystal = FakeCrystal()
    bridge.orchestrator.services["crystal"] = crystal

    bridge._on_session_started(SessionStarted(session_id="s", name="n"))

    thread = bridge._crystal_thread
    assert thread is not None, "an enabled bridge must start the broadcast thread"
    thread.join(timeout=5)
    assert len(crystal.calls) == 1, f"expected one crystal broadcast, got {crystal.calls}"
    call = crystal.calls[0]
    assert call["duration"] == 3600
    assert call["hardware_level"] == 2
    assert call["intention"] == "n"
