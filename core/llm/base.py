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


# ---------------------------------------------------------------------------
# Thinking-token stripping
# ---------------------------------------------------------------------------
# Some providers (DeepSeek V4, Anthropic extended-thinking, Z.AI GLM-4.x,
# various OpenRouter-routed reasoning models) emit their chain-of-thought
# either as a separate ``reasoning_content`` attribute on the message or
# inline as ``<think>...</think>`` blocks within ``content``. The helpers
# below extract the reasoning and return clean display content so it never
# leaks into chat responses, caches, or downstream tool-call parsing.

_OPEN_TAG = "<think>"
_CLOSE_TAG = "</think>"
_TAG_LEN = len(_OPEN_TAG)


def _suffix_prefix_len(text: str, tag: str) -> int:
    """Length of the longest suffix of ``text`` that is a prefix of ``tag``.

    Used to detect a tag that may have been split across stream deltas, e.g.
    ``"hello <thi"`` has suffix ``"<thi"`` which is a prefix of ``"<think>"``
    so the filter must hold those 4 bytes back until the next delta.
    """
    n = min(len(text), len(tag) - 1)
    text_lower = text.lower()
    tag_lower = tag.lower()
    for k in range(n, 0, -1):
        if tag_lower.startswith(text_lower[-k:]):
            return k
    return 0


def strip_thinking(content: str) -> tuple[str, str | None]:
    """Remove ``<think>...</think>`` blocks from ``content``.

    Returns a ``(clean_content, reasoning_or_None)`` tuple. ``reasoning`` is
    the concatenated inner text of every think block (useful for surfacing
    in debug_info), or ``None`` when no think blocks were present.

    Unterminated ``<think>`` blocks (rare in non-streaming responses, but
    possible if a provider truncates mid-thought) are treated as reasoning
    and stripped from the clean content.
    """
    if not content or _OPEN_TAG not in content.lower():
        return content, None

    reasoning_parts: list[str] = []
    remaining = content
    while _OPEN_TAG in remaining.lower():
        lower = remaining.lower()
        open_idx = lower.find(_OPEN_TAG)
        after_open = remaining[open_idx + _TAG_LEN :]
        close_idx = after_open.lower().find(_CLOSE_TAG)
        if close_idx == -1:
            reasoning_parts.append(after_open.strip())
            remaining = remaining[:open_idx]
            break
        reasoning_parts.append(after_open[:close_idx].strip())
        remaining = remaining[:open_idx] + after_open[close_idx + len(_CLOSE_TAG) :]

    reasoning = "\n".join(p for p in reasoning_parts if p).strip() or None
    clean = remaining.strip()
    return clean, reasoning


