"""Router-level tests for POST /audio/stop — fake service, no hardware.

The endpoint imports ``vajra_service`` from its module at request time, so
monkeypatching the module attribute swaps the dependency per test. No real
sounddevice call can happen: the fake service never touches audio.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.core.services.vajra_service as vajra_service_module
from backend.app.api.v1.endpoints.audio import router


class FakeService:
    def __init__(self, result=None, error=None):
        self.stop_calls = 0
        self.result = (
            result if result is not None else {"was_playing": False, "pending_cancelled": 0, "sd_stop_error": None}
        )
        self.error = error
        # /play surface
        self.current_audio_data = [1.0, 2.0, 3.0]
        self.epoch_value = 7
        self.broadcast_calls: list[tuple] = []

    def stop_playback(self):
        self.stop_calls += 1
        if self.error is not None:
            raise self.error
        return dict(self.result)

    def current_playback_epoch(self):
        return self.epoch_value

    async def broadcast_audio(self, audio_data, hardware_level=2, *, stop_epoch_floor=None):
        self.broadcast_calls.append((audio_data, hardware_level, stop_epoch_floor))
        return True


@pytest.fixture
def make_client(monkeypatch):
    def _make(fake: FakeService) -> TestClient:
        monkeypatch.setattr(vajra_service_module, "vajra_service", fake)
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/audio")
        return TestClient(app)

    return _make


def test_stop_delegates_exactly_once(make_client):
    fake = FakeService(result={"was_playing": True, "pending_cancelled": 0, "sd_stop_error": None})
    client = make_client(fake)

    response = client.post("/api/v1/audio/stop")

    assert response.status_code == 200
    assert fake.stop_calls == 1
    body = response.json()
    assert body["status"] == "success"
    assert body["stopped"] is True
    assert body["was_playing"] is True
    assert body["pending_cancelled"] == 0
    assert isinstance(body["message"], str) and body["message"]


def test_stop_reports_nothing_playing(make_client):
    fake = FakeService()  # idle result
    client = make_client(fake)

    response = client.post("/api/v1/audio/stop")

    assert response.status_code == 200
    assert fake.stop_calls == 1
    body = response.json()
    assert body["status"] == "success"
    assert body["stopped"] is False
    assert body["was_playing"] is False
    assert body["pending_cancelled"] == 0
    assert isinstance(body["message"], str) and body["message"]


def test_stop_reports_pending_cancelled(make_client):
    fake = FakeService(result={"was_playing": False, "pending_cancelled": 2, "sd_stop_error": None})
    client = make_client(fake)

    response = client.post("/api/v1/audio/stop")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["stopped"] is True
    assert body["was_playing"] is False
    assert body["pending_cancelled"] == 2


def test_stop_surfaces_sd_error_as_500(make_client):
    fake = FakeService(result={"was_playing": True, "pending_cancelled": 0, "sd_stop_error": "ImportError: no sd"})
    client = make_client(fake)

    response = client.post("/api/v1/audio/stop")

    assert response.status_code == 500
    assert "ImportError" in response.json()["detail"]
    assert fake.stop_calls == 1


def test_stop_service_failure_is_500(make_client):
    fake = FakeService(error=RuntimeError("kaboom"))
    client = make_client(fake)

    response = client.post("/api/v1/audio/stop")

    assert response.status_code == 500
    assert "kaboom" in response.json()["detail"]
    assert fake.stop_calls == 1


def test_play_passes_stop_epoch_floor_to_broadcast(make_client):
    """The BackgroundTask race fix: /play must capture the playback epoch at
    REQUEST time and hand it to broadcast_audio as stop_epoch_floor, so a
    Stop landing before the background task runs still gates playback off."""
    fake = FakeService()
    client = make_client(fake)

    response = client.post("/api/v1/audio/play", json={"hardware_level": 3})

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    # TestClient runs background tasks after the response; exactly one
    # broadcast, with the epoch captured at request time.
    assert len(fake.broadcast_calls) == 1
    audio_data, hardware_level, stop_epoch_floor = fake.broadcast_calls[0]
    assert audio_data == fake.current_audio_data
    assert hardware_level == 3
    assert stop_epoch_floor == fake.epoch_value
