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


def test_visible_text_falls_back_to_reasoning():
    from core.llm.base import visible_text

    assert visible_text("hello", "hidden thought") == "hello"
    assert visible_text("", "the blessing is complete") == "the blessing is complete"
    assert visible_text(None, "  only reasoning  ") == "only reasoning"
    assert visible_text("<think>scratch</think>\n amen", None) == "amen"
    assert visible_text("<think>scratch</think>", None) == "scratch"
    assert visible_text("", None) == ""


def test_candidate_models_auto_tries_one_fallback():
    provider = OpenAICompatibleProvider(
        name="test",
        api_key="sk-test",
        base_url="http://localhost:1234/v1",
        default_model="default-model",
        fallback_models=["fb-a", "fb-b", "fb-c"],
    )
    from core.llm.models import ChatRequest

    auto = ChatRequest(messages=[])
    assert provider._candidate_models(auto) == ["default-model", "fb-a"]
    pinned = ChatRequest(messages=[], model="pinned-model")
    assert provider._candidate_models(pinned) == ["pinned-model"]
