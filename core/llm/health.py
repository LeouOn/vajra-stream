# core/llm/health.py
"""Health-check heartbeat task."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from core.llm.models import HealthStatus
from core.llm.registry import ProviderRegistry

logger = logging.getLogger(__name__)


async def start_health_heartbeat(
    registry: ProviderRegistry,
    interval_seconds: int = 30,
    on_update: Callable[[list[HealthStatus]], Awaitable[None]] | None = None,
) -> None:
    """Run health checks in a loop until cancelled.

    Each iteration calls ``registry.health_check_all()`` and, when provided,
    awaits ``on_update`` with the resulting statuses. Per-iteration errors are
    logged so the loop keeps running; :class:`asyncio.CancelledError` is logged
    and re-raised to support graceful shutdown.

    Args:
        registry: Provider registry to health-check on each sweep.
        interval_seconds: Seconds to sleep between health-check sweeps.
        on_update: Optional async callback invoked with the latest list of
            :class:`~core.llm.models.HealthStatus` after each sweep.
    """
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
