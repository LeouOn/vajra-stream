"""VajraStreamService.stop_playback and the playback start gate — no hardware.

Every test installs its OWN explicit fakes (monkeypatch on the real
sounddevice module's attributes, which the service's function-local
``import sounddevice as sd`` resolves at call time), so nothing here relies
on tests/conftest.py's blanket sounddevice stub and no real sounddevice
call is ever made.

A controlled thread scheduler (``ControlledThread``) captures the daemon
playback worker instead of running it, so each test decides exactly when a
queued worker is released — including releasing it AFTER stop_playback(),
which is the race the start gate exists for.

The service instances are built with ``__new__`` plus only the state the
playback/stop paths touch: the real ``__init__`` constructs generators and
astrology engines that these tests do not exercise.
"""

import sys
import threading
import time

import numpy as np
import pytest
import sounddevice

import backend.core.services.vajra_service as vajra_service_module
from backend.core.services.vajra_service import VajraStreamService

# Captured at import, before any test patches threading.Thread.
_REAL_THREAD = threading.Thread

SAMPLES = np.linspace(0.0, 1.0, 256, dtype=np.float64)


class ControlledThread:
    """Thread stand-in that captures the worker; tests release it explicitly."""

    last: "ControlledThread | None" = None

    def __init__(self, target=None, args=(), kwargs=None, daemon=None, name=None):
        self.target = target
        self.daemon = False
        self.started = False
        ControlledThread.last = self

    def start(self):
        self.started = True

    def release(self):
        """Run the captured worker body synchronously (the 'scheduler')."""
        assert self.target is not None
        self.target()


class FakeSoundDevice:
    """Recorder for play/wait/stop; wait() parks only when asked to."""

    def __init__(self):
        self.calls: list[tuple] = []
        self._wait_gate = threading.Event()
        self.park_in_wait = False

    def play(self, data, samplerate=None, **kwargs):
        self.calls.append(("play", tuple(getattr(data, "shape", ())), samplerate))

    def wait(self):
        self.calls.append(("wait",))
        if self.park_in_wait:
            self._wait_gate.wait(timeout=5)
        self.calls.append(("wait_done",))

    def stop(self):
        self.calls.append(("stop",))
        self._wait_gate.set()

    def names(self):
        return [call[0] for call in self.calls]


def make_service() -> VajraStreamService:
    """A VajraStreamService with only the playback-control state initialized."""
    svc = VajraStreamService.__new__(VajraStreamService)
    svc.current_audio_data = None
    svc.level2_broadcaster = None
    svc.level3_broadcaster = None
    svc._playback_lock = threading.RLock()
    svc._playback_epoch = 0
    svc._playback_pending = 0
    # int counter post-fix; bool-compatible (truthiness) pre-fix.
    svc._playback_active = 0
    return svc


def _install_fakes(monkeypatch, thread_cls=ControlledThread):
    """Explicit sounddevice recorders + controlled thread scheduler."""
    fake = FakeSoundDevice()
    monkeypatch.setattr(sounddevice, "play", fake.play)
    monkeypatch.setattr(sounddevice, "wait", fake.wait)
    monkeypatch.setattr(sounddevice, "stop", fake.stop)
    ControlledThread.last = None
    monkeypatch.setattr(threading, "Thread", thread_cls)
    return fake


@pytest.fixture
def fake_sd(monkeypatch):
    """Install explicit play/wait/stop recorders on the real sounddevice module."""
    return _install_fakes(monkeypatch)


async def test_stop_when_idle_is_harmless_and_calls_sd_stop(fake_sd):
    svc = make_service()

    result = svc.stop_playback()

    assert fake_sd.names() == ["stop"]
    assert result == {"was_playing": False, "pending_cancelled": 0, "sd_stop_error": None}


async def test_stop_cuts_active_playback_and_reports_was_playing(fake_sd):
    svc = make_service()
    assert await svc.broadcast_audio(SAMPLES)
    worker = ControlledThread.last
    assert worker is not None and worker.started

    # Release the worker in a REAL thread; it parks inside fake sd.wait().
    fake_sd.park_in_wait = True
    runner = _REAL_THREAD(target=worker.release)
    runner.start()
    deadline = time.monotonic() + 5
    while not svc._playback_active and time.monotonic() < deadline:
        time.sleep(0.005)
    assert svc._playback_active, "worker never became active"

    result = svc.stop_playback()

    assert result["was_playing"]
    assert result["pending_cancelled"] == 0
    assert result["sd_stop_error"] is None
    assert "play" in fake_sd.names()
    assert "stop" in fake_sd.names()
    runner.join(timeout=5)
    assert not runner.is_alive()
    assert not svc._playback_active


async def test_repeated_stop_is_safe(fake_sd):
    svc = make_service()
    assert await svc.broadcast_audio(SAMPLES)
    ControlledThread.last.release()  # worker runs to completion (wait passes)

    first = svc.stop_playback()
    second = svc.stop_playback()
    third = svc.stop_playback()

    assert fake_sd.names().count("stop") == 3
    assert first["sd_stop_error"] is None
    assert second["sd_stop_error"] is None
    assert third["sd_stop_error"] is None
    # The released worker finished long before the stops: nothing to report.
    assert second == {"was_playing": False, "pending_cancelled": 0, "sd_stop_error": None}
    assert third == second


async def test_generated_samples_remain_after_stop(fake_sd):
    svc = make_service()
    svc.current_audio_data = SAMPLES.copy()
    assert await svc.broadcast_audio(svc.current_audio_data)
    ControlledThread.last.release()

    svc.stop_playback()

    assert svc.current_audio_data is not None
    assert np.array_equal(svc.current_audio_data, SAMPLES)


