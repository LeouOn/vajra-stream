# tests/core/llm/test_providers.py
"""Tests for provider construction."""
import pytest

from core.llm.providers import (
    AnthropicProvider,
    DeepSeekProvider,
    LMStudioProvider,
    LocalGGUFProvider,
    MinimaxProvider,
    OpenAIProvider,
    OpenRouterProvider,
)


def test_openai_provider_construction(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    p = OpenAIProvider()
    assert p.name == "openai"
    assert p.priority == 50
    assert p.default_model == "gpt-4o-mini"


def test_openrouter_provider_construction(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-test")
    p = OpenRouterProvider()
    assert p.name == "openrouter"
    assert p.priority == 90
    assert p.default_model == "google/gemini-2.0-flash-001"


def test_deepseek_provider_construction(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-test")
    p = DeepSeekProvider()
    assert p.name == "deepseek"
    assert p.priority == 70
    assert p.default_model == "deepseek-chat"


def test_minimax_provider_construction(monkeypatch):
    monkeypatch.setenv("MINIMAX_API_KEY", "mm-test")
    p = MinimaxProvider()
    assert p.name == "minimax"
    assert p.priority == 40
    assert p.default_model == "MiniMax-Text-01"


def test_lm_studio_provider_construction():
    p = LMStudioProvider()
    assert p.name == "lm_studio"
    assert p.priority == 80
    assert p.default_model == "local-model"


def test_all_providers_have_unique_names():
    classes = [
        OpenAIProvider,
        OpenRouterProvider,
        DeepSeekProvider,
        MinimaxProvider,
        LMStudioProvider,
        AnthropicProvider,
        LocalGGUFProvider,
    ]
    names = {cls.__name__ for cls in classes}
    assert len(names) == 7


def test_anthropic_provider_construction(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ant-test")
    p = AnthropicProvider()
    assert p.name == "anthropic"
    assert p.priority == 60
    assert p.default_model == "claude-3-5-haiku-20241022"


def test_anthropic_provider_requires_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        AnthropicProvider()


def test_local_gguf_provider_construction(tmp_path):
    (tmp_path / "test-instruct.gguf").touch()
    p = LocalGGUFProvider(models_dir=str(tmp_path))
    assert p.name == "local"
    assert p.priority == 30
    assert p.default_model == "test-instruct.gguf"


def test_local_gguf_provider_no_models(tmp_path):
    p = LocalGGUFProvider(models_dir=str(tmp_path))
    assert p.default_model == "unknown"
