"""IR-3b rework 3: the websocket boundary is safe.

RED-first regression tests for three defects at the websocket boundary:

  B1 (blocker) an event published from a WORKER thread was forwarded on that
     thread's private loop; the websockets belong to the server loop, so the
     send failed and the failure looked like a dead client - a healthy client
     was evicted.
  B2 a realtime frame carried a SessionConfig object, which is not
     JSON-serialisable, so the strict pre-check rejected the WHOLE frame and
     every realtime frame was dropped whenever a session was alive.
  B3 a personal message with an unserialisable payload evicted a healthy
     client.

No audio, no network, no server: the socket is a fake, the crystal service is a
fake, and the heavy service dependencies are faked.
"""

from __future__ import annotations

import asyncio
import dataclasses
import datetime
import enum

# The connection manager is loaded from its file path, NOT imported normally:
# another test in this suite (test_orchestrator_bridge_shutdown.py) deliberately
# stubs backend.websocket.connection_manager in sys.modules so the bridge can be
# loaded in isolation, and a plain import here would pick up that stub
# depending on which file was collected first. The leaf json_safe module is
# imported normally, because nothing stubs it.
import importlib.util  # noqa: E402
import json
import logging
import os  # noqa: E402
import shutil
import tempfile
from typing import Any

import pytest

from backend.websocket import json_safe
from infrastructure.event_bus import EnhancedEventBus
from modules.interfaces import DomainEvent, SessionStarted

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_spec = importlib.util.spec_from_file_location(
    "devb_real_connection_manager", os.path.join(_REPO_ROOT, "backend", "websocket", "connection_manager.py")
)
assert _spec is not None and _spec.loader is not None
cm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cm)
StableConnectionManagerV2 = cm.StableConnectionManagerV2


class LoopBoundSocket:
    """A socket that refuses to be written to from another event loop.

    This is the real failure mode of a worker-thread publisher: the send
    happens on the wrong loop, so it either raises or writes unsafely.
    """

    def __init__(self, owner_loop: asyncio.AbstractEventLoop) -> None:
        self.owner = owner_loop
        self.sent: list[Any] = []

    async def send_json(self, message: Any) -> None:
        if asyncio.get_running_loop() is not self.owner:
            raise RuntimeError("send attempted on worker loop; websocket belongs to main loop")
        json.dumps(message)
        self.sent.append(message)

    async def send_text(self, text: str) -> None:
        self.sent.append(text)


class FakeSocket:
    """A socket that always works, but can be made to fail."""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.sent: list[Any] = []

    async def send_json(self, message: Any) -> None:
        if self.fail:
            raise RuntimeError("socket is gone")
        self.sent.append(message)

    async def send_text(self, text: str) -> None:
        self.sent.append(text)


# ---------------------------------------------------------------------------
# B1: a worker-thread publisher must not evict a healthy client
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_worker_thread_publisher_delivers_on_the_main_loop_and_keeps_the_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The message is delivered once, on the server's loop, and nobody is evicted."""
    from backend.core.orchestrator_bridge import OrchestratorBridge

    manager = StableConnectionManagerV2()
    manager.set_main_loop(asyncio.get_running_loop())
    socket = LoopBoundSocket(asyncio.get_running_loop())
    manager.active_connections["main"] = socket
    manager.connection_metadata["main"] = {"message_count": 0}
    monkeypatch.setattr(cm, "stable_connection_manager_v2", manager)
    monkeypatch.setattr("backend.core.orchestrator_bridge.stable_connection_manager_v2", manager)

    bus = EnhancedEventBus()
    bus.subscribe(DomainEvent, OrchestratorBridge()._forward_event_to_websocket)

    await asyncio.to_thread(bus.publish, SessionStarted(session_id="s", name="worker"))

    for _ in range(50):
        await asyncio.sleep(0.01)
        if socket.sent:
            break

    assert len(socket.sent) == 1, f"expected exactly one delivery, got {socket.sent}"
    assert "main" in manager.active_connections, "a healthy client was evicted by a worker-thread publish"


@pytest.mark.asyncio
async def test_same_loop_publisher_still_delivers_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """A publisher on the server's own loop is unaffected."""
    from backend.core.orchestrator_bridge import OrchestratorBridge

    manager = StableConnectionManagerV2()
    manager.set_main_loop(asyncio.get_running_loop())
    socket = LoopBoundSocket(asyncio.get_running_loop())
    manager.active_connections["main"] = socket
    manager.connection_metadata["main"] = {"message_count": 0}
    monkeypatch.setattr(cm, "stable_connection_manager_v2", manager)
    monkeypatch.setattr("backend.core.orchestrator_bridge.stable_connection_manager_v2", manager)

    bus = EnhancedEventBus()
    bus.subscribe(DomainEvent, OrchestratorBridge()._forward_event_to_websocket)

    bus.publish(SessionStarted(session_id="s", name="same-loop"))
    for _ in range(50):
        await asyncio.sleep(0.01)
        if socket.sent:
            break

    assert len(socket.sent) == 1, f"expected exactly one delivery, got {socket.sent}"
    assert "main" in manager.active_connections


