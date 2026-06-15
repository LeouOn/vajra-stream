# core/llm/providers/anthropic.py
"""Anthropic Claude provider (native SDK, not OpenAI-compatible)."""
from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator

from anthropic import AsyncAnthropic

from core.llm.models import (
    ChatChunk,
    ChatRequest,
    ChatResponse,
    HealthStatus,
    ModelInfo,
)

logger = logging.getLogger(__name__)


class AnthropicProvider:
    """Provider for the Anthropic Messages API (Claude models).

    Uses the native ``anthropic`` async SDK rather than the OpenAI-compatible
    base class, because Anthropic has a distinct message format and usage
    model.
    """

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = "claude-3-5-haiku-20241022",
        priority: int = 60,
        timeout_seconds: int = 120,
    ) -> None:
        # Accept either ANTHROPIC_API_KEY (Anthropic's documented name) or
        # ANTHROPIC_AUTH_TOKEN (Anthropic SDK / proxy convention).
        key = (
            api_key
            or os.getenv("ANTHROPIC_API_KEY")
            or os.getenv("ANTHROPIC_AUTH_TOKEN")
            or ""
        )
        if not key:
            raise ValueError(
                "Anthropic provider requires ANTHROPIC_API_KEY or "
                "ANTHROPIC_AUTH_TOKEN env var (or api_key argument)"
            )
        self.name = "anthropic"
        self.priority = priority
        self.default_model = default_model
        self.timeout_seconds = timeout_seconds
        self._client = AsyncAnthropic(api_key=key, timeout=timeout_seconds)

    async def health_check(self) -> HealthStatus:
        # Anthropic has no list-models endpoint; a successful client
        # construction is considered healthy.
        return HealthStatus(
            provider=self.name,
            healthy=True,
        )

    async def list_models(self) -> list[ModelInfo]:
        # Anthropic does not expose a models listing API.
        return []

    def _build_messages(
        self, request: ChatRequest
    ) -> tuple[list[dict], str | None]:
        """Split request into (messages, system_prompt) for Anthropic API.

        Anthropic requires the system prompt to be a top-level parameter,
        not part of the messages list.
        """
        system: str | None = request.system_prompt
        messages: list[dict] = []
        for m in request.messages:
            if m.role == "system" and system is None:
                system = m.content
                continue
            messages.append({"role": m.role, "content": m.content})
        return messages, system

    async def generate(self, request: ChatRequest) -> ChatResponse:
        model = request.model or self.default_model
        messages, system = self._build_messages(request)
        try:
            kwargs: dict = {
                "model": model,
                "max_tokens": request.max_tokens,
                "messages": messages,
            }
            if system:
                kwargs["system"] = system
            response = await self._client.messages.create(**kwargs)
            text = ""
            if response.content:
                text = getattr(response.content[0], "text", "") or ""
            return ChatResponse(
                content=text,
                provider=self.name,
                model=model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                finish_reason=response.stop_reason or "stop",
            )
        except Exception as e:
            logger.error(f"generate failed for {self.name}/{model}: {e}")
            raise RuntimeError(f"{self.name} generation failed: {e}") from e

    async def stream(self, request: ChatRequest) -> AsyncIterator[ChatChunk]:
        model = request.model or self.default_model
        messages, system = self._build_messages(request)
        try:
            kwargs: dict = {
                "model": model,
                "max_tokens": request.max_tokens,
                "messages": messages,
            }
            if system:
                kwargs["system"] = system
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
            logger.error(f"stream failed for {self.name}/{model}: {e}")
            yield ChatChunk(
                content=f"[stream error: {e}]",
                done=True,
                provider=self.name,
                model=model,
            )

    async def close(self) -> None:
        # The anthropic async client manages an underlying httpx client.
        await self._client.close()
