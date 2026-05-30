import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)

@pytest.mark.integration
class TestAudioAPI:
    """Test audio endpoints"""

    def test_get_audio_status(self):
        response = client.get("/api/v1/audio/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "has_audio" in data

    def test_get_audio_presets(self):
        response = client.get("/api/v1/audio/presets")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "heart-chakra" in data["presets"]

    def test_generate_chakra_audio(self):
        # We only request a very short duration for the test to keep it fast
        response = client.post(
            "/api/v1/audio/generate_chakra",
            json={"chakra_name": "heart", "duration": 0.1}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["audio_generated"] is True
        assert data["samples"] > 0

    def test_play_audio(self):
        # Play audio endpoint should work after generation
        response = client.post(
            "/api/v1/audio/play",
            json={"hardware_level": 2}
        )
        # Should succeed because we just generated audio in the previous test
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_stop_audio(self):
        response = client.post("/api/v1/audio/stop")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
