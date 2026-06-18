# core/context/healing_dialogue.py
"""Healing dialogue context module — injects phase + insights into the prompt.

Implements :class:`HealingPhaseContextModule`, a :class:`ContextModule` that
reads the live :class:`~core.healing_dialogue.DialogueState` and surfaces the
current phase, accumulated insights, and recommended practice (if any) into
the assembled system prompt.

Mirrors the structure of :class:`~core.context.astrology.AstrologyContextModule`
and :class:`~core.context.anatomy.AnatomyContextModule`:

* ``gather`` is async, defensive, and returns a :class:`ContextData` (with
  ``error`` set on failure rather than raising).
* ``render`` is sync and returns ``""`` when there is nothing to show.

The module is constructed per-session with the current :class:`DialogueState`
reference, so subsequent ``gather`` calls see the latest state mutations.
"""
from __future__ import annotations

import logging

from core.context.models import ContextData, ContextRequest
from core.healing_dialogue.phases import DialogueState

logger = logging.getLogger(__name__)


class HealingPhaseContextModule:
    """Injects current phase, accumulated insights, and recommended practice.

    Constructed with a reference to the live :class:`DialogueState` for a
    session. Because the reference is held (not copied), each ``gather``
    sees the latest phase and insights even after the service mutates the
    state between turns.
    """

    name = "healing_dialogue"

    def __init__(self, state: DialogueState) -> None:
        self._state = state

    async def gather(self, request: ContextRequest) -> ContextData:
        """Collect the current phase, insights, and practice.

        ``request`` is accepted for Protocol conformance but ignored — the
        module reads from the bound :class:`DialogueState`. Never raises;
        returns ``ContextData`` with ``error`` set on internal failure.
        """
        try:
            state = self._state
            data: dict = {
                "session_id": state.session_id,
                "current_phase": state.current_phase.value,
                "phase_started_at": (
                    state.phase_started_at.isoformat()
                    if state.phase_started_at
                    else None
                ),
                "chart_id": state.chart_id,
                "accumulated_insights": dict(state.accumulated_insights),
            }
            if state.recommended_practice:
                data["recommended_practice"] = state.recommended_practice
            if state.dedication_text:
                data["dedication_text"] = state.dedication_text
            return ContextData(module_name=self.name, data=data)
        except Exception as exc:  # noqa: BLE001 — module must not raise
            logger.warning("HealingPhaseContextModule gather() failed: %s", exc)
            return ContextData(module_name=self.name, error=str(exc))

    def render(self, data: ContextData) -> str:
        """Render the healing-dialogue section as Markdown.

        Empty on any error or missing phase. The recommended practice is
        surfaced only when present (Release / Dedication phases).
        """
        d = data.data
        if not d:
            return ""
        phase = d.get("current_phase")
        if not phase:
            return ""

        lines: list[str] = ["### Healing Dialogue Context", ""]
        lines.append(f"**Current phase:** {phase.upper()}")
        if d.get("session_id"):
            lines.append(f"**Session:** `{d['session_id']}`")
        if d.get("chart_id") is not None:
            lines.append(f"**Linked chart:** id={d['chart_id']}")
        lines.append("")

        insights = d.get("accumulated_insights") or {}
        if insights:
            lines.append("**Accumulated insights:**")
            for key, value in insights.items():
                label = str(key).replace("_", " ").title()
                lines.append(f"  - {label}: {_render_inline(value)}")
            lines.append("")

        practice = d.get("recommended_practice")
        if practice:
            lines.append("**Recommended practice (offered in Release):**")
            lines.append(f"  {_render_inline(practice)}")
            lines.append("")

        dedication = d.get("dedication_text")
        if dedication:
            lines.append("**Dedication sealed:**")
            lines.append(f"  > {dedication}")
            lines.append("")

        return "\n".join(lines) + "\n"


def _render_inline(value) -> str:
    """Render a context value as a compact single-line string.

    Lists become ``"a, b, c"``; dicts become ``"k: v; k2: v2"`` (max 6
    items); everything else is ``str(value)``. Defensive truncation keeps
    large chart dicts from blowing up the system prompt.
    """
    if isinstance(value, (list, tuple)):
        items = [str(v) for v in value[:8]]
        rendered = ", ".join(items)
        if len(value) > 8:
            rendered += f", ... (+{len(value) - 8} more)"
        return rendered
    if isinstance(value, dict):
        items = list(value.items())[:6]
        rendered = "; ".join(f"{k}: {v}" for k, v in items)
        if len(value) > 6:
            rendered += f"; ... (+{len(value) - 6} more)"
        return rendered
    return str(value)


__all__ = ["HealingPhaseContextModule"]
