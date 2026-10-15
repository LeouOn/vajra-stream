"""Gallery: every real image in one list, served safely, broken files skipped and reported.

Everything runs against tmp dirs: the ledger DB, render artifacts, hosted saves
and folios are redirected, so the real generated/ is never read or written.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

import core.working as working
from backend.app.api.v1.endpoints import gallery as gallery_endpoint
from backend.app.api.v1.endpoints import image_generation
from backend.core.services import gallery
from backend.core.services.image_generation_service import ImageGenerationService, ImageProvider, ProviderResult
from backend.core.services.render import jobs
from core import operations


def image_bytes(fmt: str = "PNG", size: tuple[int, int] = (48, 32), shade: int = 0) -> bytes:
    """A small real image; ``shade`` makes otherwise-equal images differ."""
    img = Image.new("RGB", size)
    img.putdata([((x * 5 + shade) % 256, (y * 7) % 256, shade % 256) for y in range(size[1]) for x in range(size[0])])
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def data_url(data: bytes, media_type: str = "image/png") -> str:
    return f"data:{media_type};base64,{base64.b64encode(data).decode('ascii')}"


@pytest.fixture
def roots(tmp_path, monkeypatch) -> dict[str, Path]:
    hosted = tmp_path / "images"
    hosted.mkdir()
    workings = tmp_path / "workings"
    workings.mkdir()
    monkeypatch.setattr(operations, "get_db_path", lambda: str(tmp_path / "ops.db"))
    monkeypatch.setattr(jobs, "artifact_base", lambda: tmp_path)
    monkeypatch.setattr(working, "WORKINGS_DIR", workings)
    monkeypatch.setattr(image_generation, "hosted_output_dir", lambda: hosted)
    return {"base": tmp_path, "hosted": hosted, "workings": workings}


@pytest.fixture
def client(roots) -> TestClient:
    app = FastAPI()
    app.include_router(gallery_endpoint.router, prefix="/api/v1")
    return TestClient(app)


def add_render(
    base: Path, *, prompt: str = "a quiet lake", data: bytes | None = None, working_id: str | None = None
) -> dict[str, Any]:
    data = data if data is not None else image_bytes()
    params = {
        "prompt": prompt,
        "preset": "square-1024",
        "width": 48,
        "height": 32,
        "seed": 7,
        "backend": "comfyui-qwen-image-2.1",
        "working_id": working_id,
        "purpose": "witness" if working_id else "free",
    }
    op = operations.create_operation(
        "render", f"Render: {prompt}", params=params, provenance={"seed": "draw"}, working_id=working_id
    )
    operations.start_operation(op["id"])
    rel = jobs.artifact_relpath(op)
    (base / rel).parent.mkdir(parents=True, exist_ok=True)
    (base / rel).write_bytes(data)
    result = {
        "image_url": f"/api/v1/render/jobs/{op['id']}/image",
        "width": 48,
        "height": 32,
        "seed": 7,
        "sha256": hashlib.sha256(data).hexdigest(),
        "artifact_path": str(rel),
        "backend_execution_seconds": 12.5,
    }
    return operations.complete_operation(op["id"], result)


def add_hosted(hosted: Path, name: str, data: bytes, sidecar: dict[str, Any] | None = None) -> Path:
    path = hosted / name
    path.write_bytes(data)
    if sidecar is not None:
        path.with_suffix(".json").write_text(json.dumps(sidecar), encoding="utf-8")
    return path


def add_folio(workings: Path, wid: str, witness: dict[str, Any], **extra: Any) -> None:
    folio = {"working_id": wid, "sealed_at": "2026-07-01T10:00:00+00:00", "witness": witness, **extra}
    (workings / f"{wid}.json").write_text(json.dumps(folio), encoding="utf-8")


# -- listing -------------------------------------------------------------------------


def test_lists_all_three_sources_newest_first(client, roots):
    op = add_render(roots["base"], prompt="lotus at dawn")
    add_hosted(
        roots["hosted"],
        "img_1785633576_cb2a7bbc.png",
        image_bytes(shade=1),
        {"prompt": "golden mandala", "provider": "openrouter", "model": "m/x", "size": "1024x1024", "sha256": None},
    )
    add_folio(
        roots["workings"],
        "wrk_aaa111",
        {"status": "ok", "image_data_url": data_url(image_bytes("JPEG", shade=2), "image/jpeg"), "prompt": "a stupa"},
    )

    body = client.get("/api/v1/gallery").json()

    assert [item["source"] for item in body["items"]] == ["local-render", "hosted", "witness"]
    assert body["total"] == 3
    assert body["counts"] == {"local-render": 1, "hosted": 1, "witness": 1}
    assert body["skipped"] == []

    render, hosted, witness = body["items"]
    assert render["id"] == f"render:{op['id']}"
    assert render["prompt"] == "lotus at dawn"
    assert render["image_url"] == f"/api/v1/render/jobs/{op['id']}/image"
    assert render["links"] == {"operation_id": op["id"], "working_id": None}
    assert render["origin"]["seed"] == 7
    assert render["origin"]["seed_provenance"] == "draw"
    assert render["origin"]["backend_execution_seconds"] == 12.5
    assert (render["width"], render["height"], render["media_type"]) == (48, 32, "image/png")

    assert hosted["image_url"] == "/api/v1/gallery/hosted/img_1785633576_cb2a7bbc.png"
    assert hosted["prompt"] == "golden mandala"
    assert hosted["origin"]["provider"] == "openrouter"
    assert hosted["origin"]["model"] == "m/x"
    assert hosted["settings"]["size"] == "1024x1024"
    assert "_path" not in hosted

    assert witness["image_url"] == "/api/v1/gallery/witness/wrk_aaa111/image"
    assert witness["media_type"] == "image/jpeg"
    assert witness["links"] == {"operation_id": None, "working_id": "wrk_aaa111"}
    assert witness["created_at"] == "2026-07-01T10:00:00+00:00"


def test_hosted_save_without_sidecar_still_listed(client, roots):
    add_hosted(roots["hosted"], "img_1785633576_cb2a7bbc.jpg", image_bytes("JPEG"))
    (item,) = client.get("/api/v1/gallery").json()["items"]
    assert item["prompt"] is None
    assert item["origin"]["sidecar"] is False
    assert item["created_at"] == "2026-08-02T01:19:36+00:00"  # from the file name's unix time
    assert item["media_type"] == "image/jpeg"


def test_render_links_its_folio(client, roots):
    op = add_render(roots["base"], working_id="wrk_abc123")
    (item,) = client.get("/api/v1/gallery").json()["items"]
    assert item["links"] == {"operation_id": op["id"], "working_id": "wrk_abc123"}
    assert item["purpose"] == "witness"


def test_hosted_witness_is_merged_into_its_saved_file(client, roots):
    data = image_bytes(shade=9)
    add_hosted(roots["hosted"], "img_1785633576_cb2a7bbc.png", data)  # legacy save, no sidecar
    add_folio(
        roots["workings"],
        "wrk_twin01",
        {"status": "ok", "image_data_url": data_url(data), "prompt": "the folio prompt", "model": "m/y"},
    )

    body = client.get("/api/v1/gallery").json()
    (item,) = body["items"]
    assert item["source"] == "hosted"
    assert item["links"]["working_id"] == "wrk_twin01"
    assert item["purpose"] == "witness"
    assert item["prompt"] == "the folio prompt"
    assert item["origin"]["model"] == "m/y"
    assert body["counts"] == {"local-render": 0, "hosted": 1, "witness": 0}


def test_local_witness_and_hidden_folios_add_no_item(client, roots):
    add_folio(roots["workings"], "wrk_local1", {"status": "ok", "source": "local-render", "image_url": "/x"})
    add_folio(roots["workings"], "wrk_hidden", {"status": "ok", "image_data_url": data_url(image_bytes())}, hidden=True)
    add_folio(roots["workings"], "wrk_errorx", {"status": "error", "error": "boom"})
    assert client.get("/api/v1/gallery").json()["total"] == 0


def test_corrupt_files_are_skipped_and_reported(client, roots):
    good = image_bytes()
    add_hosted(roots["hosted"], "img_1700000000_00000001.png", b"\x89PNG_FAKE_BYTES")  # the old test stub
    add_hosted(roots["hosted"], "img_1700000001_00000002.png", good[:-12])  # truncated: no IEND
    add_hosted(roots["hosted"], "img_1700000002_00000003.jpg", b"<html>not an image</html>" * 10)
    add_hosted(roots["hosted"], "img_1700000003_00000004.jpg", image_bytes("JPEG")[:-200])  # truncated JPEG
    add_hosted(roots["hosted"], "img_1700000004_00000005.png", good)
    (roots["hosted"] / "notes.txt").write_text("ignored", encoding="utf-8")
    bad_render = add_render(roots["base"], data=b"\x89PNG\r\n\x1a\n" + b"\x00" * 10)
    missing = add_render(roots["base"])
    (roots["base"] / missing["result"]["artifact_path"]).unlink()
    add_folio(roots["workings"], "wrk_junk01", {"status": "ok", "image_data_url": "data:image/png;base64,QUJD"})

    body = client.get("/api/v1/gallery").json()

    assert [item["id"] for item in body["items"]] == ["hosted:img_1700000004_00000005.png"]
    reasons = {entry["ref"]: entry["reason"] for entry in body["skipped"]}
    assert set(reasons) == {
        "img_1700000000_00000001.png",
        "img_1700000001_00000002.png",
        "img_1700000002_00000003.jpg",
        "img_1700000003_00000004.jpg",
        bad_render["id"],
        missing["id"],
        "wrk_junk01",
    }
    assert "too small" in reasons["img_1700000000_00000001.png"]
    assert "truncated" in reasons["img_1700000001_00000002.png"]
    assert "not a PNG, JPEG or WebP" in reasons["img_1700000002_00000003.jpg"]
    assert "truncated" in reasons["img_1700000003_00000004.jpg"]
    assert reasons[missing["id"]] == "image file is missing"


def test_source_filter_and_paging(client, roots):
    for i in range(5):
        add_hosted(roots["hosted"], f"img_17000000{i:02d}_0000000{i}.png", image_bytes(shade=i))
    add_render(roots["base"])

    hosted = client.get("/api/v1/gallery", params={"source": "hosted", "limit": 2, "offset": 1}).json()
    assert hosted["total"] == 5
    assert hosted["counts"] == {"local-render": 1, "hosted": 5, "witness": 0}
    assert [item["id"] for item in hosted["items"]] == [
        "hosted:img_1700000003_00000003.png",
        "hosted:img_1700000002_00000002.png",
    ]
    assert client.get("/api/v1/gallery", params={"source": "local-render"}).json()["total"] == 1
    assert client.get("/api/v1/gallery", params={"offset": 10}).json()["items"] == []
    assert client.get("/api/v1/gallery", params={"source": "mops"}).status_code == 422
    assert client.get("/api/v1/gallery", params={"limit": 0}).status_code == 422


def test_empty_when_nothing_exists(client, roots, tmp_path, monkeypatch):
    monkeypatch.setattr(image_generation, "hosted_output_dir", lambda: tmp_path / "absent")
    monkeypatch.setattr(working, "WORKINGS_DIR", tmp_path / "absent-too")
    body = client.get("/api/v1/gallery").json()
    assert body["items"] == [] and body["total"] == 0 and body["skipped"] == []


def test_caption_facts_pass_through(client, roots):
    facts = [{"label": "moon", "value": "waxing"}]
    add_hosted(roots["hosted"], "img_1785633576_cb2a7bbc.png", image_bytes(), {"prompt": "p", "caption_facts": facts})
    (item,) = client.get("/api/v1/gallery").json()["items"]
    assert item["caption_facts"] == facts


# -- hosted file route -----------------------------------------------------------------


def test_hosted_route_serves_the_image_with_its_real_type(client, roots):
    data = image_bytes("JPEG")
    add_hosted(roots["hosted"], "img_1785633576_cb2a7bbc.png", data)  # named .png, really a JPEG
    res = client.get("/api/v1/gallery/hosted/img_1785633576_cb2a7bbc.png")
    assert res.status_code == 200
    assert res.content == data
    assert res.headers["content-type"] == "image/jpeg"


@pytest.mark.parametrize(
    "name",
    [
        "..%2F..%2Fpyproject.toml",
        "..%5C..%5Cpyproject.toml",
        "%2E%2E%2Fsecret.png",
        "img_1785633576_cb2a7bbc.png%00.txt",
        "img_1785633576_CB2A7BBC.png",
        "img_1785633576_cb2a7bbc.json",
        "secret.png",
        "img_1785633576_cb2a7bbc.png.bak",
    ],
)
def test_hosted_route_rejects_anything_but_an_exact_save_name(client, roots, name):
    add_hosted(roots["hosted"], "img_1785633576_cb2a7bbc.png", image_bytes(), {"prompt": "p"})
    (roots["base"] / "secret.png").write_bytes(image_bytes())
    res = client.get(f"/api/v1/gallery/hosted/{name}")
    assert res.status_code == 404


@pytest.mark.parametrize("name", ["../secret.png", "..\\secret.png", "/etc/passwd", "img_1_abcdef12.png/../x"])
def test_hosted_file_never_leaves_its_directory(roots, name):
    (roots["base"] / "secret.png").write_bytes(image_bytes())
    with pytest.raises(gallery.GalleryNotFound):
        gallery.hosted_file(roots["hosted"], name)


def test_hosted_route_refuses_a_corrupt_file(client, roots):
    add_hosted(roots["hosted"], "img_1700000000_00000001.png", b"\x89PNG_FAKE_BYTES")
    assert client.get("/api/v1/gallery/hosted/img_1700000000_00000001.png").status_code == 415
    assert client.get("/api/v1/gallery/hosted/img_1700000009_00000009.png").status_code == 404


# -- witness route ---------------------------------------------------------------------


def test_witness_route_decodes_the_inline_image(client, roots):
    data = image_bytes("JPEG")
    add_folio(roots["workings"], "wrk_aaa111", {"status": "ok", "image_data_url": data_url(data, "image/jpeg")})
    res = client.get("/api/v1/gallery/witness/wrk_aaa111/image")
    assert res.status_code == 200
    assert res.content == data
    assert res.headers["content-type"] == "image/jpeg"


def test_witness_route_404s(client, roots):
    add_folio(roots["workings"], "wrk_local1", {"status": "ok", "source": "local-render", "image_url": "/x"})
    assert client.get("/api/v1/gallery/witness/wrk_local1/image").status_code == 404
    assert client.get("/api/v1/gallery/witness/wrk_nope00/image").status_code == 404
    assert client.get("/api/v1/gallery/witness/..%2Fwrk_local1/image").status_code == 404
    assert client.get("/api/v1/gallery/witness/index/image").status_code == 404


def test_witness_route_refuses_corrupt_data(client, roots):
    add_folio(roots["workings"], "wrk_junk01", {"status": "ok", "image_data_url": "data:image/png;base64,QUJD"})
    assert client.get("/api/v1/gallery/witness/wrk_junk01/image").status_code == 415


# -- hosted saves write a sidecar --------------------------------------------------------


class _FakeProvider(ImageProvider):
    def __init__(self, data: bytes) -> None:
        self.data = data

    async def generate(self, prompt: str, model: str, size: str, quality: str, n: int, **kwargs: Any) -> ProviderResult:
        return ProviderResult(
            image_data_url=data_url(self.data), model=model, cost_usd=0.01, provider="openrouter", revised_prompt="rp"
        )


async def test_generate_writes_a_sidecar_the_gallery_reads(client, roots):
    data = image_bytes()
    service = ImageGenerationService(
        {"enabled": True, "image_output_dir": str(roots["hosted"]), "prompt_style_prefix": "Thangka style"}
    )
    service._providers["openrouter"] = _FakeProvider(data)

    result = await service.generate("white tara", model="m/z", size="1792x1024")

    saved = Path(result["image_file_path"])
    sidecar = json.loads(saved.with_suffix(".json").read_text(encoding="utf-8"))
    assert sidecar["prompt"] == "white tara"
    assert sidecar["full_prompt"] == "Thangka style. white tara"
    assert sidecar["provider"] == "openrouter"
    assert sidecar["model"] == "m/z"
    assert sidecar["size"] == "1792x1024"
    assert sidecar["revised_prompt"] == "rp"
    assert sidecar["sha256"] == hashlib.sha256(data).hexdigest()
    assert sidecar["bytes"] == len(data)
    assert sidecar["filename"] == saved.name
    assert sidecar["created_at"].endswith("+00:00")

    (item,) = client.get("/api/v1/gallery").json()["items"]
    assert item["id"] == f"hosted:{saved.name}"
    assert item["prompt"] == "white tara"
    assert item["origin"]["model"] == "m/z"
    assert item["origin"]["sidecar"] is True


def test_save_survives_an_unwritable_sidecar(tmp_path, monkeypatch):
    service = ImageGenerationService({"image_output_dir": str(tmp_path)})
    real_write_text = Path.write_text

    def refuse_json(self: Path, *args: Any, **kwargs: Any) -> Any:
        if self.suffix == ".json":
            raise OSError("disk full")
        return real_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", refuse_json)
    saved = service._save_image(data_url(image_bytes()), "p", {"prompt": "p"})
    assert saved is not None and Path(saved).is_file()
    assert not Path(saved).with_suffix(".json").exists()


# -- hosted output dir -------------------------------------------------------------------


def test_relative_output_dir_is_anchored_at_the_project_root(monkeypatch):
    from core.schema import get_project_root

    service = ImageGenerationService({"image_output_dir": "generated/images"})
    image_generation._anchor_output_dir(service)
    assert Path(service.config["image_output_dir"]) == get_project_root() / "generated" / "images"


def test_absolute_output_dir_is_kept(tmp_path):
    service = ImageGenerationService({"image_output_dir": str(tmp_path)})
    image_generation._anchor_output_dir(service)
    assert service.config["image_output_dir"] == str(tmp_path)


def test_saved_listing_route_is_retired():
    app = FastAPI()
    app.include_router(image_generation.router, prefix="/api/v1")
    assert all(getattr(route, "path", "") != "/api/v1/images/saved" for route in app.routes)


def test_renders_are_read_past_one_ledger_page(client, roots, monkeypatch):
    monkeypatch.setattr(gallery, "_RENDER_PAGE", 2)
    ids = {add_render(roots["base"], prompt=f"p{i}")["id"] for i in range(5)}
    body = client.get("/api/v1/gallery", params={"source": "local-render"}).json()
    assert body["total"] == 5
    assert {item["links"]["operation_id"] for item in body["items"]} == ids
