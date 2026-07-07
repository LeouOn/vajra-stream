# tests/core/llm/test_registry.py
import asyncio

import pytest

from core.llm.models import HealthStatus
from core.llm.registry import ProviderRegistry


class FakeProvider:
    """Minimal provider stub satisfying the BaseLLMProvider Protocol."""

    def __init__(self, name, priority=50, healthy=True):
        self.name = name
        self.priority = priority
        self._healthy = healthy
        self.closed = False

    async def health_check(self) -> HealthStatus:
        return HealthStatus(provider=self.name, healthy=self._healthy)

    async def list_models(self):
        return []

    async def generate(self, request):
        raise NotImplementedError

    async def stream(self, request):
        raise NotImplementedError

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_registry_registration():
    """register() appends; providers property returns sorted by priority desc."""
    registry = ProviderRegistry()
    registry.register(FakeProvider("low", priority=10))
    registry.register(FakeProvider("high", priority=90))
    registry.register(FakeProvider("mid", priority=50))

    names = [p.name for p in registry.providers]
    assert names == ["high", "mid", "low"]
    assert len(registry) == 3
    assert "high" in registry
    assert "missing" not in registry

    # duplicate name raises
    with pytest.raises(ValueError, match="already registered"):
        registry.register(FakeProvider("high", priority=20))


@pytest.mark.asyncio
async def test_registry_pick_keeps_provider_through_hysteresis_threshold():
    """A single failed health check is treated as a transient blip by
    hysteresis — the provider remains effectively healthy and is preferred
    over a lower-priority genuinely-healthy peer.
    """
    registry = ProviderRegistry()
    registry.register(FakeProvider("high-sick", priority=90, healthy=False))
    registry.register(FakeProvider("low-ok", priority=10, healthy=True))

    # First pick: high-sick fails once (1/2) — still effectively healthy.
    first = await registry.pick_best(use_cache=False)
    assert first is not None
    assert first.name == "high-sick"

    # Second pick: high-sick has now failed twice (2/2) — marked down, so
    # pick_best falls through to the lower-priority genuinely-healthy one.
    second = await registry.pick_best(use_cache=False)
    assert second is not None
    assert second.name == "low-ok"


@pytest.mark.asyncio
async def test_registry_pick_returns_none_when_all_fail_threshold():
    """After FAILURE_THRESHOLD consecutive failures of every provider,
    pick_best() returns None.

    Implementation detail: ``pick_best`` short-circuits at the first
    effectively-healthy provider, so the lower-priority provider only gets
    its failure count incremented after the higher-priority one has been
    excluded. We therefore need a third call to mark the second provider
    down once both have crossed the threshold.
    """
    registry = ProviderRegistry()
    registry.register(FakeProvider("a", priority=90, healthy=False))
    registry.register(FakeProvider("b", priority=10, healthy=False))

    # Call 1: a fails once (1/2) — still effectively healthy — a is returned.
    #          b is never iterated.
    first = await registry.pick_best(use_cache=False)
    assert first is not None

    # Call 2: a reaches threshold (2/2) — marked down — falls through to b,
    #          which has its first failure (1/2) — still effectively healthy.
    second = await registry.pick_best(use_cache=False)
    assert second is not None

    # Call 3: a stays down; b reaches threshold (2/2) — also down — None.
    third = await registry.pick_best(use_cache=False)
    assert third is None


@pytest.mark.asyncio
async def test_registry_health_check_all():
    """health_check_all() runs all provider checks concurrently."""
    registry = ProviderRegistry()
    concurrent = {"count": 0, "max": 0}

    class SlowProvider(FakeProvider):
        async def health_check(self) -> HealthStatus:
            concurrent["count"] += 1
            concurrent["max"] = max(concurrent["max"], concurrent["count"])
            await asyncio.sleep(0.05)
            concurrent["count"] -= 1
            return HealthStatus(provider=self.name, healthy=self._healthy)

    registry.register(SlowProvider("a", priority=10))
    registry.register(SlowProvider("b", priority=20))
    registry.register(SlowProvider("c", priority=30))

    statuses = await registry.health_check_all(use_cache=False)
    assert len(statuses) == 3
    # If truly parallel, at least 2 run concurrently.
    assert concurrent["max"] >= 2


@pytest.mark.asyncio
async def test_registry_close_all():
    """close_all() closes every provider and clears the registry."""
    registry = ProviderRegistry()
    p1 = FakeProvider("a")
    p2 = FakeProvider("b")
    registry.register(p1)
    registry.register(p2)

    await registry.close_all()
    assert p1.closed
    assert p2.closed
    assert len(registry) == 0
