"""Render phase B: reference images (W2-1), witness renders linked to folios (W2-2), sigils.

Nothing here contacts a real ComfyUI: adapters run on ``httpx.MockTransport`` backed
by the :class:`FakeComfy` from ``test_render_engine``; the ledger uses a tmp DB,
artifacts and folios go to tmp_path.
"""

from __future__ import annotations

import hashlib
import io
import json
import time
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

import core.working as working
from backend.core.services.render import jobs, references
from backend.core.services.render import worker as worker_mod
from backend.core.services.render.base import RenderSpec
from backend.core.services.render.comfyui import BACKEND_NAME, ComfyUIQwenImage21Adapter, build_graph
from backend.core.services.render.jobs import RenderJobRequest
from backend.core.services.render.worker import RenderWorker
from core import operations
from tests.unit.test_render_engine import FakeComfy

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(operations, "get_db_path", lambda: str(tmp_path / "ops.db"))
    monkeypatch.setattr(jobs, "artifact_base", lambda: tmp_path)
    monkeypatch.setattr(worker_mod, "_worker", None)
    monkeypatch.setattr(working, "WORKINGS_DIR", tmp_path / "workings")
    # Any accidental use of the settings-driven adapter must fail loudly, not reach 127.0.0.1:8188.
    monkeypatch.setitem(jobs.BACKENDS, BACKEND_NAME, lambda: pytest.fail("real ComfyUI adapter used in a test"))
    yield tmp_path
    operations.remove_listener(working.witness_listener)


@pytest.fixture
def fake(monkeypatch) -> FakeComfy:
    comfy = FakeComfy()
    adapter = ComfyUIQwenImage21Adapter(
        "http://comfy.test", transport=httpx.MockTransport(comfy.handler), poll_interval=0.001
    )
    monkeypatch.setitem(jobs.BACKENDS, BACKEND_NAME, lambda: adapter)
    return comfy


def image_bytes(fmt: str, size: tuple[int, int] = (40, 24), **save: Any) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, (200, 120, 40)).save(buffer, format=fmt, **save)
    return buffer.getvalue()


def app_client(*routers: Any) -> TestClient:
    app = FastAPI()
    for router, prefix in routers:
        app.include_router(router, prefix=prefix)
    return TestClient(app)


@pytest.fixture
def render_client() -> TestClient:
    from backend.app.api.v1.endpoints.render import router

    return app_client((router, "/api/v1"))


@pytest.fixture
def operator_client() -> TestClient:
    from backend.app.api.v1.endpoints.operator import router

    return app_client((router, "/api/v1/operator"))


# -- W2-1: header sniffing -----------------------------------------------------------


@pytest.mark.parametrize(
    ("fmt", "save", "ext"),
    [
        ("PNG", {}, "png"),
        ("JPEG", {"quality": 80}, "jpg"),
        ("JPEG", {"progressive": True}, "jpg"),
        ("WEBP", {"lossless": False}, "webp"),
        ("WEBP", {"lossless": True}, "webp"),
    ],
)
def test_sniff_reads_type_and_size_from_the_header(fmt, save, ext):
    info = references.sniff_image(image_bytes(fmt, (40, 24), **save))
    assert (info.ext, info.width, info.height) == (ext, 40, 24)


def test_sniff_reads_extended_webp_header():
    # VP8X (extended) is what WebP with alpha / metadata uses.
    rgba = io.BytesIO()
    Image.new("RGBA", (33, 17), (1, 2, 3, 128)).save(rgba, format="WEBP")
    data = rgba.getvalue()
    assert data[12:16] == b"VP8X"
    assert references.sniff_image(data).ext == "webp"
    assert (references.sniff_image(data).width, references.sniff_image(data).height) == (33, 17)


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"hello, I am a text file named lotus.png",
        image_bytes("GIF"),
        image_bytes("BMP"),
        image_bytes("PNG")[:20],  # truncated header
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00",  # JPEG with no frame header
    ],
)
def test_sniff_rejects_other_or_broken_files(data):
    with pytest.raises(references.UnsupportedImage):
        references.sniff_image(data)


# -- W2-1: upload / get routes -------------------------------------------------------


