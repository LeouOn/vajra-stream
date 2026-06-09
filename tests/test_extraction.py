"""
Integration tests for the astrology extraction system.

Covers:
- ``POST /api/v1/astrology/extract`` batch endpoint (queued → done flow)
- ``GET / DELETE /api/v1/astrology/runs/{id}`` run management
- ``GET / POST /api/v1/astrology/locations`` and the ``/seed`` helper
- The 8 per-calculation endpoints (``/lots``, ``/midpoints``, ...)
- The ``core.schema.init_db`` idempotency contract

DB isolation
------------
The tests use a fresh SQLite file under ``tests/.pytest_tmp/`` (not the real
``vajra_stream.db``). The redirect is performed by setting the
``DATABASE_URL`` env var **before** any module that instantiates
``backend.app.config.settings`` is imported, so pydantic-settings picks up
our test path on first construction. The env var name is whatever the rest
of the test stack uses (the app's :class:`Settings` reads ``DATABASE_URL``).
"""

from __future__ import annotations

import os

# ---------------------------------------------------------------------------
# CRITICAL: redirect the DB BEFORE the app is imported.
# ---------------------------------------------------------------------------
# pydantic-settings reads env vars on first instantiation of the Settings
# class, and that happens the first time `backend.app.config.settings` is
# imported — which happens transitively when `backend.app.main` is loaded
# below. We must set DATABASE_URL before any `from backend.app...` line
# executes, so we do it at the top of this module.
_TMP_DB_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), ".pytest_tmp"
)
os.makedirs(_TMP_DB_DIR, exist_ok=True)
_TEST_DB_PATH = os.path.abspath(os.path.join(_TMP_DB_DIR, "test_extraction.db"))

# Wipe any stale DB file from a previous run so each pytest invocation
# starts with a clean schema.
if os.path.exists(_TEST_DB_PATH):
    os.unlink(_TEST_DB_PATH)

os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"

# Now safe to import the app + FastAPI machinery.
import time  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from core.schema import init_db  # noqa: E402

# Initialize the test schema once at module load (idempotent — see below).
init_db(_TEST_DB_PATH).close()

from backend.app.main import app  # noqa: E402


def _poll_run_for_completion(
    client: TestClient, run_id: int, timeout_s: float = 30.0
) -> dict:
    """Poll ``GET /astrology/runs/{id}`` until status is terminal.

    Returns the final run-row dict. Raises :class:`AssertionError` if the
    run doesn't reach a terminal state (``done`` / ``error`` / ``partial``)
    before ``timeout_s`` elapses.
    """
    deadline = time.monotonic() + timeout_s
    last: dict | None = None
    while time.monotonic() < deadline:
        r = client.get(f"/api/v1/astrology/runs/{run_id}")
        assert r.status_code == 200, f"GET run failed: {r.text}"
        last = r.json()
        if last.get("status") in ("done", "error", "partial"):
            return last
        time.sleep(0.25)
    raise AssertionError(
        f"Run {run_id} did not complete within {timeout_s}s; last status: {last}"
    )


@pytest.fixture
def client() -> TestClient:
    """Return a FastAPI :class:`TestClient` bound to the test app.

    The test app is shared across tests (imported once at module load),
    but the underlying SQLite file is the isolated test DB so the tests
    can read/write freely without polluting ``vajra_stream.db``.
    """
    return TestClient(app)


