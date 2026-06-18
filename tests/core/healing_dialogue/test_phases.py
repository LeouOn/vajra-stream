# tests/core/healing_dialogue/test_phases.py
"""Tests for the five-phase dialogue arc and DialogueState data model.

Covers:
* :class:`DialoguePhase` enum values + ``next_after`` ordering.
* :class:`DialogueState` construction with defaults.
* ``to_dict()`` / ``from_dict()`` round-trip fidelity (all fields preserved).
* ``advance_phase()`` walks the full arc ARRIVAL -> ... -> COMPLETED.
* ``is_terminal()`` is False for every phase except COMPLETED.
* ``append_message()`` records ``{role, content, timestamp}`` entries.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from core.healing_dialogue.phases import DialoguePhase, DialogueState

# ---------------------------------------------------------------------------
# DialoguePhase enum
# ---------------------------------------------------------------------------


def test_dialogue_phase_enum_values():
    """The enum has the six documented members with the documented values."""
    assert DialoguePhase.ARRIVAL.value == "arrival"
    assert DialoguePhase.SEEING.value == "seeing"
    assert DialoguePhase.MEETING.value == "meeting"
    assert DialoguePhase.RELEASE.value == "release"
    assert DialoguePhase.DEDICATION.value == "dedication"
    assert DialoguePhase.COMPLETED.value == "completed"


def test_dialogue_phase_enum_membership():
    """DialoguePhase('arrival') resolves to ARRIVAL (used by from_dict)."""
    assert DialoguePhase("arrival") is DialoguePhase.ARRIVAL
    assert DialoguePhase("completed") is DialoguePhase.COMPLETED


def test_dialogue_phase_unknown_value_raises():
    """An unknown phase string raises ValueError."""
    with pytest.raises(ValueError):
        DialoguePhase("not-a-phase")


@pytest.mark.parametrize(
    ("current", "expected_next"),
    [
        (DialoguePhase.ARRIVAL, DialoguePhase.SEEING),
        (DialoguePhase.SEEING, DialoguePhase.MEETING),
        (DialoguePhase.MEETING, DialoguePhase.RELEASE),
        (DialoguePhase.RELEASE, DialoguePhase.DEDICATION),
        (DialoguePhase.DEDICATION, DialoguePhase.COMPLETED),
        (DialoguePhase.COMPLETED, DialoguePhase.COMPLETED),
    ],
)
def test_next_after_walks_the_arc(current, expected_next):
    """next_after() returns the following phase; COMPLETED is its own successor."""
    assert DialoguePhase.next_after(current) is expected_next


# ---------------------------------------------------------------------------
# DialogueState construction
# ---------------------------------------------------------------------------


def _make_state(**overrides) -> DialogueState:
    """Build a minimal DialogueState with sensible defaults for tests."""
    base = {
        "session_id": "test-session-1",
        "chart_id": None,
        "current_phase": DialoguePhase.ARRIVAL,
        "phase_started_at": datetime.now(timezone.utc),
    }
    base.update(overrides)
    return DialogueState(**base)


def test_dialogue_state_defaults():
    """Optional fields get empty/dict/None defaults; started_at is stamped."""
    state = _make_state()
    assert state.message_history == []
    assert state.accumulated_insights == {}
    assert state.astrology_context is None
    assert state.somatic_findings is None
    assert state.recommended_practice is None
    assert state.dedication_text is None
    assert state.completed_at is None
    # started_at is auto-populated and timezone-aware.
    assert isinstance(state.started_at, datetime)
    assert state.started_at.tzinfo is not None


# ---------------------------------------------------------------------------
# Serialization round-trip
# ---------------------------------------------------------------------------


def test_to_dict_from_dict_round_trip_preserves_all_fields():
    """to_dict() -> from_dict() preserves every field (including nested data)."""
    started = datetime(2026, 6, 17, 10, 0, tzinfo=timezone.utc)
    phase_started = datetime(2026, 6, 17, 10, 5, tzinfo=timezone.utc)
    completed = datetime(2026, 6, 17, 11, 0, tzinfo=timezone.utc)

    original = DialogueState(
        session_id="round-trip-1",
        chart_id=42,
        current_phase=DialoguePhase.MEETING,
        phase_started_at=phase_started,
        message_history=[
            {"role": "user", "content": "I lost everything.", "timestamp": phase_started.isoformat()},
            {"role": "assistant", "content": "I hear you.", "timestamp": phase_started.isoformat()},
        ],
        accumulated_insights={
            "emotions": ["grief", "fear"],
            "body_locations": ["chest"],
            "themes": ["cosmic_timing"],
        },
        astrology_context={"chart_id": 42, "natal": {"sun": "Gemini"}},
        somatic_findings={"primary": "chest tightness"},
        recommended_practice={"name": "tonglen", "steps": ["breathe in"]},
        dedication_text="May this merit reach all who suffer.",
        started_at=started,
        completed_at=completed,
    )

    serialized = original.to_dict()
    # Serialized form must be JSON-safe types only.
    assert isinstance(serialized["current_phase"], str)
    assert serialized["current_phase"] == "meeting"
    assert isinstance(serialized["phase_started_at"], str)
    assert isinstance(serialized["started_at"], str)
    assert isinstance(serialized["completed_at"], str)

    restored = DialogueState.from_dict(serialized)

    assert restored.session_id == original.session_id
    assert restored.chart_id == original.chart_id
    assert restored.current_phase is original.current_phase
    assert restored.phase_started_at == original.phase_started_at
    assert restored.message_history == original.message_history
    assert restored.accumulated_insights == original.accumulated_insights
    assert restored.astrology_context == original.astrology_context
    assert restored.somatic_findings == original.somatic_findings
    assert restored.recommended_practice == original.recommended_practice
    assert restored.dedication_text == original.dedication_text
    assert restored.started_at == original.started_at
    assert restored.completed_at == original.completed_at


def test_from_dict_ignores_unknown_keys():
    """Unknown keys in the dict are ignored (defensive forward-compat)."""
    payload = {
        "session_id": "ignore-unknown",
        "current_phase": "arrival",
        "phase_started_at": datetime.now(timezone.utc).isoformat(),
        "future_field": "ignored",
        "another_unknown": 123,
    }
    state = DialogueState.from_dict(payload)
    assert state.session_id == "ignore-unknown"
    assert state.current_phase is DialoguePhase.ARRIVAL


def test_from_dict_missing_phase_raises():
    """from_dict raises KeyError when current_phase is absent."""
    with pytest.raises(KeyError):
        DialogueState.from_dict({"session_id": "x"})


# ---------------------------------------------------------------------------
# advance_phase
# ---------------------------------------------------------------------------


def test_advance_phase_walks_full_arc_and_stamps_phase_started_at():
    """Each advance moves one step; phase_started_at updates; COMPLETED is sticky."""
    state = _make_state()
    first_phase_started = state.phase_started_at

    seen: list[DialoguePhase] = [state.current_phase]
    for _ in range(10):  # walk past the end deliberately
        state.advance_phase()
        seen.append(state.current_phase)

    # The arc is exactly: ARRIVAL -> SEEING -> MEETING -> RELEASE -> DEDICATION
    # -> COMPLETED -> COMPLETED -> ...
    expected = [
        DialoguePhase.ARRIVAL,
        DialoguePhase.SEEING,
        DialoguePhase.MEETING,
        DialoguePhase.RELEASE,
        DialoguePhase.DEDICATION,
        DialoguePhase.COMPLETED,
        DialoguePhase.COMPLETED,
        DialoguePhase.COMPLETED,
        DialoguePhase.COMPLETED,
        DialoguePhase.COMPLETED,
        DialoguePhase.COMPLETED,
    ]
    assert seen == expected

    # phase_started_at advanced past the original.
    assert state.phase_started_at >= first_phase_started


def test_advance_phase_into_completed_stamps_completed_at():
    """completed_at is stamped exactly once on entering COMPLETED."""
    state = _make_state(current_phase=DialoguePhase.DEDICATION)
    assert state.completed_at is None

    state.advance_phase()
    assert state.current_phase is DialoguePhase.COMPLETED
    assert state.completed_at is not None

    # Advancing again from COMPLETED must not overwrite completed_at.
    first = state.completed_at
    state.advance_phase()
    assert state.completed_at == first


# ---------------------------------------------------------------------------
# is_terminal
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("phase", "expected"),
    [
        (DialoguePhase.ARRIVAL, False),
        (DialoguePhase.SEEING, False),
        (DialoguePhase.MEETING, False),
        (DialoguePhase.RELEASE, False),
        (DialoguePhase.DEDICATION, False),
        (DialoguePhase.COMPLETED, True),
    ],
)
def test_is_terminal_only_true_for_completed(phase, expected):
    """is_terminal() returns True only when current_phase is COMPLETED."""
    state = _make_state(current_phase=phase)
    assert state.is_terminal() is expected


# ---------------------------------------------------------------------------
# append_message
# ---------------------------------------------------------------------------


def test_append_message_adds_entry_with_timestamp():
    """append_message appends {role, content, timestamp} to message_history."""
    state = _make_state()
    assert state.message_history == []

    state.append_message("user", "I lost everything in the market today.")
    state.append_message("assistant", "I am here with you.")

    assert len(state.message_history) == 2

    user_msg = state.message_history[0]
    assert user_msg["role"] == "user"
    assert user_msg["content"] == "I lost everything in the market today."
    assert "timestamp" in user_msg
    # timestamp is an ISO-8601 string parseable back to a datetime.
    parsed = datetime.fromisoformat(user_msg["timestamp"])
    assert parsed.tzinfo is not None

    assistant_msg = state.message_history[1]
    assert assistant_msg["role"] == "assistant"
    assert assistant_msg["content"] == "I am here with you."


def test_append_message_preserves_order():
    """Multiple appends land in chronological order at the tail of the list."""
    state = _make_state()
    for i in range(5):
        state.append_message("user", f"message-{i}")
    assert [m["content"] for m in state.message_history] == [
        "message-0",
        "message-1",
        "message-2",
        "message-3",
        "message-4",
    ]