def test_upload_stores_content_addressed_and_returns_201(render_client, tmp_path):
    data = image_bytes("PNG", (64, 32))
    response = render_client.post("/api/v1/render/references", files={"image": ("lotus.png", data, "image/png")})
    assert response.status_code == 201
    body = response.json()
    digest = hashlib.sha256(data).hexdigest()
    assert body == {"reference_id": digest, "sha256": digest, "filename": f"{digest}.png", "width": 64, "height": 32}
    stored = tmp_path / "generated" / "renders" / "references" / f"{digest}.png"
    assert stored.read_bytes() == data


def test_upload_type_comes_from_the_header_not_the_name(render_client, tmp_path):
    jpeg = image_bytes("JPEG")
    response = render_client.post("/api/v1/render/references", files={"image": ("misnamed.png", jpeg, "image/png")})
    assert response.status_code == 201
    assert response.json()["filename"].endswith(".jpg")

    fake_png = b"not really an image" * 10
    rejected = render_client.post("/api/v1/render/references", files={"image": ("x.png", fake_png, "image/png")})
    assert rejected.status_code == 415
    assert "header" in rejected.json()["detail"]
    assert not list((tmp_path / "generated" / "renders" / "references").glob("*.png"))


def test_upload_dedups_identical_files(render_client, tmp_path):
    data = image_bytes("WEBP")
    first = render_client.post("/api/v1/render/references", files={"image": ("a.webp", data, "image/webp")}).json()
    stored = tmp_path / "generated" / "renders" / "references" / first["filename"]
    mtime = stored.stat().st_mtime_ns
    second = render_client.post("/api/v1/render/references", files={"image": ("b.webp", data, "image/webp")})
    assert second.status_code == 201
    assert second.json() == first
    assert stored.stat().st_mtime_ns == mtime  # not rewritten
    assert len(list(stored.parent.iterdir())) == 1


def test_upload_size_limit_is_413(render_client, monkeypatch):
    assert references.MAX_REFERENCE_BYTES == 20 * 1024 * 1024
    data = image_bytes("PNG", (64, 64))
    monkeypatch.setattr(references, "MAX_REFERENCE_BYTES", len(data) - 1)
    response = render_client.post("/api/v1/render/references", files={"image": ("big.png", data, "image/png")})
    assert response.status_code == 413
    monkeypatch.setattr(references, "MAX_REFERENCE_BYTES", len(data))
    assert render_client.post("/api/v1/render/references", files={"image": ("ok.png", data)}).status_code == 201


def test_upload_requires_the_image_field(render_client):
    response = render_client.post("/api/v1/render/references", files={"file": ("x.png", image_bytes("PNG"))})
    assert response.status_code == 422


def test_get_reference_serves_the_stored_file(render_client):
    data = image_bytes("JPEG")
    ref = render_client.post("/api/v1/render/references", files={"image": ("a.jpg", data)}).json()
    got = render_client.get(f"/api/v1/render/references/{ref['reference_id']}")
    assert got.status_code == 200
    assert got.content == data
    assert got.headers["content-type"] == "image/jpeg"
    assert render_client.get("/api/v1/render/references/" + "0" * 64).status_code == 404
    assert render_client.get("/api/v1/render/references/..%2F..%2Fsecret").status_code == 404


# -- W2-1: reference on a render job -----------------------------------------------


def test_job_request_validates_reference_id(render_client):
    ref = references.store_reference(image_bytes("PNG"))
    ok = render_client.post("/api/v1/render/jobs", json={"prompt": "x", "reference_id": ref["reference_id"]})
    assert ok.status_code == 202
    assert ok.json()["operation"]["params"]["reference_id"] == ref["reference_id"]
    for bad in ("0" * 64, "not-a-sha", ref["reference_id"][:10]):
        assert render_client.post("/api/v1/render/jobs", json={"prompt": "x", "reference_id": bad}).status_code == 422


