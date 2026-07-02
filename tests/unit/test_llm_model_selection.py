# tests/unit/test_llm_model_selection.py
"""Unit tests for Nemotron-default model selection and the model-level
fallback chain.

Covers the contracts added in the ``feat(llm): Nemotron free as default +
model-level fallback chain`` commit:

* :data:`core.llm.defaults.NEMOTRON_FREE_MODEL_ID` is the OpenRouter
  provider default.
* :data:`core.llm.defaults.DEFAULT_MODELS_BY_USE_CASE` pins the right
  features (outlook_narrative, blessing_loop, ...) to Nemotron.
* :class:`core.llm.providers.openrouter.OpenRouterProvider` ships with a
  four-model ``fallback_models`` chain.
* :meth:`core.llm.base.OpenAICompatibleProvider.generate` walks the chain
  on failure but skips it when the caller pins ``request.model``.
* :meth:`core.llm.registry.ProviderRegistry.pick_best` returns the
  highest-priority *healthy* provider.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from core.llm.base import OpenAICompatibleProvider
from core.llm.defaults import (
    DEFAULT_MODELS_BY_USE_CASE,
    KNOWN_FEATURED_MODEL_IDS,
    NEMOTRON_FREE_MODEL_ID,
)
from core.llm.models import ChatMessage, ChatRequest, HealthStatus
from core.llm.providers.openrouter import OpenRouterProvider
from core.llm.registry import ProviderRegistry

pytestmark = pytest.mark.unit


# ─── defaults.py + provider wiring ────────────────────────────────────


def test_nemotron_free_model_id_is_canonical():
    """The constant must match the OpenRouter id for the free Nemotron SKU."""
    assert NEMOTRON_FREE_MODEL_ID == "nvidia/nemotron-3-ultra-550b-a55b:free"
    assert NEMOTRON_FREE_MODEL_ID.endswith(":free")


def test_openrouter_default_is_nemotron_free(monkeypatch):
    """OpenRouterProvider.default_model must be Nemotron free."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-test")
    provider = OpenRouterProvider()
    assert provider.default_model == NEMOTRON_FREE_MODEL_ID
    # The class-level constant also points at the same id.
    assert OpenRouterProvider.NEMOTRON_FREE_MODEL == NEMOTRON_FREE_MODEL_ID


@pytest.mark.parametrize(
    "use_case",
    ["outlook_narrative", "blessing_loop"],
)
def test_defaults_pin_nemotron_for_unbounded_loops(use_case: str):
    """The two unbounded/24x7 use cases must default to the free model so
    the loop never incurs cost."""
    entry = DEFAULT_MODELS_BY_USE_CASE[use_case]
    assert entry["model_id"] == NEMOTRON_FREE_MODEL_ID, (
        f"{use_case} should default to Nemotron free, got {entry['model_id']}"
    )
    assert entry["provider"] == "openrouter"


def test_defaults_every_entry_has_rationale():
    """Every use-case entry must ship a non-empty rationale for the UI."""
    for use_case, entry in DEFAULT_MODELS_BY_USE_CASE.items():
        assert "model_id" in entry, f"{use_case} missing model_id"
        assert "display_name" in entry, f"{use_case} missing display_name"
        assert "provider" in entry, f"{use_case} missing provider"
        assert entry["rationale"], f"{use_case} must have non-empty rationale"


def test_known_featured_models_include_nemotron():
    """The featured list (UI top-of-catalogue) must include Nemotron."""
    assert NEMOTRON_FREE_MODEL_ID in KNOWN_FEATURED_MODEL_IDS
    # OpenRouterProvider keeps its own tuple in sync with the defaults list.
    assert NEMOTRON_FREE_MODEL_ID in OpenRouterProvider.KNOWN_FEATURED_MODELS


# ─── fallback chain declaration ───────────────────────────────────────


def test_openrouter_provider_has_four_model_fallback_chain(monkeypatch):
    """The fallback chain must be exactly:
    Nemotron → DeepSeek V4 Flash → DeepSeek Chat → GPT-4o-mini.
    """
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-test")
    provider = OpenRouterProvider()
    assert provider.fallback_models == [
        NEMOTRON_FREE_MODEL_ID,
        "deepseek/deepseek-v4-flash",
        "deepseek/deepseek-chat",
        "openai/gpt-4o-mini",
    ]


