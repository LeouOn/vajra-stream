"""
Lightweight chat progress store.

Components subscribe to receive real-time updates as the backend processes
async chat jobs. The WebSocket hook writes to this store; CommandCenter reads
from it to render progress indicators.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

# job_id -> latest progress snapshot
_progress: dict[str, dict[str, Any]] = {}
_listeners: list[Callable[[str, dict[str, Any]], None]] = []


def update(job_id: str, event: dict[str, Any]) -> None:
    """Record a progress event for *job_id* and notify listeners."""
    merged = {**_progress.get(job_id, {}), **event, "job_id": job_id}
    _progress[job_id] = merged
    for fn in _listeners:
        try:
            fn(job_id, merged)
        except Exception:
            logger.exception("chat progress listener failed")


def get(job_id: str) -> dict[str, Any] | None:
    return _progress.get(job_id)


def subscribe(fn: Callable[[str, dict[str, Any]], None]) -> Callable[[], None]:
    """Subscribe to progress updates. Returns an unsubscribe function."""
    _listeners.append(fn)
    return lambda: _listeners.remove(fn) if fn in _listeners else None


def clear(job_id: str) -> None:
    _progress.pop(job_id, None)
