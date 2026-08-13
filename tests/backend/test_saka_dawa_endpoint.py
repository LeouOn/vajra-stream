# tests/backend/test_saka_dawa_endpoint.py
"""GET /api/v1/operator/saka-dawa — Losar-anchored Saka Dawa calendar."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from backend.app.main import app

    return TestClient(app)


def test_saka_dawa_endpoint_returns_lunar_fields_not_hardcoded_months(client):
    """Response is the Losar-anchored payload, not Gregorian May–June."""
    resp = client.get("/api/v1/operator/saka-dawa", params={"at": "2026-05-31"})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    body = resp.json()

    assert "is_saka_dawa" in body
    assert isinstance(body["is_saka_dawa"], bool)
    assert "is_duchen" in body
    assert isinstance(body["is_duchen"], bool)
    assert "multiplier" in body
    assert body["multiplier"] in (1, 10000, 100000)
    assert "lunar_month" in body
    assert "lunar_day" in body
    assert "current_date" in body
    assert isinstance(body["current_date"], str)
    assert "T" in body["current_date"]
    assert "losar" in body
    assert "saka_dawa_duchen" in body

    assert "saka_dawa_months" not in body, (
        f"OLD KEY 'saka_dawa_months' found in response — endpoint still hardcoded: {body.get('saka_dawa_months')}"
    )
    assert "in_saka_dawa_window" not in body, (
        "OLD KEY 'in_saka_dawa_window' found in response — endpoint still hardcoded"
    )


def test_saka_dawa_endpoint_2025_duchen_follows_losar_not_chinese_ny(client):
    """2025 Losar is Feb 28; Duchen is June 11, not the Chinese-month-4 full moon."""
    resp = client.get("/api/v1/operator/saka-dawa", params={"at": "2025-06-11"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_saka_dawa"] is True
    assert body["is_duchen"] is True
    assert body["multiplier"] == 100000
    assert body["losar"] == "2025-02-28"
    assert body["saka_dawa_duchen"] == "2025-06-11"
    assert body["calendar"] == "phugpa-losar"


def test_saka_dawa_endpoint_rejects_chinese_new_year_2025(client):
    """Jan 29 2025 is Chinese New Year, not Losar — must not be Saka Dawa."""
    resp = client.get("/api/v1/operator/saka-dawa", params={"at": "2025-01-29"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_saka_dawa"] is False
    assert body["is_duchen"] is False


def test_saka_dawa_endpoint_rejects_bad_at_param(client):
    resp = client.get("/api/v1/operator/saka-dawa", params={"at": "not-a-date"})
    assert resp.status_code == 400
