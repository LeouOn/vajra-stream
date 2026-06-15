# core/llm/cache.py
"""Async-safe TTL cache wrapper around cachetools.

cachetools.TTLCache uses a single TTL per cache instance.  For per-key
TTL (the ``ttl`` argument to :meth:`set`) we layer a ``{key: expires_at}``
dict on top, checked lazily on :meth:`get`.
"""
import asyncio
import time
from typing import Any, Optional

from cachetools import TTLCache as _TTLCache


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