def test_graph_wires_reference_into_the_text_encoder():
    plain = build_graph("p", 256, 256, 256, 256, 1, "x")
    assert "13" not in plain
    assert set(plain["4"]["inputs"]) == {"clip", "prompt", "negative_prompt", "resolution"}

    graph = build_graph("p", 256, 256, 256, 256, 1, "x", reference_image="vajra-reference-a.png")
    assert graph["13"] == {"class_type": "LoadImage", "inputs": {"image": "vajra-reference-a.png"}}
    assert graph["4"]["inputs"]["vae"] == ["3", 0]
    assert graph["4"]["inputs"]["images.image_1"] == ["13", 0]
    adapter = ComfyUIQwenImage21Adapter("http://comfy.test")
    spec = RenderSpec("j", "p", 1, 256, 256, 256, 256, reference_image="r.png")
    assert adapter.build_graph(spec)["13"]["inputs"]["image"] == "r.png"


async def test_adapter_upload_returns_comfyui_name_with_subfolder(fake):
    adapter = jobs.get_backend()
    assert await adapter.upload_reference(b"\x89PNG data", "vajra-reference-x.png") == "vajra-reference-upload-1.png"
    fake.upload_subfolder = "vajra"
    assert await adapter.upload_reference(b"\x89PNG data", "x.png") == "vajra/vajra-reference-upload-2.png"
    assert b'name="image"' in fake.uploads[0] and b"\x89PNG data" in fake.uploads[0]


async def test_reference_job_uploads_a_copy_and_records_sha(fake, tmp_path):
    data = image_bytes("PNG", (48, 48))
    ref = references.store_reference(data)
    stored = references.find_reference(ref["reference_id"])
    before = (stored.read_bytes(), stored.stat().st_mtime_ns)

    op = jobs.submit_job(RenderJobRequest(prompt="Tara", width=256, height=256, seed=7, reference_id=ref["sha256"]))
    assert await RenderWorker(timeout_seconds=5).drain() == 1

    done = operations.get_operation(op["id"])
    assert done["status"] == "success", done["error"]
    assert done["params"]["reference_id"] == ref["reference_id"]
    assert done["result"]["reference_sha256"] == hashlib.sha256(data).hexdigest()
    assert len(fake.uploads) == 1 and data in fake.uploads[0]
    graph = fake.prompts["p1"]["prompt"]
    assert graph["13"]["inputs"]["image"] == "vajra-reference-upload-1.png"
    assert graph["4"]["inputs"]["images.image_1"] == ["13", 0]
    assert fake.calls.index(("POST", "/upload/image")) < fake.calls.index(("POST", "/prompt"))
    sidecar = json.loads((tmp_path / done["result"]["sidecar_path"]).read_text(encoding="utf-8"))
    assert sidecar["reference"] == {
        "reference_id": ref["reference_id"],
        "sha256": ref["sha256"],
        "backend_image": "vajra-reference-upload-1.png",
    }
    assert sidecar["graph"]["13"]["class_type"] == "LoadImage"
    assert (stored.read_bytes(), stored.stat().st_mtime_ns) == before  # original untouched


async def test_reference_missing_on_disk_fails_explicitly(fake):
    ref = references.store_reference(image_bytes("PNG"))
    op = jobs.submit_job(RenderJobRequest(prompt="x", width=256, height=256, reference_id=ref["reference_id"]))
    references.find_reference(ref["reference_id"]).unlink()
    await RenderWorker(timeout_seconds=5).drain()
    failed = operations.get_operation(op["id"])
    assert failed["status"] == "error" and "is not stored" in failed["error"]
    assert ("POST", "/prompt") not in fake.calls


async def test_reference_job_reattaches_after_restart_without_reuploading(fake, tmp_path):
    ref = references.store_reference(image_bytes("PNG"))
    op = jobs.submit_job(RenderJobRequest(prompt="x", width=256, height=256, seed=3, reference_id=ref["sha256"]))
    operations.start_operation(op["id"])
    operations.update_operation_result(
        op["id"],
        {
            "backend_prompt_id": "p-old",
            "queue_position": 0,
            "reference_sha256": ref["sha256"],
            "reference_image": "vajra-reference-old.png",
        },
    )
    fake.prompts["p-old"] = {"prompt": build_graph("x", 256, 256, 256, 256, 3, "x", "vajra-reference-old.png")}
    fake.finish("p-old")

    assert await RenderWorker(timeout_seconds=5).recover() == 1
    done = operations.get_operation(op["id"])
    assert done["status"] == "success", done["error"]
    assert done["result"]["reference_sha256"] == ref["sha256"]
    assert fake.uploads == [] and ("POST", "/prompt") not in fake.calls
    sidecar = json.loads((tmp_path / done["result"]["sidecar_path"]).read_text(encoding="utf-8"))
    assert sidecar["graph"]["13"]["inputs"]["image"] == "vajra-reference-old.png"


