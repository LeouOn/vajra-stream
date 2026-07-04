"""
Practice Engine API
====================

REST endpoints for the multi-practice recitation engine.

* GET    /practices/list               — list all loaded practice definitions
* POST   /practices/{id}/start         — start a practice session
* POST   /practices/{id}/stop          — stop a practice session
* GET    /practices/{id}/status        — current status of one practice
* GET    /practices/status             — status of every known session
* GET    /practices/history            — recent completed-session history

The engine itself lives at ``core/practice_engine.py`` and emits the
``PRACTICE_STARTED`` / ``PRACTICE_RECITED`` / ``PRACTICE_COMPLETED`` /
``PRACTICE_STOPPED`` WebSocket events through ``stable_connection_manager_v2``.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from core.practice_engine import get_practice_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/practices", tags=["practices"])


# ─── Request / response models ─────────────────────────────────────────────


class StartPracticeRequest(BaseModel):
    """Body for ``POST /practices/{id}/start``."""

    intention: str = Field(
        default="",
        description="Optional dedication intention for this session.",
    )
    interval_seconds: float = Field(
        default=2.0,
        ge=0.05,
        description="Seconds between each recitation.",
    )
    target_count: int | None = Field(
        default=None,
        ge=1,
        description="Override the practice's default target repetition count.",
    )
    enable_tts: bool = Field(
        default=True,
        description="Speak each recitation via the TTS provider (buddhist_chant role).",
    )


class StopPracticeRequest(BaseModel):
    """Body for ``POST /practices/{id}/stop`` (all fields optional)."""

    reason: str = Field(default="user", description="Reason recorded in history.")


# ─── Routes ────────────────────────────────────────────────────────────────


@router.get("/list", summary="List all available practices")
async def list_practices() -> dict:
    """Return every practice definition loaded from ``knowledge/practices/``."""
    engine = get_practice_engine()
    return {"practices": engine.list_practices()}


@router.post("/{practice_id}/start", summary="Start a practice session")
async def start_practice(practice_id: str, body: StartPracticeRequest) -> dict:
    """Begin reciting ``practice_id``. Returns the initial session status."""
    engine = get_practice_engine()
    if engine.get_definition(practice_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown practice: {practice_id}")
    try:
        session = await engine.start(
            practice_id,
            intention=body.intention,
            interval_seconds=body.interval_seconds,
            target_count=body.target_count,
            enable_tts=body.enable_tts,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception("Failed to start practice %s", practice_id)
        raise HTTPException(status_code=500, detail=str(e)) from e
    return {"status": "started", "session": session.to_status_dict()}


@router.post("/{practice_id}/stop", summary="Stop a practice session")
async def stop_practice(practice_id: str, body: StopPracticeRequest | None = None) -> dict:
    """Stop ``practice_id`` if running. Records history with the given reason."""
    engine = get_practice_engine()
    reason = body.reason if body is not None else "user"
    session = await engine.stop(practice_id, reason=reason)
    if session is None:
        return {"status": "not_running", "practice_id": practice_id}
    return {"status": "stopped", "session": session.to_status_dict()}


@router.get("/{practice_id}/status", summary="Get current status of a practice")
async def practice_status(practice_id: str) -> dict:
    """
    Return the live status of ``practice_id``.

    A 404 is only raised when the practice id itself is unknown. If the
    practice exists but no session has been started yet, we return a
    ``not_started`` payload so the frontend can render an idle state
    without treating it as an error.
    """
    engine = get_practice_engine()
    definition = engine.get_definition(practice_id)
    if definition is None:
        raise HTTPException(status_code=404, detail=f"Unknown practice: {practice_id}")
    status = engine.status(practice_id)
    if status is None:
        return {
            "status": "not_started",
            "practice_id": practice_id,
            "name": definition.name,
        }
    return status


@router.get("/status", summary="Get status of all known practice sessions")
async def all_practice_status() -> dict:
    """Status snapshot for every session the engine has tracked."""
    engine = get_practice_engine()
    return {"sessions": engine.all_status()}


@router.get("/history", summary="Get recent practice session history")
async def practice_history(
    limit: int = Query(default=50, ge=1, le=500),
) -> dict:
    """Return recent completed practice sessions (newest first)."""
    engine = get_practice_engine()
    return {"history": engine.history(limit=limit), "count": len(engine.history(limit=limit))}
