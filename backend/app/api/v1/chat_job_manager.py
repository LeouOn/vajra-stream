"""
Chat job manager — tracks in-progress async chat sessions.

Stores job state in memory. Each job has an id, a status, a list of
tool-call progress events, and a final result. The background task
updates the job as tools execute; the frontend reads progress over
WebSocket.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

logger = logging.getLogger(__name__)

# ── In-memory job store ──────────────────────────────────────────────
# job_id -> { status, created_at, events, result, error, connection_id }
_jobs: dict[str, dict[str, Any]] = {}


def create_job(connection_id: str | None = None) -> str:
    job_id = f"chat_{uuid.uuid4().hex[:12]}"
    _jobs[job_id] = {
        "status": "pending",
        "created_at": time.time(),
        "events": [],
        "result": None,
        "error": None,
        "connection_id": connection_id,
    }
    return job_id


def get_job(job_id: str) -> dict[str, Any] | None:
    return _jobs.get(job_id)


def update_job(job_id: str, **kwargs: Any) -> None:
    job = _jobs.get(job_id)
    if job:
        job.update(kwargs)


def add_event(job_id: str, event: dict[str, Any]) -> None:
    job = _jobs.get(job_id)
    if job:
        job["events"].append({**event, "ts": time.time()})


def cleanup_old_jobs(max_age_seconds: float = 600.0) -> None:
    now = time.time()
    expired = [jid for jid, j in _jobs.items() if now - j["created_at"] > max_age_seconds]
    for jid in expired:
        del _jobs[jid]


def start_background(coro: Any, *, loop: asyncio.AbstractEventLoop | None = None) -> asyncio.Task:
    """Schedule a coroutine as a background task with error logging."""
    if loop is None:
        loop = asyncio.get_event_loop()

    async def _wrapper() -> None:
        try:
            await coro
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Background chat task failed")

    return loop.create_task(_wrapper())
