# tests/core/healing_dialogue/test_service.py
"""Tests for HealingDialogueService — session lifecycle + DB persistence.

Strategy:
* Each test gets a fresh tmp SQLite DB via the ``healing_service`` fixture,
  which monkeypatches ``core.schema.get_db_path`` to a ``tmp_path`` file and
  initializes the schema. No test ever touches the real ``vajra_stream.db``.
* The LLM is mocked via a ``StubDialogue`` whose ``respond()`` returns a
  configurable canned dict. No real network calls.
* The summary path (triggered on COMPLETED) uses a ``FakeRegistry`` whose
  ``pick_best()`` returns ``None``, forcing the deterministic fallback
  summary — so we never need a second LLM mock.

Covers:
* ``create_session()`` — inserts a row, returns session_id + phase.
* ``process_message()`` — appends user + assistant turns, persists, returns content.
* ``get_session()`` — loads full state by id, including message_history.
* ``list_sessions()`` — returns sessions newest-first.
* ``advance_phase()`` — manual advance walks ARRIVAL -> SEEING -> ...
* Phase hint from the LLM advances the phase within ``process_message``.
* ``get_session()`` raises KeyError on a missing id.
"""
from __future__ import annotations

import sqlite3

import pytest

from conftest import FakeEmptyRegistry, StubDialogue
from core.schema import apply_schema
from modules.healing_dialogue import HealingDialogueService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def healing_service(tmp_path, monkeypatch):
    """Yield a HealingDialogueService backed by a fresh tmp SQLite DB.

    * Patches ``core.schema.get_db_path`` to point at ``<tmp_path>/test.db``.
    * Applies the full schema so every table exists.
    * Injects a StubDialogue so no real LLM is contacted.
    * Injects a FakeEmptyRegistry so summarize_session uses the fallback.
    """
    db_path = str(tmp_path / "test.db")
    # Patch get_db_path on the schema module — the service does a function-
    # level `from core.schema import get_db_path` inside _connect(), so the
    # patched attribute is picked up on every call.
    import core.schema as schema_mod

    monkeypatch.setattr(schema_mod, "get_db_path", lambda *a, **k: db_path)

    # Initialize the schema on the tmp DB.
    conn = sqlite3.connect(db_path)
    apply_schema(conn)
    conn.close()

    service = HealingDialogueService(event_bus=None)
    # Bypass the lazy registry/dialogue builders so we never construct a real
    # ProviderRegistry (which would try to read env vars / network).
    service._registry = FakeEmptyRegistry()  # noqa: SLF001
    service._dialogue = StubDialogue()  # noqa: SLF001
    return service


# ---------------------------------------------------------------------------
# create_session()
# ---------------------------------------------------------------------------


async def test_create_session_returns_session_id_and_arrival_phase(healing_service):
    """create_session() returns an int session_id at the ARRIVAL phase."""
    result = await healing_service.create_session()

    assert isinstance(result["session_id"], int)
    assert result["session_id"] >= 1
    assert result["phase"] == "arrival"
    assert "started_at" in result
    assert result["chart_id"] is None
    assert result["session_type"] == "dialogue"


async def test_create_session_persists_row_to_db(healing_service):
    """create_session() inserts a row that list_sessions() can see."""
    created = await healing_service.create_session()

    sessions = await healing_service.list_sessions()
    assert len(sessions) == 1
    assert sessions[0]["session_id"] == created["session_id"]


async def test_create_session_with_chart_id_and_type(healing_service):
    """create_session() honors chart_id and session_type kwargs."""
    result = await healing_service.create_session(chart_id=7, session_type="reflection")
    assert result["chart_id"] == 7
    assert result["session_type"] == "reflection"


async def test_create_multiple_sessions_yields_distinct_ids(healing_service):
    """Each create_session() call returns a new autoincrement id."""
    first = await healing_service.create_session()
    second = await healing_service.create_session()
    third = await healing_service.create_session()
    ids = {first["session_id"], second["session_id"], third["session_id"]}
    assert len(ids) == 3


# ---------------------------------------------------------------------------
# process_message()
# ---------------------------------------------------------------------------


async def test_process_message_returns_content_and_phase(healing_service):
    """process_message() returns the assistant content and the current phase."""
    healing_service.dialogue.next_response = {
        "content": "I hear the weight of this. You are not alone.",
        "phase_hint": None,
        "insights_update": {},
    }
    session = await healing_service.create_session()

    result = await healing_service.process_message(session["session_id"], "I lost everything.")

    assert result["session_id"] == session["session_id"]
    assert result["content"] == "I hear the weight of this. You are not alone."
    assert result["phase"] == "arrival"
    assert result["phase_hint"] is None


