# tests/backend/test_healing_endpoints.py
"""End-to-end REST tests for the healing dialogue endpoints.

Strategy:
* A ``healing_app`` fixture builds a :class:`TestClient` whose
  ``HealingDialogueService`` is wired to a fresh tmp SQLite DB and a
  :class:`StubDialogue` (no real LLM calls, no network).
* The service factory ``get_healing_service`` is monkeypatched to return the
  pre-configured service, so every endpoint request uses our stubs.
* Each test is fully isolated — fresh tmp DB, fresh service, fresh history.

Covers:
* ``POST /api/v1/healing/sessions`` — creates a session, returns 200.
* ``GET  /api/v1/healing/sessions`` — lists sessions.
* ``GET  /api/v1/healing/sessions/{id}`` — loads a specific session.
* ``POST /api/v1/healing/sessions/{id}/advance`` — advances the phase.
* ``POST /api/v1/healing/sessions/{id}/messages`` — sends a message (LLM mocked).
* ``GET  /api/v1/healing/sessions/{missing}`` — returns 404.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# The StubDialogue / FakeEmptyRegistry doubles live in the healing-dialogue
# conftest and are shared with tests/core/healing_dialogue/test_service.py.
# Add that directory to sys.path so we can import them here without duplicating.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core" / "healing_dialogue"))
from conftest import FakeEmptyRegistry, StubDialogue  # noqa: E402

from core.schema import apply_schema
from modules.healing_dialogue import HealingDialogueService

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def healing_app(tmp_path, monkeypatch):
    """Build a TestClient wired to a tmp DB + StubDialogue.

    Returns a small ``App`` namespace with ``client`` (the TestClient) and
    ``dialogue`` (the StubDialogue, so tests can mutate ``next_response``).
    """
    db_path = str(tmp_path / "test.db")
    import core.schema as schema_mod

    monkeypatch.setattr(schema_mod, "get_db_path", lambda *a, **k: db_path)

    # Initialize the schema on the tmp DB.
    conn = sqlite3.connect(db_path)
    apply_schema(conn)
    conn.close()

    # Build the service with stubbed collaborators so no real LLM/registry
    # is ever constructed.
    service = HealingDialogueService(event_bus=None)
    service._registry = FakeEmptyRegistry()  # noqa: SLF001
    stub_dialogue = StubDialogue()
    service._dialogue = stub_dialogue  # noqa: SLF001

    # Patch the per-request factory so every endpoint uses our service.
    import backend.app.api.v1.endpoints.healing_dialogue as endpoint_mod

    monkeypatch.setattr(endpoint_mod, "get_healing_service", lambda: service)

    from backend.app.main import app

    client = TestClient(app)

    class App:
        def __init__(self, client, dialogue, service):
            self.client = client
            self.dialogue = dialogue
            self.service = service

    return App(client=client, dialogue=stub_dialogue, service=service)


# ---------------------------------------------------------------------------
# POST /api/v1/healing/sessions
# ---------------------------------------------------------------------------


def test_create_session_endpoint_returns_200(healing_app):
    """POST /sessions creates a session and returns 200 with the session id."""
    resp = healing_app.client.post("/api/v1/healing/sessions")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["session_id"], int)
    assert body["phase"] == "arrival"
    assert "started_at" in body


def test_create_session_endpoint_accepts_query_params(healing_app):
    """chart_id and session_type can be passed as query params."""
    resp = healing_app.client.post(
        "/api/v1/healing/sessions",
        params={"chart_id": 5, "session_type": "reflection"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["chart_id"] == 5
    assert body["session_type"] == "reflection"


# ---------------------------------------------------------------------------
# GET /api/v1/healing/sessions
# ---------------------------------------------------------------------------


def test_list_sessions_endpoint_returns_empty_initially(healing_app):
    """GET /sessions returns an empty list when no sessions exist."""
    resp = healing_app.client.get("/api/v1/healing/sessions")
    assert resp.status_code == 200
    body = resp.json()
    assert body["sessions"] == []
    assert body["count"] == 0


def test_list_sessions_endpoint_returns_created_sessions(healing_app):
    """GET /sessions lists sessions created via POST."""
    # Create two sessions.
    r1 = healing_app.client.post("/api/v1/healing/sessions").json()
    r2 = healing_app.client.post("/api/v1/healing/sessions").json()

    resp = healing_app.client.get("/api/v1/healing/sessions")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 2
    ids = [s["session_id"] for s in body["sessions"]]
    assert {r1["session_id"], r2["session_id"]} == set(ids)


def test_list_sessions_endpoint_respects_limit(healing_app):
    """GET /sessions?limit=N caps the row count."""
    for _ in range(3):
        healing_app.client.post("/api/v1/healing/sessions")

    resp = healing_app.client.get("/api/v1/healing/sessions", params={"limit": 1})
    assert resp.status_code == 200
    assert resp.json()["count"] == 1


# ---------------------------------------------------------------------------
# GET /api/v1/healing/sessions/{id}
# ---------------------------------------------------------------------------


def test_get_session_endpoint_returns_full_state(healing_app):
    """GET /sessions/{id} returns the session's full state."""
    created = healing_app.client.post("/api/v1/healing/sessions").json()
    sid = created["session_id"]

    resp = healing_app.client.get(f"/api/v1/healing/sessions/{sid}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == sid
    assert body["phase"] == "arrival"
    assert body["message_history"] == []
    assert body["summary"] is None


def test_get_session_endpoint_returns_404_for_missing_id(healing_app):
    """GET /sessions/{missing} returns 404."""
    resp = healing_app.client.get("/api/v1/healing/sessions/999999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/healing/sessions/{id}/advance
# ---------------------------------------------------------------------------


def test_advance_phase_endpoint_advances_to_seeing(healing_app):
    """POST /sessions/{id}/advance moves ARRIVAL -> SEEING."""
    created = healing_app.client.post("/api/v1/healing/sessions").json()
    sid = created["session_id"]

    resp = healing_app.client.post(f"/api/v1/healing/sessions/{sid}/advance")
    assert resp.status_code == 200
    body = resp.json()
    assert body["advanced"] is True
    assert body["phase"] == "seeing"


def test_advance_phase_endpoint_404_for_missing_id(healing_app):
    """POST /sessions/{missing}/advance returns 404."""
    resp = healing_app.client.post("/api/v1/healing/sessions/999999/advance")
    assert resp.status_code == 404


def test_advance_phase_endpoint_completed_reports_advanced_false(healing_app):
    """After reaching COMPLETED, advance reports advanced=False."""
    created = healing_app.client.post("/api/v1/healing/sessions").json()
    sid = created["session_id"]

    # Walk all 5 advances to reach COMPLETED.
    for _ in range(5):
        healing_app.client.post(f"/api/v1/healing/sessions/{sid}/advance")

    resp = healing_app.client.post(f"/api/v1/healing/sessions/{sid}/advance")
    assert resp.status_code == 200
    body = resp.json()
    assert body["advanced"] is False
    assert body["phase"] == "completed"


# ---------------------------------------------------------------------------
# POST /api/v1/healing/sessions/{id}/messages
# ---------------------------------------------------------------------------


def test_send_message_endpoint_returns_assistant_content(healing_app):
    """POST /sessions/{id}/messages returns the mocked assistant content."""
    healing_app.dialogue.next_response = {
        "content": "I hear the weight of this. You are held.",
        "phase_hint": None,
        "insights_update": {},
    }
    created = healing_app.client.post("/api/v1/healing/sessions").json()
    sid = created["session_id"]

    resp = healing_app.client.post(
        f"/api/v1/healing/sessions/{sid}/messages",
        json={"message": "I lost everything in the market today."},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["content"] == "I hear the weight of this. You are held."
    assert body["phase"] == "arrival"
    assert body["session_id"] == sid


def test_send_message_endpoint_appends_turns_to_history(healing_app):
    """After POST messages, GET session shows both turns in history."""
    healing_app.dialogue.next_response = {
        "content": "I am present with you.",
        "phase_hint": None,
        "insights_update": {},
    }
    created = healing_app.client.post("/api/v1/healing/sessions").json()
    sid = created["session_id"]

    healing_app.client.post(
        f"/api/v1/healing/sessions/{sid}/messages",
        json={"message": "I feel heavy."},
    )

    loaded = healing_app.client.get(f"/api/v1/healing/sessions/{sid}").json()
    roles = [m["role"] for m in loaded["message_history"]]
    contents = [m["content"] for m in loaded["message_history"]]
    assert roles == ["user", "assistant"]
    assert contents == ["I feel heavy.", "I am present with you."]


def test_send_message_endpoint_404_for_missing_session(healing_app):
    """POST /sessions/{missing}/messages returns 404."""
    resp = healing_app.client.post(
        "/api/v1/healing/sessions/999999/messages",
        json={"message": "hello"},
    )
    assert resp.status_code == 404


def test_send_message_endpoint_422_for_empty_message(healing_app):
    """POST /messages with an empty message body fails validation (422)."""
    created = healing_app.client.post("/api/v1/healing/sessions").json()
    sid = created["session_id"]

    resp = healing_app.client.post(
        f"/api/v1/healing/sessions/{sid}/messages",
        json={"message": ""},
    )
    assert resp.status_code == 422


def test_send_message_endpoint_returns_hint_without_advancing(healing_app):
    """The LLM may suggest a phase transition, but the phase stays the same.
    The hint is returned so the frontend can offer an Advance button."""
    healing_app.dialogue.next_response = {
        "content": "Shall we see what the stars say about this?",
        "phase_hint": "seeing",
        "insights_update": {},
    }
    created = healing_app.client.post("/api/v1/healing/sessions").json()
    sid = created["session_id"]

    resp = healing_app.client.post(
        f"/api/v1/healing/sessions/{sid}/messages",
        json={"message": "why did this happen?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["phase"] == "arrival"  # phase UNCHANGED
    assert data["phase_hint"] == "seeing"  # hint returned as suggestion


# ---------------------------------------------------------------------------
# Independence: each test gets a fresh DB
# ---------------------------------------------------------------------------


def test_sessions_do_not_leak_between_tests(healing_app):
    """Sanity check: the fixture's tmp DB starts empty for each test."""
    resp = healing_app.client.get("/api/v1/healing/sessions")
    assert resp.json()["count"] == 0
