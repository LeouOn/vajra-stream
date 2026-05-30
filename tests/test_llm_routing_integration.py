from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)

@pytest.fixture
def mock_env_vars():
    with patch("os.getenv") as mock_getenv:
        def getenv_side_effect(key, default=None):
            if key == "DEEPSEEK_API_KEY":
                return "sk-test-deepseek"
            if key == "OPENAI_API_KEY":
                return None
            if key == "ANTHROPIC_API_KEY":
                return None
            if key == "DEEPSEEK_BASE_URL":
                return "https://api.deepseek.com"
            return default
        mock_getenv.side_effect = getenv_side_effect
        yield mock_getenv

def test_chat_endpoint_deepseek_routing(mock_env_vars):
    with patch("openai.OpenAI") as mock_openai_class:
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = "DeepSeek test response"
        mock_msg.tool_calls = None
        mock_completion.choices = [MagicMock(message=mock_msg)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client

        payload = {
            "messages": [{"role": "user", "content": "Hello"}],
            "provider": "deepseek",
            "model": "deepseek-chat"
        }

        response = client.post("/api/v1/llm/chat", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "DeepSeek test response" in data["response"]
        mock_openai_class.assert_called_once()


def test_chat_endpoint_lm_studio_routing(mock_env_vars):
    with patch("openai.OpenAI") as mock_openai_class:
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = "LM Studio prefixed test response"
        mock_msg.tool_calls = None
        mock_completion.choices = [MagicMock(message=mock_msg)]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client

        payload = {
            "messages": [{"role": "user", "content": "Hello lm_studio"}],
            "provider": "auto",
            "model": "lm_studio:qwen2.5"
        }

        response = client.post("/api/v1/llm/chat", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "LM Studio prefixed test response" in data["response"]
        mock_openai_class.assert_called_once()
        call_kwargs = mock_openai_class.call_args[1]
        assert call_kwargs.get("base_url") == "http://127.0.0.1:1234/v1"

        create_kwargs = mock_client.chat.completions.create.call_args[1]
        assert create_kwargs.get("model") == "qwen2.5"
