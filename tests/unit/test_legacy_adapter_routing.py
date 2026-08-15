"""Outlook / chat model specs must land on OpenRouter, not pick_best."""

from __future__ import annotations

import pytest

from core.llm.defaults import NEMOTRON_FREE_MODEL_ID
from core.llm.legacy_adapter import _detect_provider_from_name, _parse_model_spec


@pytest.mark.unit
@pytest.mark.parametrize(
    ("spec", "provider", "model"),
    [
        (None, None, None),
        ("auto", None, None),
        (
            NEMOTRON_FREE_MODEL_ID,
            None,
            NEMOTRON_FREE_MODEL_ID,
        ),
        (
            f"openrouter:{NEMOTRON_FREE_MODEL_ID}",
            "openrouter",
            NEMOTRON_FREE_MODEL_ID,
        ),
        ("deepseek:deepseek-chat", "deepseek", "deepseek-chat"),
        ("lm-studio:qwen", "lm_studio", "qwen"),
    ],
)
def test_parse_model_spec(spec, provider, model):
    assert _parse_model_spec(spec) == (provider, model)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("name", "expected"),
    [
        (NEMOTRON_FREE_MODEL_ID, "openrouter"),
        ("nvidia/nemotron-3-ultra-550b-a55b", "openrouter"),
        ("deepseek/deepseek-v4-flash", "openrouter"),
        ("poolside/laguna-s-2.1:free", "openrouter"),
        ("poolside/laguna-xs-2.1:free", "openrouter"),
        ("inclusionai/ling-3.0-flash", "openrouter"),
        ("nvidia/nemotron-3.5-lightning:free", "openrouter"),
        ("nemotron-3-ultra", "openrouter"),
        ("deepseek-v4-flash", "deepseek"),
        ("claude-3-5-haiku", "anthropic"),
        ("gpt-4o-mini", "openai"),
        ("local-model.gguf", "local"),
        ("", None),
    ],
)
def test_detect_provider_from_name(name, expected):
    assert _detect_provider_from_name(name) == expected


@pytest.mark.unit
def test_generate_reports_the_model_that_ran(monkeypatch):
    """Outlook's model_used must be Laguna/DeepSeek, not the OpenRouter default."""
    from unittest.mock import AsyncMock, MagicMock

    from core.llm.legacy_adapter import LegacyLLMIntegration
    from core.llm.models import ChatResponse

    provider = MagicMock()
    provider.name = "openrouter"
    provider.default_model = NEMOTRON_FREE_MODEL_ID
    provider.generate = AsyncMock(
        return_value=ChatResponse(
            content="PONG",
            provider="openrouter",
            model="poolside/laguna-xs-2.1:free",
        )
    )

    registry = MagicMock()
    registry.providers = [provider]
    registry.pick_best = AsyncMock(return_value=provider)

    llm = LegacyLLMIntegration(registry=registry)
    text = llm.generate("Reply PONG", model="poolside/laguna-xs-2.1:free", max_tokens=16)
    assert text == "PONG"
    active = llm.get_active_provider()
    assert active["provider"] == "openrouter"
    assert active["model"] == "poolside/laguna-xs-2.1:free"