def test_fallback_chain_starts_with_default_model(monkeypatch):
    """The default model must be the first entry of the fallback chain so
    it's tried first."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-test")
    provider = OpenRouterProvider()
    assert provider.fallback_models[0] == provider.default_model


# ─── generate() fallback behaviour ────────────────────────────────────


def _build_response(*, content: str = "OK") -> Any:
    """Build a minimal stand-in for an OpenAI ChatCompletion response."""
    message = MagicMock()
    message.content = content
    message.reasoning_content = None
    choice = MagicMock()
    choice.message = message
    choice.finish_reason = "stop"
    response = MagicMock()
    response.choices = [choice]
    usage = MagicMock()
    usage.prompt_tokens = 5
    usage.completion_tokens = 1
    response.usage = usage
    return response


def _make_request(**overrides: Any) -> ChatRequest:
    """Build a ChatRequest with sensible defaults for fallback tests."""
    base: dict[str, Any] = {
        "messages": [ChatMessage(role="user", content="Say OK in one word.")],
        "max_tokens": 10,
        "temperature": 0.0,
    }
    base.update(overrides)
    return ChatRequest(**base)


@pytest.mark.asyncio
async def test_generate_falls_through_chain_on_failure():
    """When the first model raises, generate() must try the next model in
    the fallback chain and return its response."""
    provider = OpenAICompatibleProvider(
        name="test-fallback",
        api_key="sk-test",
        base_url="http://localhost/v1",
        default_model="primary-model",
        fallback_models=["primary-model", "secondary-model"],
    )

    call_sequence: list[str] = []

    async def fake_create(**kwargs: Any) -> Any:
        model = kwargs["model"]
        call_sequence.append(model)
        if model == "primary-model":
            # Simulate the upstream 404 / API error.
            raise RuntimeError("simulated 404 from upstream")
        return _build_response(content="ok")

    # Patch the AsyncOpenAI client's chat completions create method.
    provider._client.chat.completions.create = fake_create  # type: ignore[assignment]

    response = await provider.generate(_make_request())
    assert response.model == "secondary-model"
    assert response.content == "ok"
    # Confirms both models were attempted in order.
    assert call_sequence == ["primary-model", "secondary-model"]
    await provider.close()


@pytest.mark.asyncio
async def test_generate_raises_when_all_models_fail():
    """If every model in the chain raises, generate() must surface a
    RuntimeError that mentions exhaustion."""
    provider = OpenAICompatibleProvider(
        name="test-fallback",
        api_key="sk-test",
        base_url="http://localhost/v1",
        default_model="primary-model",
        fallback_models=["primary-model", "secondary-model"],
    )

    async def always_fails(**kwargs: Any) -> Any:
        raise RuntimeError(f"upstream rejected {kwargs['model']}")

    provider._client.chat.completions.create = always_fails  # type: ignore[assignment]

    with pytest.raises(RuntimeError, match="all models exhausted"):
        await provider.generate(_make_request())
    await provider.close()


@pytest.mark.asyncio
async def test_generate_respects_explicit_model_override():
    """When request.model is pinned, generate() must NOT walk the chain —
    the user's choice is honored even if it fails."""
    provider = OpenAICompatibleProvider(
        name="test-no-fallback",
        api_key="sk-test",
        base_url="http://localhost/v1",
        default_model="primary-model",
        fallback_models=["primary-model", "secondary-model"],
    )

    attempted: list[str] = []

    async def fake_create(**kwargs: Any) -> Any:
        attempted.append(kwargs["model"])
        if kwargs["model"] == "pinned-by-user":
            raise RuntimeError("user-pinned model is down")
        return _build_response()

    provider._client.chat.completions.create = fake_create  # type: ignore[assignment]

    # request.model is set explicitly — fallback chain must be skipped.
    request = _make_request(model="pinned-by-user")

    with pytest.raises(RuntimeError, match="generation failed"):
        await provider.generate(request)
    # The fallback model must NOT have been probed.
    assert attempted == ["pinned-by-user"]
    await provider.close()