async def test_worker_queued_before_stop_never_plays(fake_sd):
    """The race the start gate exists for: worker released AFTER Stop."""
    svc = make_service()
    assert await svc.broadcast_audio(SAMPLES)
    worker = ControlledThread.last
    assert worker is not None
    assert svc._playback_pending == 1  # queued, not yet past the gate

    result = svc.stop_playback()

    assert not result["was_playing"]
    assert result["pending_cancelled"] == 1

    worker.release()  # the scheduler finally runs it — must NOT become audible

    assert "play" not in fake_sd.names()
    assert fake_sd.names() == ["stop"]
    assert svc._playback_pending == 0
    assert not svc._playback_active


async def test_playback_after_stop_still_works(fake_sd):
    """Stop gates only workers queued before it; it is not a permanent mute."""
    svc = make_service()
    svc.stop_playback()

    assert await svc.broadcast_audio(SAMPLES)
    ControlledThread.last.release()

    assert "play" in fake_sd.names()
    assert svc._playback_epoch >= 1


# ---------------------------------------------------------------------------
# F1-FIX regressions (qitem-20261002145611-2f830921) — each was RED against
# the pre-fix service (see /tmp/vajra_red_swap.py red-check procedure).
# ---------------------------------------------------------------------------


async def test_cancelled_worker_does_not_clear_new_active_playback(fake_sd):
    """Bug 1: a worker cancelled at the start gate must not clear the active
    flag/count owned by a LATER worker that is still playing."""
    svc = make_service()
    assert await svc.broadcast_audio(SAMPLES)  # worker A queued
    worker_a = ControlledThread.last
    assert not svc.stop_playback()["was_playing"]  # Stop cancels A
    fake_sd._wait_gate.clear()  # that Stop set the gate; B must be able to park

    assert await svc.broadcast_audio(SAMPLES)  # worker B queued under new epoch
    worker_b = ControlledThread.last
    fake_sd.park_in_wait = True
    runner = _REAL_THREAD(target=worker_b.release)
    runner.start()
    deadline = time.monotonic() + 5
    while not svc._playback_active and time.monotonic() < deadline:
        time.sleep(0.005)
    assert svc._playback_active, "worker B never became active"

    worker_a.release()  # cancelled worker exits while B is still inside sd.wait

    assert svc._playback_active, "cancelled worker cleared another worker's active state"

    result = svc.stop_playback()
    assert result["was_playing"]
    assert result["pending_cancelled"] == 0
    runner.join(timeout=5)
    assert not runner.is_alive()
    assert not svc._playback_active


async def test_conversion_failure_releases_pending(monkeypatch, fake_sd):
    """Bug 2: a MemoryError in the stereo conversion must still release the
    pending count — otherwise idle Stops later report phantom cancellations."""

    def _raise_memory_error(*args, **kwargs):
        raise MemoryError("simulated conversion failure")

    monkeypatch.setattr(np, "column_stack", _raise_memory_error)
    svc = make_service()
    assert await svc.broadcast_audio(SAMPLES)
    assert svc._playback_pending == 1

    ControlledThread.last.release()  # conversion raises inside the worker

    assert svc._playback_pending == 0, "pending stuck after conversion failure"
    assert "play" not in fake_sd.names()
    assert not svc._playback_active

    result = svc.stop_playback()
    assert result["pending_cancelled"] == 0
    assert not result["was_playing"]


class StartFailsThread(ControlledThread):
    """Thread stand-in whose start() fails before any worker can run."""

    def start(self):
        raise RuntimeError("simulated thread start failure")


async def test_thread_start_failure_rolls_back_pending(monkeypatch):
    """Bug 3: a Thread creation/start failure must roll back the pending
    increment — no worker exists to release it."""
    fake = _install_fakes(monkeypatch, StartFailsThread)
    svc = make_service()

    ok = await svc.broadcast_audio(SAMPLES)

    assert ok is False
    assert svc._playback_pending == 0, "pending stuck after thread start failure"

    result = svc.stop_playback()
    assert result["pending_cancelled"] == 0
    assert not result["was_playing"]
    assert fake.names() == ["stop"]


async def test_broadcast_requested_before_stop_is_gated(fake_sd):
    """BackgroundTask race: a Stop landing between the play REQUEST and the
    broadcast spawn must still gate the worker off (stop_epoch_floor)."""
    svc = make_service()
    floor = svc.current_playback_epoch()  # captured at request time
    svc.stop_playback()  # Stop arrives before broadcast_audio runs

    assert await svc.broadcast_audio(SAMPLES, stop_epoch_floor=floor)

    ControlledThread.last.release()
    assert "play" not in fake_sd.names(), "playback became audible despite stop after request"
    assert svc._playback_pending == 0
    assert not svc._playback_active


async def test_broadcast_with_current_floor_still_plays(fake_sd):
    """Control: a floor equal to the current epoch (no Stop since request)
    does not mute playback."""
    svc = make_service()
    floor = svc.current_playback_epoch()

    assert await svc.broadcast_audio(SAMPLES, stop_epoch_floor=floor)

    ControlledThread.last.release()
    assert "play" in fake_sd.names()


async def test_stop_without_sounddevice_reports_error_not_exception(monkeypatch):
    svc = make_service()
    monkeypatch.setitem(sys.modules, "sounddevice", None)

    result = svc.stop_playback()

    assert not result["was_playing"]
    assert "import of sounddevice halted" in str(result["sd_stop_error"])


def test_service_class_exposes_stop_playback():
    assert callable(getattr(VajraStreamService, "stop_playback", None))
    assert callable(getattr(vajra_service_module.vajra_service, "stop_playback", None))