async def test_process_message_appends_user_and_assistant_to_history(healing_service):
    """After process_message(), get_session() shows both turns in message_history."""
    healing_service.dialogue.next_response = {
        "content": "I am present with you.",
        "phase_hint": None,
        "insights_update": {},
    }
    session = await healing_service.create_session()

    await healing_service.process_message(session["session_id"], "I feel heavy.")

    loaded = await healing_service.get_session(session["session_id"])
    roles = [m["role"] for m in loaded["message_history"]]
    contents = [m["content"] for m in loaded["message_history"]]
    assert roles == ["user", "assistant"]
    assert contents[0] == "I feel heavy."
    assert contents[1] == "I am present with you."


async def test_process_message_merges_insights(healing_service):
    """insights_update from the LLM is merged into accumulated_insights."""
    healing_service.dialogue.next_response = {
        "content": "I feel the grief and fear in your chest.",
        "phase_hint": None,
        "insights_update": {
            "emotions": ["grief", "fear"],
            "body_locations": ["chest"],
        },
    }
    session = await healing_service.create_session()

    await healing_service.process_message(session["session_id"], "it's heavy.")

    loaded = await healing_service.get_session(session["session_id"])
    assert loaded["accumulated_insights"]["emotions"] == ["grief", "fear"]
    assert loaded["accumulated_insights"]["body_locations"] == ["chest"]


async def test_process_message_returns_hint_without_advancing(healing_service):
    """The LLM may suggest a phase transition, but the phase does NOT change
    automatically. The hint is returned so the user can decide to advance."""
    healing_service.dialogue.next_response = {
        "content": "I hear you. Shall we see what the stars say?",
        "phase_hint": "seeing",
        "insights_update": {},
    }
    session = await healing_service.create_session()
    assert session["phase"] == "arrival"

    result = await healing_service.process_message(session["session_id"], "why did this happen?")
    assert result["phase"] == "arrival"  # phase UNCHANGED
    assert result["phase_hint"] == "seeing"  # hint returned as suggestion


async def test_process_message_ignores_backward_phase_hint(healing_service):
    """A phase_hint naming the current or earlier phase is rejected (no advance)."""
    healing_service.dialogue.next_response = {
        "content": "Let's go back.",
        "phase_hint": "arrival",  # same as current — must not move
        "insights_update": {},
    }
    session = await healing_service.create_session()

    result = await healing_service.process_message(session["session_id"], "hi")
    assert result["phase"] == "arrival"


async def test_process_message_ignores_invalid_phase_hint(healing_service):
    """A phase_hint with a bogus value is rejected gracefully (no advance, no crash)."""
    healing_service.dialogue.next_response = {
        "content": "hmm",
        "phase_hint": "not-a-phase",
        "insights_update": {},
    }
    session = await healing_service.create_session()

    result = await healing_service.process_message(session["session_id"], "hi")
    assert result["phase"] == "arrival"


async def test_process_message_unknown_session_raises_keyerror(healing_service):
    """process_message() on a missing session_id raises KeyError (404 in the API)."""
    with pytest.raises(KeyError):
        await healing_service.process_message(99999, "hello")


# ---------------------------------------------------------------------------
# get_session()
# ---------------------------------------------------------------------------


async def test_get_session_returns_full_state(healing_service):
    """get_session() returns phase, started_at, empty history, and DB columns."""
    created = await healing_service.create_session(chart_id=3)

    loaded = await healing_service.get_session(created["session_id"])
    assert loaded["session_id"] == created["session_id"]
    assert loaded["phase"] == "arrival"
    assert loaded["chart_id"] == 3
    assert loaded["message_history"] == []
    assert loaded["accumulated_insights"] == {}
    assert loaded["summary"] is None
    assert loaded["key_insights"] is None


async def test_get_session_missing_id_raises_keyerror(healing_service):
    """get_session() on a missing id raises KeyError."""
    with pytest.raises(KeyError):
        await healing_service.get_session(99999)


# ---------------------------------------------------------------------------
# list_sessions()
# ---------------------------------------------------------------------------


async def test_list_sessions_empty_when_none_exist(healing_service):
    """list_sessions() on a fresh DB returns an empty list."""
    assert await healing_service.list_sessions() == []


