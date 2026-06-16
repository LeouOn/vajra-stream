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

    async def pick_best(self, use_cache: bool = True) -> BaseLLMProvider | None:
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