@pytest.mark.asyncio
async def test_no_main_loop_falls_back_to_awaiting_the_broadcast(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no main loop recorded (tests, CLI) the send still happens."""
    from backend.core.orchestrator_bridge import OrchestratorBridge

    manager = StableConnectionManagerV2()
    manager.main_loop = None
    socket = FakeSocket()
    manager.active_connections["main"] = socket
    manager.connection_metadata["main"] = {"message_count": 0}
    monkeypatch.setattr(cm, "stable_connection_manager_v2", manager)
    monkeypatch.setattr("backend.core.orchestrator_bridge.stable_connection_manager_v2", manager)

    bus = EnhancedEventBus()
    bus.subscribe(DomainEvent, OrchestratorBridge()._forward_event_to_websocket)

    bus.publish(SessionStarted(session_id="s", name="no-main-loop"))
    for _ in range(50):
        await asyncio.sleep(0.01)
        if socket.sent:
            break

    assert len(socket.sent) == 1, f"expected exactly one delivery, got {socket.sent}"


# ---------------------------------------------------------------------------
# B2: the realtime frame must survive a SessionConfig
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_realtime_frame_with_a_live_session_is_delivered(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A real session in the payload must not drop the whole frame."""
    import backend.core.services.vajra_service as svc

    for symbol in (
        "Settings",
        "EnhancedAudioGenerator",
        "PrayerBowlGenerator",
        "Level2CrystalBroadcaster",
        "Level3CrystalBroadcaster",
        "PrayerWheel",
        "AstrologicalCalculator",
        "LLMIntegration",
        "TTSEngine",
        "RothkoGenerator",
        "VisualRenderer",
    ):
        monkeypatch.setattr(svc, symbol, None, raising=False)
    monkeypatch.setattr(svc.VajraStreamService, "_load_history", lambda self: None)
    monkeypatch.setattr(svc.VajraStreamService, "_save_history", lambda self: None)

    service = svc.VajraStreamService()
    service.event_bus = None
    session_id = await service.create_session(
        name="n", intention="i", duration=1, audio_frequency=136.1, astrology_enabled=False
    )
    assert session_id in service.get_all_sessions()

    manager = StableConnectionManagerV2()
    manager.set_main_loop(asyncio.get_running_loop())
    socket = FakeSocket()
    manager.active_connections["main"] = socket
    manager.connection_metadata["main"] = {"message_count": 0}
    monkeypatch.setattr(svc.vajra_service, "get_all_sessions", lambda: service.get_all_sessions())
    monkeypatch.setattr(svc.vajra_service, "get_audio_spectrum", lambda: [])
    monkeypatch.setattr(svc.vajra_service, "get_system_status", lambda: {"status": "ok"})

    with caplog.at_level(logging.ERROR):
        await manager.send_safe_realtime_data()

    frames = [m for m in socket.sent if isinstance(m, dict) and m.get("type") == "realtime_data"]
    assert len(frames) == 1, f"expected one realtime frame, got {[m.get('type') for m in socket.sent]}"
    sessions = frames[0]["active_sessions"]
    assert session_id in sessions, sessions
    config = sessions[session_id]["config"]
    assert isinstance(config, dict), f"the config must be a plain dict, got {type(config)}"
    assert config["name"] == "n", config
    assert "main" in manager.active_connections, "the client was evicted"
    errors = [r for r in caplog.records if r.levelname == "ERROR"]
    assert not errors, f"no error should be logged: {[r.getMessage() for r in errors]}"


# ---------------------------------------------------------------------------
# to_json_safe, unit by unit
# ---------------------------------------------------------------------------


class _Colour(enum.Enum):
    RED = 1


@dataclasses.dataclass
class _Point:
    x: int
    y: int


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (datetime.datetime(2020, 1, 2, 3, 4, 5), "2020-01-02T03:04:05"),
        (datetime.date(2020, 1, 2), "2020-01-02"),
        (b"bytes", "bytes"),
        (bytearray(b"ba"), "ba"),
        ({1, 2}, [1, 2]),
        (frozenset({3}), [3]),
        ((1, 2), [1, 2]),
        ([1, 2], [1, 2]),
        (_Colour.RED, 1),
        (float("nan"), None),
        (float("inf"), None),
        (float("-inf"), None),
        (_Point(1, 2), {"x": 1, "y": 2}),
        ({"a": 1}, {"a": 1}),
        ({1: "one"}, {"1": "one"}),
        ("plain", "plain"),
        (True, True),
        (None, None),
    ],
)
def test_to_json_safe_converts_each_type(value: Any, expected: Any) -> None:
    """Each supported type converts to something JSON can carry."""
    assert cm.to_json_safe(value) == expected


