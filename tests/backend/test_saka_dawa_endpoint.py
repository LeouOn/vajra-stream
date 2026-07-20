# tests/backend/test_saka_dawa_endpoint.py
"""TDD test for GET /api/v1/operator/saka-dawa — lunar calendar integration.

Task 3 (RED): Prove the gap — endpoint returns hardcoded [5, 6] months
instead of real lunar data from core.auspicious_timing.check_saka_dawa().

Task 4 (GREEN): After wiring the endpoint, this same test passes.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Fixture: TestClient wired to the real FastAPI app
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    """Return a TestClient for the full FastAPI app."""
    from backend.app.main import app

    return TestClient(app)


# ---------------------------------------------------------------------------
# Task 3 — RED: Prove the gap exists
# ---------------------------------------------------------------------------


def test_saka_dawa_endpoint_returns_lunar_fields_not_hardcoded_months(client):
    """GET /api/v1/operator/saka-dawa must return lunar calendar fields.

    The current endpoint hardcodes ``now.month in (5, 6)`` and returns
    ``saka_dawa_months: [5, 6]``.  This test mocks lunar_python so that
    the 4th Tibetan lunar month is active (day 15 = Duchen), then asserts
    the response shape matches what ``check_saka_dawa()`` would return.

    EXPECTED FAILURE (RED): The endpoint does NOT yet call
    ``core.auspicious_timing.check_saka_dawa()``, so the response will
    either be ``{"error": "Saka Dawa practice not found"}`` or contain
    the hardcoded ``saka_dawa_months: [5, 6]`` key — both of which this
    test rejects.
    """
    # ------------------------------------------------------------------
    # Mock lunar_python at the point of use (core.auspicious_timing).
    # The endpoint currently does NOT call check_saka_dawa(), so this
    # mock won't affect the RED run — the test fails because the
    # endpoint returns hardcoded [5, 6] instead of lunar fields.
    # After Task 4 wires the endpoint, the mock takes effect and the
    # same test passes (GREEN).
    # ------------------------------------------------------------------
    mock_lunar = MagicMock()
    mock_lunar.getMonth.return_value = 4
    mock_lunar.getDay.return_value = 15

    mock_solar = MagicMock()

    with (
        patch("lunar_python.Solar.Solar.fromYmd", return_value=mock_solar),
        patch("lunar_python.Lunar.Lunar.fromSolar", return_value=mock_lunar),
    ):
        resp = client.get("/api/v1/operator/saka-dawa")

    # The endpoint should return 200 (not 500).
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    body = resp.json()

    # ── MUST HAVE: lunar calendar fields ──────────────────────────────
    assert "is_saka_dawa" in body, f"Missing 'is_saka_dawa' in {list(body.keys())}"
    assert isinstance(body["is_saka_dawa"], bool), f"is_saka_dawa should be bool, got {type(body['is_saka_dawa'])}"

    assert "is_duchen" in body, f"Missing 'is_duchen' in {list(body.keys())}"
    assert isinstance(body["is_duchen"], bool), f"is_duchen should be bool, got {type(body['is_duchen'])}"

    assert "multiplier" in body, f"Missing 'multiplier' in {list(body.keys())}"
    # Day 15 = Duchen → multiplier should be 100000
    assert body["multiplier"] in (10000, 100000), f"multiplier should be 10000 or 100000, got {body['multiplier']}"

    assert "lunar_month" in body, f"Missing 'lunar_month' in {list(body.keys())}"
    assert isinstance(body["lunar_month"], int), f"lunar_month should be int, got {type(body['lunar_month'])}"

    assert "lunar_day" in body, f"Missing 'lunar_day' in {list(body.keys())}"
    assert isinstance(body["lunar_day"], int), f"lunar_day should be int, got {type(body['lunar_day'])}"

    assert "current_date" in body, f"Missing 'current_date' in {list(body.keys())}"
    # current_date should be an ISO-format string
    assert isinstance(body["current_date"], str), f"current_date should be str, got {type(body['current_date'])}"
    assert "T" in body["current_date"], f"current_date should be ISO format, got {body['current_date']}"

    # ── MUST NOT HAVE: old hardcoded keys ─────────────────────────────
    assert (
        "saka_dawa_months" not in body
    ), f"OLD KEY 'saka_dawa_months' found in response — endpoint still hardcoded: {body.get('saka_dawa_months')}"
    assert (
        "in_saka_dawa_window" not in body
    ), "OLD KEY 'in_saka_dawa_window' found in response — endpoint still hardcoded"
