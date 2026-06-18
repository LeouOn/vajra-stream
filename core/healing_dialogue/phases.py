# core/healing_dialogue/phases.py
"""Five-phase dialogue arc and session state.

Defines :class:`DialoguePhase` — the five-phase Vajrayana healing arc
(``ARRIVAL → SEEING → MEETING → RELEASE → DEDICATION → COMPLETED``) — and
:class:`DialogueState`, the JSON-serializable session state carried between
turns.

The phase enum intentionally re-uses the name ``DialoguePhase`` (and not
``RitualPhase``, which is already defined in both ``core/ritual_engine`` and
``core/ritual_sequencer``) to avoid a name collision in the public API.

See ``docs/specs/2026-06-17-healing-dialogue-design.md`` section 3 for the
phase semantics and section 5 for the data model.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class DialoguePhase(str, Enum):
    """The five-phase healing dialogue arc plus a terminal state.

    Phases are visited in declaration order. ``COMPLETED`` is terminal and
    is reached after ``DEDICATION`` finishes — see
    :meth:`DialogueState.advance_phase`.
    """

    ARRIVAL = "arrival"
    SEEING = "seeing"
    MEETING = "meeting"
    RELEASE = "release"
    DEDICATION = "dedication"
    COMPLETED = "completed"

    @classmethod
    def next_after(cls, phase: DialoguePhase) -> DialoguePhase:
        """Return the phase that follows ``phase`` in the arc.

        ``DEDICATION`` is followed by ``COMPLETED``. ``COMPLETED`` is terminal
        and returns itself.
        """
        order = [
            cls.ARRIVAL,
            cls.SEEING,
            cls.MEETING,
            cls.RELEASE,
            cls.DEDICATION,
            cls.COMPLETED,
        ]
        try:
            idx = order.index(phase)
        except ValueError:  # pragma: no cover - defensive
            return cls.ARRIVAL
        return order[min(idx + 1, len(order) - 1)]


def _now_utc() -> datetime:
    """Return a timezone-aware UTC ``datetime`` (ISO-8601 serializable)."""
    return datetime.now(timezone.utc)


def _dt_to_iso(dt: datetime | None) -> str | None:
    """Serialize a ``datetime`` to ISO-8601, or ``None`` if ``dt`` is None."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _dt_from_iso(s: str | None) -> datetime | None:
    """Parse an ISO-8601 string back to a timezone-aware ``datetime``."""
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@dataclass
class DialogueState:
    """Mutable session state carried between dialogue turns.

    Mirrors the data model in spec section 5. ``message_history`` is a list
    of ``{"role", "content", "timestamp"}`` dicts; ``accumulated_insights``
    holds themes / emotions / body_locations / chart_findings discovered
    across the session.

    The state is JSON-serializable via :meth:`to_dict` and reconstructable via
    :meth:`from_dict`. Phase transitions are advanced by
    :meth:`advance_phase`, which also stamps ``phase_started_at`` to now.
    """

    session_id: str
    chart_id: int | None
    current_phase: DialoguePhase
    phase_started_at: datetime
    message_history: list[dict] = field(default_factory=list)
    accumulated_insights: dict = field(default_factory=dict)
    astrology_context: dict | None = None
    somatic_findings: dict | None = None
    recommended_practice: dict | None = None
    dedication_text: str | None = None
    started_at: datetime = field(default_factory=_now_utc)
    completed_at: datetime | None = None

    # ------------------------------------------------------------------
    # Phase helpers
    # ------------------------------------------------------------------
    def advance_phase(self) -> DialoguePhase:
        """Move to the next phase in the arc.

        Updates ``current_phase`` and ``phase_started_at``. When leaving
        ``DEDICATION`` (i.e. entering ``COMPLETED``), ``completed_at`` is
        stamped to now.

        Returns:
            The new :class:`DialoguePhase`.
        """
        prev = self.current_phase
        nxt = DialoguePhase.next_after(prev)
        self.current_phase = nxt
        self.phase_started_at = _now_utc()
        if nxt is DialoguePhase.COMPLETED and self.completed_at is None:
            self.completed_at = self.phase_started_at
        return nxt

    def is_terminal(self) -> bool:
        """Return ``True`` when the session is finished (``COMPLETED``)."""
        return self.current_phase is DialoguePhase.COMPLETED

    def append_message(self, role: str, content: str) -> None:
        """Append a ``{role, content, timestamp}`` entry to ``message_history``."""
        self.message_history.append(
            {
                "role": role,
                "content": content,
                "timestamp": _now_utc().isoformat(),
            }
        )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        """Serialize to a JSON-serializable ``dict``.

        Datetimes become ISO-8601 strings, the phase becomes its string
        value. Suitable for ``json.dumps`` and SQLite ``TEXT`` columns.
        """
        return {
            "session_id": self.session_id,
            "chart_id": self.chart_id,
            "current_phase": self.current_phase.value,
            "phase_started_at": _dt_to_iso(self.phase_started_at),
            "message_history": list(self.message_history),
            "accumulated_insights": dict(self.accumulated_insights),
            "astrology_context": self.astrology_context,
            "somatic_findings": self.somatic_findings,
            "recommended_practice": self.recommended_practice,
            "dedication_text": self.dedication_text,
            "started_at": _dt_to_iso(self.started_at),
            "completed_at": _dt_to_iso(self.completed_at),
        }

    @classmethod
    def from_dict(cls, d: dict) -> DialogueState:
        """Reconstruct a :class:`DialogueState` from :meth:`to_dict` output.

        Unknown keys are ignored; missing keys fall back to dataclass
        defaults. Unknown phase values raise ``KeyError`` via
        :class:`DialoguePhase`.
        """
        phase_raw = d.get("current_phase") or d.get("phase")
        if phase_raw is None:
            raise KeyError("current_phase missing from DialogueState dict")
        current_phase = DialoguePhase(phase_raw)
        started_raw = d.get("started_at")
        return cls(
            session_id=d["session_id"],
            chart_id=d.get("chart_id"),
            current_phase=current_phase,
            phase_started_at=_dt_from_iso(d.get("phase_started_at"))
            or _now_utc(),
            message_history=list(d.get("message_history") or []),
            accumulated_insights=dict(d.get("accumulated_insights") or {}),
            astrology_context=d.get("astrology_context"),
            somatic_findings=d.get("somatic_findings"),
            recommended_practice=d.get("recommended_practice"),
            dedication_text=d.get("dedication_text"),
            started_at=_dt_from_iso(started_raw) or _now_utc(),
            completed_at=_dt_from_iso(d.get("completed_at")),
        )


__all__ = ["DialoguePhase", "DialogueState"]
