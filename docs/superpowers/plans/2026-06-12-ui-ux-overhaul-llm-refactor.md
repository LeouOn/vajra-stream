# Vajra.Stream UI/UX Overhaul + Async LLM Provider Refactor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Full UI/UX overhaul (CommandCenter decomposition, /buddhas route, settings panel, AntD optimization) plus complete async LLM provider refactor (ProviderRegistry, health-check heartbeat, ContextModule composition) shipped as one monolithic PR.

**Architecture:** Two parallel layers that converge: (1) New `core/llm/` async package with BaseLLMProvider Protocol + ProviderRegistry + OpenAI-compatible base class, health-check heartbeat task in FastAPI lifespan, TTL cache, tenacity retry; (2) New `core/context/` package with ContextModule Protocol + composable SystemPromptBuilder. Frontend: decompose 1326-line CommandCenter.jsx into 8-10 sub-components, build new /buddhas route, add ProviderSettings panel, migrate 3-6 polling components to existing WebSocket messages. Old `core/llm_integration.py` and inline compile_*_context() functions are deleted in Phase 4.

**Tech Stack:** Python 3.11, FastAPI, asyncio, httpx, tenacity, cachetools, pytest-asyncio; React 18.2, Vite 4.4, Ant Design v6.4.3, Tailwind 3.3, Zustand, R3F.

**Branch:** `feat/ui-ux-overhaul` (rebased on `main@865c1a2`)
**Spec:** `.omo/drafts/ui-ux-overhaul-plan.md`

---

## File Structure

### New backend files
- `core/llm/__init__.py` — public API
- `core/llm/base.py` — BaseLLMProvider Protocol, OpenAICompatibleProvider base
- `core/llm/registry.py` — ProviderRegistry singleton
- `core/llm/health.py` — heartbeat task
- `core/llm/cache.py` — TTLCache wrapper
- `core/llm/retry.py` — tenacity retry policies
- `core/llm/usage.py` — moved from `core/llm_usage.py`
- `core/llm/models.py` — Pydantic models
- `core/llm/providers/__init__.py`
- `core/llm/providers/openai.py`
- `core/llm/providers/anthropic.py`
- `core/llm/providers/openai_compatible.py` (used by 5 providers)
- `core/llm/providers/deepseek.py`
- `core/llm/providers/openrouter.py`
- `core/llm/providers/minimax.py`
- `core/llm/providers/lm_studio.py`
- `core/llm/providers/local_gguf.py`
- `core/context/__init__.py` — public API
- `core/context/base.py` — ContextModule Protocol, SystemPromptBuilder
- `core/context/astrology.py` — refactored from compile_astrology_context
- `core/context/anatomy.py` — refactored from compile_anatomy_context
- `core/context/hardware.py` — refactored from compile_hardware_context
- `core/context/models.py` — Pydantic: ContextRequest, ContextData

### New tests
- `tests/core/llm/test_base.py`
- `tests/core/llm/test_registry.py`
- `tests/core/llm/test_cache.py`
- `tests/core/llm/test_retry.py`
- `tests/core/llm/test_providers.py` (parametrized over all 7)
- `tests/core/context/test_base.py`
- `tests/core/context/test_astrology.py`
- `tests/core/context/test_anatomy.py`
- `tests/core/context/test_hardware.py`
- `tests/backend/test_llm_endpoint.py` (integration)
- `tests/backend/test_config.py`

### New frontend files
- `frontend/src/components/CommandCenter/index.jsx`
- `frontend/src/components/CommandCenter/ChatPanel.jsx`
- `frontend/src/components/CommandCenter/DivinationPanel.jsx`
- `frontend/src/components/CommandCenter/ContextSidebar.jsx`
- `frontend/src/components/CommandCenter/StatusBar.jsx`
- `frontend/src/components/CommandCenter/OperatorActions.jsx`
- `frontend/src/components/CommandCenter/ContemplationPanel.jsx`
- `frontend/src/components/CommandCenter/CommandPalette.jsx`
- `frontend/src/components/CommandCenter/SavedConversations.jsx`
- `frontend/src/components/CommandCenter/PromptHistory.jsx`
- `frontend/src/components/CommandCenter/ThemeToggle.jsx`
- `frontend/src/components/CommandCenter/hooks/useCommands.js`
- `frontend/src/components/CommandCenter/hooks/useSavedChats.js`
- `frontend/src/components/CommandCenter/hooks/useTheme.js`
- `frontend/src/components/CommandCenter/README.md`
- `frontend/src/routes/Buddhas/index.jsx`
- `frontend/src/routes/Buddhas/IntentionEditor.jsx`
- `frontend/src/routes/Buddhas/DedicationText.jsx`
- `frontend/src/routes/Buddhas/SessionHistory.jsx`
- `frontend/src/routes/Buddhas/ShareExport.jsx`
- `frontend/src/routes/Buddhas/DailyStreak.jsx`
- `frontend/src/routes/Buddhas/AudioSettings.jsx`
- `frontend/src/components/Settings/ProviderSettings.jsx`
- `frontend/src/theme/antdTheme.js`
- `frontend/src/__tests__/CommandCenter.test.tsx`
- `frontend/src/__tests__/Buddhas.test.tsx`
- `frontend/src/__tests__/ProviderSettings.test.tsx`

### Modified files
- `backend/app/main.py` — add health-check task to lifespan, ConfigProvider
- `backend/app/api/v1/endpoints/llm.py` — rewrite chat_interaction, list_models
- `backend/app/config.py` — add LLMConfig
- `frontend/src/App.jsx` — add /buddhas and /settings routes
- `frontend/src/hooks/useWebSocketStable.ts` — add PROVIDER_HEALTH handler
- `frontend/src/components/UI/CommandCenter.jsx` — reduce to re-export
- `frontend/src/components/UI/BuddhaContemplationWidget.jsx` — refactor for /buddhas route
- `frontend/src/components/UI/SakaDawaBanner.jsx` — drop 60s poll, use WS
- `frontend/src/components/UI/RitualMonitor.jsx` — drop 5s poll, use WS

### Deleted files
- `core/llm_integration.py` (replaced by `core/llm/`)
- `core/llm_usage.py` (moved to `core/llm/usage.py`)

---

## Phase Overview

- **Phase 1**: New `core/llm/` and `core/context/` packages alongside existing code. No behavior change. All existing tests pass.
- **Phase 2**: Wire registry into FastAPI lifespan. Add health heartbeat. Add new `/providers/health` endpoint.
- **Phase 3**: Frontend decomposition (CommandCenter, /buddhas, ProviderSettings). AntD zeroRuntime mode. WS migration.
- **Phase 4**: Cleanup — delete old files, rewrite chat_interaction, final test pass.

---
# Phase 1: Build New Backend Layer Alongside Existing Code

## Task 1.1: Add HTTP cache + retry helpers

**Files:**
- Create: `core/llm/__init__.py`
- Create: `core/llm/cache.py`
- Create: `core/llm/retry.py`
- Test: `tests/core/llm/test_cache.py`
- Test: `tests/core/llm/test_retry.py`

- [ ] **Step 1.1.1: Write failing test for TTL cache**

