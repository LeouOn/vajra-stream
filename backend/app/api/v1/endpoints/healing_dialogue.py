"""Healing Dialogue REST endpoints.

Exposes the :class:`~modules.healing_dialogue.HealingDialogueService` over
a small REST surface. The service is instantiated per-request (no shared
state) and builds its own :class:`~core.llm.registry.ProviderRegistry` on
first use via :func:`~core.llm.bootstrap.build_default_registry` — this
mirrors the pattern documented in the spec (section 4): the FastAPI
lifespan registry is for the health-check heartbeat; the dialogue service
has its own so it works identically outside the lifespan.

Routes (all under ``/api/v1/healing/``):

* ``POST   /sessions``                       — create a new session
* ``POST   /sessions/{session_id}/messages`` — send a message
* ``GET    /sessions/{session_id}``          — load a session's full state
* ``GET    /sessions``                       — list recent sessions
* ``POST   /sessions/{session_id}/advance``  — manually advance the phase
* ``POST   /sessions/{session_id}/summarize``— generate or re-generate summary

See ``docs/specs/2026-06-17-healing-dialogue-design.md`` section 4 for the
integration map.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from modules.healing_dialogue import HealingDialogueService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/healing", tags=["healing-dialogue"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class CreateSessionRequest(BaseModel):
    """Optional body for ``POST /sessions``.

    All fields are optional — clients can also drive the endpoint with
    query parameters for a lighter curl one-liner.
    """

    chart_id: int | None = Field(
        default=None,
        description="Optional saved_natal_charts.id to link the session to.",
    )
    session_type: str = Field(
        default="dialogue",
        description="Session type tag ('dialogue', 'reflection', ...).",
    )


class MessageRequest(BaseModel):
    """Body for ``POST /sessions/{id}/messages``."""

    message: str = Field(
        ...,
        description="The user's message to the healing dialogue.",
        min_length=1,
        max_length=8000,
    )


# ---------------------------------------------------------------------------
# Service factory
# ---------------------------------------------------------------------------


def get_healing_service() -> HealingDialogueService:
    """Construct a fresh :class:`HealingDialogueService`.

    Built per-request with no event_bus wiring for v1. The service lazily
    builds its own :class:`~core.llm.registry.ProviderRegistry` on first
    use, so this call is cheap.
    """
    return HealingDialogueService(event_bus=None)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/sessions", summary="Create a new healing dialogue session")
async def create_session(
    chart_id: int | None = Query(default=None, description="Optional chart id to link."),
    session_type: str = Query(default="dialogue", description="Session type tag."),
):
    """Open a fresh healing dialogue session at the ARRIVAL phase.

    Returns the new session id and the initial phase. Optionally links the
    session to a saved natal chart — when linked, the SEEING phase pulls
    natal + transit context automatically.
    """
    service = get_healing_service()
    try:
        return await service.create_session(chart_id=chart_id, session_type=session_type)
    except Exception as exc:  # noqa: BLE001 — surface as HTTP 500
        logger.exception("healing_dialogue.create_session failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/messages", summary="Send a message to the dialogue")
async def send_message(session_id: int, body: MessageRequest):
    """Advance the dialogue one turn with a user message.

    The service loads the persisted state, appends the user turn, calls the
    LLM, appends the assistant turn, updates accumulated insights and
    (optionally) the phase, then persists everything. Returns the assistant
    response plus the current phase and any phase-transition hint.
    """
    service = get_healing_service()
    try:
        return await service.process_message(session_id, body.message)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("healing_dialogue.send_message failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/sessions/{session_id}", summary="Get a session's full state")
async def get_session(session_id: int):
    """Load a session's full state including the complete message history.

    Includes the LLM-generated summary and structured key insights when the
    session has been summarized.
    """
    service = get_healing_service()
    try:
        return await service.get_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("healing_dialogue.get_session failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/sessions", summary="List recent healing dialogue sessions")
async def list_sessions(
    limit: int = Query(default=20, ge=1, le=200, description="Max sessions to return."),
):
    """List recent healing dialogue sessions, newest first.

    Returns summary rows (no transcript body) suitable for a session picker.
    """
    service = get_healing_service()
    try:
        sessions = await service.list_sessions(limit=limit)
        return {"sessions": sessions, "count": len(sessions)}
    except Exception as exc:  # noqa: BLE001
        logger.exception("healing_dialogue.list_sessions failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/advance", summary="Advance to the next phase")
async def advance_phase(session_id: int):
    """Manually advance the session to the next phase.

    Use this when the user wants to skip ahead (e.g. "I'm ready for the
    practice") rather than waiting for the LLM to offer a transition.
    Entering SEEING for the first time pulls astrology context. Entering
    COMPLETED triggers :meth:`HealingDialogueService.summarize_session`.
    """
    service = get_healing_service()
    try:
        return await service.advance_phase(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("healing_dialogue.advance_phase failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/summarize", summary="Generate or regenerate the session summary")
async def summarize(session_id: int):
    """Generate (or regenerate) the LLM summary for a session.

    Safe to call on any session — summarized sessions get a fresh summary;
    incomplete sessions get one too (useful when the dialogue was abandoned
    mid-arc but you still want the insights captured for the outlook
    feedback loop).
    """
    service = get_healing_service()
    try:
        summary = await service.summarize_session(session_id)
        return {"session_id": session_id, "summary": summary}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("healing_dialogue.summarize failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


__all__ = ["router"]
