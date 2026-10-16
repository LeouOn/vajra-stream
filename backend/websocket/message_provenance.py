"""Provenance of every WebSocket message type (the honest instrument).

Every message the backend sends over ``/ws`` passes through
``StableConnectionManagerV2.broadcast`` / ``send_personal_message``, and both
call :func:`annotate`. That makes provenance structural: a producer does not
have to remember to label its values, because the label is attached at the one
choke point from this reviewed table.

``WS_MESSAGE_PROVENANCE`` maps each message type to either

- a ``{field: kind}`` map (see ``core/provenance.py``) that :func:`annotate`
  attaches as ``provenance`` beside the values: inside ``data`` when the
  message has a ``data`` dict, otherwise at the top level; or
- a reason string, for messages that carry no displayed derived values
  (control frames, chat lifecycle) or that label themselves.

Labels a producer already set win (``RNG_READING`` sends its own draw map).
``tests/unit/test_ws_message_provenance.py`` fails when a type the backend
emits (per ``scripts/audit_ws_contract.py``) is missing here, so a new message
type cannot ship unclassified.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from core.provenance import COMPUTED, DRAW, RECORD, with_provenance

logger = logging.getLogger(__name__)

_RECITATION_STATUS = {
    "total_recited": RECORD,
    "mala_count": RECORD,
    "dedications": RECORD,
    "current_index": RECORD,
    "current_cycle": RECORD,
    "progress_pct": RECORD,
    "started_at": RECORD,
    "last_recited_at": RECORD,
}

_PRACTICE_STATUS = {
    "total_recited": RECORD,
    "mala_count": RECORD,
    "mala_rounds": RECORD,
    "current_repetition": RECORD,
    "elapsed_seconds": RECORD,
    "progress_pct": RECORD,
    "target_count": RECORD,
    "started_at": RECORD,
    "last_recited_at": RECORD,
}

_PRACTICE_END = {"total_count": RECORD, "mala_rounds": RECORD, "duration_seconds": RECORD}

_HEALING_BROADCAST = {
    # The carriers follow the rate (computed); the broadcast itself is a record.
    "frequency_hz": COMPUTED,
    "frequencies": COMPUTED,
    "duration_minutes": RECORD,
    "lat": COMPUTED,
    "lon": COMPUTED,
}

_RITUAL_RECORD = {
    "merit_multiplier": COMPUTED,
    "planetary_hour": COMPUTED,
    "timing_quality": COMPUTED,
    "narrative_length": RECORD,
    "started_at": RECORD,
    "completed_at": RECORD,
}

_NO_VALUES = "no displayed derived values"

WS_MESSAGE_PROVENANCE: dict[str, Mapping[str, str] | str] = {
    # --- live streams -----------------------------------------------------
    "realtime_data": {"audio_spectrum": COMPUTED, "active_sessions": RECORD, "system_status": RECORD},
    "session_update": {"status": RECORD},
    "SESSION_STARTED": {"session_id": RECORD},
    "RADIONICS_RATE_BROADCAST": {"rate": COMPUTED, "frequency": RECORD},
    "SCALAR_WAVE_ACTIVE": {"session_count": RECORD},
    "RNG_READING": {
        # rng_attunement_service.reading_provenance() is sent by the producer;
        # these are the same labels, so a reading is a draw even if it is not.
        "coherence": DRAW,
        "entropy": DRAW,
        "floating_needle_score": DRAW,
        "tone_arm": DRAW,
        "needle_position": DRAW,
        "needle_state": DRAW,
        "trend": DRAW,
        "quality": DRAW,
    },
    "CRYSTAL_BROADCAST_STARTED": {"session_id": RECORD},
    "HEALING_BROADCAST_STARTED": _HEALING_BROADCAST,
    # --- practice and recitation counts ----------------------------------
    "BUDDHA_RECITATION_UPDATE": _RECITATION_STATUS,
    "BUDDHA_RECITATION_STARTED": {"total_buddhas": RECORD},
    "BUDDHA_NAME_RECITED": _RECITATION_STATUS,
    "BUDDHA_RECITATION_STOPPED": _RECITATION_STATUS,
    "PRACTICE_STARTED": {"target_count": RECORD},
    "PRACTICE_RECITED": _PRACTICE_STATUS,
    "PRACTICE_COMPLETED": _PRACTICE_END,
    "PRACTICE_STOPPED": _PRACTICE_END,
    # --- calendar and timing (deterministic from the clock) -------------
    "SAKA_DAWA_CHECK": {
        "is_saka_dawa": COMPUTED,
        "is_duchen": COMPUTED,
        "multiplier": COMPUTED,
        "days_until_duchen": COMPUTED,
        "saka_dawa_duchen": COMPUTED,
        "losar": COMPUTED,
    },
    "PLANETARY_HOUR_SHIFT": {"hour": COMPUTED, "tithi": COMPUTED, "nakshatra": COMPUTED},
    "RITUAL_ENGINE_STATUS": {
        "rituals_today": RECORD,
        "total_merit_today": RECORD,
        "rituals_this_hour": RECORD,
        "current_hour": COMPUTED,
    },
    "RITUAL_PHASE": {"planetary_hour": COMPUTED, "narrative_length": RECORD},
    "RITUAL_COMPLETED": _RITUAL_RECORD,
    # --- journey (fiction; the character's stats are drawn) -------------
    "JOURNEY_STAGE_STARTED": {"stage": RECORD},
    "JOURNEY_STAGE_COMPLETED": {"stage": RECORD, "blessings_count": RECORD},
    "JOURNEY_COMPLETED": {"total_stages": RECORD, "total_blessings": RECORD},
    # --- accounting -------------------------------------------------------
    "LLM_USAGE_UPDATE": {
        "total_calls": RECORD,
        "total_cost_usd": RECORD,
        "calls_today": RECORD,
        "cost_today": RECORD,
        "daily_cost_usd": RECORD,
        "remaining_balance": RECORD,
        "provider_stats": RECORD,
    },
    "PROVIDER_HEALTH": {"statuses": RECORD},
    "BACKGROUND_GENERATION": {"stats": RECORD},
    # --- self-labeled or value-free --------------------------------------
    "operation_update": "the operation row is a record; its own provenance map labels its params (core/operations.py)",
    "IDLE_REFLECTION": f"{_NO_VALUES}: reflective text",
    "heartbeat": f"{_NO_VALUES}: connection keep-alive",
    "connection_status": f"{_NO_VALUES}: connection handshake",
    "ping": f"{_NO_VALUES}: keep-alive",
    "pong": f"{_NO_VALUES}: keep-alive",
    "settings_updated": f"{_NO_VALUES}: acknowledgement",
    "error": f"{_NO_VALUES}: error text",
    "ERROR": f"{_NO_VALUES}: error text",
    "system_error": f"{_NO_VALUES}: error text",
    "chat_started": f"{_NO_VALUES}: chat lifecycle",
    "chat_tool_start": f"{_NO_VALUES}: chat lifecycle",
    "chat_tool_complete": f"{_NO_VALUES}: chat lifecycle; tool results label their own values",
    "chat_tool_error": f"{_NO_VALUES}: chat lifecycle",
    "chat_complete": f"{_NO_VALUES}: chat lifecycle",
    "chat_error": f"{_NO_VALUES}: chat lifecycle",
    "chat_cancelled": f"{_NO_VALUES}: chat lifecycle",
}


def annotate(message: Any) -> Any:
    """Return ``message`` with its type's provenance map attached.

    Never raises and never mutates the caller's dict: on any problem the
    message is returned unchanged (a label must not cost a broadcast).
    """
    if not isinstance(message, dict):
        return message
    mapping = WS_MESSAGE_PROVENANCE.get(str(message.get("type")))
    if not isinstance(mapping, Mapping):
        return message
    try:
        data = message.get("data")
        if isinstance(data, dict):
            return {**message, "data": with_provenance(dict(data), mapping)}
        return with_provenance(dict(message), mapping)
    except (TypeError, ValueError) as exc:
        logger.debug("provenance annotate skipped for %s: %s", message.get("type"), exc)
        return message
