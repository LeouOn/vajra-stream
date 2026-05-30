import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)

@pytest.mark.integration
def test_full_user_workflow():
    """
    Test a complete user journey:
    1. Start an RNG session.
    2. Request a healing chakra audio.
    3. Play the audio.
    4. Stop the RNG session.
    """
    # 1. Start RNG session
    rng_res = client.post(
        "/api/v1/rng-attunement/session/create",
        json={"baseline_tone_arm": 5.0, "sensitivity": 1.0}
    )
    assert rng_res.status_code == 200
    session_id = rng_res.json().get("session_id")
    assert session_id is not None

    # 2. Request chakra audio
    audio_res = client.post(
        "/api/v1/audio/generate_chakra",
        json={"chakra_name": "third_eye", "duration": 1.0}
    )
    assert audio_res.status_code == 200
    assert audio_res.json()["audio_generated"] is True

    # 3. Play audio
    play_res = client.post(
        "/api/v1/audio/play",
        json={"hardware_level": 2}
    )
    assert play_res.status_code == 200

    # 4. Stop RNG session
    stop_res = client.post(f"/api/v1/rng-attunement/session/{session_id}/stop")
    assert stop_res.status_code == 200
    assert stop_res.json()["status"] == "success"