async def test_list_sessions_returns_rows_newest_first(healing_service):
    """list_sessions() returns sessions ordered by started_at DESC."""
    first = await healing_service.create_session()
    await healing_service.create_session()  # middle session — ordering anchor only
    third = await healing_service.create_session()

    sessions = await healing_service.list_sessions()
    ids = [s["session_id"] for s in sessions]
    # Newest first — third was created last so should be first in the list.
    assert ids[0] == third["session_id"]
    assert ids[-1] == first["session_id"]
    assert len(sessions) == 3


async def test_list_sessions_respects_limit(healing_service):
    """list_sessions(limit=N) caps the number of rows returned."""
    for _ in range(5):
        await healing_service.create_session()

    sessions = await healing_service.list_sessions(limit=2)
    assert len(sessions) == 2


async def test_list_sessions_summary_row_shape(healing_service):
    """Each list_sessions() row has the documented summary keys (no transcript)."""
    await healing_service.create_session(chart_id=11, session_type="reflection")
    sessions = await healing_service.list_sessions()
    row = sessions[0]
    expected_keys = {
        "session_id",
        "chart_id",
        "session_type",
        "started_at",
        "ended_at",
        "summary",
        "phases_completed",
        "linked_outlook_id",
    }
    assert expected_keys.issubset(set(row.keys()))
    assert row["chart_id"] == 11
    assert row["session_type"] == "reflection"
    # No transcript body leaks into the summary row.
    assert "message_history" not in row
    assert "transcript_json" not in row


# ---------------------------------------------------------------------------
# advance_phase()
# ---------------------------------------------------------------------------


async def test_advance_phase_walks_one_step(healing_service):
    """Manual advance_phase() moves ARRIVAL -> SEEING."""
    session = await healing_service.create_session()
    assert session["phase"] == "arrival"

    result = await healing_service.advance_phase(session["session_id"])
    assert result["advanced"] is True
    assert result["phase"] == "seeing"


async def test_advance_phase_full_arc(healing_service):
    """Repeated advance_phase() walks the full arc to COMPLETED."""
    session = await healing_service.create_session()
    sid = session["session_id"]

    seen_phases = []
    for _ in range(5):
        r = await healing_service.advance_phase(sid)
        seen_phases.append(r["phase"])

    assert seen_phases == ["seeing", "meeting", "release", "dedication", "completed"]


async def test_advance_phase_completed_is_sticky(healing_service):
    """Once COMPLETED, advance_phase() reports advanced=False and stays put."""
    session = await healing_service.create_session()
    sid = session["session_id"]

    # Walk to COMPLETED.
    for _ in range(5):
        await healing_service.advance_phase(sid)

    result = await healing_service.advance_phase(sid)
    assert result["advanced"] is False
    assert result["phase"] == "completed"
    assert "already" in result["message"].lower()


async def test_advance_phase_missing_session_raises_keyerror(healing_service):
    """advance_phase() on a missing id raises KeyError."""
    with pytest.raises(KeyError):
        await healing_service.advance_phase(99999)


async def test_advance_phase_into_seeing_with_chart_pulls_no_astrology_when_chart_missing(
    healing_service,
):
    """Advancing into SEEING with a chart_id that doesn't exist -> astrology_context stays None.

    The _pull_astrology_context() helper is defensive: a missing chart row
    returns None rather than crashing the advance.
    """
    session = await healing_service.create_session(chart_id=99999)
    sid = session["session_id"]

    await healing_service.advance_phase(sid)  # ARRIVAL -> SEEING

    loaded = await healing_service.get_session(sid)
    assert loaded["phase"] == "seeing"
    # Chart 99999 doesn't exist, so astrology_context is None (not an error).
    assert loaded["astrology_context"] is None


# ---------------------------------------------------------------------------
# Event emission (light check — event_bus is None by default)
# ---------------------------------------------------------------------------


async def test_create_session_with_event_bus_does_not_crash(tmp_path, monkeypatch):
    """create_session() tolerates an event_bus without raising."""
    db_path = str(tmp_path / "test.db")
    import core.schema as schema_mod

    monkeypatch.setattr(schema_mod, "get_db_path", lambda *a, **k: db_path)
    conn = sqlite3.connect(db_path)
    apply_schema(conn)
    conn.close()

    class RecordingBus:
        def __init__(self):
            self.events = []

        def publish(self, event):
            self.events.append(event)

    bus = RecordingBus()
    service = HealingDialogueService(event_bus=bus)
    service._registry = FakeEmptyRegistry()  # noqa: SLF001
    service._dialogue = StubDialogue()  # noqa: SLF001

    await service.create_session()

    assert len(bus.events) == 1
    # The event is a HealingSessionStarted dataclass.
    assert hasattr(bus.events[0], "target_name")