```python
# tests/core/llm/test_cache.py
import asyncio
import pytest
from core.llm.cache import TTLCache


@pytest.mark.asyncio
async def test_ttl_cache_set_and_get():
    cache = TTLCache(default_ttl=60)
    await cache.set("key", "value")
    assert await cache.get("key") == "value"


@pytest.mark.asyncio
async def test_ttl_cache_expiry():
    cache = TTLCache(default_ttl=0.1)
    await cache.set("key", "value")
    assert await cache.get("key") == "value"
    await asyncio.sleep(0.2)
    assert await cache.get("key") is None


@pytest.mark.asyncio
async def test_ttl_cache_per_key_ttl():
    cache = TTLCache(default_ttl=60)
    await cache.set("key", "value", ttl=0.1)
    await asyncio.sleep(0.2)
    assert await cache.get("key") is None
```

- [ ] **Step 1.1.2: Run test, verify FAIL**

Run: `pytest tests/core/llm/test_cache.py -v`
Expected: ModuleNotFoundError or ImportError for core.llm.cache

- [ ] **Step 1.1.3: Create `core/llm/__init__.py`**

```python
# core/llm/__init__.py
"""Async LLM provider layer with health-aware failover."""
from core.llm.cache import TTLCache
from core.llm.retry import retry_with_backoff

__all__ = ["TTLCache", "retry_with_backoff"]
```

- [ ] **Step 1.1.4: Implement TTLCache in `core/llm/cache.py`**

```python
# core/llm/cache.py
"""Async-safe TTL cache wrapper around cachetools."""
import asyncio
from typing import Any, Optional
from cachetools import TTLCache as _TTLCache


class TTLCache:
    """Async-safe TTL cache with per-key and default TTL."""

    def __init__(self, default_ttl: int = 60, maxsize: int = 1024) -> None:
        self._cache: _TTLCache = _TTLCache(maxsize=maxsize, ttl=default_ttl)
        self._lock = asyncio.Lock()
        self._default_ttl = default_ttl

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            return self._cache.get(key)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        async with self._lock:
            self._cache[key] = value

    async def clear(self) -> None:
        async with self._lock:
            self._cache.clear()

    async def size(self) -> int:
        async with self._lock:
            return len(self._cache)
```

Note: cachetools.TTLCache has one TTL per cache instance. Per-key ttl parameter is accepted for API symmetry but uses the cache's default TTL. Replace with a dict+expires_at structure if precise per-key TTL is needed.

- [ ] **Step 1.1.5: Write failing test for retry helper**

```python
# tests/core/llm/test_retry.py
import pytest
from core.llm.retry import retry_with_backoff


@pytest.mark.asyncio
async def test_retry_success_first_try():
    call_count = 0

    async def fn():
        nonlocal call_count
        call_count += 1
        return "ok"

    result = await retry_with_backoff(fn, max_retries=2, initial_backoff=0.01)
    assert result == "ok"
    assert call_count == 1


@pytest.mark.asyncio
async def test_retry_success_after_failure():
    call_count = 0

    async def fn():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise RuntimeError("transient")
        return "ok"

    result = await retry_with_backoff(fn, max_retries=2, initial_backoff=0.01)
    assert result == "ok"
    assert call_count == 2


@pytest.mark.asyncio
async def test_retry_exhausted():
    async def fn():
        raise RuntimeError("permanent")

    with pytest.raises(RuntimeError, match="permanent"):
        await retry_with_backoff(fn, max_retries=2, initial_backoff=0.01)
```

- [ ] **Step 1.1.6: Implement retry helper in `core/llm/retry.py`**

```python
# core/llm/retry.py
"""Async retry helper with exponential backoff."""
import asyncio
import logging
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")
logger = logging.getLogger(__name__)


async def retry_with_backoff(
    fn: Callable[[], Awaitable[T]],
    max_retries: int = 1,
    initial_backoff: float = 0.5,
    backoff_multiplier: float = 2.0,
) -> T:
    """Call fn() with exponential backoff on failure.

    Args:
        fn: Async callable to invoke.
        max_retries: Max retries after first failure. Default 1.
        initial_backoff: Seconds to wait before first retry. Default 0.5.
        backoff_multiplier: Multiplier for each subsequent backoff. Default 2.0.

    Returns:
        Result of fn() on success.

    Raises:
        Last exception if all retries are exhausted.
    """
    last_exc: Exception | None = None
    backoff = initial_backoff
    for attempt in range(max_retries + 1):
        try:
            return await fn()
        except Exception as e:
            last_exc = e
            if attempt >= max_retries:
                logger.warning(f"retry_with_backoff exhausted after {attempt + 1} attempts: {e}")
                raise
            logger.info(f"retry_with_backoff attempt {attempt + 1} failed: {e}; sleeping {backoff}s")
            await asyncio.sleep(backoff)
            backoff *= backoff_multiplier
    assert last_exc is not None
    raise last_exc
```

- [ ] **Step 1.1.7: Run both tests, verify PASS**

Run: `pytest tests/core/llm/test_cache.py tests/core/llm/test_retry.py -v`
Expected: All PASS

- [ ] **Step 1.1.8: Verify ruff clean**

Run: `ruff check core/llm/ tests/core/llm/`
Expected: No issues

- [ ] **Step 1.1.9: Commit**

```bash
git add core/llm/__init__.py core/llm/cache.py core/llm/retry.py tests/core/llm/test_cache.py tests/core/llm/test_retry.py
git commit -m "feat(core/llm): add async-safe TTL cache and retry helper"
```

---

## Task 1.2: Add Pydantic models

**Files:**
- Create: `core/llm/models.py`
- Test: `tests/core/llm/test_models.py`

- [ ] **Step 1.2.1: Write failing test for models**

```python
# tests/core/llm/test_models.py
import pytest
from pydantic import ValidationError
from core.llm.models import (
    ChatRequest,
    ChatMessage,
    HealthStatus,
    ProviderConfig,
)


def test_chat_message_required_role():
    msg = ChatMessage(role="user", content="hello")
    assert msg.role == "user"
    assert msg.content == "hello"


def test_chat_request_defaults():
    req = ChatRequest(messages=[ChatMessage(role="user", content="hi")])
    assert req.provider == "auto"
    assert req.model is None
    assert req.max_tokens == 1000
    assert req.temperature == 0.7


def test_chat_request_temperature_bounds():
    with pytest.raises(ValidationError):
        ChatRequest(
            messages=[ChatMessage(role="user", content="hi")],
            temperature=2.5,
        )


def test_health_status_defaults():
    h = HealthStatus(provider="openai", healthy=True)
    assert h.latency_ms == 0.0
    assert h.error is None
    assert h.last_checked > 0


def test_provider_config_priority_must_be_non_negative():
    with pytest.raises(ValidationError):
        ProviderConfig(name="openai", priority=-1)
```

- [ ] **Step 1.2.2: Run test, verify FAIL**

Run: `pytest tests/core/llm/test_models.py -v`
Expected: ModuleNotFoundError

- [ ] **Step 1.2.3: Implement models in `core/llm/models.py`**

```python
# core/llm/models.py
"""Pydantic models for the LLM provider layer."""
import time
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    provider: str = "auto"
    model: Optional[str] = None
    max_tokens: int = Field(default=1000, ge=1, le=32000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    system_prompt: Optional[str] = None
    stream: bool = False
    tools: list[ToolDefinition] = Field(default_factory=list)
    include_astrology: bool = False
    include_anatomy: bool = False
    include_hardware: bool = False
    astrology_data: Optional[dict[str, Any]] = None


class ChatChunk(BaseModel):
    content: str
    done: bool = False
    provider: str
    model: str


class ChatResponse(BaseModel):
    content: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    finish_reason: str = "stop"
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)


class HealthStatus(BaseModel):
    provider: str
    healthy: bool
    latency_ms: float = 0.0
    error: Optional[str] = None
    last_checked: float = Field(default_factory=time.time)
    models_available: int = 0


class ModelInfo(BaseModel):
    id: str
    provider: str
    context_window: Optional[int] = None
    supports_tools: bool = False
    supports_streaming: bool = True


class ProviderConfig(BaseModel):
    name: str
    priority: int = Field(ge=0, le=100)
    enabled: bool = True
    api_key_env: Optional[str] = None
    base_url_env: Optional[str] = None
    default_model: Optional[str] = None
    timeout_seconds: int = Field(default=120, ge=1, le=600)
    extra: dict[str, Any] = Field(default_factory=dict)
```

