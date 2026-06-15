# core/llm/base.py
"""Base LLM provider abstractions."""
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from openai import AsyncOpenAI

from core.llm.models import (
    ChatChunk,
    ChatRequest,
    ChatResponse,
    HealthStatus,
    ModelInfo,
)

logger = logging.getLogger(__name__)


@runtime_checkable
class BaseLLMProvider(Protocol):
    """Protocol that all LLM providers must satisfy."""

    name: str
    priority: int

    async def health_check(self) -> HealthStatus: ...
    async def list_models(self) -> list[ModelInfo]: ...
    async def generate(self, request: ChatRequest) -> ChatResponse: ...
    async def stream(self, request: ChatRequest) -> AsyncIterator[ChatChunk]: ...
    async def close(self) -> None: ...


class OpenAICompatibleProvider:
    """Async base class for OpenAI-compatible providers.

    Used by: openai, openrouter, deepseek, minimax, lm_studio.
    """

    def __init__(
        self,
        name: str,
        api_key: str,
        base_url: str,
        default_model: str,
        timeout_seconds: int = 120,
        priority: int = 50,
    ) -> None:
        if not api_key:
            raise ValueError(f"{name} provider requires a non-empty api_key")
        if not base_url:
            raise ValueError(f"{name} provider requires a non-empty base_url")
        self.name = name
        self.priority = priority
        self.default_model = default_model
        self.timeout_seconds = timeout_seconds
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
        )

    async def health_check(self) -> HealthStatus:
        start = time.time()
        try:
            models = await asyncio.wait_for(self._client.models.list(), timeout=2.0)
            latency_ms = (time.time() - start) * 1000
            return HealthStatus(
                provider=self.name,
                healthy=True,
                latency_ms=latency_ms,
                models_available=len(models.data),
            )
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            logger.warning(f"health_check failed for {self.name}: {e}")
            return HealthStatus(
                provider=self.name,
                healthy=False,
                latency_ms=latency_ms,
                error=str(e)[:200],
            )

    async def list_models(self) -> list[ModelInfo]:
        try:
            models = await self._client.models.list()
            return [
                ModelInfo(id=m.id, provider=self.name, supports_streaming=True)
                for m in models.data
            ]
        except Exception as e:
            logger.warning(f"list_models failed for {self.name}: {e}")
            return []

    async def generate(self, request: ChatRequest) -> ChatResponse:
        messages = self._build_messages(request)
        model = request.model or self.default_model
        try:
            response = await self._client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                tools=[t.model_dump() for t in request.tools] if request.tools else None,
            )
            choice = response.choices[0]
            return ChatResponse(
                content=choice.message.content or "",
                provider=self.name,
                model=model,
                input_tokens=response.usage.prompt_tokens if response.usage else 0,
                output_tokens=response.usage.completion_tokens if response.usage else 0,
                finish_reason=choice.finish_reason or "stop",
            )
        except Exception as e:
            logger.error(f"generate failed for {self.name}/{model}: {e}")
            raise RuntimeError(f"{self.name} generation failed: {e}") from e

    async def stream(self, request: ChatRequest) -> AsyncIterator[ChatChunk]:
        messages = self._build_messages(request)
        model = request.model or self.default_model
        try:
            stream = await self._client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                stream=True,
            )
            async for chunk in stream:
                content = ""
                if chunk.choices:
                    content = chunk.choices[0].delta.content or ""
                yield ChatChunk(content=content, done=False, provider=self.name, model=model)
            yield ChatChunk(content="", done=True, provider=self.name, model=model)
        except Exception as e:
            logger.error(f"stream failed for {self.name}/{model}: {e}")
            yield ChatChunk(content=f"[stream error: {e}]", done=True, provider=self.name, model=model)

    def _build_messages(self, request: ChatRequest) -> list[dict]:
        msgs: list[dict] = []
        if request.system_prompt:
            msgs.append({"role": "system", "content": request.system_prompt})
        for m in request.messages:
            entry: dict = {"role": m.role, "content": m.content}
            if m.name:
                entry["name"] = m.name
            if m.tool_call_id:
                entry["tool_call_id"] = m.tool_call_id
            msgs.append(entry)
        return msgs

    async def close(self) -> None:
        await self._client.close()
