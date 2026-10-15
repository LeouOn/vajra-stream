"""MOPS is retired (owner decision 2026-10-14, docs/DEVELOPMENT_ROADMAP.md "Decisions").

The per-second throughput counter and its routes are gone. Work that takes
real time is recorded in the operations ledger instead: a scalar-radionics
broadcast is one ``broadcast`` operation with a measured duration.
"""

import importlib
import time
from unittest.mock import MagicMock

import pytest

from core import operations


@pytest.fixture(autouse=True)
def isolated_ledger(tmp_path, monkeypatch):
    db = tmp_path / "ops.db"
    monkeypatch.setattr(operations, "get_db_path", lambda: str(db))
    yield db


# ---------------------------------------------------------------------------
# The engine and its routes are gone
# ---------------------------------------------------------------------------


def test_mops_engine_module_is_gone():
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("backend.core.services.mops_engine")
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("backend.app.api.v1.endpoints.mops")


@pytest.fixture(scope="module")
def client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from backend.app.api.v1.api import api_router

    app = FastAPI()
    app.include_router(api_router, prefix="/api/v1")
    return TestClient(app)


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/v1/mops/current"),
        ("get", "/api/v1/mops/history"),
        ("get", "/api/v1/scalar/mops-metrics"),
        ("post", "/api/v1/scalar/benchmark"),
        ("post", "/api/v1/scalar/breathing-cycle"),
    ],
)
def test_mops_routes_return_404(client, method, path):
    assert getattr(client, method)(path).status_code == 404


def test_ledger_routes_are_the_replacement(client):
    summary = client.get("/api/v1/operations/summary")
    assert summary.status_code == 200
    assert {"completed", "active", "seconds_held"} <= summary.json().keys()


def test_scalar_methods_report_no_throughput_figures(client):
    body = client.get("/api/v1/scalar/methods").json()
    assert "combined_potential_mmops" not in body
    assert "progress_to_terra_mops_percent" not in body
    assert all("estimated_mops" not in m for m in body["methods"])


# ---------------------------------------------------------------------------
# A broadcast is recorded as one real, timed operation
# ---------------------------------------------------------------------------


@pytest.fixture
def broadcaster(monkeypatch):
    """Broadcaster with no DBs and a fake scalar generator (no audio, no sqlite)."""
    import core.integrated_scalar_radionics as mod

    monkeypatch.setattr(mod, "HAS_SCALAR", False)
    monkeypatch.setattr(mod, "HAS_BLESSINGS", False)
    monkeypatch.setattr(mod, "HAS_ANATOMY", False)
    b = mod.IntegratedScalarRadionicsBroadcaster()
    gen = MagicMock()
    gen.generate_hybrid_stream.side_effect = lambda n: [0.5] * n
    gen.thermal.state.temperature = 40.0
    b.scalar_gen = gen
    return b


def _config(duration_seconds: float):
    from core.integrated_scalar_radionics import BroadcastConfiguration, IntentionType

    return BroadcastConfiguration(
        intention=IntentionType.HEALING,
        target_count=1,
        duration_seconds=duration_seconds,
        scalar_intensity=0.5,
        frequency_hz=None,
        mantra="Om Mani Padme Hum",
    )


def test_broadcast_records_completed_operation_with_measured_elapsed_time(broadcaster):
    results = broadcaster.broadcast_to_targets(_config(0.2))

    assert "mops" not in results and "operations" not in results
    op = operations.get_operation(results["operation_id"])
    assert op is not None
    assert op["kind"] == "broadcast"
    assert op["status"] == "success"
    assert op["title"] == "Scalar-radionics broadcast: healing"
    assert op["params"]["requested_duration_seconds"] == 0.2
    assert op["params"]["frequency_hz"] == 528
    # Measured from started_at to finished_at, not assumed from the request.
    assert op["elapsed_seconds"] >= 0.2
    assert op["result"]["values_generated"] == results["values_generated"] > 0

    summary = operations.summarize_operations()
    assert summary["completed"] == 1
    assert summary["active"] == 0
    assert summary["seconds_held"] == op["elapsed_seconds"]


def test_broadcast_failure_is_recorded_and_reraised(broadcaster):
    broadcaster.scalar_gen.generate_hybrid_stream.side_effect = RuntimeError("generator exploded")

    with pytest.raises(RuntimeError, match="generator exploded"):
        broadcaster.broadcast_to_targets(_config(0.1))

    [op] = operations.list_operations(kind="broadcast")
    assert op["status"] == "error"
    assert op["error"] == "generator exploded"
    assert op["elapsed_seconds"] is not None


def test_broadcast_still_runs_when_ledger_is_unavailable(broadcaster, monkeypatch):
    def broken(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(operations, "create_operation", broken)
    start = time.monotonic()
    results = broadcaster.broadcast_to_targets(_config(0.05))

    assert time.monotonic() - start >= 0.05
    assert results["operation_id"] is None
    assert results["values_generated"] > 0
