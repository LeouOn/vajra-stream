from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from container import container


@pytest.fixture
def client():
    return TestClient(app)


@patch("openai.OpenAI")
def test_outlook_api_e2e_lm_studio(mock_openai_cls, client):
    # Setup mock
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content="Test narrative from LM Studio"))
    ]

    # Set up our LLM Integration so it uses auto (which falls back to lm_studio)
    if hasattr(container, "llm_integration") and container.llm_integration:
        container.llm_integration.model_type = "auto"

    # Send request with a model name that doesn't trigger gpt, claude, deepseek
    payload = {
        "lat": 34.0,
        "lon": -118.0,
        "languages": ["English"],
        "genre": "healing",
        "model": "gemma-4-e4b-it-uncensored-max-opus-4.7",
        "include_astrology": False,
        "include_tarot": False,
        "include_iching": False,
    }

    response = client.post("/api/v1/outlook/generate_single", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "narrative" in data
    assert data["narrative"] == "Test narrative from LM Studio"

    # Verify that the LLM Integration correctly routed to LM Studio
    # by checking if OpenAI was initialized with the LM Studio base URL
    mock_openai_cls.assert_called_with(base_url="http://127.0.0.1:1234/v1", api_key="lm-studio")

    # And check that the correct model was requested
    mock_client.chat.completions.create.assert_called_once()
    kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "gemma-4-e4b-it-uncensored-max-opus-4.7"