# -- W2-2: witness renders -----------------------------------------------------------


def seal(intention: str = "a lamp in the dark") -> dict[str, Any]:
    return working.run_working(intention, broadcast=False)


def fake_hosted(monkeypatch) -> list[str]:
    prompts: list[str] = []

    def generate_image(prompt: str, **kwargs: Any) -> dict[str, Any]:
        prompts.append(prompt)
        return {"image_data_url": "data:image/png;base64,QQ==", "model": "hosted-test", "cost_usd": 0.01}

    monkeypatch.setattr("backend.core.llm_agent.tools.generate_image", generate_image)
    return prompts


def test_witness_local_returns_202_and_links_the_job(operator_client, fake, monkeypatch):
    hosted = fake_hosted(monkeypatch)
    folio = seal()
    response = operator_client.post(
        f"/api/v1/operator/workings/{folio['working_id']}/witness", json={"backend": "local"}
    )
    assert response.status_code == 202
    body = response.json()
    assert set(body) == {"working_id", "operation"}
    op = body["operation"]
    assert body["working_id"] == folio["working_id"]
    assert op["kind"] == "render" and op["status"] == "queued"
    assert op["working_id"] == folio["working_id"]
    assert op["params"]["purpose"] == "witness"
    assert op["params"]["prompt"] == folio["image_prompt"]
    assert hosted == []
    assert "witness" not in working.load_working(folio["working_id"])  # untouched until the render ends
    listed = operations.list_operations(working_id=folio["working_id"], kind="render")
    assert [o["id"] for o in listed] == [op["id"]]


def test_witness_manifest_alias_and_default_go_local_when_reachable(operator_client, fake):
    folio = seal()
    response = operator_client.post(f"/api/v1/operator/workings/{folio['working_id']}/manifest")
    assert response.status_code == 202
    assert response.json()["operation"]["params"]["purpose"] == "witness"
    assert ("GET", "/system_stats") in fake.calls


