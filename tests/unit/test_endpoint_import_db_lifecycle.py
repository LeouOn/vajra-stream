"""Endpoint modules must own ZERO import-time database work.

Historically, importing backend/app/api/v1/endpoints/{astrology,locations,
agent_suggestions}.py called core.schema.init_db() at module load, and
importing radionics.py constructed IntegratedScalarRadionicsBroadcaster(),
whose BlessingDatabase initializes the schema — so merely importing a router
migrated the database. Schema initialization is owned by the application
lifespan (backend/app/main.py critical path).

Proof strategy (no live DB, no APIs, no server):
- Fresh SUBPROCESS per endpoint module under a scratch DATABASE_URL (never
  the live DB) with core.schema.init_db spied and the broadcaster class
  faked before import: importing the module must trigger zero schema calls,
  zero broadcaster constructions, and create zero DB files.
- In-process: the radionics broadcaster is constructed lazily by
  get_broadcaster(), exactly once, also under concurrent callers.
- In-process: representative DB-backed routes work against a seeded
  temporary schema (core.schema.init_db under the conftest's isolated
  DATABASE_URL), and fail honestly (HTTP 500) when the schema is absent.
"""

import json
import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ENDPOINT_MODULES = (
    "backend.app.api.v1.endpoints.astrology",
    "backend.app.api.v1.endpoints.locations",
    "backend.app.api.v1.endpoints.agent_suggestions",
    "backend.app.api.v1.endpoints.radionics",
)

_PROBE_TEMPLATE = r"""
import importlib
import json
import os
import sys

sys.path.insert(0, {repo_root!r})

import core.schema as schema

_init_calls = []


def _spy_init_db(*args, **kwargs):
    _init_calls.append({{"args": [str(a) for a in args], "kwargs": sorted(kwargs)}})


schema.init_db = _spy_init_db

import core.integrated_scalar_radionics as _isr

_constructions = []


class _FakeBroadcaster:
    def __init__(self):
        _constructions.append(1)


_isr.IntegratedScalarRadionicsBroadcaster = _FakeBroadcaster

importlib.import_module({module!r})

print("RESULT " + json.dumps({{
    "init_db_calls": _init_calls,
    "broadcaster_constructions": len(_constructions),
    "scratch_files": sorted(os.listdir({db_dir!r})),
}}))
"""


def _run_import_probe(module_name: str, tmp_path) -> dict:
    """Import one endpoint module in a fresh process under a scratch DB URL."""
    db_dir = tmp_path / f"scratch-{module_name.rsplit('.', 1)[-1]}"
    db_dir.mkdir()
    env = dict(os.environ)
    # Scratch DB only — never the live vajra_stream.db (conftest also pins
    # DATABASE_URL for this pytest process; the child gets its own scratch).
    env["DATABASE_URL"] = f"sqlite:///{db_dir}/probe.db"
    script = _PROBE_TEMPLATE.format(repo_root=REPO_ROOT, module=module_name, db_dir=str(db_dir))
    proc = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
    )
    # The radionics probe transitively imports the orchestrator/container/
    # vajra_service stack, which can take minutes on a busy shared box —
    # the generous timeout is deliberate.
    assert proc.returncode == 0, f"probe crashed:\n{proc.stderr[-3000:]}"
    for line in reversed(proc.stdout.splitlines()):
        if line.startswith("RESULT "):
            return json.loads(line[len("RESULT ") :])
    raise AssertionError(f"no RESULT line in probe output; stdout tail: {proc.stdout[-1500:]}")


@pytest.mark.parametrize("module_name", ENDPOINT_MODULES)
def test_endpoint_import_owns_no_db_work(module_name, tmp_path):
    """Importing each endpoint module must do no schema work and create no DB.

    Asserts only what these files own: the spy catches any
    core.schema.init_db call and the fake broadcaster any construction that
    importing the module (directly or via its own module-level code)
    triggers; the scratch dir listing catches file side effects.
    """
    result = _run_import_probe(module_name, tmp_path)

    assert (
        result["init_db_calls"] == []
    ), f"{module_name} triggered core.schema.init_db at import: {result['init_db_calls']}"
    assert result["broadcaster_constructions"] == 0, f"{module_name} constructed a broadcaster at import"
    assert (
        result["scratch_files"] == []
    ), f"{module_name} created files in the scratch DB dir at import: {result['scratch_files']}"


# ---------------------------------------------------------------------------
# radionics broadcaster: deferred construction + reuse
# ---------------------------------------------------------------------------


