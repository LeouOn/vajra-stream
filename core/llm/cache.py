# core/llm/cache.py
"""Async-safe TTL cache wrapper around cachetools.

cachetools.TTLCache uses a single TTL per cache instance.  For per-key
TTL (the ``ttl`` argument to :meth:`set`) we layer a ``{key: expires_at}``
dict on top, checked lazily on :meth:`get`.

This module also exposes :class:`LLMResponseCache`, a higher-level cache
keyed on (system_prompt + prompt + model + max_tokens + temperature)
with two semantic tiers:

* **chat** (short TTL, default 5 minutes) — used for general chat turns
  where the same prompt is likely to recur within a session.
* **static** (long TTL, default 1 hour) — used for deterministic / low
  temperature generation (e.g. structured extraction) where the same
  inputs should yield the same outputs.

Both tiers are opt-in to avoid surprising callers with stale data.
"""
import asyncio
import hashlib
from typing import Any

from cachetools import TTLCache as _TTLCache

# Default TTLs in seconds.
CHAT_TTL_SECONDS = 300  # 5 minutes
STATIC_TTL_SECONDS = 3600  # 1 hour


class TTLCache:
    """Async-safe TTL cache with per-key and default TTL."""

    def __init__(self, default_ttl: float = 60, maxsize: int = 1024) -> None:
        self._cache: _TTLCache = _TTLCache(maxsize=maxsize, ttl=default_ttl)
        self._lock = asyncio.Lock()
        self._default_ttl = default_ttl
        self._expires: dict[str, float] = {}

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            # Per-key expiry override (shorter than default TTL).
            exp = self._expires.get(key)
            if exp is not None and time.monotonic() > exp:
                del self._cache[key]
                del self._expires[key]
                return None
            return self._cache.get(key)

    async def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        async with self._lock:
            self._cache[key] = value
            if ttl is not None:
                self._expires[key] = time.monotonic() + ttl
            else:
                self._expires.pop(key, None)

    async def clear(self) -> None:
        async with self._lock:
            self._cache.clear()
            self._expires.clear()

    async def size(self) -> int:
        async with self._lock:
            return len(self._cache)


# Late import to keep the module-level import block tidy.
import time  # noqa: E402


class LLMResponseCache:
    """Semantic LLM response cache with chat (5 min) and static (1 hour) tiers.

    The cache is keyed on a SHA-256 hash of:

        system_prompt + prompt + model + max_tokens + temperature

    so any change in inputs yields a different key.  Tier suffixes (``:chat``
    vs ``:static``) keep the two TTL strategies isolated.

    Usage::

        cache = LLMResponseCache()
        key_inputs = (system_prompt, prompt, model, max_tokens, temperature)
        cached = await cache.get_chat(*key_inputs)
        if cached is not None:
            return cached
        response = await provider.generate(request)
        await cache.set_chat(*key_inputs, response)
        return response

    Notes:
        * Chat-tier caching is only appropriate when ``temperature`` is low
          enough that a cached response is still useful.  Callers should
          skip the cache when ``temperature > 0.1``.
        * The static tier assumes the caller has already gated on
          ``temperature == 0`` (or another determinism proxy).
    """

    def __init__(
        self,
        chat_ttl: float = CHAT_TTL_SECONDS,
        static_ttl: float = STATIC_TTL_SECONDS,
        maxsize: int = 512,
    ) -> None:
        # Two underlying TTLCaches share the maxsize budget.  Each tier
        # gets half so neither can starve the other under sustained load.
        half = max(64, maxsize // 2)
        self._chat = TTLCache(default_ttl=chat_ttl, maxsize=half)
        self._static = TTLCache(default_ttl=static_ttl, maxsize=half)
        self.chat_ttl = chat_ttl
        self.static_ttl = static_ttl

    @staticmethod
    def make_key(
        system_prompt: str,
        prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        """Build a deterministic cache key from the inputs that affect output."""
        h = hashlib.sha256()
        h.update((system_prompt or "").encode("utf-8", errors="ignore"))
        h.update(b"\x00")
        h.update((prompt or "").encode("utf-8", errors="ignore"))
        h.update(b"\x00")
        h.update((model or "").encode("utf-8", errors="ignore"))
        h.update(b"\x00")
        h.update(str(int(max_tokens)).encode("ascii"))
        h.update(b"\x00")
        # Normalise temperature to avoid key drift on 0.7 vs 0.70.
        h.update(f"{float(temperature):.4f}".encode("ascii"))
        return h.hexdigest()

    async def get_chat(
        self,
        system_prompt: str,
        prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> Any | None:
        key = self.make_key(system_prompt, prompt, model, max_tokens, temperature) + ":chat"
        return await self._chat.get(key)

    async def set_chat(
        self,
        system_prompt: str,
        prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
        value: Any,
    ) -> None:
        key = self.make_key(system_prompt, prompt, model, max_tokens, temperature) + ":chat"
        await self._chat.set(key, value, ttl=self.chat_ttl)

    async def get_static(
        self,
        system_prompt: str,
        prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> Any | None:
        key = self.make_key(system_prompt, prompt, model, max_tokens, temperature) + ":static"
        return await self._static.get(key)

    async def set_static(
        self,
        system_prompt: str,
        prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
        value: Any,
    ) -> None:
        key = self.make_key(system_prompt, prompt, model, max_tokens, temperature) + ":static"
        await self._static.set(key, value, ttl=self.static_ttl)

    async def clear(self) -> None:
        await self._chat.clear()
        await self._static.clear()