@pytest.mark.integration
class TestExtractionAPI:
    def test_schema_apply_idempotent(self, client):  # noqa: ARG002
        """``init_db`` must be safe to call repeatedly on the same DB."""
        from core.schema import init_db

        # Should not raise — re-running on an already-migrated DB is a no-op.
        init_db()
        init_db()
        init_db()

    def test_schema_creates_compassionate_blessing_tables(self, client):  # noqa: ARG002
        """Regression: init_db must own the compassionate_blessings tables.

        Pre-Task 1, ``core/compassionate_blessings.py`` created
        ``blessing_targets``, ``blessing_sessions``, and
        ``mantra_dedications`` inside its own ``__init__``. The
        centralized migration runner in ``core/schema.py`` now owns
        every table, so a fresh ``init_db()`` must produce all three
        without any side import of compassionate_blessings.
        """
        import sqlite3
        from core.schema import get_db_path, init_db

        init_db()
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        try:
            for table in (
                "blessing_targets",
                "blessing_sessions",
                "mantra_dedications",
            ):
                row = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table,),
                ).fetchone()
                assert row is not None, f"{table} not created by init_db()"
        finally:
            conn.close()

    def test_batch_extract_small(self, client):
        """A single-tuple batch should queue, run, and reach 'done'.

        This is the canonical happy-path assertion for the background
        runner. Multi-tuple coverage lives in
        :meth:`test_batch_extract_multi_no_hang` (regression test for
        the asyncio.to_thread executor starvation that previously hung
        on tuple 3).
        """
        r = client.post(
            "/api/v1/astrology/extract",
            json={
                "tuples": [
                    {
                        "date_iso": "2026-06-01T12:00:00Z",
                        "lat": 0.0,
                        "lon": 0.0,
                    },
                ],
                "config": {"systems": ["western", "lots"]},
            },
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "run_id" in data
        assert data["status"] == "queued"
        assert data["total_tuples"] == 1

        final = _poll_run_for_completion(client, data["run_id"], timeout_s=20.0)
        assert final["status"] in ("done", "partial"), (
            f"expected terminal status, got {final['status']!r}: {final}"
        )
        assert final["completed_tuples"] == 1
        assert final["total_tuples"] == 1

    def test_batch_extract_multi_no_hang(self, client):
        """Regression: 5-tuple batch must complete, not hang on tuple 3.

        Previously the background runner used ``asyncio.to_thread`` for
        every tuple, which under FastAPI's :class:`TestClient` starved
        the default executor on the 3rd concurrent call. The run would
        sit at ``completed_tuples=2`` until the poll timeout fired.

        This test pins the fix: 5 tuples with the ``western`` system
        must all reach ``done`` within a generous timeout.
        """
        tuples = [
            {
                "date_iso": f"2026-{i + 1:02d}-01T12:00:00Z",
                "lat": float(i) * 5.0,
                "lon": float(i) * 5.0,
            }
            for i in range(5)
        ]
        r = client.post(
            "/api/v1/astrology/extract",
            json={"tuples": tuples, "config": {"systems": ["western"]}},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["total_tuples"] == 5

        final = _poll_run_for_completion(
            client, data["run_id"], timeout_s=30.0
        )
        assert final["status"] in ("done", "partial"), (
            f"expected terminal status, got {final['status']!r}: {final}"
        )
        assert final["completed_tuples"] == 5, (
            f"expected 5/5 completed, got {final['completed_tuples']}/5"
        )
        assert final["total_tuples"] == 5

    def test_batch_extract_empty(self, client):
        """Empty tuple list must be rejected with HTTP 400."""
        r = client.post(
            "/api/v1/astrology/extract",
            json={"tuples": [], "config": {"systems": ["western"]}},
        )
        assert r.status_code == 400

    def test_batch_extract_dedup(self, client):
        """3 identical tuples must collapse to a single queued tuple."""
        t = {"date_iso": "2026-01-01T12:00:00Z", "lat": 0.0, "lon": 0.0}
        r = client.post(
            "/api/v1/astrology/extract",
            json={"tuples": [t, t, t], "config": {"systems": ["western"]}},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total_tuples"] == 1

    def test_run_management(self, client):
        """Full lifecycle: create → list → get → delete → 404 on re-get."""
        r = client.post(
            "/api/v1/astrology/extract",
            json={
                "tuples": [
                    {"date_iso": "2026-01-01T12:00:00Z", "lat": 0, "lon": 0}
                ],
                "config": {"systems": ["western"]},
            },
        )
        assert r.status_code == 200, r.text
        run_id = r.json()["run_id"]

        # List
        r1 = client.get("/api/v1/astrology/runs")
        assert r1.status_code == 200
        listed = r1.json()
        assert "runs" in listed
        assert any(row["id"] == run_id for row in listed["runs"])

        # Get one
        r2 = client.get(f"/api/v1/astrology/runs/{run_id}")
        assert r2.status_code == 200
        assert r2.json()["id"] == run_id

        # Delete
        r3 = client.delete(f"/api/v1/astrology/runs/{run_id}")
        assert r3.status_code == 200
        assert r3.json().get("deleted") is True

        # Confirm 404 on the second get
        r4 = client.get(f"/api/v1/astrology/runs/{run_id}")
        assert r4.status_code == 404

    def test_locations_crud(self, client):
        """Seed → list → filter → create a custom location."""
        # Seed
        r = client.post("/api/v1/astrology/locations/seed")
        assert r.status_code == 200, r.text
        seed_body = r.json()
        assert seed_body.get("status") in ("loaded", "skipped")

        # List (all)
        r1 = client.get("/api/v1/astrology/locations")
        assert r1.status_code == 200
        all_locs = r1.json()
        assert isinstance(all_locs, list)
        assert len(all_locs) >= 10  # 15 in seed.json, but a prior test could have added more

        # Filter by category
        r2 = client.get("/api/v1/astrology/locations?category=sacred_site")
        assert r2.status_code == 200
        sacred = r2.json()
        assert len(sacred) == 10
        assert all(loc["category"] == "sacred_site" for loc in sacred)

        # Create a custom location
        r3 = client.post(
            "/api/v1/astrology/locations",
            json={
                "name": "Test Site",
                "lat": 0.0,
                "lon": 0.0,
                "category": "custom",
                "timezone": "UTC",
            },
        )
        assert r3.status_code == 201, r3.text
        created = r3.json()
        assert created["name"] == "Test Site"
        assert created["category"] == "custom"
        assert "id" in created

    def test_per_calc_endpoints(self, client):
        """All 8 per-calc POST endpoints must return 200 with valid bodies."""
        base = {"date_iso": "2026-01-01T12:00:00Z", "lat": 0, "lon": 0}
        for path in [
            "/api/v1/astrology/lots",
            "/api/v1/astrology/midpoints",
            "/api/v1/astrology/antiscia",
            "/api/v1/astrology/fixed-stars",
            "/api/v1/astrology/solar-return",
            "/api/v1/astrology/profection",
            "/api/v1/astrology/year-ahead",
            "/api/v1/astrology/astrocartography",
        ]:
            if path.endswith("/solar-return"):
                body = {
                    "natal_date_iso": "2000-01-01T12:00:00Z",
                    "natal_lat": 0,
                    "natal_lon": 0,
                    "return_year": 2026,
                }
            elif path.endswith("/profection"):
                body = {
                    "natal_date_iso": "2000-01-01T12:00:00Z",
                    "target_year": 2025,
                }
            elif path.endswith("/year-ahead"):
                body = {
                    "natal_date_iso": "2000-01-01T12:00:00Z",
                    "natal_lat": 0,
                    "natal_lon": 0,
                }
            else:
                body = dict(base)
            r = client.post(path, json=body)
            assert r.status_code == 200, f"{path} returned {r.status_code}: {r.text}"
            payload = r.json()
            assert payload.get("status") == "success", (
                f"{path} returned non-success payload: {payload}"
            )
