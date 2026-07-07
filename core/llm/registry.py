# core/llm/registry.py
"""ProviderRegistry: ordered, health-aware provider collection."""
from __future__ import annotations

import asyncio
import logging

from core.llm.base import BaseLLMProvider
from core.llm.cache import TTLCache
from core.llm.models import HealthStatus

logger = logging.getLogger(__name__)


class ProviderRegistry:
    # Hysteresis: a provider must fail this many *consecutive* health checks
    # before being treated as down. Prevents Down->Healthy->Down thrashing when
    # upstream providers (e.g. DeepSeek) have transient latency spikes.
    FAILURE_THRESHOLD = 2

    def __init__(self, health_cache_ttl: int = 60) -> None:
        self._providers: list[BaseLLMProvider] = []
        self._health_cache = TTLCache(default_ttl=health_cache_ttl)
        self._consecutive_failures: dict[str, int] = {}

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
        self._consecutive_failures.pop(name, None)

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

    def _is_effectively_healthy(self, provider_name: str, status: HealthStatus) -> bool:
        """Apply hysteresis to a health status update.

        A single failed health check is treated as a transient blip -- the
        provider is kept healthy until it fails ``FAILURE_THRESHOLD`` checks
        in a row. A success resets the consecutive-failure counter to zero.
        """
        if status.healthy:
            self._consecutive_failures[provider_name] = 0
            return True
        count = self._consecutive_failures.get(provider_name, 0) + 1
        self._consecutive_failures[provider_name] = count
        if count < self.FAILURE_THRESHOLD:
            logger.info(
                "Provider %s failed health check (%d/%d consecutive), keeping healthy",
                provider_name,
                count,
                self.FAILURE_THRESHOLD,
            )
            return True
        return False

    async def pick_best(self, use_cache: bool = True) -> BaseLLMProvider | None:
        statuses = await self.health_check_all(use_cache=use_cache)
        for provider in self.providers:
            status = next((s for s in statuses if s.provider == provider.name), None)
            if status is not None and self._is_effectively_healthy(provider.name, status):
                return provider
        return None

    async def failover_chain(self) -> list[BaseLLMProvider]:
        statuses = await self.health_check_all()
        chain: list[BaseLLMProvider] = []
        for provider in self.providers:
            status = next((s for s in statuses if s.provider == provider.name), None)
            if status is not None and self._is_effectively_healthy(provider.name, status):
                chain.append(provider)
        return chain

    async def close_all(self) -> None:
        await asyncio.gather(*[p.close() for p in self._providers], return_exceptions=True)
        self._providers.clear()
        await self._health_cache.clear()

    def __len__(self) -> int:
        return len(self._providers)

    def __contains__(self, name: str) -> bool:
        return any(p.name == name for p in self._providers)
