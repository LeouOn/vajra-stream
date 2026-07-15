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
    ZAIProvider,
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
    assert p.default_model == "deepseek/deepseek-v4-pro"
    assert p._fallback_models == ["deepseek/deepseek-v4-flash", "google/gemini-3.5-flash", "xiaomi/mimo-v2.5-pro"]


def test_deepseek_provider_construction(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-test")
    p = DeepSeekProvider()
    assert p.name == "deepseek"
    assert p.priority == 70
    assert p.default_model == "deepseek-v4-flash"


def test_minimax_provider_construction(monkeypatch):
    monkeypatch.setenv("MINIMAX_API_KEY", "mm-test")
    p = MinimaxProvider()
    assert p.name == "minimax"
    assert p.priority == 40
    assert p.default_model == "MiniMax-M3"


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
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        AnthropicProvider()


def test_anthropic_provider_accepts_auth_token(monkeypatch):
    """ANTHROPIC_AUTH_TOKEN should be accepted as an alias for ANTHROPIC_API_KEY."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "ant-via-auth-token")
    p = AnthropicProvider()
    assert p.name == "anthropic"


def test_local_gguf_provider_construction(tmp_path):
    (tmp_path / "test-instruct.gguf").touch()
    p = LocalGGUFProvider(models_dir=str(tmp_path))
    assert p.name == "local"
    assert p.priority == 30
    assert p.default_model == "test-instruct.gguf"


def test_local_gguf_provider_no_models(tmp_path):
    p = LocalGGUFProvider(models_dir=str(tmp_path))
    assert p.default_model == "unknown"


def test_z_ai_provider_construction(monkeypatch):
    monkeypatch.setenv("ZAI_API_KEY", "zai-test")
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    p = ZAIProvider()
    assert p.name == "z_ai"
    assert p.priority == 65
    assert p.default_model == "glm-4.6"
    # AsyncAnthropic client should point at the coding plan endpoint.
    assert "api.z.ai" in str(p._client.base_url)


def test_z_ai_provider_accepts_legacy_key_name(monkeypatch):
    """Z_AI_API_KEY (legacy) should be accepted as an alias for ZAI_API_KEY."""
    monkeypatch.delenv("ZAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.setenv("Z_AI_API_KEY", "zai-via-legacy")
    p = ZAIProvider()
    assert p.name == "z_ai"


def test_z_ai_provider_accepts_anthropic_token(monkeypatch):
    """ANTHROPIC_AUTH_TOKEN should also work on the coding plan endpoint."""
    monkeypatch.delenv("ZAI_API_KEY", raising=False)
    monkeypatch.delenv("Z_AI_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "ant-via-auth-token")
    p = ZAIProvider()
    assert p.name == "z_ai"


def test_z_ai_provider_requires_key(monkeypatch):
    monkeypatch.delenv("ZAI_API_KEY", raising=False)
    monkeypatch.delenv("Z_AI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    with pytest.raises(ValueError, match="ZAI_API_KEY"):
        ZAIProvider()
