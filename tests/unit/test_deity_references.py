"""A user thangka reference pinned to a deity conditions that deity's witness renders.

No ComfyUI is contacted: the render backend registry entry fails the test if used,
and submit_witness_render only queues an operation.
"""

from __future__ import annotations

import io

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

import core.working as working
from backend.core.services.render import deity_references, jobs, references
from backend.core.services.render import worker as worker_mod
from backend.core.services.render.comfyui import BACKEND_NAME
from core import operations


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(operations, "get_db_path", lambda: str(tmp_path / "ops.db"))
    monkeypatch.setattr(jobs, "artifact_base", lambda: tmp_path)
    monkeypatch.setattr(worker_mod, "_worker", None)
    monkeypatch.setattr(working, "WORKINGS_DIR", tmp_path / "workings")
    monkeypatch.setitem(jobs.BACKENDS, BACKEND_NAME, lambda: pytest.fail("real ComfyUI adapter used in a test"))
    yield tmp_path
    operations.remove_listener(working.witness_listener)


def stored_reference() -> str:
    buffer = io.BytesIO()
    Image.new("RGB", (32, 48), (20, 160, 90)).save(buffer, format="PNG")
    return references.store_reference(buffer.getvalue())["reference_id"]


@pytest.fixture
def client() -> TestClient:
    from backend.app.api.v1.endpoints.iconography import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


def test_pin_resolve_and_unpin():
    ref = stored_reference()
    row = deity_references.set_reference("Green Tara", ref)
    assert row["deity"] == "green_tara" and row["reference_id"] == ref
    assert deity_references.reference_for("green_tara") == ref
    assert deity_references.reference_for("white_tara") is None
    assert deity_references.mapping_path().read_bytes().count(b"\r\n") == 0
    assert deity_references.clear_reference("green_tara") is True
    assert deity_references.clear_reference("green_tara") is False
    assert deity_references.reference_for("green_tara") is None


def test_pin_rejects_unknown_deity_or_reference():
    ref = stored_reference()
    with pytest.raises(deity_references.UnknownDeity):
        deity_references.set_reference("Zeus", ref)
    with pytest.raises(references.InvalidReference):
        deity_references.set_reference("green_tara", "0" * 64)


def test_missing_image_is_ignored_not_fatal():
    ref = stored_reference()
    deity_references.set_reference("green_tara", ref)
    references.find_reference(ref).unlink()
    assert deity_references.reference_for("green_tara") is None
    assert deity_references.all_references()["green_tara"]["available"] is False


def test_witness_render_uses_the_pinned_reference():
    ref = stored_reference()
    deity_references.set_reference("medicine_buddha", ref)
    folio = working.run_working("healing for all who are ill", broadcast=False, deity="Medicine Buddha")
    op = working.submit_witness_render(folio["working_id"])["operation"]
    assert op["params"]["reference_id"] == ref
    assert "lapis lazuli blue" in op["params"]["prompt"]
    assert any(f["label"] == "Deity" for f in op["params"]["caption_facts"])

    plain = working.run_working("peace for the river", broadcast=False)
    assert working.submit_witness_render(plain["working_id"])["operation"]["params"]["reference_id"] is None


def test_api(client):
    listing = client.get("/api/v1/iconography").json()["deities"]
    assert {d["id"] for d in listing} >= {"green_tara", "avalokiteshvara", "buddha_generic"}
    assert all(d["sources"] for d in listing)

    one = client.get("/api/v1/iconography/Avalokiteshvara (Chenrezig)").json()
    assert one["form"] == "four_armed" and "crystal mala" in one["prompt_clause"]
    assert client.get("/api/v1/iconography/avalokiteshvara", params={"form": "thousand_armed"}).json()["form"] == (
        "thousand_armed"
    )
    assert client.get("/api/v1/iconography/zeus").status_code == 404

    ref = stored_reference()
    assert client.put("/api/v1/iconography/green_tara/reference", json={"reference_id": ref}).status_code == 200
    assert client.get("/api/v1/iconography/green_tara").json()["reference_id"] == ref
    pinned = {d["id"]: d["reference"] for d in client.get("/api/v1/iconography").json()["deities"]}
    assert pinned["green_tara"]["reference_id"] == ref and pinned["white_tara"] is None
    assert client.put("/api/v1/iconography/zeus/reference", json={"reference_id": ref}).status_code == 404
    bad = client.put("/api/v1/iconography/green_tara/reference", json={"reference_id": "f" * 64})
    assert bad.status_code == 422
    assert client.delete("/api/v1/iconography/green_tara/reference").json() == {"deity": "green_tara", "removed": True}
