# tests/core/llm/test_health.py
import asyncio

import pytest

from core.llm.health import start_health_heartbeat
from core.llm.models import HealthStatus
from core.llm.registry import ProviderRegistry


class StubProvider:
    """Minimal provider stub satisfying the BaseLLMProvider Protocol."""

    def __init__(self, name: str = "stub", priority: int = 50, fail: bool = False):
        self.name = name
        self.priority = priority
        self._fail = fail
        self.check_count = 0

    async def health_check(self) -> HealthStatus:
        self.check_count += 1
        if self._fail:
            raise RuntimeError("boom")
        return HealthStatus(provider=self.name, healthy=True)

    async def list_models(self):
        return []

    async def generate(self, request):
        raise NotImplementedError

    async def stream(self, request):
        raise NotImplementedError

    async def close(self):
        pass


@pytest.mark.asyncio
async def test_heartbeat_runs_and_cancels():
    """Heartbeat calls health_check repeatedly and cancels cleanly."""
    # Short TTL so the cache expires between 0.1s intervals.
    registry = ProviderRegistry(health_cache_ttl=0.01)
    provider = StubProvider()
    registry.register(provider)

    task = asyncio.create_task(
        start_health_heartbeat(registry, interval_seconds=0.1)
    )
    await asyncio.sleep(0.25)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert provider.check_count >= 2


@pytest.mark.asyncio
async def test_heartbeat_handles_provider_failure():
    """Heartbeat does not crash when a provider's health_check raises."""
    registry = ProviderRegistry(health_cache_ttl=0.01)
    provider = StubProvider(fail=True)
    registry.register(provider)

    task = asyncio.create_task(
        start_health_heartbeat(registry, interval_seconds=0.1)
    )
    await asyncio.sleep(0.25)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Loop continued past failures; check_count proves health_check was invoked.
    assert provider.check_count >= 2
