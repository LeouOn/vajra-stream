"""core.operations — the ledger of real, timed operations (schema v7)."""

import time

import pytest

from core import operations
from core.operations import OperationError


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    db = tmp_path / "ops.db"
    monkeypatch.setattr(operations, "get_db_path", lambda: str(db))
    yield db


def test_lifecycle_records_real_elapsed_time():
    op = operations.create_operation("render", "Witness image", params={"width": 1024}, provenance={"seed": "draw"})
    assert op["status"] == "queued"
    assert op["started_at"] is None and op["elapsed_seconds"] is None
    assert op["params"] == {"width": 1024}
    assert op["provenance"] == {"seed": "draw"}

    operations.start_operation(op["id"])
    time.sleep(0.05)
    done = operations.complete_operation(op["id"], result={"image": "x.png"})

    assert done["status"] == "success"
    assert done["result"] == {"image": "x.png"}
    assert done["elapsed_seconds"] >= 0.05
    assert done["finished_at"] >= done["started_at"]


def test_invalid_transitions_are_rejected():
    op = operations.create_operation("broadcast", "Medicine Buddha")
    with pytest.raises(OperationError):
        operations.complete_operation(op["id"])  # never started
    operations.start_operation(op["id"])
    operations.complete_operation(op["id"])
    with pytest.raises(OperationError):
        operations.fail_operation(op["id"], "late")
    with pytest.raises(OperationError):
        operations.update_operation_result(op["id"], {"x": 1})
    with pytest.raises(OperationError):
        operations.start_operation("does-not-exist")


def test_failure_without_start_has_no_elapsed_time():
    op = operations.create_operation("render", "Never ran")
    failed = operations.fail_operation(op["id"], "backend offline")
    assert failed["status"] == "error"
    assert failed["error"] == "backend offline"
    assert failed["elapsed_seconds"] is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"kind": "mops", "title": "x"},
        {"kind": "render", "title": "   "},
        {"kind": "render", "title": "x", "provenance": {"seed": "measured"}},
    ],
)
def test_create_validates_input(kwargs):
    kind = kwargs.pop("kind")
    title = kwargs.pop("title")
    with pytest.raises(OperationError):
        operations.create_operation(kind, title, **kwargs)


def test_listeners_see_every_change_and_cannot_break_operations():
    seen = []

    def broken(_op):
        raise RuntimeError("listener bug")

    operations.add_listener(seen.append)
    operations.add_listener(broken)
    try:
        op = operations.create_operation("working", "Sitting")
        operations.start_operation(op["id"])
        operations.update_operation_result(op["id"], {"progress": 0.5})
        operations.complete_operation(op["id"])
    finally:
        operations.remove_listener(seen.append)
        operations.remove_listener(broken)

    assert [o["status"] for o in seen] == ["queued", "running", "running", "success"]
    assert seen[2]["result"] == {"progress": 0.5}


def test_list_filters_and_summary():
    a = operations.create_operation("render", "a", working_id="w1")
    operations.start_operation(a["id"])
    operations.complete_operation(a["id"])
    b = operations.create_operation("broadcast", "b")
    operations.cancel_operation(b["id"])
    operations.create_operation("render", "c")

    assert {o["title"] for o in operations.list_operations(kind="render")} == {"a", "c"}
    assert [o["title"] for o in operations.list_operations(working_id="w1")] == ["a"]
    assert [o["title"] for o in operations.list_operations(status="cancelled")] == ["b"]

    summary = operations.summarize_operations()
    assert summary["by_kind"] == {"render": 2, "broadcast": 1}
    assert summary["active"] == 1
    assert summary["completed"] == 1
    assert summary["seconds_held"] >= 0


def test_reconcile_marks_stale_operations_interrupted():
    stale = operations.create_operation("broadcast", "left running")
    operations.start_operation(stale["id"])
    keep = operations.create_operation("render", "re-attachable")
    operations.start_operation(keep["id"])

    assert operations.reconcile_interrupted(exclude_kinds=frozenset({"render"})) == 1
    assert operations.get_operation(stale["id"])["status"] == "interrupted"
    assert operations.get_operation(stale["id"])["elapsed_seconds"] is not None
    assert operations.get_operation(keep["id"])["status"] == "running"


def test_api_routes(tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from backend.app.api.v1.endpoints.operations import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    op = operations.create_operation("render", "via api")
    assert client.get(f"/api/v1/operations/{op['id']}").json()["title"] == "via api"
    assert client.get("/api/v1/operations/nope").status_code == 404
    assert client.get("/api/v1/operations", params={"kind": "render"}).json()["count"] == 1
    assert client.get("/api/v1/operations", params={"kind": "mops"}).status_code == 422
    assert client.get("/api/v1/operations/summary").json()["active"] == 1
