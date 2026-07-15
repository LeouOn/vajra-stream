# core/llm/providers/z_ai.py
"""Z.AI / GLM provider for the international coding plan.

The coding plan exposes an Anthropic Messages-API-compatible endpoint at
``https://api.z.ai/api/anthropic`` (NOT the OpenAI-compatible ``paas/v4``
endpoint, which is pay-as-you-go and returns 429 for coding-plan keys).

Both ``ZAI_API_KEY`` and ``ANTHROPIC_AUTH_TOKEN`` work on this endpoint.
Models are served as ``glm-4.6``, ``glm-4.5``, ``glm-4.5-air``, etc.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import AsyncIterator

from anthropic import AsyncAnthropic

from core.llm.base import BaseLLMProvider
from core.llm.models import (
    ChatChunk,
    ChatRequest,
    ChatResponse,
    HealthStatus,
    ModelInfo,
)

logger = logging.getLogger(__name__)

# Canonical coding plan endpoint (Anthropic protocol).
CODING_PLAN_BASE_URL = "https://api.z.ai/api/anthropic"

# Models available on the coding plan (verified via /v1/messages probes).
SUPPORTED_MODELS = ("glm-4.6", "glm-4.5", "glm-4.5-air")


class ZAIProvider(BaseLLMProvider):
    """Provider for Z.AI's international coding plan (Anthropic-compatible).

    Uses the native ``anthropic`` async SDK pointed at Z.AI's coding-plan
    endpoint. The protocol is Anthropic Messages API, so we reuse the same
    request/response mapping as :class:`AnthropicProvider`.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str = "glm-4.6",
        priority: int = 65,
        timeout_seconds: int = 120,
    ) -> None:
        # Accept ZAI_API_KEY (current), Z_AI_API_KEY (legacy), or
        # ANTHROPIC_AUTH_TOKEN (the Anthropic-SDK alias that also works on
        # this endpoint per probe results).
        key = (
            api_key or os.getenv("ZAI_API_KEY") or os.getenv("Z_AI_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN") or ""
        )
        if not key:
            raise ValueError(
                "Z.AI coding-plan provider requires ZAI_API_KEY, "
                "Z_AI_API_KEY, or ANTHROPIC_AUTH_TOKEN env var "
                "(or api_key argument)"
            )
        self.name = "z_ai"
        self.priority = priority
        self.default_model = default_model
        self.timeout_seconds = timeout_seconds
        self._client = AsyncAnthropic(
            api_key=key,
            base_url=base_url or os.getenv("ZAI_BASE_URL", CODING_PLAN_BASE_URL),
            timeout=timeout_seconds,
        )

    async def health_check(self) -> HealthStatus:
        """Quick health probe via a minimal ``/v1/messages`` call."""
        start = time.time()
        try:
            await self._client.messages.create(
                model=self.default_model,
                max_tokens=1,
                messages=[{"role": "user", "content": "."}],
            )
            latency_ms = (time.time() - start) * 1000
            return HealthStatus(
                provider=self.name,
                healthy=True,
                latency_ms=latency_ms,
                models_available=len(SUPPORTED_MODELS),
            )
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            logger.warning("health_check failed for %s: %s", self.name, e)
            return HealthStatus(
                provider=self.name,
                healthy=False,
                latency_ms=latency_ms,
                error=str(e)[:200],
            )

    async def list_models(self) -> list[ModelInfo]:
        """Return the known coding-plan models (no /models endpoint)."""
        return [
            ModelInfo(
                id=m,
                provider=self.name,
                supports_streaming=True,
                supports_tools=True,
            )
            for m in SUPPORTED_MODELS
        ]

    async def generate(self, request: ChatRequest) -> ChatResponse:
        """Generate via the Anthropic Messages API."""
        messages = [{"role": m.role, "content": m.content} for m in request.messages if m.role != "system"]
        system = request.system_prompt or next((m.content for m in request.messages if m.role == "system"), None)
        model = request.model or self.default_model
        kwargs: dict = {
            "model": model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        try:
            response = await self._client.messages.create(**kwargs)
            text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    text += block.text
            return ChatResponse(
                content=text,
                provider=self.name,
                model=model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                finish_reason=response.stop_reason or "stop",
            )
        except Exception as e:
            logger.error("z_ai generate failed: %s", e)
            raise RuntimeError(f"z_ai generation failed: {e}") from e

    async def stream(self, request: ChatRequest) -> AsyncIterator[ChatChunk]:
        """Stream via the Anthropic Messages API."""
        messages = [{"role": m.role, "content": m.content} for m in request.messages if m.role != "system"]
        system = request.system_prompt or next((m.content for m in request.messages if m.role == "system"), None)
        model = request.model or self.default_model
        kwargs: dict = {
            "model": model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        try:
            async with self._client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    yield ChatChunk(
                        content=text,
                        done=False,
                        provider=self.name,
                        model=model,
                    )
            yield ChatChunk(content="", done=True, provider=self.name, model=model)
        except Exception as e:
            logger.error("z_ai stream failed: %s", e)
            yield ChatChunk(
                content=f"[stream error: {e}]",
                done=True,
                provider=self.name,
                model=model,
            )

    async def close(self) -> None:
        await self._client.close()