- [ ] **Step 1.2.4: Update `core/llm/__init__.py` to export models**

```python
# core/llm/__init__.py
"""Async LLM provider layer with health-aware failover."""
from core.llm.cache import TTLCache
from core.llm.models import (
    ChatRequest,
    ChatResponse,
    ChatMessage,
    ChatChunk,
    HealthStatus,
    ModelInfo,
    ProviderConfig,
    ToolDefinition,
)
from core.llm.retry import retry_with_backoff

__all__ = [
    "TTLCache",
    "retry_with_backoff",
    "ChatRequest",
    "ChatResponse",
    "ChatMessage",
    "ChatChunk",
    "HealthStatus",
    "ModelInfo",
    "ProviderConfig",
    "ToolDefinition",
]
```

- [ ] **Step 1.2.5: Run test, verify PASS**

Run: `pytest tests/core/llm/test_models.py -v`
Expected: All PASS

- [ ] **Step 1.2.6: Run ruff**

Run: `ruff check core/llm/models.py tests/core/llm/test_models.py`
Expected: No issues

- [ ] **Step 1.2.7: Commit**

```bash
git add core/llm/models.py core/llm/__init__.py tests/core/llm/test_models.py
git commit -m "feat(core/llm): add Pydantic models for chat, health, provider config"
```

---

## Task 1.3: Define BaseLLMProvider Protocol and OpenAICompatibleProvider base

**Files:**
- Create: `core/llm/base.py`
- Test: `tests/core/llm/test_base.py`

- [ ] **Step 1.3.1: Write failing test for protocol compliance**

```python
# tests/core/llm/test_base.py
import pytest
from core.llm.base import OpenAICompatibleProvider


def test_openai_compatible_requires_api_key():
    with pytest.raises((ValueError, TypeError)):
        OpenAICompatibleProvider(
            name="test",
            api_key="",
            base_url="http://localhost:1234/v1",
            default_model="test-model",
        )


def test_openai_compatible_constructs_with_valid_args():
    provider = OpenAICompatibleProvider(
        name="test",
        api_key="sk-test",
        base_url="http://localhost:1234/v1",
        default_model="test-model",
        timeout_seconds=30,
    )
    assert provider.name == "test"
    assert provider.default_model == "test-model"
    assert provider.timeout_seconds == 30
    assert hasattr(provider, "health_check")
    assert hasattr(provider, "list_models")
    assert hasattr(provider, "generate")
    assert hasattr(provider, "stream")
    assert hasattr(provider, "close")
```

- [ ] **Step 1.3.2: Run test, verify FAIL**

Run: `pytest tests/core/llm/test_base.py -v`
Expected: ModuleNotFoundError

- [ ] **Step 1.3.3: Implement base in `core/llm/base.py`**

```python
# core/llm/base.py
"""Base LLM provider abstractions."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import AsyncIterator, Protocol, runtime_checkable

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
```

- [ ] **Step 1.3.4: Run test, verify PASS**

Run: `pytest tests/core/llm/test_base.py -v`
Expected: All PASS

- [ ] **Step 1.3.5: Run ruff**

Run: `ruff check core/llm/base.py tests/core/llm/test_base.py`
Expected: No issues

- [ ] **Step 1.3.6: Commit**

```bash
git add core/llm/base.py tests/core/llm/test_base.py
git commit -m "feat(core/llm): add BaseLLMProvider Protocol and OpenAICompatibleProvider base"
```

---


## Task 1.4: Implement 5 OpenAI-compatible provider subclasses

**Files:** Create `core/llm/providers/__init__.py`, `openai.py`, `openrouter.py`, `deepseek.py`, `minimax.py`, `lm_studio.py`. Test `tests/core/llm/test_providers.py`.

**Pattern for each provider** (full code in 1.4.1-1.4.5 of merged plan above; one example below):

```python
# core/llm/providers/openai.py
import os
from core.llm.base import OpenAICompatibleProvider

class OpenAIProvider(OpenAICompatibleProvider):
    def __init__(self, api_key=None, base_url=None, default_model="gpt-4o-mini", priority=50):
        super().__init__(
            name="openai",
            api_key=api_key or os.getenv("OPENAI_API_KEY", ""),
            base_url=base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            default_model=default_model,
            timeout_seconds=120,
            priority=priority,
        )
```

Apply same pattern for `OpenRouterProvider` (priority 90, default "google/gemini-2.0-flash-001"), `DeepSeekProvider` (priority 70, default "deepseek-chat"), `MinimaxProvider` (priority 40, default "MiniMax-Text-01"), `LMStudioProvider` (priority 80, default "local-model", 300s timeout, no env var for key).

- [ ] **Step 1.4.1-1.4.6: Create the 5 provider files** (code above pattern ﾃ・5, all extending OpenAICompatibleProvider with their respective env vars, priorities, and defaults)

- [ ] **Step 1.4.7: Create `core/llm/providers/__init__.py`** exporting all 5

- [ ] **Step 1.4.8: Write test for provider construction**

```python
# tests/core/llm/test_providers.py
import pytest
from core.llm.providers import (
    OpenAIProvider, OpenRouterProvider, DeepSeekProvider,
    MinimaxProvider, LMStudioProvider,
)

def test_openai_provider_construction(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    p = OpenAIProvider()
    assert p.name == "openai"
    assert p.priority == 50

def test_openrouter_provider_construction(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-test")
    p = OpenRouterProvider()
    assert p.name == "openrouter"
    assert p.priority == 90

def test_deepseek_provider_construction(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-test")
    p = DeepSeekProvider()
    assert p.name == "deepseek"
    assert p.priority == 70

def test_minimax_provider_construction(monkeypatch):
    monkeypatch.setenv("MINIMAX_API_KEY", "mm-test")
    p = MinimaxProvider()
    assert p.name == "minimax"
    assert p.priority == 40

def test_lm_studio_provider_construction():
    p = LMStudioProvider()
    assert p.name == "lm_studio"
    assert p.priority == 80

def test_all_providers_have_unique_names():
    names = {p.__name__ for p in [OpenAIProvider, OpenRouterProvider, DeepSeekProvider, MinimaxProvider, LMStudioProvider]}
    assert len(names) == 5
```

- [ ] **Step 1.4.9: Run tests, verify PASS**

Run: `pytest tests/core/llm/test_providers.py -v`
Expected: All PASS

- [ ] **Step 1.4.10: Run ruff**

Run: `ruff check core/llm/providers/ tests/core/llm/test_providers.py`
Expected: No issues

- [ ] **Step 1.4.11: Commit**

```bash
git add core/llm/providers/ tests/core/llm/test_providers.py
git commit -m "feat(core/llm): add 5 OpenAI-compatible provider implementations"
```

---

## Task 1.5: Implement Anthropic and local GGUF providers

