# tests/core/healing_dialogue/test_context_module.py
"""Tests for HealingPhaseContextModule.

Covers:
* ``name`` attribute is ``"healing_dialogue"``.
* ``gather()`` returns a :class:`ContextData` with phase info (no error).
* ``render()`` produces non-empty Markdown.
* Insights accumulated on the state are surfaced in the rendered output.
* Recommended practice and dedication text appear when present.
* The module holds a reference to the state, so mutations between calls
  are reflected in subsequent ``gather()`` results.
"""

from __future__ import annotations

from datetime import datetime, timezone

from core.context.healing_dialogue import HealingPhaseContextModule
from core.context.models import ContextRequest
from core.healing_dialogue.phases import DialoguePhase, DialogueState


def _make_state(**overrides) -> DialogueState:
    """Build a minimal DialogueState for tests."""
    base = {
        "session_id": "ctx-test-session",
        "chart_id": None,
        "current_phase": DialoguePhase.SEEING,
        "phase_started_at": datetime.now(timezone.utc),
    }
    base.update(overrides)
    return DialogueState(**base)


# ---------------------------------------------------------------------------
# name attribute
# ---------------------------------------------------------------------------


def test_module_name_is_healing_dialogue():
    """The module's name attribute is exactly 'healing_dialogue'."""
    state = _make_state()
    mod = HealingPhaseContextModule(state)
    assert mod.name == "healing_dialogue"


# ---------------------------------------------------------------------------
# gather()
# ---------------------------------------------------------------------------


async def test_gather_returns_context_data_with_phase_info():
    """gather() returns ContextData carrying session_id, phase, started_at, chart_id."""
    state = _make_state(current_phase=DialoguePhase.MEETING, chart_id=7)
    mod = HealingPhaseContextModule(state)

    data = await mod.gather(ContextRequest())

    assert data.module_name == "healing_dialogue"
    assert data.error is None
    assert data.data["session_id"] == "ctx-test-session"
    assert data.data["current_phase"] == "meeting"
    assert data.data["chart_id"] == 7
    assert data.data["phase_started_at"] is not None


async def test_gather_includes_accumulated_insights_when_present():
    """gather() surfaces the accumulated_insights dict from the state."""
    state = _make_state(
        accumulated_insights={
            "emotions": ["grief", "fear"],
            "body_locations": ["chest"],
        },
    )
    mod = HealingPhaseContextModule(state)

    data = await mod.gather(ContextRequest())

    assert data.data["accumulated_insights"] == {
        "emotions": ["grief", "fear"],
        "body_locations": ["chest"],
    }


async def test_gather_includes_recommended_practice_when_present():
    """gather() surfaces the recommended_practice when the state has one."""
    practice = {"name": "tonglen", "steps": ["breathe in suffering", "send out relief"]}
    state = _make_state(recommended_practice=practice)
    mod = HealingPhaseContextModule(state)

    data = await mod.gather(ContextRequest())

    assert data.data["recommended_practice"] == practice


async def test_gather_includes_dedication_text_when_present():
    """gather() surfaces the dedication_text when the state has one."""
    state = _make_state(dedication_text="May this merit reach all who suffer.")
    mod = HealingPhaseContextModule(state)

    data = await mod.gather(ContextRequest())

    assert data.data["dedication_text"] == "May this merit reach all who suffer."


async def test_gather_omits_optional_fields_when_absent():
    """gather() omits recommended_practice / dedication_text keys when absent."""
    state = _make_state()
    mod = HealingPhaseContextModule(state)

    data = await mod.gather(ContextRequest())

    assert "recommended_practice" not in data.data
    assert "dedication_text" not in data.data


async def test_gather_sees_live_state_mutations():
    """Because the module holds a reference, later gather() calls see mutations."""
    state = _make_state(current_phase=DialoguePhase.ARRIVAL)
    mod = HealingPhaseContextModule(state)

    first = await mod.gather(ContextRequest())
    assert first.data["current_phase"] == "arrival"

    # Mutate the state in place — the module should see it next time.
    state.current_phase = DialoguePhase.RELEASE
    state.accumulated_insights = {"emotions": ["anger"]}

    second = await mod.gather(ContextRequest())
    assert second.data["current_phase"] == "release"
    assert second.data["accumulated_insights"] == {"emotions": ["anger"]}


# ---------------------------------------------------------------------------
# render()
# ---------------------------------------------------------------------------


def test_render_produces_non_empty_markdown():
    """render() returns non-empty Markdown with the phase heading."""
    state = _make_state(current_phase=DialoguePhase.SEEING)
    mod = HealingPhaseContextModule(state)

    # Module holds a reference to the state (not a copy).
    assert mod._state is state  # noqa: SLF001 — intentional reach for the test

    gathered = _gather_sync(mod)
    rendered = mod.render(gathered)
    assert isinstance(rendered, str)
    assert rendered.strip() != ""
    assert "Healing Dialogue Context" in rendered
    assert "SEEING" in rendered


def test_render_surfaces_accumulated_insights():
    """Insights on the state are rendered into the Markdown output (sync path)."""
    state = _make_state(
        accumulated_insights={
            "emotions": ["grief", "fear"],
            "body_locations": ["chest", "throat"],
            "themes": ["cosmic_timing"],
        },
    )
    mod = HealingPhaseContextModule(state)
    gathered = _gather_sync(mod)
    rendered = mod.render(gathered)

    assert "Accumulated insights" in rendered
    assert "Emotions" in rendered
    assert "Body Locations" in rendered
    assert "Themes" in rendered
    assert "grief" in rendered
    assert "chest" in rendered


def test_render_surfaces_recommended_practice():
    """The recommended practice appears when present (Release / Dedication phases)."""
    state = _make_state(
        current_phase=DialoguePhase.RELEASE,
        recommended_practice={
            "name": "Vajrasattva purification",
            "tradition": "Vajrayana",
        },
    )
    mod = HealingPhaseContextModule(state)
    gathered = _gather_sync(mod)
    rendered = mod.render(gathered)

    assert "Recommended practice" in rendered
    assert "Vajrasattva" in rendered


def test_render_surfaces_dedication_text():
    """The dedication text is rendered as a blockquote when present."""
    dedication = "May whatever merit arose here reach all beings who suffer loss."
    state = _make_state(
        current_phase=DialoguePhase.DEDICATION,
        dedication_text=dedication,
    )
    mod = HealingPhaseContextModule(state)
    gathered = _gather_sync(mod)
    rendered = mod.render(gathered)

    assert "Dedication sealed" in rendered
    assert dedication in rendered


def test_render_includes_session_id_and_chart_id():
    """render() surfaces the session_id (inline code) and chart_id when linked."""
    state = _make_state(chart_id=42)
    mod = HealingPhaseContextModule(state)
    gathered = _gather_sync(mod)
    rendered = mod.render(gathered)

    assert "ctx-test-session" in rendered
    assert "id=42" in rendered


def test_render_empty_data_returns_empty_string():
    """render() with empty ContextData returns an empty string."""
    from core.context.models import ContextData

    state = _make_state()
    mod = HealingPhaseContextModule(state)
    assert mod.render(ContextData(module_name="healing_dialogue")) == ""


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _gather_sync(mod: HealingPhaseContextModule):
    """Run gather() synchronously for the sync render() tests.

    Uses ``asyncio.run`` for a fresh, self-contained event loop per call.
    """
    import asyncio

    return asyncio.run(mod.gather(ContextRequest()))