def test_radionics_broadcaster_is_deferred_and_reused(monkeypatch):
    import backend.app.api.v1.endpoints.radionics as radionics

    constructions = []

    class FakeBroadcaster:
        def __init__(self):
            constructions.append(1)

    monkeypatch.setattr(radionics, "IntegratedScalarRadionicsBroadcaster", FakeBroadcaster)
    monkeypatch.setattr(radionics, "_broadcaster_instance", None)

    first = radionics.get_broadcaster()
    second = radionics.get_broadcaster()

    assert isinstance(first, FakeBroadcaster)
    assert first is second, "get_broadcaster must reuse the shared instance"
    assert constructions == [1], "get_broadcaster must construct exactly once across calls"


def test_radionics_broadcaster_construction_is_thread_safe(monkeypatch):
    import backend.app.api.v1.endpoints.radionics as radionics

    constructions = []

    class FakeBroadcaster:
        def __init__(self):
            constructions.append(1)

    monkeypatch.setattr(radionics, "IntegratedScalarRadionicsBroadcaster", FakeBroadcaster)
    monkeypatch.setattr(radionics, "_broadcaster_instance", None)

    barrier = threading.Barrier(2)
    results: list[object] = []
    errors: list[BaseException] = []

    def _worker():
        try:
            barrier.wait(timeout=5)
            results.append(radionics.get_broadcaster())
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=_worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert not errors, errors
    assert len(results) == 2
    assert results[0] is results[1]
    assert constructions == [1], "concurrent first use must still construct exactly once"


# ---------------------------------------------------------------------------
# DB-backed routes against a seeded temporary schema
# ---------------------------------------------------------------------------


@pytest.fixture
def seeded_client(tmp_path, monkeypatch):
    """TestClient for the three DB-backed routers against an ISOLATED schema.

    Each router's DB-path resolution is pointed at a per-test scratch file —
    never the process-wide temp DB (later suites like
    tests/integration/test_extraction.py assert their own seeding against
    that one) and never the live DB. Plain FastAPI(): no lifespan, so no
    background warmup and no external clients are started.
    """
    from types import SimpleNamespace

    from core.schema import init_db as core_init_db

    db_file = tmp_path / "lifecycle.db"
    conn = core_init_db(str(db_file))
    conn.close()

    from backend.app.api.v1.endpoints import agent_suggestions, astrology, locations

    monkeypatch.setattr(astrology, "get_db_path", lambda: str(db_file))
    monkeypatch.setattr(agent_suggestions, "get_db_path", lambda: str(db_file))
    monkeypatch.setattr(locations, "backend_settings", SimpleNamespace(DATABASE_URL=f"sqlite:///{db_file}"))

    app = FastAPI()
    app.include_router(astrology.router, prefix="/api/v1/astrology")
    app.include_router(locations.router, prefix="/api/v1/astrology/locations")
    app.include_router(agent_suggestions.router, prefix="/api/v1")
    return TestClient(app)


def test_saved_charts_route_works_with_seeded_schema(seeded_client):
    response = seeded_client.get("/api/v1/astrology/charts")
    assert response.status_code == 200
    assert response.json() == []