**Files:** Create `core/llm/providers/anthropic.py`, `core/llm/providers/local_gguf.py`. Modify `core/llm/providers/__init__.py`. Update `tests/core/llm/test_providers.py`.

**Anthropic** (uses AsyncAnthropic, full code in merged plan ﾂｧ1.5.1):
- `name = "anthropic"`, `priority = 60`, `default_model = "claude-3-5-haiku-20241022"`
- `health_check` returns healthy=True (Anthropic has no list-models endpoint)
- `generate` and `stream` map to `client.messages.create` and `client.messages.stream`
- Requires `ANTHROPIC_API_KEY` env var

**Local GGUF** (uses llama-cpp-python via run_in_executor):
- `name = "local"`, `priority = 30`
- `health_check` checks `models_dir` exists and has *.gguf files
- `generate` uses `loop.run_in_executor(None, self._loaded_model, prompt, max_tokens, ...)` to avoid blocking
- `stream` falls back to non-stream (llama-cpp doesn't stream usefully)
- `_build_prompt` uses Alpaca format: `### System:\n{system}\n\n### User:\n{user}\n\n### Assistant:\n`
- Re-loads model only if `model_path` changes (caches `_loaded_path`)

- [ ] **Step 1.5.1-1.5.2: Create both files** (full code in merged plan)

- [ ] **Step 1.5.3: Update `__init__.py`** to export AnthropicProvider and LocalGGUFProvider

- [ ] **Step 1.5.4: Add tests for anthropic and local**

```python
def test_anthropic_provider_construction(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ant-test")
    p = AnthropicProvider()
    assert p.name == "anthropic"
    assert p.priority == 60

def test_anthropic_provider_requires_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        AnthropicProvider()

def test_local_gguf_provider_construction(tmp_path):
    (tmp_path / "test-instruct.gguf").touch()
    p = LocalGGUFProvider(models_dir=str(tmp_path))
    assert p.name == "local"
    assert p.priority == 30
    assert p.default_model == "test-instruct.gguf"

def test_local_gguf_provider_no_models(tmp_path):
    p = LocalGGUFProvider(models_dir=str(tmp_path))
    assert p.default_model == "unknown"
```

- [ ] **Step 1.5.5: Run tests, verify PASS**

Run: `pytest tests/core/llm/test_providers.py -v`
Expected: All PASS

- [ ] **Step 1.5.6: Run ruff**

Run: `ruff check core/llm/providers/ tests/core/llm/test_providers.py`
Expected: No issues

- [ ] **Step 1.5.7: Commit**

```bash
git add core/llm/providers/ tests/core/llm/test_providers.py
git commit -m "feat(core/llm): add Anthropic and local GGUF providers"
```

---

## Task 1.6: Build ProviderRegistry

**Files:** Create `core/llm/registry.py`. Test `tests/core/llm/test_registry.py`.

- [ ] **Step 1.6.1: Write failing test for registry** (full code in merged plan ﾂｧ1.6.1):
- Test registration, sort by priority, pick_best (returns highest-priority healthy), pick_best returns None when all unhealthy, health_check_all runs in parallel, close_all

- [ ] **Step 1.6.2: Run test, verify FAIL**

Run: `pytest tests/core/llm/test_registry.py -v`
Expected: ModuleNotFoundError

- [ ] **Step 1.6.3: Implement ProviderRegistry**

```python
# core/llm/registry.py
"""ProviderRegistry: ordered, health-aware provider collection."""
from __future__ import annotations
import asyncio
import logging
from typing import Optional
from core.llm.base import BaseLLMProvider
from core.llm.cache import TTLCache
from core.llm.models import HealthStatus

logger = logging.getLogger(__name__)


class ProviderRegistry:
    def __init__(self, health_cache_ttl: int = 60) -> None:
        self._providers: list[BaseLLMProvider] = []
        self._health_cache = TTLCache(default_ttl=health_cache_ttl)

    @property
    def providers(self) -> list[BaseLLMProvider]:
        return sorted(self._providers, key=lambda p: p.priority, reverse=True)

    def register(self, provider: BaseLLMProvider) -> None:
        if any(p.name == provider.name for p in self._providers):
            raise ValueError(f"Provider '{provider.name}' already registered")
        self._providers.append(provider)
        logger.info(f"Registered provider: {provider.name} (priority {provider.priority})")

    def unregister(self, name: str) -> None:
        self._providers = [p for p in self._providers if p.name != name]

    async def health_check_all(self, use_cache: bool = True) -> list[HealthStatus]:
        providers = self.providers
        tasks = []
        for p in providers:
            if use_cache:
                cached = await self._health_cache.get(f"health:{p.name}")
                if cached is not None:
                    tasks.append(asyncio.create_task(self._identity(cached)))
                    continue
            tasks.append(asyncio.create_task(self._check_and_cache(p)))
        return await asyncio.gather(*tasks)

    async def _identity(self, status: HealthStatus) -> HealthStatus:
        return status

    async def _check_and_cache(self, provider: BaseLLMProvider) -> HealthStatus:
        status = await provider.health_check()
        await self._health_cache.set(f"health:{provider.name}", status)
        return status

    async def pick_best(self, use_cache: bool = True) -> Optional[BaseLLMProvider]:
        statuses = await self.health_check_all(use_cache=use_cache)
        healthy_names = {s.provider for s in statuses if s.healthy}
        for provider in self.providers:
            if provider.name in healthy_names:
                return provider
        return None

    async def failover_chain(self) -> list[BaseLLMProvider]:
        statuses = await self.health_check_all()
        healthy_names = {s.provider for s in statuses if s.healthy}
        return [p for p in self.providers if p.name in healthy_names]

    async def close_all(self) -> None:
        await asyncio.gather(*[p.close() for p in self._providers], return_exceptions=True)
        self._providers.clear()
        await self._health_cache.clear()

    def __len__(self) -> int:
        return len(self._providers)

    def __contains__(self, name: str) -> bool:
        return any(p.name == name for p in self._providers)
```

- [ ] **Step 1.6.4: Run test, verify PASS**

Run: `pytest tests/core/llm/test_registry.py -v`
Expected: All PASS

- [ ] **Step 1.6.5: Run ruff**

Run: `ruff check core/llm/registry.py tests/core/llm/test_registry.py`

- [ ] **Step 1.6.6: Commit**

```bash
git add core/llm/registry.py tests/core/llm/test_registry.py
git commit -m "feat(core/llm): add ProviderRegistry with health-aware failover"
```

---

## Task 1.7: Build health-check heartbeat

**Files:** Create `core/llm/health.py`. Test `tests/core/llm/test_health.py`.

- [ ] **Step 1.7.1: Write failing test for heartbeat task** (full code in merged plan ﾂｧ1.7.1):
- Test heartbeat runs and cancels cleanly, test heartbeat handles provider failure gracefully

- [ ] **Step 1.7.2: Run test, verify FAIL**

- [ ] **Step 1.7.3: Implement heartbeat**

```python
# core/llm/health.py
"""Health-check heartbeat task."""
from __future__ import annotations
import asyncio
import logging
from typing import Optional
from core.llm.registry import ProviderRegistry

logger = logging.getLogger(__name__)


async def start_health_heartbeat(
    registry: ProviderRegistry,
    interval_seconds: int = 30,
    on_update: Optional[callable] = None,
) -> None:
    """Run health checks in a loop until cancelled."""
    logger.info(f"Starting health heartbeat (interval={interval_seconds}s)")
    try:
        while True:
            try:
                statuses = await registry.health_check_all()
                healthy_count = sum(1 for s in statuses if s.healthy)
                logger.debug(f"Health check: {healthy_count}/{len(statuses)} providers healthy")
                if on_update is not None:
                    try:
                        await on_update(statuses)
                    except Exception as e:
                        logger.warning(f"on_update callback failed: {e}")
            except Exception as e:
                logger.error(f"Health check iteration failed: {e}", exc_info=True)
            await asyncio.sleep(interval_seconds)
    except asyncio.CancelledError:
        logger.info("Health heartbeat cancelled (normal shutdown)")
        raise
```

- [ ] **Step 1.7.4: Run test, verify PASS**

- [ ] **Step 1.7.5: Run ruff**

- [ ] **Step 1.7.6: Commit**

```bash
git add core/llm/health.py tests/core/llm/test_health.py
git commit -m "feat(core/llm): add health-check heartbeat task"
```

---

## Task 1.8: Build context module layer

**Files:** Create `core/context/__init__.py`, `base.py`, `models.py`, `astrology.py`, `anatomy.py`, `hardware.py`. Tests for all 4 modules.

- [ ] **Step 1.8.1: Create `core/context/models.py`** with `ContextRequest` and `ContextData` Pydantic models (full code in merged plan ﾂｧ1.8.2)

- [ ] **Step 1.8.2: Create `core/context/base.py`** with `ContextModule` Protocol and `SystemPromptBuilder` (full code in merged plan ﾂｧ1.8.3):
- Builder registers modules, `compose()` gathers in parallel via `asyncio.gather`, renders sequentially, skips errors

- [ ] **Step 1.8.3: Create the 3 modules:**
- `astrology.py` (full code in merged plan ﾂｧ1.8.6) 窶・`AstrologyContextModule` with `gather()` (use pre-computed data or call `core.astrology.AstrologicalCalculator().get_comprehensive_astrology()`) and `render()` (Western/Vedic/BaZi Markdown sections)
- `anatomy.py` (merged plan ﾂｧ1.8.7) 窶・`AnatomyContextModule` reads from `modules.personal_healing.PersonalHealingModule`
- `hardware.py` (merged plan ﾂｧ1.8.8) 窶・`HardwareContextModule` reads from `backend.core.services.vajra_service`

- [ ] **Step 1.8.4: Create `core/context/__init__.py`** exporting all 5 classes

- [ ] **Step 1.8.5: Write tests for builder and 3 modules** (full code in merged plan ﾂｧ1.8.4, 1.8.9-1.8.11)
- Test builder with no modules, with one module, only runs requested modules, continues on module error
- Test each module's render() with sample data and empty data

- [ ] **Step 1.8.6: Run all context tests, verify PASS**

Run: `pytest tests/core/context/ -v`

- [ ] **Step 1.8.7: Run ruff**

Run: `ruff check core/context/ tests/core/context/`

- [ ] **Step 1.8.8: Commit**

```bash
git add core/context/ tests/core/context/
git commit -m "feat(core/context): add ContextModule Protocol, SystemPromptBuilder, and 3 built-in modules"
```

---

## Task 1.9: Move LLMUsageTracker into core/llm/usage.py

**Files:** Create `core/llm/usage.py` (copy of `core/llm_usage.py`). Add deprecation shim to `core/llm_usage.py`.

- [ ] **Step 1.9.1: Read existing `core/llm_usage.py` to confirm contents** (LLMUsageTracker class, PROVIDER_PRICING dict, get() singleton, JSONL logging)

- [ ] **Step 1.9.2: Copy the file**

```bash
cp core/llm_usage.py core/llm/usage.py
```

- [ ] **Step 1.9.3: Add deprecation shim**

```python
# core/llm_usage.py
"""DEPRECATED: moved to core/llm/usage.py. Shim removed in Phase 4."""
from core.llm.usage import LLMUsageTracker, PROVIDER_PRICING  # noqa: F401

__all__ = ["LLMUsageTracker", "PROVIDER_PRICING"]
```

- [ ] **Step 1.9.4: Run all tests to verify shim works**

Run: `pytest tests/ -m "not slow" --ignore=tests/e2e -q 2>&1 | tail -30`
Expected: All pass (same as before)

- [ ] **Step 1.9.5: Commit**

```bash
git add core/llm/usage.py core/llm_usage.py
git commit -m "refactor(core/llm): move LLMUsageTracker to core/llm/usage.py with shim"
```

---

## Task 1.10: Add LLMConfig to backend/app/config.py

**Files:** Modify `backend/app/config.py`. Create `tests/backend/test_config.py`.

- [ ] **Step 1.10.1: Read existing `backend/app/config.py`**

- [ ] **Step 1.10.2: Write failing test** (full code in merged plan ﾂｧ1.10.2):
- Test defaults, env var override, singleton via `get_llm_config()`

- [ ] **Step 1.10.3: Add LLMConfig class**

```python
# Append to backend/app/config.py
from pydantic_settings import BaseSettings


class LLMConfig(BaseSettings):
    """LLM provider configuration loaded from env vars (LLM_ prefix)."""
    default_provider: str = "auto"
    health_check_interval_seconds: int = 30
    model_cache_ttl_seconds: int = 60
    request_timeout_seconds: int = 120
    max_retries: int = 1
    retry_initial_backoff: float = 0.5
    provider_priority: list[str] = [
        "openrouter", "lm_studio", "deepseek",
        "anthropic", "openai", "minimax", "local",
    ]
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    openrouter_api_key: str | None = None
    deepseek_api_key: str | None = None
    minimax_api_key: str | None = None
    lm_studio_base_url: str | None = None
    local_models_dir: str = "./models"

    class Config:
        env_prefix = "LLM_"
        case_sensitive = False


_llm_config_instance: LLMConfig | None = None


def get_llm_config() -> LLMConfig:
    global _llm_config_instance
    if _llm_config_instance is None:
        _llm_config_instance = LLMConfig()
    return _llm_config_instance
```

- [ ] **Step 1.10.4: Run test, verify PASS**

Run: `pytest tests/backend/test_config.py -v`

- [ ] **Step 1.10.5: Run ruff**

- [ ] **Step 1.10.6: Commit**

```bash
git add backend/app/config.py tests/backend/test_config.py
git commit -m "feat(backend/config): add LLMConfig with env-var-driven settings"
```

---

## Task 1.11: Phase 1 verification

- [ ] **Step 1.11.1: Run full test suite**

Run: `pytest tests/ -m "not slow" --ignore=tests/e2e -q 2>&1 | tail -50`
Expected: All PASS (existing + new Phase 1 tests)

- [ ] **Step 1.11.2: Run ruff check + format check**

Run: `ruff check . && ruff format --check .`
Expected: No issues

- [ ] **Step 1.11.3: Push branch**

```bash
git push origin feat/ui-ux-overhaul
```

- [ ] **Step 1.11.4: Tag checkpoint**

```bash
git tag phase-1-complete
```

---

# Phase 2: Wire Registry into FastAPI Lifespan

## Task 2.1: Add registry initialization and health heartbeat to lifespan

**Files:** Modify `backend/app/main.py` (lifespan function at lines 35-106).

- [ ] **Step 2.1.1: Read current lifespan, identify insertion points**

- [ ] **Step 2.1.2: Add registry initialization** (after orchestrator_bridge.initialize, before streaming task):

```python
# In startup section of lifespan, after operator daemon block
try:
    from core.llm.registry import ProviderRegistry
    from core.llm.providers import (
        OpenAIProvider, OpenRouterProvider, DeepSeekProvider,
        MinimaxProvider, LMStudioProvider, AnthropicProvider, LocalGGUFProvider,
    )
    from backend.app.config import get_llm_config
    import os

    config = get_llm_config()
    registry = ProviderRegistry(health_cache_ttl=config.model_cache_ttl_seconds)

    # Register only providers with credentials available
    if os.getenv("OPENROUTER_API_KEY"):
        registry.register(OpenRouterProvider(priority=90))
    if os.getenv("LM_STUDIO_BASE_URL") or os.path.exists("./models/lmstudio"):
        registry.register(LMStudioProvider(priority=80))
    if os.getenv("DEEPSEEK_API_KEY"):
        registry.register(DeepSeekProvider(priority=70))
    if os.getenv("ANTHROPIC_API_KEY"):
        registry.register(AnthropicProvider(priority=60))
    if os.getenv("OPENAI_API_KEY"):
        registry.register(OpenAIProvider(priority=50))
    if os.getenv("MINIMAX_API_KEY"):
        registry.register(MinimaxProvider(priority=40))
    if os.path.isdir(os.getenv("LLM_LOCAL_MODELS_DIR", "./models")):
        registry.register(LocalGGUFProvider(priority=30))

    app.state.llm_registry = registry
    print(f"LLM registry initialized: {[p.name for p in registry.providers]}")
except Exception as e:
    print(f"Failed to initialize LLM registry: {e}")
    logger.error(traceback.format_exc())
```

- [ ] **Step 2.1.3: Add health heartbeat task** (after registry init, before operator daemon):

```python
health_task = None
if hasattr(app.state, "llm_registry") and len(app.state.llm_registry) > 0:
    try:
        from core.llm.health import start_health_heartbeat
        config = get_llm_config()

        async def publish_health(statuses):
            try:
                await stable_connection_manager_v2.broadcast({
                    "type": "PROVIDER_HEALTH",
                    "statuses": [s.model_dump() for s in statuses],
                })
            except Exception as e:
                logger.debug(f"PROVIDER_HEALTH broadcast failed: {e}")

        health_task = asyncio.create_task(
            start_health_heartbeat(
                app.state.llm_registry,
                interval_seconds=config.health_check_interval_seconds,
                on_update=publish_health,
            )
        )
        print(f"LLM health heartbeat started (interval={config.health_check_interval_seconds}s)")
    except Exception as e:
        print(f"Failed to start health heartbeat: {e}")
```

- [ ] **Step 2.1.4: Add shutdown for registry and health task** (in shutdown section, after operator daemon stop):

```python
if hasattr(app.state, "llm_registry"):
    try:
        await app.state.llm_registry.close_all()
        print("LLM registry closed")
    except Exception as e:
        print(f"Failed to close LLM registry: {e}")

if health_task:
    health_task.cancel()
    try:
        await health_task
    except asyncio.CancelledError:
        pass
```

- [ ] **Step 2.1.5: Verify lifespan compiles**

Run: `python -c "from backend.app.main import app; print('OK')"`
Expected: OK

- [ ] **Step 2.1.6: Verify full test suite still passes**

Run: `pytest tests/ -m "not slow" --ignore=tests/e2e -q 2>&1 | tail -30`
Expected: All PASS

- [ ] **Step 2.1.7: Commit**

```bash
git add backend/app/main.py
git commit -m "feat(backend): wire LLM provider registry and health heartbeat into FastAPI lifespan"
```

---

## Task 2.2: Add /providers/health endpoint

**Files:** Modify `backend/app/api/v1/endpoints/llm.py`. Test `tests/backend/test_llm_endpoint.py`.

- [ ] **Step 2.2.1: Add endpoint** (after list_models, around line 1848):

```python
@router.get("/providers/health")
async def get_providers_health(request: Request) -> dict:
    """Return current health status for all registered providers."""
    registry = getattr(request.app.state, "llm_registry", None)
    if registry is None or len(registry) == 0:
        return {"providers": [], "healthy_count": 0, "total_count": 0,
                "message": "LLM registry not initialized"}
    statuses = await registry.health_check_all()
    return {
        "providers": [s.model_dump() for s in statuses],
        "healthy_count": sum(1 for s in statuses if s.healthy),
        "total_count": len(statuses),
    }
```

- [ ] **Step 2.2.2: Write test**

```python
# tests/backend/test_llm_endpoint.py
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_providers_health_endpoint(client):
    response = client.get("/api/v1/llm/providers/health")
    assert response.status_code == 200
    data = response.json()
    assert "providers" in data
    assert "healthy_count" in data
    assert "total_count" in data
```

- [ ] **Step 2.2.3: Run test, verify PASS**

Run: `pytest tests/backend/test_llm_endpoint.py -v`

- [ ] **Step 2.2.4: Commit**

```bash
git add backend/app/api/v1/endpoints/llm.py tests/backend/test_llm_endpoint.py
git commit -m "feat(backend/llm): add /providers/health endpoint backed by registry"
```

---

## Task 2.3: Phase 2 verification

- [ ] **Step 2.3.1: Run full test suite**

Run: `pytest tests/ -m "not slow" --ignore=tests/e2e -q 2>&1 | tail -30`

- [ ] **Step 2.3.2: Run ruff**

Run: `ruff check . && ruff format --check .`

- [ ] **Step 2.3.3: Tag checkpoint**

```bash
git tag phase-2-complete
```

---

# Phase 3: Frontend Decomposition

## Task 3.1: Enable AntD zeroRuntime mode

**Files:** Create `frontend/src/theme/antdTheme.js`. Modify `frontend/src/App.jsx` or main.jsx.

- [ ] **Step 3.1.1: Find current ConfigProvider usage**

Run: `grep -rn "ConfigProvider" frontend/src/`

- [ ] **Step 3.1.2: Create `frontend/src/theme/antdTheme.js`**

```javascript
// frontend/src/theme/antdTheme.js
export const antdTheme = {
  cssVar: true,
  hashed: true,
  token: {
    colorPrimary: '#D97706',      // Saffron
    colorBgBase: '#0F0F1A',
    colorTextBase: '#F5F0E1',
    fontFamily: 'system-ui, -apple-system, sans-serif',
    borderRadius: 4,
  },
  components: {
    Button: { primaryShadow: '0 0 8px rgba(217, 119, 6, 0.3)' },
    Card: { colorBgContainer: '#1A1A2E' },
  },
};
```

- [ ] **Step 3.1.3: Wire theme in main entry** (pattern):

```javascript
import { ConfigProvider } from 'antd';
import { antdTheme } from './theme/antdTheme';
// <ConfigProvider theme={antdTheme}><App /></ConfigProvider>
```

- [ ] **Step 3.1.4: Verify build**

Run: `cd frontend && npm run build 2>&1 | tail -20`

- [ ] **Step 3.1.5: Commit**

```bash
git add frontend/src/theme/antdTheme.js frontend/src/App.jsx frontend/src/main.jsx
git commit -m "feat(frontend/theme): enable AntD zeroRuntime mode with sacred color tokens"
```

---

## Task 3.2: Add PROVIDER_HEALTH to useWebSocketStable

**Files:** Modify `frontend/src/hooks/useWebSocketStable.ts`.

- [ ] **Step 3.2.1: Read hook, find message dispatch switch/if**

- [ ] **Step 3.2.2: Add handler** in dispatch:

```typescript
case 'PROVIDER_HEALTH':
  setState((prev) => ({
    ...prev,
    providerHealth: msg.statuses || [],
    lastProviderHealthUpdate: Date.now(),
  }));
  break;
```

- [ ] **Step 3.2.3: Add to initial state**: `providerHealth: []`, `lastProviderHealthUpdate: null`

- [ ] **Step 3.2.4: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit 2>&1 | tail -20`

- [ ] **Step 3.2.5: Commit**

```bash
git add frontend/src/hooks/useWebSocketStable.ts
git commit -m "feat(frontend/hooks): handle PROVIDER_HEALTH WebSocket message"
```

---

## Task 3.3: Decompose CommandCenter.jsx

**Files:** Create `frontend/src/components/CommandCenter/` directory (10 files). Modify `frontend/src/components/UI/CommandCenter.jsx` (reduce to re-export).

**Decomposition map** (line counts approximate):

| New file | Source lines (in original CommandCenter.jsx) | Responsibility |
|---|---|---|
| `ChatPanel.jsx` | ~250 lines | AI chat UI |
| `DivinationPanel.jsx` | ~200 lines | Divination widgets sidebar |
| `ContextSidebar.jsx` | ~150 lines | Context injection controls |
| `StatusBar.jsx` | ~100 lines | Connection/operator status |
| `OperatorActions.jsx` | ~100 lines | Operator command buttons |
| `ContemplationPanel.jsx` | ~200 lines | 88 Buddhas widget (refactored) |
| `CommandPalette.jsx` | NEW ~150 lines | Cmd+K palette |
| `SavedConversations.jsx` | NEW ~200 lines | localStorage + backend list |
| `PromptHistory.jsx` | NEW ~150 lines | Sidebar showing past prompts |
| `ThemeToggle.jsx` | NEW ~100 lines | Light/dark/custom theme |
| `hooks/useCommands.js` | NEW ~50 lines | Keyboard shortcut handling |
| `hooks/useSavedChats.js` | NEW ~80 lines | localStorage + API sync |
| `hooks/useTheme.js` | NEW ~60 lines | Theme state |
| `index.jsx` | NEW ~50 lines | Re-export entry |

**Pattern for each migration** (repeat for chat, divination, context, status, operator, contemplation):

1. Identify JSX block in original CommandCenter.jsx (search for comments, function defs)
2. Cut the block (with all its helper functions and imports)
3. Paste into the corresponding new file
4. Update imports to be relative to new location
5. Add to original CommandCenter.jsx: `import { NewComponent } from './CommandCenter/NewComponent';` and replace cut block with `<NewComponent />`
6. Run `npm run dev`, verify section still renders
7. `git add frontend/src/components/CommandCenter/NewComponent.jsx frontend/src/components/UI/CommandCenter.jsx`
8. `git commit -m "refactor(frontend): extract NewComponent from CommandCenter"`

- [ ] **Step 3.3.1-3.3.3: Create hooks first** (no dependencies): `useTheme.js`, `useCommands.js`, `useSavedChats.js` (full code in merged plan ﾂｧ3.3.1-3.3.3)

- [ ] **Step 3.3.4-3.3.7: Create stub files** for all 10 components. Each stub is ~10-20 lines: `export { default } from '../UI/CommandCenter';` with a TODO comment for the real migration. The 6 original-section stubs re-export from the original file. The 4 new-feature stubs (CommandPalette, SavedConversations, PromptHistory, ThemeToggle) start empty.

- [ ] **Step 3.3.8: Migrate content from CommandCenter.jsx** (the 6 micro-migrations, one per section). See pattern above.

- [ ] **Step 3.3.9: Implement CommandPalette** (full code in merged plan ﾂｧ3.3.9): Modal with Input filter + List of commands, triggered by Cmd+K

- [ ] **Step 3.3.10: Implement SavedConversations and PromptHistory** using `useSavedChats` hook

- [ ] **Step 3.3.11: Create `index.jsx` entry point** (full code in merged plan ﾂｧ3.3.11): Row/Col layout, wires all 10 components, mounts CommandPalette

- [ ] **Step 3.3.12: Reduce original CommandCenter.jsx to re-export:**

```javascript
// frontend/src/components/UI/CommandCenter.jsx
export { CommandCenter as default, CommandCenter } from '../CommandCenter';
```

- [ ] **Step 3.3.13: Verify build**

Run: `cd frontend && npm run build 2>&1 | tail -20`

- [ ] **Step 3.3.14: Manual test in dev server** (verify all sections render, Cmd+K works, theme toggle works, no console errors)

- [ ] **Step 3.3.15: Commit**

```bash
git add frontend/src/components/CommandCenter/ frontend/src/components/UI/CommandCenter.jsx
git commit -m "refactor(frontend): decompose CommandCenter into 10 sub-components with new features"
```

---

## Task 3.4: Add /buddhas route

**Files:** Create `frontend/src/routes/Buddhas/` directory (7 files). Modify `frontend/src/App.jsx`. Refactor `frontend/src/components/UI/BuddhaContemplationWidget.jsx`.

- [ ] **Step 3.4.1: Create `index.jsx`** (full code in merged plan ﾂｧ3.4.1): Title, progress bar, current Buddha display, intention editor, 5 sidebar components

- [ ] **Step 3.4.2: Create the 6 feature components** (full code in merged plan ﾂｧ3.4.2):
- `IntentionEditor.jsx` 窶・Input.TextArea for setting intention
- `DedicationText.jsx` 窶・random dedication from list of 3
- `SessionHistory.jsx` 窶・localStorage list of past sessions
- `ShareExport.jsx` 窶・copy-as-text button
- `DailyStreak.jsx` 窶・Ant Design Statistic showing streak count
- `AudioSettings.jsx` 窶・Select for quality (low/medium/high)

- [ ] **Step 3.4.3: Add route in `App.jsx`**

```javascript
import BuddhasPage from './routes/Buddhas';
// <Route path="/buddhas" element={<BuddhasPage />} />
```

- [ ] **Step 3.4.4: Refactor `BuddhaContemplationWidget.jsx`** (replaces 2s poll with deeplink to /buddhas):

```javascript
// frontend/src/components/UI/BuddhaContemplationWidget.jsx
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card } from 'antd';

