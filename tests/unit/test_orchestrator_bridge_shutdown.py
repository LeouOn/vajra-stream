"""
Wave 1 Task 11 — OrchestratorBridge daemon thread cancellation.

Regression test: ``OrchestratorBridge._on_session_started`` used to spawn a
``threading.Thread(daemon=True)`` for the crystal broadcast that was never
tracked or cancelled. ``bridge.shutdown()`` must now join that thread within
a bounded timeout so the process can exit cleanly.

The test fakes the orchestrator + crystal service so we do not pull in heavy
runtime dependencies. We drive ``_on_session_started`` directly with a
hand-rolled ``SessionStarted`` event and a blocking fake broadcast that
blocks until the shutdown event is set.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import threading
import time
from datetime import datetime
from types import ModuleType, SimpleNamespace
from uuid import uuid4

import pytest

# We load ``orchestrator_bridge.py`` directly from its file path to bypass
# ``backend/core/__init__.py``, which eagerly imports ``services`` and
# triggers a circular import at collection time. The production runtime
# avoids this because ``main.py`` imports many other modules first, but a
# unit test must be able to load this module in isolation.
#
# We also stub ``scripts.unified_orchestrator`` and
# ``backend.websocket.connection_manager`` so the bridge module
# body — which imports ``UnifiedOrchestrator`` at class-definition time —
# does not pull in the rest of the application graph.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Inject stubs before importing the bridge.
if "scripts.unified_orchestrator" not in sys.modules:
    _stub_scripts = ModuleType("scripts.unified_orchestrator")
    _stub_scripts.UnifiedOrchestrator = object  # placeholder, never instantiated here
    sys.modules["scripts.unified_orchestrator"] = _stub_scripts
if "backend.websocket.connection_manager" not in sys.modules:
    _stub_ws = ModuleType("backend.websocket.connection_manager")
    _stub_ws.stable_connection_manager_v2 = object()
    sys.modules["backend.websocket.connection_manager"] = _stub_ws

_BRIDGE_PATH = os.path.join(_REPO_ROOT, "backend", "core", "orchestrator_bridge.py")
_spec = importlib.util.spec_from_file_location("backend.core.orchestrator_bridge", _BRIDGE_PATH)
assert _spec is not None and _spec.loader is not None
ob_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ob_module)
OrchestratorBridge = ob_module.OrchestratorBridge


class _BlockingCrystal:
    """Fake crystal service whose broadcast blocks until released.

    Mirrors the long-running nature of ``crystal.broadcast_intention``
    (real impl runs for ``duration`` seconds) while letting the test
    deterministically verify that ``shutdown()`` interrupts it via the
    ``stop_event`` kwarg.
    """

    def __init__(self) -> None:
        self.broadcast_started = threading.Event()
        self.broadcast_calls: list[dict] = []

    def broadcast_intention(self, *, stop_event=None, **kwargs):  # noqa: ANN001
        self.broadcast_calls.append({"stop_event": stop_event, **kwargs})
        self.broadcast_started.set()
        if stop_event is None:
            return
        while not stop_event.wait(timeout=0.05):
            pass


def _make_session_started() -> object:
    """Build a minimal SessionStarted event without importing the world."""
    from modules.interfaces import SessionStarted

    return SessionStarted(
        timestamp=datetime.now(),
        event_id=str(uuid4()),
        session_id=str(uuid4()),
        name="test-intention",
    )


@pytest.fixture
def fresh_bridge():
    """Return a fresh, isolated OrchestratorBridge (bypassing the singleton).

    Singleton state would otherwise leak between tests / the real app.
    We invoke ``OrchestratorBridge.__new__`` directly with ``_instance``
    cleared so the real initialiser runs and sets up ``_shutdown_event``
    and ``_crystal_thread`` exactly as in production.
    """
    prev_instance = OrchestratorBridge._instance
    OrchestratorBridge._instance = None
    try:
        bridge = OrchestratorBridge()
    finally:
        # Restore the cached singleton so unrelated code paths still see it.
        OrchestratorBridge._instance = prev_instance

    # Reset per-instance state to a clean slate (the previous singleton may
    # already have had a started thread from earlier code paths).
    bridge.orchestrator = None
    bridge.initialized = False
    bridge._crystal_thread = None
    bridge._shutdown_event = threading.Event()

    crystal = _BlockingCrystal()
    fake_orchestrator = SimpleNamespace(
        services={"crystal": crystal},
        event_bus=None,
    )
    bridge.orchestrator = fake_orchestrator
    bridge.initialized = True

    yield bridge, crystal

    # Safety net: never leave a thread running between tests.
    try:
        bridge.shutdown()  # type: ignore[attr-defined]
    except Exception:
        pass


def test_shutdown_joins_crystal_thread_within_2s(fresh_bridge):
    """``bridge.shutdown()`` must join the broadcast thread within 2 s."""
    bridge, crystal = fresh_bridge

    # Spawn the daemon thread via the production code path.
    bridge._on_session_started(_make_session_started())

    # Wait until the broadcast actually starts running in the background
    # thread, otherwise shutdown could race ahead and the test would not
    # exercise the cancellation path at all.
    assert crystal.broadcast_started.wait(timeout=2.0), "Crystal broadcast never started — thread spawn broken"

    # Sanity: the implementation must expose a reference to the thread it
    # spawned, otherwise it cannot join it.
    thread = getattr(bridge, "_crystal_thread", None)
    assert thread is not None, "OrchestratorBridge did not track the spawned crystal thread"
    assert thread.is_alive(), "Test harness: broadcast thread should still be running"

    # The shutdown must (a) exist and (b) join within 2 s. The fake crystal
    # only releases once the bridge's shutdown event is set, so a correct
    # implementation will set the event then join.
    start = time.monotonic()
    bridge.shutdown()
    elapsed = time.monotonic() - start

    assert not thread.is_alive(), f"Crystal broadcast thread still alive after shutdown ({elapsed:.2f}s)"
    assert elapsed < 2.0, f"shutdown() took {elapsed:.2f}s to join the thread — must be < 2s"


def test_shutdown_idempotent(fresh_bridge):
    """Calling shutdown() twice must be safe (no error, fast)."""
    bridge, _ = fresh_bridge

    bridge._on_session_started(_make_session_started())
    bridge.shutdown()
    # Second call must not raise.
    bridge.shutdown()
