"""GET /api/v1/practices/{id}/status must include the count key the UI reads.

Ticket CD-4: the engine's status dict reports recitations under
``total_recited`` (core/practice_engine.py), and the route returned that dict
as-is, while frontend/src/components/UI/PracticeDetail.tsx reads
``typeof data.count === 'number' ? data.count : 0`` — so the live recitation
counter rendered 0 forever. The fix is additive: every shape the route
returns now also carries ``count`` (== total_recited; 0 when not started).

Offline: TestClient against a bare FastAPI app with the practices router and
a patched engine — no server, no DB, no network.
"""

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.v1.endpoints import practices as practices_endpoint


class FakeDefinition:
    def __init__(self, name: str) -> None:
        self.name = name


class FakeEngine:
    """Minimal engine double: one known practice, pluggable status dict."""

    def __init__(self, status: dict[str, Any] | None) -> None:
        self._status = status

    def get_definition(self, practice_id: str) -> FakeDefinition | None:
        if practice_id == "metta":
            return FakeDefinition("Metta Bhavana")
        return None

    def status(self, practice_id: str) -> dict[str, Any] | None:
        return self._status


@pytest.fixture()
def client(monkeypatch) -> TestClient:
    app = FastAPI()
    app.include_router(practices_endpoint.router, prefix="/api/v1")

    def _fake_engine() -> FakeEngine:
        return FakeEngine(app.state.status)

    monkeypatch.setattr(practices_endpoint, "get_practice_engine", _fake_engine)
    return TestClient(app)


def _running_status() -> dict[str, Any]:
    return {
        "practice_id": "metta",
        "practice_name": "Metta Bhavana",
        "intention": "may all beings be happy",
        "target_count": 108,
        "total_recited": 7,
        "mala_count": 7,
        "mala_rounds": 0,
        "current_repetition": 8,
        "running": True,
        "started_at": "2026-10-21T04:00:00+00:00",
        "last_recited_at": "2026-10-21T04:00:42+00:00",
        "elapsed_seconds": 42.0,
        "progress_pct": 6.5,
    }


def test_running_practice_returns_count_equal_to_total_recited(client: TestClient, monkeypatch) -> None:
    client.app.state.status = _running_status()
    response = client.get("/api/v1/practices/metta/status")
    assert response.status_code == 200
    data = response.json()

    assert data["count"] == 7, "count must mirror the engine's total_recited for the UI counter"
    assert data["total_recited"] == 7, "existing engine keys must be unchanged"
    assert data["running"] is True


def test_never_started_practice_returns_count_zero(client: TestClient, monkeypatch) -> None:
    client.app.state.status = None
    response = client.get("/api/v1/practices/metta/status")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "not_started"
    assert data["count"] == 0, "the not_started shape must also carry count (0) for the UI counter"
    assert data["practice_id"] == "metta"


def test_unknown_practice_id_is_still_404(client: TestClient, monkeypatch) -> None:
    client.app.state.status = _running_status()
    response = client.get("/api/v1/practices/nope/status")
    assert response.status_code == 404
