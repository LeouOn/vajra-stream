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
