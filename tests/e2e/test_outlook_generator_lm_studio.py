import os

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)

def is_lm_studio_running():
    import requests
    try:
        url = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")
        requests.get(f"{url}/models", timeout=2)
        return True
    except Exception:
        return False

@pytest.mark.skipif(
    not (os.getenv("RUN_LIVE_LLM_TESTS") and is_lm_studio_running()),
    reason="Requires RUN_LIVE_LLM_TESTS env var and LM Studio running"
)
def test_outlook_generate_single_with_lm_studio_default():
    """
    Test that /api/v1/outlook/generate_single works correctly when LM Studio is the default
    model_type and no model is explicitly passed.
    """
    # Override container or set env var to force auto-detect to find LM Studio?
    # is_lm_studio_running already proved it's running, so auto-detect will pick it up
    # on startup if it wasn't overridden. Let's make sure it doesn't return "No LLM initialized"

    payload = {
        "lat": 34.05,
        "lon": -118.24,
        "languages": ["English"],
        "genre": "healing",
        "custom_context": "test initialization",
        "include_astrology": False,
        "include_tarot": False,
        "include_iching": False
    }

    response = client.post("/api/v1/outlook/generate_single", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    narrative = data.get("narrative", "")
    assert "No LLM initialized" not in narrative, "Should not return 'No LLM initialized' when LM studio is running and auto-detected"
    assert len(narrative) > 50, f"Narrative too short: {narrative}"
