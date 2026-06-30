# core/llm/base.py
"""Base LLM provider abstractions."""
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from openai import AsyncOpenAI

from core.llm.cache import LLMResponseCache
from core.llm.models import (
    ChatChunk,
    ChatRequest,
    ChatResponse,
    HealthStatus,
    ModelInfo,
)
from core.llm.usage import LLMUsageTracker, UsageRecord

logger = logging.getLogger(__name__)

# Module-level singleton cache shared by all OpenAI-compatible providers.
# Lazy-instantiated so test isolation isn't disturbed. Providers opt in
# to caching via the constructor flag; the cache itself is only consulted
# for low-temperature calls.
_RESPONSE_CACHE: LLMResponseCache | None = None


def get_response_cache() -> LLMResponseCache:
    global _RESPONSE_CACHE
    if _RESPONSE_CACHE is None:
        _RESPONSE_CACHE = LLMResponseCache()
    return _RESPONSE_CACHE


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
        enable_cache: bool = False,
    ) -> None:
        if not api_key:
            raise ValueError(f"{name} provider requires a non-empty api_key")
        if not base_url:
            raise ValueError(f"{name} provider requires a non-empty base_url")
        self.name = name
        self.priority = priority
        self.default_model = default_model
        self.timeout_seconds = timeout_seconds
        self.enable_cache = enable_cache
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

        # Cache lookup (only for deterministic-ish requests). The static
        # tier assumes the caller has already pinned temperature to 0; the
        # chat tier accepts any low-temperature call.
        cache = get_response_cache() if self.enable_cache else None
        system_for_cache = request.system_prompt or ""
        prompt_for_cache = next(
            (m.content for m in reversed(request.messages) if m.role == "user"),
            "",
        )
        if cache is not None and request.temperature <= 0.1:
            try:
                cached = await cache.get_static(
                    system_for_cache, prompt_for_cache, model,
                    request.max_tokens, request.temperature,
                )
                if cached is not None:
                    return cached
            except Exception:  # noqa: BLE001 — cache failures must never break generation
                logger.debug("response cache get failed", exc_info=True)

        start_time = time.time()
        try:
            response = await self._client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                tools=[t.model_dump() for t in request.tools] if request.tools else None,
            )
            choice = response.choices[0]
            chat_response = ChatResponse(
                content=choice.message.content or "",
                provider=self.name,
                model=model,
                input_tokens=response.usage.prompt_tokens if response.usage else 0,
                output_tokens=response.usage.completion_tokens if response.usage else 0,
                finish_reason=choice.finish_reason or "stop",
            )
            latency_ms = int((time.time() - start_time) * 1000)

            self._record_usage(
                model=model,
                prompt_tokens=chat_response.input_tokens,
                completion_tokens=chat_response.output_tokens,
                latency_ms=latency_ms,
            )

            if cache is not None and request.temperature <= 0.1:
                try:
                    await cache.set_static(
                        system_for_cache, prompt_for_cache, model,
                        request.max_tokens, request.temperature, chat_response,
                    )
                except Exception:  # noqa: BLE001
                    logger.debug("response cache set failed", exc_info=True)

            return chat_response
        except Exception as e:
            logger.error(f"generate failed for {self.name}/{model}: {e}")
            raise RuntimeError(f"{self.name} generation failed: {e}") from e

    def _record_usage(
        self,
        *,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: int,
        endpoint: str = "chat",
        success: bool = True,
    ) -> None:
        """Best-effort usage recording — never propagates exceptions."""
        try:
            tracker = LLMUsageTracker.get()
            tracker.record(UsageRecord(
                provider=self.name,
                model=model,
                prompt_tokens=prompt_tokens or 0,
                completion_tokens=completion_tokens or 0,
                total_tokens=(prompt_tokens or 0) + (completion_tokens or 0),
                latency_ms=latency_ms,
                endpoint=endpoint,
                success=success,
            ))
        except Exception:  # noqa: BLE001
            logger.debug("LLMUsageTracker.record failed", exc_info=True)

    async def stream(self, request: ChatRequest) -> AsyncIterator[ChatChunk]:
        messages = self._build_messages(request)
        model = request.model or self.default_model
        start_time = time.time()
        # Aggregate usage from the final chunk when the upstream API
        # supports ``stream_options.include_usage`` (OpenAI, OpenRouter,
        # DeepSeek, MiniMax). LM Studio ignores the option gracefully.
        usage_prompt = 0
        usage_completion = 0
        try:
            stream = await self._client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                stream=True,
                stream_options={"include_usage": True},
            )
            async for chunk in stream:
                content = ""
                if chunk.choices:
                    content = chunk.choices[0].delta.content or ""
                if getattr(chunk, "usage", None):
                    usage_prompt = chunk.usage.prompt_tokens or usage_prompt
                    usage_completion = chunk.usage.completion_tokens or usage_completion
                yield ChatChunk(content=content, done=False, provider=self.name, model=model)
            yield ChatChunk(content="", done=True, provider=self.name, model=model)
        except Exception as e:
            logger.error(f"stream failed for {self.name}/{model}: {e}")
            yield ChatChunk(content=f"[stream error: {e}]", done=True, provider=self.name, model=model)
        finally:
            if usage_prompt or usage_completion:
                self._record_usage(
                    model=model,
                    prompt_tokens=usage_prompt,
                    completion_tokens=usage_completion,
                    latency_ms=int((time.time() - start_time) * 1000),
                    endpoint="stream",
                )

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
