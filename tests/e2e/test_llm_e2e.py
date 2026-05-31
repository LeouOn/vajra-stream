import os

import pytest
from fastapi.testclient import TestClient

# DO NOT import sys and mock things. We want the real app to boot, though it might fail if hardware missing.
# We will just patch hardware at the start if necessary so the app boots, but NEVER mock LLMs.
from backend.app.main import app

client = TestClient(app)

@pytest.mark.skipif(
    not os.getenv("RUN_LIVE_LLM_TESTS") or not os.getenv("DEEPSEEK_API_KEY"),
    reason="Requires valid DEEPSEEK_API_KEY and RUN_LIVE_LLM_TESTS env var"
)
def test_live_deepseek_api():
    """
    Sends a LIVE request to the DeepSeek API through the backend router.
    WARNING: This test costs API credits.
    """
    payload = {
        "messages": [{"role": "user", "content": "Reply with exactly the word 'SUCCESS' and nothing else. Do not use any tools."}],
        "provider": "deepseek",
        "model": "deepseek-chat"
    }

    response = client.post("/api/v1/llm/chat", json=payload)

    assert response.status_code == 200
    data = response.json()
    response_text = data.get("response", "").upper()

    # Check that it didn't fall back to rule-based fallback
    assert "SUCCESS" in response_text
    assert "WELCOME TO THE VAJRA.STREAM AI COMMAND CENTER" not in response_text

def is_lm_studio_running():
    import requests
    try:
        url = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")
        requests.get(f"{url}/models", timeout=2)
        return True
    except Exception:
        return False

@pytest.mark.skipif(not is_lm_studio_running(), reason="LM Studio not running")
def test_live_local_model():
    """
    Sends a LIVE request to the local model (via LM Studio or local GGUF depending on user setup).
    Ensure your local server is running, or a .gguf file is present in /models.
    """
    payload = {
        "messages": [{"role": "user", "content": "Reply with exactly the word 'SUCCESS' and nothing else. Do not use any tools."}],
        "provider": "lm_studio"
    }

    response = client.post("/api/v1/llm/chat", json=payload)

    assert response.status_code == 200
    data = response.json()
    response_text = data.get("response", "").upper()

    # Check that it didn't fall back
    assert "SUCCESS" in response_text
    assert "WELCOME TO THE VAJRA.STREAM AI COMMAND CENTER" not in response_text
