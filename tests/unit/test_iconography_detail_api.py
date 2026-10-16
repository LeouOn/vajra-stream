"""GET /iconography/{deity} carries what the Iconography screen shows.

The forms name an ornament set by key; the detail response includes that set's
text, and the pinned reference row (with ``available``) even when the image is
gone, so the screen can say the pin is stale instead of hiding it.
"""

from __future__ import annotations

import io

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from backend.core.services.render import deity_references, jobs, references
from core import iconography


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "artifact_base", lambda: tmp_path)
    yield tmp_path


@pytest.fixture
def client() -> TestClient:
    from backend.app.api.v1.endpoints.iconography import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


def stored_reference() -> str:
    buffer = io.BytesIO()
    Image.new("RGB", (16, 24), (200, 40, 40)).save(buffer, format="PNG")
    return references.store_reference(buffer.getvalue())["reference_id"]


def test_detail_includes_the_ornament_set_text_its_forms_name(client):
    body = client.get("/api/v1/iconography/green_tara").json()
    sets = iconography.load_iconography()["ornament_sets"]
    used = {form["ornaments"] for form in body["deity"]["forms"] if form.get("ornaments")}
    assert used and set(body["ornament_sets"]) == used
    assert all(body["ornament_sets"][key] == sets[key] for key in used)
    assert body["reference"] is None


def test_detail_reports_a_stale_pin_rather_than_hiding_it(client):
    ref = stored_reference()
    deity_references.set_reference("white_tara", ref)
    body = client.get("/api/v1/iconography/white_tara").json()
    assert body["reference_id"] == ref
    assert body["reference"]["reference_id"] == ref and body["reference"]["available"] is True
    assert body["reference"]["set_at"]

    references.find_reference(ref).unlink()
    body = client.get("/api/v1/iconography/white_tara").json()
    assert body["reference_id"] is None
    assert body["reference"]["available"] is False
