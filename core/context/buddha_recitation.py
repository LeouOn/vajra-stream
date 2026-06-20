# core/context/buddha_recitation.py
"""88 Buddhas recitation context module — injects today's practice into prompts.

Implements :class:`BuddhaRecitationContextModule`, a stateless
:class:`~core.context.base.ContextModule` that reads recent rows from the
``buddha_recitation_sessions`` table (via the read-side helpers in
:mod:`core.buddha_recitation_loop`) and surfaces the practitioner's current
recitation activity — intention, cycles completed, total names recited, and
dedication — into the assembled system prompt.

Mirrors the structure of :class:`~core.context.astrology.AstrologyContextModule`
and :class:`~core.context.hardware.HardwareContextModule`:

* ``gather`` is async, defensive, and returns a :class:`ContextData` (with
  ``error`` set on failure rather than raising).
* ``render`` is sync and returns ``""`` when there is nothing to show.

The module is stateless: each ``gather`` reads the live table, so it always
reflects the latest practice session(s) regardless of when it was
constructed.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from core.context.models import ContextData, ContextRequest

logger = logging.getLogger(__name__)


class BuddhaRecitationContextModule:
    """Injects recent 88 Buddhas recitation practice data into system prompts.

    Stateless — constructed without arguments. ``gather`` reads today's
    sessions (falling back to the most recent session when today is empty)
    plus the current day streak from
    :mod:`core.buddha_recitation_loop`. Never raises; returns
    ``ContextData`` with ``error`` set on internal failure.
    """

    name = "buddha_recitation"

    async def gather(self, request: ContextRequest) -> ContextData:
        """Collect today's recitation activity plus the current streak.

        ``request`` is accepted for Protocol conformance but ignored — the
        module reads from the shared ``buddha_recitation_sessions`` table.
        Returns empty :class:`ContextData` (no error) when there is no
        recent practice to surface, so the builder simply skips rendering.
        """
        try:
            from core.buddha_recitation_loop import get_recent_sessions, get_streak

            sessions = get_recent_sessions(limit=50)
            if not sessions:
                return ContextData(module_name=self.name)

            today_iso = date.today().isoformat()
            todays = [s for s in sessions if _session_day(s.get("started_at")) == today_iso]
            # Fall back to the single most recent session if today is empty
            # so the prompt still reflects current practice.
            relevant = todays if todays else [sessions[0]]

            data: dict[str, Any] = {
                "intention": relevant[-1].get("intention"),
                "cycles_completed": _sum_int(relevant, "cycles_completed"),
                "total_recited": _sum_int(relevant, "total_recited"),
                "dedication_text": relevant[-1].get("dedication_text"),
                "session_count": len(relevant),
                "scope": "today" if todays else "most_recent",
                "streak_days": get_streak(),
            }
            return ContextData(module_name=self.name, data=data)
        except Exception as exc:  # noqa: BLE001 — module must not raise
            logger.warning("BuddhaRecitationContextModule gather() failed: %s", exc)
            return ContextData(module_name=self.name, error=str(exc))

    def render(self, data: ContextData) -> str:
        """Render the recitation section as Markdown.

        Empty on any error or when no intention is present. The streak is
        surfaced as an additional line when greater than zero.
        """
        d = data.data
        if not d:
            return ""
        intention = d.get("intention")
        if not intention:
            return ""

        lines: list[str] = ["## Recent 88 Buddhas Practice", ""]
        lines.append(f"- Intention: {intention}")
        lines.append(f"- Cycles completed: {d.get('cycles_completed', 0)}")
        lines.append(f"- Total recitations: {d.get('total_recited', 0)}")
        dedication = d.get("dedication_text")
        if dedication:
            lines.append(f"- Dedication: {dedication}")
        streak = d.get("streak_days")
        if streak:
            lines.append(f"- Current streak: {streak} day(s)")
        return "\n".join(lines) + "\n"


def _session_day(started_at: str | None) -> str | None:
    """Return the ``YYYY-MM-DD`` prefix of ``started_at``, or ``None``.

    Defensive against malformed or missing timestamps — returns ``None``
    which simply excludes the row from the today filter.
    """
    if not started_at:
        return None
    try:
        return datetime.fromisoformat(str(started_at)).date().isoformat()
    except (ValueError, TypeError):
        # Fall back to the ISO prefix when the value isn't a clean ISO stamp.
        text = str(started_at)
        return text[:10] if len(text) >= 10 else None


def _sum_int(rows: list[dict], key: str) -> int:
    """Sum ``key`` across ``rows``, coercing ``None``/missing to ``0``."""
    total = 0
    for row in rows:
        try:
            total += int(row.get(key) or 0)
        except (TypeError, ValueError):
            continue
    return total


__all__ = ["BuddhaRecitationContextModule"]