def test_locations_routes_work_with_seeded_schema(seeded_client):
    listing = seeded_client.get("/api/v1/astrology/locations")
    assert listing.status_code == 200
    assert listing.json() == []

    created = seeded_client.post(
        "/api/v1/astrology/locations",
        json={
            "name": "Probe Peak",
            "lat": 37.77,
            "lon": -122.42,
            "category": "custom",
            "timezone": "America/Los_Angeles",
            "tags": ["probe"],
            "notes": "lifecycle test row",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["name"] == "Probe Peak"
    assert body["tags"] == ["probe"]

    fetched = seeded_client.get(f"/api/v1/astrology/locations/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Probe Peak"


def test_intentional_paths_route_works_with_seeded_schema(seeded_client):
    response = seeded_client.get("/api/v1/intentional_paths")
    assert response.status_code == 200
    assert response.json() == []


def test_db_routes_fail_honestly_without_schema(monkeypatch, tmp_path):
    """Documented behavior when the schema does NOT exist.

    astrology's list route translates the sqlite error into HTTP 500 with
    the cause in ``detail``. agent_suggestions' GET /intentional_paths has
    no try/except, so the raw OperationalError propagates — with
    raise_server_exceptions=False that surfaces as a generic 500 (body
    "Internal Server Error", no detail field).
    """
    from backend.app.api.v1.endpoints import agent_suggestions, astrology

    missing = str(tmp_path / "no-schema.db")
    monkeypatch.setattr(astrology, "get_db_path", lambda: missing)
    monkeypatch.setattr(agent_suggestions, "get_db_path", lambda: missing)

    app = FastAPI()
    app.include_router(astrology.router, prefix="/api/v1/astrology")
    app.include_router(agent_suggestions.router, prefix="/api/v1")
    client = TestClient(app, raise_server_exceptions=False)

    charts = client.get("/api/v1/astrology/charts")
    assert charts.status_code == 500
    assert "no such table" in charts.json()["detail"]

    paths = client.get("/api/v1/intentional_paths")
    assert paths.status_code == 500
    assert paths.text == "Internal Server Error"


# ---------------------------------------------------------------------------
# Scratch DB gate contract: only session scratch and exact extraction dir
# ---------------------------------------------------------------------------


class TestScratchDbGate:
    """Verify that _is_scratch_db_path enforces the strict allowlist and rejects symlinks."""

    def test_gate_accepts_session_temp_db(self):
        from tests.conftest import _TEST_DB_DIR, _is_scratch_db_path

        session_db = os.path.join(_TEST_DB_DIR, "vajra_stream.db")
        assert _is_scratch_db_path(session_db) is True

    def test_gate_accepts_extraction_scratch_db(self):
        from tests.conftest import _is_scratch_db_path

        extraction_db = os.path.join(REPO_ROOT, "tests", "integration", ".pytest_tmp", "test_extraction.db")
        assert _is_scratch_db_path(extraction_db) is True

    def test_gate_rejects_live_repo_db(self):
        from tests.conftest import _is_scratch_db_path

        live_db = os.path.join(REPO_ROOT, "vajra_stream.db")
        assert _is_scratch_db_path(live_db) is False

    def test_gate_rejects_live_backend_app_db(self):
        from tests.conftest import _is_scratch_db_path

        backend_db = os.path.join(REPO_ROOT, "backend", "app", "vajra_stream.db")
        assert _is_scratch_db_path(backend_db) is False

    def test_gate_rejects_arbitrary_tmp_path(self, tmp_path):
        from tests.conftest import _is_scratch_db_path

        # An arbitrary /tmp directory must NOT be accepted
        other_tmp_db = str(tmp_path / "arbitrary.db")
        assert _is_scratch_db_path(other_tmp_db) is False

    def test_gate_rejects_arbitrary_pytest_tmp_path(self, tmp_path):
        from tests.conftest import _is_scratch_db_path

        # An arbitrary path containing a .pytest_tmp directory must NOT be accepted
        fake_pytest_tmp = str(tmp_path / ".pytest_tmp" / "db.sqlite")
        assert _is_scratch_db_path(fake_pytest_tmp) is False
        unit_pytest_tmp = os.path.join(REPO_ROOT, "tests", "unit", ".pytest_tmp", "fake.db")
        assert _is_scratch_db_path(unit_pytest_tmp) is False

    def test_gate_rejects_symlink_to_live_db(self):
        from tests.conftest import _TEST_DB_DIR, _is_scratch_db_path

        live_db = os.path.join(REPO_ROOT, "vajra_stream.db")
        symlink_path = os.path.join(_TEST_DB_DIR, "symlink_to_live.db")
        try:
            os.symlink(live_db, symlink_path)
            assert _is_scratch_db_path(symlink_path) is False
        finally:
            if os.path.islink(symlink_path):
                os.unlink(symlink_path)

    def test_gate_rejects_symlink_inside_session_pointing_outside(self, tmp_path):
        from tests.conftest import _TEST_DB_DIR, _is_scratch_db_path

        outside_target = str(tmp_path / "outside.db")
        Path(outside_target).touch()
        symlink_path = os.path.join(_TEST_DB_DIR, "symlink_to_outside.db")
        try:
            os.symlink(outside_target, symlink_path)
            assert _is_scratch_db_path(symlink_path) is False
        finally:
            if os.path.islink(symlink_path):
                os.unlink(symlink_path)

    def test_gate_rejects_symlink_outside_pointing_in(self, tmp_path):
        from tests.conftest import _TEST_DB_DIR, _is_scratch_db_path

        real_session_db = os.path.join(_TEST_DB_DIR, "vajra_stream.db")
        outside_symlink = str(tmp_path / "symlink_in.db")
        os.symlink(real_session_db, outside_symlink)
        assert _is_scratch_db_path(outside_symlink) is False

    @pytest.mark.parametrize("bad_path", ["", "   ", None, "./vajra_stream.db", "relative/path.db"])
    def test_gate_rejects_relative_and_empty_paths(self, bad_path):
        from tests.conftest import _is_scratch_db_path

        assert _is_scratch_db_path(bad_path) is False

    def test_provider_key_isolation_pins_sensitive_vars(self):
        from tests.conftest import _PROVIDER_KEY_VARS

        assert "MINIMAX_API_KEY" in _PROVIDER_KEY_VARS
        assert "Z_AI_API_KEY" in _PROVIDER_KEY_VARS
        assert "ZAI_API_KEY" in _PROVIDER_KEY_VARS
        for var in ("MINIMAX_API_KEY", "Z_AI_API_KEY", "ZAI_API_KEY"):
            assert os.environ.get(var) == "", f"{var} must be pinned to empty string"
