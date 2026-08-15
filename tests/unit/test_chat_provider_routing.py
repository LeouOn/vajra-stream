"""Chat provider routing — slash-ids go to OpenRouter, not pick_best / nvidia."""

from __future__ import annotations

import pytest

from backend.app.api.v1.endpoints.llm import _normalize_model_id, _provider_for_model


@pytest.mark.unit
@pytest.mark.parametrize(
    ("provider", "model", "expected"),
    [
        ("auto", None, "auto"),
        ("auto", "nvidia/nemotron-3-ultra-550b-a55b:free", "openrouter"),
        ("nvidia", "nvidia/nemotron-3-ultra-550b-a55b:free", "openrouter"),
        ("openrouter", "deepseek/deepseek-v4-flash", "openrouter"),
        ("auto", "poolside/laguna-s-2.1:free", "openrouter"),
        ("poolside", "poolside/laguna-xs-2.1:free", "openrouter"),
        ("deepseek", "deepseek/deepseek-v4-flash", "openrouter"),
        ("auto", "lm_studio:qwen2.5", "lm_studio"),
        ("auto", "local:llama-3", "local"),
        ("anthropic", "claude-sonnet-4", "anthropic"),
        ("deepseek", "deepseek-chat", "deepseek"),
    ],
)
def test_provider_for_model(provider, model, expected):
    assert _provider_for_model(provider, model) == expected


@pytest.mark.unit
def test_normalize_model_id_strips_launcher_prefix():
    assert _normalize_model_id("lm_studio:qwen2.5") == "qwen2.5"
    assert _normalize_model_id("local:llama-3") == "llama-3"
    assert _normalize_model_id("nvidia/nemotron") == "nvidia/nemotron"
    assert _normalize_model_id(None) is None