class _ThinkingFilter:
    """Stateful streaming filter that strips ``<think>`` blocks across deltas.

    Reasoning models that stream their chain-of-thought inline do so across
    many SSE deltas, so a per-chunk regex is insufficient (the opening
    ``<think>`` and closing ``</think>`` tags can land in different chunks).

    Feed each delta to :meth:`feed` and emit what it returns. At stream end,
    call :meth:`flush` to release any tail content held back as a precaution
    against a split tag. Accumulated reasoning text is exposed via the
    :attr:`reasoning` property.
    """

    def __init__(self) -> None:
        self._buffer = ""
        self._in_think = False
        self._current_reasoning = ""
        self.reasoning_parts: list[str] = []

    def feed(self, text: str) -> str:
        """Consume a delta, returning whatever is safe to emit now."""
        if not text:
            return ""
        self._buffer += text
        out: list[str] = []
        while self._buffer:
            if self._in_think:
                idx = self._buffer.lower().find(_CLOSE_TAG)
                if idx == -1:
                    hold = _suffix_prefix_len(self._buffer, _CLOSE_TAG)
                    if hold == len(self._buffer):
                        break
                    if hold:
                        self._current_reasoning += self._buffer[:-hold]
                        self._buffer = self._buffer[-hold:]
                    else:
                        self._current_reasoning += self._buffer
                        self._buffer = ""
                    break
                self._current_reasoning += self._buffer[:idx]
                if self._current_reasoning.strip():
                    self.reasoning_parts.append(self._current_reasoning)
                self._current_reasoning = ""
                self._buffer = self._buffer[idx + len(_CLOSE_TAG) :]
                self._in_think = False
            else:
                idx = self._buffer.lower().find(_OPEN_TAG)
                if idx == -1:
                    hold = _suffix_prefix_len(self._buffer, _OPEN_TAG)
                    if hold == len(self._buffer):
                        break
                    if hold:
                        out.append(self._buffer[:-hold])
                        self._buffer = self._buffer[-hold:]
                    else:
                        out.append(self._buffer)
                        self._buffer = ""
                    break
                out.append(self._buffer[:idx])
                self._buffer = self._buffer[idx + _TAG_LEN :]
                self._in_think = True
        return "".join(out)

    def flush(self) -> str:
        """Release any buffered content at stream end."""
        if self._in_think:
            self._current_reasoning += self._buffer
            if self._current_reasoning.strip():
                self.reasoning_parts.append(self._current_reasoning)
            self._current_reasoning = ""
            self._buffer = ""
            self._in_think = False
            return ""
        out = self._buffer
        self._buffer = ""
        return out

    @property
    def reasoning(self) -> str | None:
        joined = "\n".join(p for p in self.reasoning_parts if p).strip()
        return joined or None

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
        fallback_models: list[str] | None = None,
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
        self.fallback_models = fallback_models or []
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
        candidate_models = [model]
        if not request.model and self.fallback_models:
            candidate_models = [self.default_model] + [
                m for m in self.fallback_models if m != self.default_model
            ]

        last_error: Exception | None = None
        for attempt_model in candidate_models:
            try:
                response = await self._client.chat.completions.create(
                    model=attempt_model,
                    messages=messages,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    tools=[t.model_dump() for t in request.tools] if request.tools else None,
                )
                choice = response.choices[0]
                raw_content = choice.message.content or ""
                reasoning = getattr(choice.message, "reasoning_content", None)
                content, inline_reasoning = strip_thinking(raw_content)
                if reasoning is None and inline_reasoning is not None:
                    reasoning = inline_reasoning
                elif reasoning and inline_reasoning:
                    reasoning = f"{reasoning}\n{inline_reasoning}"
                chat_response = ChatResponse(
                    content=content,
                    provider=self.name,
                    model=attempt_model,
                    input_tokens=response.usage.prompt_tokens if response.usage else 0,
                    output_tokens=response.usage.completion_tokens if response.usage else 0,
                    finish_reason=choice.finish_reason or "stop",
                    reasoning_content=reasoning,
                )
                latency_ms = int((time.time() - start_time) * 1000)

                self._record_usage(
                    model=attempt_model,
                    prompt_tokens=chat_response.input_tokens,
                    completion_tokens=chat_response.output_tokens,
                    latency_ms=latency_ms,
            )

                if cache is not None and request.temperature <= 0.1:
                    try:
                        await cache.set_static(
                            system_for_cache, prompt_for_cache, attempt_model,
                            request.max_tokens, request.temperature, chat_response,
                        )
                    except Exception:  # noqa: BLE001
                        logger.debug("response cache set failed", exc_info=True)

                return chat_response
            except Exception as e:
                last_error = e
                logger.warning(f"{self.name}/{attempt_model} failed: {e}")
                if len(candidate_models) > 1:
                    logger.info(f"Falling back to next model for {self.name}...")
                    continue
                raise RuntimeError(f"{self.name} generation failed: {e}") from e

        raise RuntimeError(f"{self.name} all models exhausted: {last_error}") from last_error

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
            thinking_filter = _ThinkingFilter()
            reasoning_emitted = False
            async for chunk in stream:
                content = ""
                reasoning = ""
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    raw = (delta.content or "") if hasattr(delta, "content") else ""
                    content = thinking_filter.feed(raw)
                    if not reasoning_emitted:
                        reasoning = getattr(delta, "reasoning_content", "") or ""
                        if reasoning:
                            thinking_filter.reasoning_parts.append(reasoning)
                if getattr(chunk, "usage", None):
                    usage_prompt = chunk.usage.prompt_tokens or usage_prompt
                    usage_completion = chunk.usage.completion_tokens or usage_completion
                if content or not chunk.choices:
                    yield ChatChunk(content=content, done=False, provider=self.name, model=model)
            tail = thinking_filter.flush()
            if tail:
                yield ChatChunk(content=tail, done=False, provider=self.name, model=model)
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
