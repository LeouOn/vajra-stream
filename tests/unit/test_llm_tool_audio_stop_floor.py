"""Unit tests for LLM tool audio playback request-time stop epoch floor.

Verifies that `_audio_play` captures `current_playback_epoch()` at request time
and passes it as `stop_epoch_floor` to `vajra_service.broadcast_audio`, preventing
a race where a Stop landing between tool invocation and async spawn could still
become audible.
"""

import asyncio
import threading
from typing import Any

import numpy as np
import sounddevice

import backend.core.llm_agent.tools as tools
import backend.core.services.vajra_service as vajra_service_module
from backend.core.services.vajra_service import VajraStreamService

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
        """Run the captured worker body synchronously."""
        assert self.target is not None
        self.target()


class FakeSoundDevice:
    """Recorder for play/wait/stop."""

    def __init__(self):
        self.calls: list[tuple] = []

    def play(self, data, samplerate=None, **kwargs):
        self.calls.append(("play", tuple(getattr(data, "shape", ())), samplerate))

    def wait(self):
        self.calls.append(("wait",))

    def stop(self):
        self.calls.append(("stop",))

    def names(self):
        return [call[0] for call in self.calls]


class ControlledSpawner:
    """Controlled spawner that captures coroutines without running them in background."""

    def __init__(self):
        self.coroutines: list[Any] = []

    def spawn(self, coro: Any) -> None:
        self.coroutines.append(coro)

    async def run_all(self):
        for coro in self.coroutines:
            await coro
        self.coroutines.clear()

    def close_all(self):
        for coro in self.coroutines:
            coro.close()
        self.coroutines.clear()


def make_service() -> VajraStreamService:
    """Create a minimal VajraStreamService for playback testing."""
    svc = VajraStreamService.__new__(VajraStreamService)
    svc.current_audio_data = SAMPLES.copy()
    svc.level2_broadcaster = None
    svc.level3_broadcaster = None
    svc._playback_lock = threading.RLock()
    svc._playback_epoch = 0
    svc._playback_pending = 0
    svc._playback_active = 0
    return svc


def test_audio_play_passes_request_time_stop_epoch_floor(monkeypatch):
    """Assert floor passed to broadcast_audio equals current_playback_epoch at request time."""
    spawner = ControlledSpawner()
    monkeypatch.setattr(tools, "_spawn", spawner.spawn)

    recorded_calls = []

    class MockVajraService:
        current_audio_data = SAMPLES

        def current_playback_epoch(self) -> int:
            return 42

        async def broadcast_audio(self, audio_data, hardware_level=2, *, stop_epoch_floor=None):
            recorded_calls.append(
                {
                    "audio_data": audio_data,
                    "hardware_level": hardware_level,
                    "stop_epoch_floor": stop_epoch_floor,
                }
            )
            return True

    monkeypatch.setattr(vajra_service_module, "vajra_service", MockVajraService())

    result = tools._audio_play(hardware_level=3)

    assert result["status"] == "success"
    assert result["hardware_level"] == 3
    assert result["audio_samples"] == len(SAMPLES)
    assert len(spawner.coroutines) == 1

    asyncio.run(spawner.run_all())

    assert len(recorded_calls) == 1
    assert recorded_calls[0]["hardware_level"] == 3
    assert recorded_calls[0]["stop_epoch_floor"] == 42


