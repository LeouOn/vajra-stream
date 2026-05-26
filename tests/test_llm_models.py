from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from backend.app.main import app

    return TestClient(app)


def test_models_endpoint(client):
    with patch("core.llm_integration.LLMIntegration") as mock_llm_class:
        mock_llm_instance = MagicMock()
        mock_llm_instance.list_available_models.return_value = {
            "local": ["test-model.gguf"],
            "api": ["OpenAI (gpt-4o)"],
        }
        mock_llm_class.return_value = mock_llm_instance

        # Mock urllib to simulate LM Studio active models
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b'{"data": [{"id": "lm-studio-model-1"}]}'
            mock_urlopen.return_value.__enter__.return_value = mock_resp

            response = client.get("/api/v1/llm/models")
            assert response.status_code == 200
            data = response.json()
            assert data.get("status") == "success"
            assert data.get("available", {}).get("lm_studio") == ["lm-studio-model-1"]
            assert data.get("available", {}).get("local") == ["test-model.gguf"]
            assert data.get("default_model") == "lm-studio-model-1"