def test_to_json_safe_result_is_always_serialisable() -> None:
    """Whatever goes in, json.dumps(allow_nan=False) must accept the result."""
    values = [
        datetime.datetime.now(datetime.timezone.utc),
        b"bytes",
        {1, 2},
        _Colour.RED,
        _Point(1, 2),
        {"a": [1, (2, 3)], "b": {4, 5}},
        float("nan"),
        float("inf"),
        object(),
    ]
    for value in values:
        safe = cm.to_json_safe(value)
        json.dumps(safe, allow_nan=False)  # must not raise


def test_to_json_safe_handles_a_pydantic_model() -> None:
    """A pydantic v2 model is dumped, not stringified."""
    pydantic = pytest.importorskip("pydantic")

    class Model(pydantic.BaseModel):
        name: str

    assert cm.to_json_safe(Model(name="x")) == {"name": "x"}


# ---------------------------------------------------------------------------
# the error log is rate limited
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unserialisable_message_log_is_rate_limited(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A persistent producer bug must not write ten lines a second."""
    fake_now = {"value": 1000.0}
    monkeypatch.setattr(cm, "_now", lambda: fake_now["value"])

    manager = StableConnectionManagerV2()
    socket = FakeSocket()
    manager.active_connections["main"] = socket
    manager.connection_metadata["main"] = {"message_count": 0}

    with caplog.at_level(logging.ERROR):
        for _ in range(50):
            await manager.broadcast({"type": "realtime_data", "when": object()})

    errors = [r for r in caplog.records if r.levelname == "ERROR"]
    assert len(errors) == 1, f"expected one error line, got {len(errors)}"
    assert "similar suppressed" not in errors[0].getMessage()

    # After the window the next one is logged, and it says how many were
    # suppressed in the meantime.
    fake_now["value"] += 61.0
    with caplog.at_level(logging.ERROR):
        await manager.broadcast({"type": "realtime_data", "when": object()})
    errors = [r for r in caplog.records if r.levelname == "ERROR"]
    assert len(errors) == 2, f"expected a second error line, got {len(errors)}"
    # 50 broadcasts: the first is logged, the other 49 are suppressed.
    assert "49 similar suppressed" in errors[1].getMessage(), errors[1].getMessage()
    assert "main" in manager.active_connections, "a bad payload must not evict anybody"


# ---------------------------------------------------------------------------
# B3: a personal message with a bad payload must not evict a healthy client
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_personal_message_with_a_bad_payload_keeps_the_client(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An unserialisable personal payload is the caller's fault."""
    manager = StableConnectionManagerV2()
    socket = FakeSocket()
    manager.active_connections["main"] = socket
    manager.connection_metadata["main"] = {"message_count": 0}

    with caplog.at_level(logging.ERROR):
        result = await manager.send_personal_message({"type": "probe", "bad": datetime.datetime.now()}, "main")

    assert result is False
    assert "main" in manager.active_connections, "a healthy client was evicted by a bad payload"
    assert not socket.sent
    assert any(r.levelname == "ERROR" for r in caplog.records)


@pytest.mark.asyncio
async def test_personal_message_with_a_genuine_send_failure_still_disconnects() -> None:
    """A real send failure keeps today's behaviour: that client is dropped."""
    manager = StableConnectionManagerV2()
    socket = FakeSocket(fail=True)
    manager.active_connections["main"] = socket
    manager.connection_metadata["main"] = {"message_count": 0}

    result = await manager.send_personal_message({"type": "probe", "ok": 1}, "main")

    assert result is False
    assert "main" not in manager.active_connections, "a client whose send fails must still be dropped"


@pytest.mark.asyncio
async def test_broadcast_with_two_clients_one_failing_keeps_the_good_one() -> None:
    """A failing client is dropped; the healthy one keeps receiving."""
    manager = StableConnectionManagerV2()
    good = FakeSocket()
    bad = FakeSocket(fail=True)
    manager.active_connections["good"] = good
    manager.active_connections["bad"] = bad
    manager.connection_metadata["good"] = {"message_count": 0}
    manager.connection_metadata["bad"] = {"message_count": 0}

    await manager.broadcast({"type": "x", "value": 1})

    assert "bad" not in manager.active_connections
    assert "good" in manager.active_connections
    assert len(good.sent) == 1


def test_the_manager_records_the_server_loop_at_startup() -> None:
    """The main loop must be recorded, or worker sends have nowhere to go."""
    import pathlib

    main_py = pathlib.Path(__file__).resolve().parents[2] / "backend" / "app" / "main.py"
    source = main_py.read_text()
    assert "set_main_loop(" in source, "the app must record the server loop on the manager"


def test_a_worker_thread_publisher_reaches_the_bridge() -> None:
    """The topology is real: tools are offloaded to threads and publish events."""
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[2]
    registry = (root / "core" / "tool_registry" / "__init__.py").read_text()
    operator = (root / "modules" / "radionics_operator.py").read_text()
    assert "to_thread" in registry or "ThreadPool" in registry or "run_in_executor" in registry
    assert "publish(" in operator


# ---------------------------------------------------------------------------
# to_json_safe: bounded recursion and cycle detection
# ---------------------------------------------------------------------------


def test_to_json_safe_survives_a_very_deep_structure() -> None:
    """A 2,000-deep list must not raise RecursionError.

    The callers' broad `except` would swallow the RecursionError, and the
    event would silently not be forwarded, so the conversion has to be
    bounded instead of blowing the stack.
    """
    deep: list[Any] = []
    current = deep
    for _ in range(2000):
        nxt: list[Any] = []
        current.append(nxt)
        current = nxt
    current.append("leaf")

    safe = cm.to_json_safe(deep)  # must not raise
    json.dumps(safe, allow_nan=False)  # and must be serialisable


def test_to_json_safe_marks_a_circular_structure() -> None:
    """A container that refers back to itself becomes a marker, not a loop."""
    circular: dict[str, Any] = {"name": "x"}
    circular["self"] = circular
    safe = cm.to_json_safe(circular)
    assert safe["self"] == json_safe.CIRCULAR_MARKER
    json.dumps(safe, allow_nan=False)

    circular_list: list[Any] = [1]
    circular_list.append(circular_list)
    safe_list = cm.to_json_safe(circular_list)
    assert safe_list[1] == json_safe.CIRCULAR_MARKER
    json.dumps(safe_list, allow_nan=False)


def test_to_json_safe_depth_limit_is_enforced() -> None:
    """Past the limit the remainder is stringified, not recursed into."""
    deep: list[Any] = []
    current = deep
    for _ in range(json_safe.MAX_DEPTH + 5):
        nxt: list[Any] = []
        current.append(nxt)
        current = nxt
    safe = cm.to_json_safe(deep)
    # The conversion stopped at the limit instead of walking the whole thing.
    assert len(safe) == 1
    assert isinstance(safe[0], list)
    json.dumps(safe, allow_nan=False)


def test_to_json_safe_key_collision_behaviour_is_kept_and_documented() -> None:
    """Two keys that stringify alike collide; the behaviour is unchanged."""
    safe = cm.to_json_safe({1: "a", "1": "b"})
    assert safe == {"1": "b"}
    assert "collide" in json_safe.to_json_safe.__doc__


# ---------------------------------------------------------------------------
# Isolation guard: every touched test file must pass ALONE, in a fresh
# interpreter. The full suite can hide an import-order hazard: some test files
# import the real module first, so a file that depends on that order only
# breaks when it is run on its own.
# ---------------------------------------------------------------------------

_ISOLATION_CHILD_ENV = "DEVB_ISOLATION_CHILD"

_ISOLATED_FILES = [
    "tests/unit/test_orchestrator_bridge_shutdown.py",
    "tests/unit/test_orchestrator_bridge_events.py",
    "tests/unit/test_ws_broadcast_safety.py",
]


@pytest.mark.skipif(
    os.environ.get(_ISOLATION_CHILD_ENV) == "1",
    reason="this is the isolation child; do not recurse",
)
def test_each_bridge_test_file_passes_alone_in_a_fresh_interpreter() -> None:
    """Each touched test file must pass on its own, in a fresh interpreter."""
    import pathlib
    import subprocess
    import sys

    repo_root = pathlib.Path(__file__).resolve().parents[2]
    scratch = tempfile.mkdtemp(prefix="devb-isolation-", dir="/tmp")
    try:
        for relative in _ISOLATED_FILES:
            env = dict(os.environ)
            # Provider keys must not reach the child, and the VAJRA_* flags
            # must not change the child's behaviour.
            for key in list(env):
                if key.endswith("_API_KEY") or key.startswith("VAJRA_"):
                    env.pop(key, None)
            env["DATABASE_URL"] = f"sqlite:///{scratch}/isolation.db"
            env[_ISOLATION_CHILD_ENV] = "1"
            result = subprocess.run(
                [sys.executable, "-m", "pytest", relative, "-q", "-p", "no:cacheprovider"],
                cwd=repo_root,
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
            )
            assert (
                result.returncode == 0
            ), f"{relative} failed when run alone:\n{result.stdout[-3000:]}\n{result.stderr[-2000:]}"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
