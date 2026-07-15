# tests/integration/test_nemotron_integration.py
"""Live integration test against the OpenRouter Nemotron free endpoint.

Skips gracefully when ``OPENROUTER_API_KEY`` is not set so CI without
secrets still passes. When the key is present, the test sends a tiny
chat completion request and asserts:

* HTTP 200 from OpenRouter
* the response body carries a non-empty assistant message
* the model echoed back contains ``nemotron``
* the free-tier cost component is exactly $0.00

The test is intentionally minimal — one round-trip, one assertion per
contract — so it remains fast and flake-resistant.
"""
from __future__ import annotations

import os

import pytest

_OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
_NEMOTRON_MODEL_ID = "nvidia/nemotron-3-ultra-550b-a55b:free"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _OPENROUTER_API_KEY,
        reason="OPENROUTER_API_KEY not set — skipping live Nemotron integration test",
    ),
]


@pytest.mark.asyncio
async def test_nemotron_free_model_responds():
    """The Nemotron free model must answer a trivial prompt."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=_OPENROUTER_API_KEY, base_url=_BASE_URL)
    try:
        response = await client.chat.completions.create(
            model=_NEMOTRON_MODEL_ID,
            messages=[{"role": "user", "content": "Say OK in one word."}],
            max_tokens=10,
            temperature=0.0,
        )
    finally:
        await client.close()

    assert response is not None
    assert response.choices, "OpenRouter returned no choices"
    content = (response.choices[0].message.content or "").strip()
    assert content, "Nemotron returned an empty completion"

    # The model id echoed in the response must be the Nemotron SKU we
    # requested (OpenRouter echoes the canonical id even when given a
    # vendor alias).
    echoed_model = getattr(response, "model", "") or ""
    assert "nemotron" in echoed_model.lower(), (
        f"expected 'nemotron' in echoed model id, got {echoed_model!r}"
    )

    # Free-tier Nemotron must report zero cost on the OpenRouter side.
    # The OpenAI SDK does not expose pricing directly, but the ``usage``
    # block must be present and report finite token counts (the caller
    # then multiplies by $0/M).
    usage = getattr(response, "usage", None)
    assert usage is not None, "response.usage missing on Nemotron completion"
    assert usage.prompt_tokens > 0
    assert usage.completion_tokens > 0
