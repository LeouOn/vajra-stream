# tests/core/llm/test_base.py
import pytest

from core.llm.base import OpenAICompatibleProvider


def test_openai_compatible_requires_api_key():
    with pytest.raises((ValueError, TypeError)):
        OpenAICompatibleProvider(
            name="test",
            api_key="",
            base_url="http://localhost:1234/v1",
            default_model="test-model",
        )


def test_openai_compatible_constructs_with_valid_args():
    provider = OpenAICompatibleProvider(
        name="test",
        api_key="sk-test",
        base_url="http://localhost:1234/v1",
        default_model="test-model",
        timeout_seconds=30,
    )
    assert provider.name == "test"
    assert provider.default_model == "test-model"
    assert provider.timeout_seconds == 30
    assert hasattr(provider, "health_check")
    assert hasattr(provider, "list_models")
    assert hasattr(provider, "generate")
    assert hasattr(provider, "stream")
    assert hasattr(provider, "close")