@pytest.mark.asyncio
async def test_generate_no_fallback_when_chain_empty():
    """A provider with an empty fallback chain raises on the first error."""
    provider = OpenAICompatibleProvider(
        name="test-no-chain",
        api_key="sk-test",
        base_url="http://localhost/v1",
        default_model="only-model",
        fallback_models=[],
    )

    async def fails(**kwargs: Any) -> Any:
        raise RuntimeError("nope")

    provider._client.chat.completions.create = fails  # type: ignore[assignment]

    with pytest.raises(RuntimeError, match="generation failed"):
        await provider.generate(_make_request())
    await provider.close()


@pytest.mark.asyncio
async def test_generate_succeeds_first_try_without_fallback_overhead():
    """When the first model succeeds, generate() must NOT probe any other
    model — verifies the happy path doesn't accidentally call every model.
    """
    provider = OpenAICompatibleProvider(
        name="test-happy",
        api_key="sk-test",
        base_url="http://localhost/v1",
        default_model="primary-model",
        fallback_models=["primary-model", "secondary-model"],
    )

    attempted: list[str] = []

    async def fake_create(**kwargs: Any) -> Any:
        attempted.append(kwargs["model"])
        return _build_response(content="primary ok")

    provider._client.chat.completions.create = fake_create  # type: ignore[assignment]

    response = await provider.generate(_make_request())
    assert response.model == "primary-model"
    assert response.content == "primary ok"
    assert attempted == ["primary-model"], "happy path must not probe fallbacks"
    await provider.close()


# ─── registry.pick_best() ─────────────────────────────────────────────


class _StubProvider:
    """Minimal BaseLLMProvider Protocol stub for registry tests."""

    def __init__(self, name: str, priority: int, healthy: bool) -> None:
        self.name = name
        self.priority = priority
        self._healthy = healthy

    async def health_check(self) -> HealthStatus:
        return HealthStatus(provider=self.name, healthy=self._healthy)

    async def list_models(self) -> list[Any]:
        return []

    async def generate(self, request: ChatRequest) -> Any:  # pragma: no cover
        raise NotImplementedError

    async def stream(self, request: ChatRequest) -> Any:  # pragma: no cover
        raise NotImplementedError

    async def close(self) -> None:
        pass


@pytest.mark.asyncio
async def test_pick_best_returns_highest_priority_healthy_provider():
    """pick_best() must skip unhealthy providers even if they have the
    highest priority, returning the next healthiest candidate."""
    registry = ProviderRegistry()
    registry.register(_StubProvider("openrouter", priority=90, healthy=False))
    registry.register(_StubProvider("lm_studio", priority=80, healthy=True))
    registry.register(_StubProvider("deepseek", priority=70, healthy=True))

    best = await registry.pick_best(use_cache=False)
    assert best is not None
    assert best.name == "lm_studio"


@pytest.mark.asyncio
async def test_pick_best_returns_none_when_all_unhealthy():
    """When every provider is sick, pick_best() must return None so the
    caller can fall through to env-var detection."""
    registry = ProviderRegistry()
    registry.register(_StubProvider("a", priority=90, healthy=False))
    registry.register(_StubProvider("b", priority=10, healthy=False))

    best = await registry.pick_best(use_cache=False)
    assert best is None


@pytest.mark.asyncio
async def test_pick_best_prefers_openrouter_when_healthy():
    """When OpenRouter (priority 90) is healthy it must beat every other
    registered provider — the registry's ordering is what makes
    Nemotron-first behaviour deterministic."""
    registry = ProviderRegistry()
    registry.register(_StubProvider("lm_studio", priority=80, healthy=True))
    registry.register(_StubProvider("openrouter", priority=90, healthy=True))
    registry.register(_StubProvider("anthropic", priority=60, healthy=True))

    best = await registry.pick_best(use_cache=False)
    assert best is not None
    assert best.name == "openrouter"
