# core/llm/retry.py
"""Async retry helper with exponential backoff."""
import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

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