def test_witness_default_falls_back_to_hosted_and_says_so(operator_client, fake, monkeypatch):
    hosted = fake_hosted(monkeypatch)
    fake.down = True
    folio = seal()
    response = operator_client.post(f"/api/v1/operator/workings/{folio['working_id']}/witness", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["witness"]["status"] == "ok" and body["witness"]["image_data_url"].startswith("data:image")
    assert body["witness_fallback"]["requested"] == "local"
    assert body["witness_fallback"]["used"] == "hosted"
    assert "unreachable" in body["witness_fallback"]["reason"]
    assert hosted == [folio["image_prompt"]]
    assert operations.list_operations(kind="render") == []
    assert "witness_fallback" not in working.load_working(folio["working_id"])  # response only


def test_witness_hosted_is_unchanged_and_skips_the_health_probe(operator_client, fake, monkeypatch):
    hosted = fake_hosted(monkeypatch)
    folio = seal()
    response = operator_client.post(
        f"/api/v1/operator/workings/{folio['working_id']}/witness", json={"backend": "hosted"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["working_id"] == folio["working_id"]
    assert body["witness"] == {
        "status": "ok",
        "image_data_url": "data:image/png;base64,QQ==",
        "model": "hosted-test",
        "cost_usd": 0.01,
        "provider_used": None,
        "prompt": folio["image_prompt"],
    }
    assert body["manifestation"] == body["witness"]
    assert "witness_fallback" not in body
    assert hosted == [folio["image_prompt"]]
    assert fake.calls == []  # no ComfyUI traffic at all
    assert operations.list_operations(kind="render") == []


def test_witness_404_and_validation(operator_client, fake):
    assert operator_client.post("/api/v1/operator/workings/wrk_missing/witness").status_code == 404
    folio = seal()
    bad = operator_client.post(f"/api/v1/operator/workings/{folio['working_id']}/witness", json={"backend": "gpu"})
    assert bad.status_code == 422


async def test_listener_writes_ok_witness_when_the_render_succeeds(fake):
    folio = seal()
    submitted = working.submit_witness_render(folio["working_id"])
    op_id = submitted["operation"]["id"]
    assert await RenderWorker(timeout_seconds=5).drain() == 1  # listener installed by submit_witness_render

    done = operations.get_operation(op_id)
    assert done["status"] == "success", done["error"]
    saved = working.load_working(folio["working_id"])
    expected = {
        "status": "ok",
        "source": "local-render",
        "operation_id": op_id,
        "image_url": f"/api/v1/render/jobs/{op_id}/image",
        "seed": done["params"]["seed"],
        "seed_provenance": "draw",
        "width": 1024,
        "height": 1024,
        "prompt": folio["image_prompt"],
    }
    assert saved["witness"] == expected
    assert saved["manifestation"] == expected
    assert saved["intention"] == folio["intention"]  # nothing else changed
    summary = next(w for w in working.list_workings() if w["working_id"] == folio["working_id"])
    assert summary["has_witness"] is True


async def test_listener_writes_error_witness_when_the_render_fails(fake):
    fake.exec_error = {"node_id": "8", "node_type": "SamplerCustom", "exception_message": "out of memory"}
    folio = seal()
    op_id = working.submit_witness_render(folio["working_id"])["operation"]["id"]
    await RenderWorker(timeout_seconds=5).drain()
    failed = operations.get_operation(op_id)
    assert failed["status"] == "error"
    witness = working.load_working(folio["working_id"])["witness"]
    assert witness == {"status": "error", "operation_id": op_id, "error": failed["error"]}
    assert "out of memory" in witness["error"]


async def test_worker_run_installs_the_witness_listener(fake):
    import asyncio

    operations.remove_listener(working.witness_listener)
    folio = seal()
    op = jobs.submit_job(
        RenderJobRequest(prompt="x", width=256, height=256, working_id=folio["working_id"], purpose="witness")
    )
    worker = worker_mod.get_render_worker()
    worker._timeout_seconds = 5
    task = asyncio.create_task(worker.run())
    try:
        for _ in range(600):
            if (working.load_working(folio["working_id"]).get("witness") or {}).get("operation_id") == op["id"]:
                break
            await asyncio.sleep(0.005)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert working.load_working(folio["working_id"])["witness"]["status"] == "ok"


def test_listener_is_idempotent_and_ignores_other_operations(fake):
    folio = seal()
    wid = folio["working_id"]
    op = operations.create_operation("render", "w", params={"purpose": "witness", "prompt": "p"}, working_id=wid)
    operations.start_operation(op["id"])
    done = operations.complete_operation(op["id"], {"image_url": "/u", "seed": 1, "width": 8, "height": 8})
    assert working.apply_witness_render(done) is True
    path = working.WORKINGS_DIR / f"{wid}.json"
    mtime = path.stat().st_mtime_ns
    assert working.apply_witness_render(done) is False  # same outcome again: no write
    assert path.stat().st_mtime_ns == mtime

    free = operations.create_operation("render", "f", params={"purpose": "free", "prompt": "p"}, working_id=wid)
    operations.start_operation(free["id"])
    assert working.apply_witness_render(operations.complete_operation(free["id"], {"image_url": "/v"})) is False
    broadcast = operations.create_operation("broadcast", "b", working_id=wid)
    assert working.apply_witness_render(operations.fail_operation(broadcast["id"], "x")) is False
    running = operations.create_operation("render", "r", params={"purpose": "witness"}, working_id=wid)
    assert working.apply_witness_render(operations.start_operation(running["id"])) is False
    assert working.apply_witness_render(operations.cancel_operation(running["id"])) is False
    assert working.load_working(wid)["witness"]["operation_id"] == op["id"]


def test_listener_never_lets_an_older_render_replace_a_newer_witness(fake):
    folio = seal()
    wid = folio["working_id"]
    older = operations.create_operation("render", "old", params={"purpose": "witness"}, working_id=wid)
    time.sleep(0.02)  # distinct created_at even on a coarse clock
    newer = operations.create_operation("render", "new", params={"purpose": "witness"}, working_id=wid)
    operations.start_operation(newer["id"])
    assert working.apply_witness_render(operations.complete_operation(newer["id"], {"image_url": "/new"}))
    operations.start_operation(older["id"])
    assert working.apply_witness_render(operations.fail_operation(older["id"], "late failure")) is False
    assert working.load_working(wid)["witness"]["image_url"] == "/new"


def test_listener_tolerates_a_missing_folio(fake):
    op = operations.create_operation("render", "w", params={"purpose": "witness"}, working_id="wrk_gone")
    operations.start_operation(op["id"])
    assert working.apply_witness_render(operations.fail_operation(op["id"], "x")) is False


# -- sigils ------------------------------------------------------------------------


@pytest.fixture
def sigils(tmp_path, monkeypatch):
    from backend.core.services import sigil_service as module

    service = module.sigil_service
    monkeypatch.setattr(service, "storage_dir", tmp_path / "sigils")
    service.storage_dir.mkdir()

    def no_network(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("sigil test made a real HTTP request")

    monkeypatch.setattr(module.requests, "post", no_network)
    monkeypatch.setattr(module.requests, "get", no_network)
    return service


async def test_sigil_comfyui_provider_queues_a_render_job(sigils, monkeypatch, fake):
    monkeypatch.setattr(sigils, "image_provider", "comfyui")
    sigil = await sigils.forge_sigil("Protection for the house", "saturn")
    assert sigil["ai_image"] is None
    render = sigil["ai_image_render"]
    assert render["status"] == "queued" and render["operation_id"]
    op = operations.get_operation(render["operation_id"])
    assert op["kind"] == "render" and op["params"]["purpose"] == "sigil"
    assert "Protection for the house" in op["params"]["prompt"]
    assert sigil["svg"].startswith("<svg")
    saved = json.loads((sigils.storage_dir / f"{sigil['id']}.json").read_text(encoding="utf-8"))
    assert saved["ai_image_render"] == render
    assert fake.calls == []  # submission never waits on ComfyUI


async def test_sigil_comfyui_submission_failure_is_reported_not_raised(sigils, monkeypatch):
    monkeypatch.setattr(sigils, "image_provider", "comfyui")

    def broken(request: RenderJobRequest) -> dict[str, Any]:
        raise RuntimeError("ledger unavailable")

    monkeypatch.setattr(jobs, "submit_job", broken)
    sigil = await sigils.forge_sigil("x")
    assert sigil["ai_image"] is None
    assert sigil["ai_image_render"] == {"operation_id": None, "status": "error", "error": "ledger unavailable"}


async def test_sigil_hosted_provider_still_returns_inline_image(sigils, monkeypatch):
    from backend.core.services import sigil_service as module

    class Reply:
        status_code = 200

        @staticmethod
        def json() -> dict[str, Any]:
            return {"data": [{"b64_json": "QUJD"}]}

    monkeypatch.setattr(sigils, "image_provider", "openai")
    monkeypatch.setattr(sigils, "openai_api_key", "sk-test")
    monkeypatch.setattr(module.requests, "post", lambda *a, **k: Reply())
    sigil = await sigils.forge_sigil("x")
    assert sigil["ai_image"] == "data:image/png;base64,QUJD"
    assert sigil["ai_image_render"] is None
    assert operations.list_operations(kind="render") == []


async def test_sigil_without_provider_has_no_image(sigils, monkeypatch):
    monkeypatch.setattr(sigils, "image_provider", "none")
    sigil = await sigils.forge_sigil("x")
    assert sigil["ai_image"] is None and sigil["ai_image_render"] is None


def test_stale_comfyui_paths_are_gone():
    source = (REPO_ROOT / "backend" / "core" / "services" / "sigil_service.py").read_text(encoding="utf-8")
    assert "COMFYUI_API_URL" not in source
    assert "comfy_workflow" not in source and "CheckpointLoaderSimple" not in source
    assert not (REPO_ROOT / "comfy_workflow.json").exists()
    launcher = (REPO_ROOT / "scripts" / "start_comfyui.bat").read_text(encoding="utf-8")
    assert "COMFYUI_LAUNCHER" in launcher
    assert "set /p" not in launcher.lower()
    # The flag ComfyUI 0.22 does not have must not be passed (comments may still name it).
    command_lines = [line for line in launcher.splitlines() if not line.strip().upper().startswith("REM")]
    assert not any("--api-only" in line for line in command_lines)
    assert "COMFYUI_LAUNCHER" in (REPO_ROOT / ".env.example").read_text(encoding="utf-8")


# -- one witness policy for the route and the LLM tools --------------------------------


def fake_hosted_off_loop(monkeypatch) -> list[bool]:
    """Hosted generator stub recording whether it ran on a thread with a running event loop."""
    import asyncio

    on_loop: list[bool] = []

    def generate_image(prompt: str, **kwargs: Any) -> dict[str, Any]:
        try:
            asyncio.get_running_loop()
            on_loop.append(True)
        except RuntimeError:
            on_loop.append(False)
        return {"image_data_url": "data:image/png;base64,QQ==", "model": "hosted-test", "cost_usd": 0.01}

    monkeypatch.setattr("backend.core.llm_agent.tools.generate_image", generate_image)
    return on_loop


async def test_hosted_witness_runs_off_the_event_loop(fake, monkeypatch):
    on_loop = fake_hosted_off_loop(monkeypatch)
    folio = seal()
    outcome = await working.forge_witness(folio["working_id"], "hosted")
    assert outcome is not None and outcome.queued is False
    assert outcome.body["witness"]["status"] == "ok"
    assert on_loop == [False]  # a worker thread, so the loop kept serving while it ran


def test_hosted_witness_route_runs_off_the_event_loop(operator_client, fake, monkeypatch):
    on_loop = fake_hosted_off_loop(monkeypatch)
    folio = seal()
    response = operator_client.post(
        f"/api/v1/operator/workings/{folio['working_id']}/witness", json={"backend": "hosted"}
    )
    assert response.status_code == 200
    assert response.json()["witness"]["status"] == "ok"
    assert on_loop == [False]


async def test_witness_tool_queues_local_render_and_returns_its_operation_id(fake, monkeypatch):
    hosted = fake_hosted(monkeypatch)
    folio = seal()
    result = await working.forge_witness_for_tool(folio["working_id"])
    assert result["status"] == "queued" and result["backend"] == "local"
    op = operations.get_operation(result["operation_id"])
    assert op["kind"] == "render" and op["working_id"] == folio["working_id"]
    assert op["params"]["purpose"] == "witness"
    assert hosted == []


async def test_witness_tool_falls_back_to_hosted_and_says_so(fake, monkeypatch):
    on_loop = fake_hosted_off_loop(monkeypatch)
    fake.down = True
    folio = seal()
    result = await working.forge_witness_for_tool(folio["working_id"])
    assert result["witness"]["status"] == "ok"
    assert result["witness_fallback"]["used"] == "hosted"
    assert on_loop == [False]
    assert operations.list_operations(kind="render") == []


async def test_witness_tool_reports_missing_folio(fake):
    assert await working.forge_witness_for_tool("wrk_missing") == {
        "error": "working_not_found",
        "working_id": "wrk_missing",
    }


async def test_chat_forge_witness_tool_uses_the_shared_policy(fake, monkeypatch):
    from backend.app.api.v1.endpoints.llm import execute_tool_locally

    hosted = fake_hosted(monkeypatch)
    folio = seal()
    result = await execute_tool_locally("forge_witness", {"working_id": folio["working_id"]})
    assert result["status"] == "queued"
    assert operations.get_operation(result["operation_id"])["params"]["purpose"] == "witness"
    assert hosted == []


def test_agent_forge_witness_tool_uses_the_shared_policy(fake, monkeypatch):
    from backend.core.llm_agent.tools import TOOL_REGISTRY

    hosted = fake_hosted(monkeypatch)
    folio = seal()
    result = TOOL_REGISTRY["forge_witness"](working_id=folio["working_id"])
    assert result["status"] == "queued"
    assert operations.get_operation(result["operation_id"])["working_id"] == folio["working_id"]
    assert hosted == []