async def test_audio_play_stop_between_request_and_spawn_blocks_playback(monkeypatch):
    """Simulate a Stop between request and spawn execution: epoch bumped before
    the spawned coroutine runs, asserting via REAL service methods with explicit
    sounddevice fakes that no sd.play occurs."""
    fake_sd = FakeSoundDevice()
    monkeypatch.setattr(sounddevice, "play", fake_sd.play)
    monkeypatch.setattr(sounddevice, "wait", fake_sd.wait)
    monkeypatch.setattr(sounddevice, "stop", fake_sd.stop)
    ControlledThread.last = None
    monkeypatch.setattr(threading, "Thread", ControlledThread)

    spawner = ControlledSpawner()
    monkeypatch.setattr(tools, "_spawn", spawner.spawn)

    svc = make_service()
    monkeypatch.setattr(vajra_service_module, "vajra_service", svc)

    # 1. Request playback via tool
    res = tools._audio_play(hardware_level=2)
    assert res["status"] == "success"
    assert len(spawner.coroutines) == 1
    spawned_coro = spawner.coroutines.pop(0)

    # 2. Stop lands BEFORE the spawned task actually executes
    stop_res = svc.stop_playback()
    assert stop_res["sd_stop_error"] is None
    assert svc.current_playback_epoch() > 0

    # 3. Now the spawned coroutine runs
    await spawned_coro

    # 4. If any worker thread was created, release it
    if ControlledThread.last is not None:
        ControlledThread.last.release()

    # 5. Assert NO sd.play occurred
    assert "play" not in fake_sd.names(), "sd.play called despite Stop before spawn execution"
    assert svc._playback_pending == 0
    assert not svc._playback_active


async def test_audio_play_without_stop_plays_successfully(monkeypatch):
    """Control: when no Stop occurs between request and spawn, playback proceeds."""
    fake_sd = FakeSoundDevice()
    monkeypatch.setattr(sounddevice, "play", fake_sd.play)
    monkeypatch.setattr(sounddevice, "wait", fake_sd.wait)
    monkeypatch.setattr(sounddevice, "stop", fake_sd.stop)
    ControlledThread.last = None
    monkeypatch.setattr(threading, "Thread", ControlledThread)

    spawner = ControlledSpawner()
    monkeypatch.setattr(tools, "_spawn", spawner.spawn)

    svc = make_service()
    monkeypatch.setattr(vajra_service_module, "vajra_service", svc)

    res = tools._audio_play(hardware_level=2)
    assert res["status"] == "success"
    assert len(spawner.coroutines) == 1

    await spawner.run_all()
    assert ControlledThread.last is not None
    ControlledThread.last.release()

    assert "play" in fake_sd.names()


def test_audio_play_no_audio_data_returns_error_dict(monkeypatch):
    """Assert existing error path returns identical error dict and does not spawn."""
    spawner = ControlledSpawner()
    monkeypatch.setattr(tools, "_spawn", spawner.spawn)

    svc = make_service()
    svc.current_audio_data = None
    monkeypatch.setattr(vajra_service_module, "vajra_service", svc)

    res = tools._audio_play()
    assert res == {"status": "error", "message": "No audio data available. Please generate audio first."}
    assert len(spawner.coroutines) == 0


def test_delegating_tools_benefit_from_stop_epoch_floor(monkeypatch):
    """Verify high-level tools that delegate to _audio_play (e.g. play_chakra_healing_audio)
    inherit the request-time stop floor."""
    spawner = ControlledSpawner()
    monkeypatch.setattr(tools, "_spawn", spawner.spawn)

    recorded_calls = []

    class MockVajraService:
        current_audio_data = SAMPLES

        def current_playback_epoch(self) -> int:
            return 99

        async def generate_chakra_audio(self, chakra_name: str, duration: float = 30.0):
            return SAMPLES

        async def broadcast_audio(self, audio_data, hardware_level=2, *, stop_epoch_floor=None):
            recorded_calls.append(
                {
                    "stop_epoch_floor": stop_epoch_floor,
                }
            )
            return True

    monkeypatch.setattr(vajra_service_module, "vajra_service", MockVajraService())

    res = tools.play_chakra_healing_audio("heart", duration=10.0)
    assert res["status"] == "success"
    assert len(spawner.coroutines) == 1

    asyncio.run(spawner.run_all())

    assert len(recorded_calls) == 1
    assert recorded_calls[0]["stop_epoch_floor"] == 99
