import os
from unittest.mock import MagicMock, patch

import pytest

from core.llm_integration import LLMIntegration


@pytest.fixture
def mock_env():
    old_deepseek = os.environ.get("DEEPSEEK_API_KEY")
    old_openai = os.environ.get("OPENAI_API_KEY")
    old_anthropic = os.environ.get("ANTHROPIC_API_KEY")

    os.environ["DEEPSEEK_API_KEY"] = "sk-deepseek-mock-key"
    os.environ["OPENAI_API_KEY"] = "sk-openai-mock-key"
    os.environ["ANTHROPIC_API_KEY"] = "sk-anthropic-mock-key"

    yield

    if old_deepseek is not None:
        os.environ["DEEPSEEK_API_KEY"] = old_deepseek
    else:
        os.environ.pop("DEEPSEEK_API_KEY", None)

    if old_openai is not None:
        os.environ["OPENAI_API_KEY"] = old_openai
    else:
        os.environ.pop("OPENAI_API_KEY", None)

    if old_anthropic is not None:
        os.environ["ANTHROPIC_API_KEY"] = old_anthropic
    else:
        os.environ.pop("ANTHROPIC_API_KEY", None)


def test_dynamic_routing_deepseek(mock_env):
    llm = LLMIntegration(model_type="auto")

    with patch("openai.OpenAI") as mock_openai_class:
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = "mocked deepseek response"
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client

        # Test routing with prefix
        res = llm.generate("Hello", model="deepseek:deepseek-v4-flash")

        assert res == "mocked deepseek response"
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "deepseek-v4-flash"


def test_dynamic_routing_openai(mock_env):
    llm = LLMIntegration(model_type="auto")

    with patch("openai.OpenAI") as mock_openai_class:
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = "mocked openai response"
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client

        # Test routing based on name auto-detection
        res = llm.generate("Hello", model="gpt-4o-custom")

        assert res == "mocked openai response"
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4o-custom"


def test_dynamic_routing_anthropic(mock_env):
    llm = LLMIntegration(model_type="auto")

    with patch("anthropic.Anthropic") as mock_anthropic_class:
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = [MagicMock()]
        mock_message.content[0].text = "mocked anthropic response"
        mock_client.messages.create.return_value = mock_message
        mock_anthropic_class.return_value = mock_client

        # Test routing with prefix
        res = llm.generate("Hello", model="anthropic:claude-3-5-sonnet")

        assert res == "mocked anthropic response"
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-3-5-sonnet"


def test_dynamic_routing_local(mock_env):
    llm = LLMIntegration(model_type="auto")

    with patch("llama_cpp.Llama") as mock_llama_class:
        mock_local_model = MagicMock()
        mock_local_model.return_value = {
            "choices": [{"text": "mocked local response"}]
        }
        mock_llama_class.return_value = mock_local_model

        # Mock existence of file
        with patch("os.path.exists", return_value=True):
            res = llm.generate("Hello", model="local:my-custom-model.gguf")

            assert res == "mocked local response"
            mock_local_model.assert_called_once()