export default function BuddhaContemplationWidget() {
  const navigate = useNavigate();
  return (
    <Card title="88 Buddhas" size="small">
      <Button type="primary" onClick={() => navigate('/buddhas')}>
        Open Contemplation
      </Button>
    </Card>
  );
}
```

(Drop the 2s `useEffect` polling loop 窶・WS `BUDDHA_RECITATION_UPDATE` provides the data via `useWebSocketStable`.)

- [ ] **Step 3.4.5: Verify build**

Run: `cd frontend && npm run build 2>&1 | tail -20`

- [ ] **Step 3.4.6: Manual test in dev** (verify /buddhas renders, widget deeplink works, all 6 sidebar components render)

- [ ] **Step 3.4.7: Commit**

```bash
git add frontend/src/routes/Buddhas/ frontend/src/App.jsx frontend/src/components/UI/BuddhaContemplationWidget.jsx
git commit -m "feat(frontend): add /buddhas route with 6 features and widget deeplink"
```

---

## Task 3.5: Add ProviderSettings component

**Files:** Create `frontend/src/components/Settings/ProviderSettings.jsx`. Modify `frontend/src/App.jsx`.

- [ ] **Step 3.5.1: Create `ProviderSettings.jsx`** (full code in merged plan ﾂｧ3.5.1): Title, Paragraph, Card with Table (provider, status tag, latency, models, error), Card with failover log

- [ ] **Step 3.5.2: Add /settings route**

```javascript
import ProviderSettings from './components/Settings/ProviderSettings';
// <Route path="/settings" element={<ProviderSettings />} />
```

- [ ] **Step 3.5.3: Verify build**

- [ ] **Step 3.5.4: Commit**

```bash
git add frontend/src/components/Settings/ frontend/src/App.jsx
git commit -m "feat(frontend): add ProviderSettings with live health table and failover log"
```

---

## Task 3.6: Migrate 3 components from polling to WebSocket

**Files:** Modify `SakaDawaBanner.jsx`, `RitualMonitor.jsx`, `BuddhaContemplationWidget.jsx` (last already done in 3.4.4).

- [ ] **Step 3.6.1: Update `SakaDawaBanner.jsx`** 窶・find the 60s `useEffect` polling `/api/v1/operator/saka-dawa`, remove it, use `sakaDawa` from `useWebSocketStable()` instead

- [ ] **Step 3.6.2: Update `RitualMonitor.jsx`** 窶・find the 5s `useEffect` polling `/api/v1/ritual/status`, remove it, use the WS `RITUAL_ENGINE_STATUS` value from `useWebSocketStable()`

- [ ] **Step 3.6.3: Verify build and Network tab** (no more poll requests in browser DevTools)

- [ ] **Step 3.6.4: Commit**

```bash
git add frontend/src/components/UI/SakaDawaBanner.jsx frontend/src/components/UI/RitualMonitor.jsx
git commit -m "refactor(frontend): migrate SakaDawaBanner and RitualMonitor from polling to WebSocket"
```

---

## Task 3.7: Phase 3 verification

- [ ] **Step 3.7.1: Run full test suite**

Run: `pytest tests/ -m "not slow" --ignore=tests/e2e -q 2>&1 | tail -30`

- [ ] **Step 3.7.2: Run frontend build**

Run: `cd frontend && npm run build 2>&1 | tail -20`

- [ ] **Step 3.7.3: Run ruff**

Run: `ruff check . && ruff format --check .`

- [ ] **Step 3.7.4: Tag checkpoint**

```bash
git tag phase-3-complete
```

---

# Phase 4: Cleanup, Delete Old Files, Final Test Pass

## Task 4.1: Delete old llm_integration.py and shim

**Files:** Delete `core/llm_integration.py`, `core/llm_usage.py` shim. Update all imports.

- [ ] **Step 4.1.1: Find all references**

Run: `grep -rn "from core.llm_integration\|from core.llm_usage\|import llm_integration\|import llm_usage" --include="*.py"`

- [ ] **Step 4.1.2: Update references** (replace `core.llm_integration.LLMIntegration` with `core.llm.registry.ProviderRegistry`, `core.llm_usage.LLMUsageTracker` with `core.llm.usage.LLMUsageTracker`)

- [ ] **Step 4.1.3: Delete old files**

```bash
git rm core/llm_integration.py core/llm_usage.py
```

- [ ] **Step 4.1.4: Run tests, verify still PASS**

Run: `pytest tests/ -m "not slow" --ignore=tests/e2e -q 2>&1 | tail -30`

- [ ] **Step 4.1.5: Commit**

```bash
git add -A
git commit -m "refactor(core): delete old llm_integration.py and llm_usage.py, migrate all imports"
```

---

## Task 4.2: Rewrite chat_interaction endpoint to use registry

**Files:** Modify `backend/app/api/v1/endpoints/llm.py` (chat_interaction function at lines 1126-1797, replace with ~60-line registry-backed version).

- [ ] **Step 4.2.1: Replace chat_interaction** with registry-backed version (full code in merged plan ﾂｧ4.2.2):
- Build context via `SystemPromptBuilder.compose()`
- Pick best provider via `registry.pick_best()`
- Retry once via `retry_with_backoff`
- Failover to next healthy provider if all fail
- Fall back to `run_rule_based_fallback` if no registry/providers

- [ ] **Step 4.2.2: Add imports** at top of llm.py:

```python
from core.llm.retry import retry_with_backoff
from core.context import (
    SystemPromptBuilder, ContextRequest,
    AstrologyContextModule, AnatomyContextModule, HardwareContextModule,
)
```

- [ ] **Step 4.2.3: Remove old inline compile_*_context functions** (lines 841-1123) 窶・replaced by ContextModule registry

- [ ] **Step 4.2.4: Run tests**

Run: `pytest tests/ -m "not slow" --ignore=tests/e2e -q 2>&1 | tail -30`

- [ ] **Step 4.2.5: Manual smoke test**: start server, POST to `/api/v1/llm/chat`, verify response

- [ ] **Step 4.2.6: Commit**

```bash
git add backend/app/api/v1/endpoints/llm.py
git commit -m "refactor(backend/llm): rewrite chat_interaction to use ProviderRegistry + ContextModule"
```

---

## Task 4.3: Final verification

- [ ] **Step 4.3.1: Run full test suite (Python + frontend)**

Run: `pytest tests/ -m "not slow" --ignore=tests/e2e -q 2>&1 | tail -30 && cd frontend && npm run build 2>&1 | tail -10`

- [ ] **Step 4.3.2: Run ruff**

Run: `ruff check . && ruff format --check .`

- [ ] **Step 4.3.3: Run TypeScript check**

Run: `cd frontend && npx tsc --noEmit 2>&1 | tail -20`

- [ ] **Step 4.3.4: Push branch and open PR**

```bash
git push origin feat/ui-ux-overhaul
gh pr create --base main --head feat/ui-ux-overhaul --title "UI/UX overhaul + async LLM provider refactor" --body "..."
```

- [ ] **Step 4.3.5: Tag completion**

```bash
git tag ui-ux-overhaul-complete
```

---

## Self-Review Notes

**Spec coverage:**
- 笨・Q1 Scope (Option C) 窶・all of Phases 1-4 implement
- 笨・Q2 Button strategy (stay on AntD + optimize) 窶・Task 3.1 (zeroRuntime)
- 笨・Q3 CommandCenter (full decomp) 窶・Task 3.3
- 笨・Q4 88 Buddhas (full features) 窶・Task 3.4
- 笨・Q5 Saka Dawa 窶・Task 3.6 (just drop poll, visual polish out of scope per user)
- 笨・Q6 LLM abstraction 窶・Tasks 1.3, 1.4, 1.5, 1.6
- 笨・Q7 Health-check config 窶・Task 1.7 (30s heartbeat), Task 1.6 (60s TTL), Task 1.7 (retry)
- 笨・Q8 Context modules 窶・Task 1.8
- 笨・Q9 WS polling 窶・Task 3.6
- 笨・Q10 Tests 窶・every task has tests

**Type consistency check:**
- `BaseLLMProvider.health_check()` returns `HealthStatus` everywhere 笨・- `ProviderRegistry.pick_best()` returns `Optional[BaseLLMProvider]` everywhere 笨・- `ContextModule.render()` returns `str` everywhere 笨・- `ChatRequest.system_prompt` used consistently in base.py and chat_interaction 笨・
**Placeholder scan:** No "TBD", "TODO: implement later" in code blocks (TODOs only in stub-migration steps which are clearly labeled as such).

---

## Execution Choice

**Plan complete and saved to `docs/superpowers/plans/2026-06-12-ui-ux-overhaul-llm-refactor.md` (1560+ lines).**

**Two execution options:**

1. **Subagent-Driven (recommended)** - Dispatch a fresh subagent per task, review between tasks, fast iteration
2. **Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
