"""Local render engine (backend/core/services/render/) against a fake ComfyUI.

Nothing here contacts a real server: every adapter runs on ``httpx.MockTransport``
backed by :class:`FakeComfy`, the ledger uses a tmp DB and artifacts go to tmp_path.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import struct
import zlib
from typing import Any

import httpx
import pytest

from backend.core.services.render import jobs
from backend.core.services.render import worker as worker_mod
from backend.core.services.render.base import MAX_SEED, PNG_MAGIC, PRESETS, RenderError, png_dimensions
from backend.core.services.render.comfyui import (
    BACKEND_NAME,
    CLIP_NAME,
    SIGMAS,
    UNET_NAME,
    VAE_NAME,
    ComfyUIQwenImage21Adapter,
    build_graph,
)
from backend.core.services.render.jobs import RenderJobRequest
from backend.core.services.render.worker import RenderWorker
from core import operations


def make_png(width: int, height: int) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    compressor = zlib.compressobj(1)
    row = b"\x00" * (1 + width * 3)
    body = b"".join(compressor.compress(row) for _ in range(height)) + compressor.flush()
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return PNG_MAGIC + chunk(b"IHDR", ihdr) + chunk(b"IDAT", body) + chunk(b"IEND", b"")


class FakeComfy:
    """Just enough of ComfyUI's HTTP API. ``hold=True`` keeps prompts executing until interrupted."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.prompts: dict[str, dict[str, Any]] = {}
        self.history: dict[str, dict[str, Any]] = {}
        self.running: list[str] = []
        self.pending: list[str] = []
        self.polls: dict[str, int] = {}
        self.view_params: list[dict[str, str]] = []
        self.interrupts: list[str] = []
        self.deleted: list[str] = []
        self.max_concurrent = 0
        # knobs
        self.hold = False
        self.complete_on_poll = 1
        self.png_size: tuple[int, int] | None = None  # None -> the export size in the graph
        self.png_bytes: bytes | None = None
        self.submit_reply: tuple[int, Any] | None = None
        self.exec_error: dict[str, Any] | None = None
        self.down = False
        self.uploads: list[bytes] = []  # raw multipart bodies sent to /upload/image
        self.upload_subfolder = ""

    def _queue_item(self, number: int, pid: str) -> list[Any]:
        return [number, pid, {}, {}, ["10"]]

    def finish(self, pid: str, status_str: str = "success", messages: list[Any] | None = None) -> None:
        if pid in self.running:
            self.running.remove(pid)
        status = {"status_str": status_str, "completed": status_str == "success", "messages": messages or []}
        outputs = {}
        if status_str == "success":
            outputs = {
                "10": {
                    "images": [{"filename": "vajra render_00001_.png", "subfolder": "vajra-render", "type": "output"}]
                }
            }
        self.history[pid] = {"prompt": [], "outputs": outputs, "status": status}

    def _png_for(self, pid: str) -> bytes:
        if self.png_bytes is not None:
            return self.png_bytes
        if self.png_size is not None:
            return make_png(*self.png_size)
        graph = self.prompts[pid]["prompt"]
        node = graph.get("12", graph["11"])["inputs"]
        return make_png(node["width"], node["height"])

    def handler(self, request: httpx.Request) -> httpx.Response:
        if self.down:
            raise httpx.ConnectError("[WinError 10061] connection refused", request=request)
        method, path = request.method, request.url.path
        self.calls.append((method, path))
        if method == "POST" and path == "/upload/image":
            content = request.read()
            self.uploads.append(content)
            name = f"vajra-reference-upload-{len(self.uploads)}.png"
            return httpx.Response(200, json={"name": name, "subfolder": self.upload_subfolder, "type": "input"})
        body = json.loads(request.content) if request.content else None
        if method == "POST" and path == "/prompt":
            if self.submit_reply is not None:
                return httpx.Response(self.submit_reply[0], json=self.submit_reply[1])
            pid = f"p{len(self.prompts) + 1}"
            self.prompts[pid] = body
            self.running.append(pid)
            self.max_concurrent = max(self.max_concurrent, len(self.running))
            return httpx.Response(200, json={"prompt_id": pid, "number": len(self.prompts), "node_errors": {}})
        if method == "GET" and path.startswith("/history/"):
            pid = path.removeprefix("/history/")
            self.polls[pid] = self.polls.get(pid, 0) + 1
            if pid in self.running and not self.hold and self.polls[pid] > self.complete_on_poll:
                if self.exec_error is not None:
                    self.finish(pid, "error", [["execution_error", self.exec_error]])
                else:
                    self.finish(pid)
            return httpx.Response(200, json={pid: self.history[pid]} if pid in self.history else {})
        if method == "GET" and path == "/queue":
            return httpx.Response(
                200,
                json={
                    "queue_running": [self._queue_item(i, p) for i, p in enumerate(self.running)],
                    "queue_pending": [self._queue_item(100 + i, p) for i, p in enumerate(self.pending)],
                },
            )
        if method == "POST" and path == "/interrupt":
            pid = body["prompt_id"]
            self.interrupts.append(pid)
            self.finish(pid, "error", [["execution_interrupted", {"prompt_id": pid}]])
            return httpx.Response(200)
        if method == "POST" and path == "/queue":
            for pid in body.get("delete", []):
                self.deleted.append(pid)
                if pid in self.pending:
                    self.pending.remove(pid)
            return httpx.Response(200)
        if method == "GET" and path == "/view":
            self.view_params.append(dict(request.url.params))
            pid = next(iter(self.history))
            for candidate, entry in self.history.items():
                if entry["outputs"]:
                    pid = candidate
            return httpx.Response(200, content=self._png_for(pid), headers={"content-type": "image/png"})
        if method == "GET" and path == "/system_stats":
            return httpx.Response(
                200,
                json={
                    "system": {"comfyui_version": "0.3.99"},
                    "devices": [{"name": "cuda:0 Test GPU", "vram_total": 24 * 2**30, "vram_free": 20 * 2**30}],
                },
            )
        return httpx.Response(404, text=f"no route {method} {path}")


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(operations, "get_db_path", lambda: str(tmp_path / "ops.db"))
    monkeypatch.setattr(jobs, "artifact_base", lambda: tmp_path)
    monkeypatch.setattr(worker_mod, "_worker", None)
    # Any accidental use of the settings-driven adapter must fail loudly, not reach 127.0.0.1:8188.
    monkeypatch.setitem(jobs.BACKENDS, BACKEND_NAME, lambda: pytest.fail("real ComfyUI adapter used in a test"))
    yield tmp_path
    # RenderWorker.run() installs the folio witness listener; keep it from leaking into other tests.
    from core.working import witness_listener

    operations.remove_listener(witness_listener)


@pytest.fixture
def fake(monkeypatch) -> FakeComfy:
    comfy = FakeComfy()
    adapter = ComfyUIQwenImage21Adapter(
        "http://comfy.test", transport=httpx.MockTransport(comfy.handler), poll_interval=0.001
    )
    monkeypatch.setitem(jobs.BACKENDS, BACKEND_NAME, lambda: adapter)
    return comfy


def submit(**kwargs: Any) -> dict[str, Any]:
    kwargs.setdefault("prompt", "A lotus on still water")
    return jobs.submit_job(RenderJobRequest(**kwargs))


async def wait_for(predicate, timeout: float = 3.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while not predicate():
        if asyncio.get_running_loop().time() > deadline:
            raise AssertionError("condition not reached")
        await asyncio.sleep(0.005)


# -- presets and graph --------------------------------------------------------


def test_presets_match_contract():
    sizes = {p.id: (p.width, p.height, p.export_width, p.export_height) for p in PRESETS.values()}
    assert sizes == {
        "square-1024": (1024, 1024, 1024, 1024),
        "desktop-19-10": (2432, 1280, 2432, 1280),
        "desktop-19-9": (2432, 1152, 2432, 1152),
        "s25": (1152, 2496, 1080, 2340),
    }
    for preset in PRESETS.values():
        assert preset.width % 32 == preset.height % 32 == 0
        assert set(preset.as_dict()) == {"id", "width", "height", "export_width", "export_height", "label"}


@pytest.mark.parametrize("preset_id", list(PRESETS))
def test_graph_shape_per_preset(preset_id):
    p = PRESETS[preset_id]
    graph = build_graph("Medicine Buddha", p.width, p.height, p.export_width, p.export_height, 7, "pre/fix")
    classes = {node_id: node["class_type"] for node_id, node in graph.items()}
    assert classes == {
        "1": "UNETLoader",
        "2": "CLIPLoader",
        "3": "VAELoader",
        "4": "TextEncodeQwenImage21",
        "5": "QwenImage21Cache",
        "6": "KSamplerSelect",
        "7": "ManualSigmas",
        "8": "SamplerCustom",
        "9": "VAEDecode",
        "10": "SaveImage",
        "11": "EmptyLatentImage",
        **({"12": "ImageScale"} if preset_id == "s25" else {}),
    }
    assert graph["1"]["inputs"]["unet_name"] == UNET_NAME == "qwen_image_2.1_turbo_bf16.safetensors"
    assert graph["2"]["inputs"] == {"clip_name": CLIP_NAME, "type": "qwen_image", "device": "default"}
    assert CLIP_NAME == "qwen3vl_8b_bf16.safetensors"
    assert graph["3"]["inputs"]["vae_name"] == VAE_NAME == "qwen_image_2.1_vae_bf16.safetensors"
    assert graph["4"]["inputs"]["prompt"] == "Medicine Buddha"
    assert graph["6"]["inputs"]["sampler_name"] == "euler"
    assert graph["7"]["inputs"]["sigmas"] == SIGMAS
    assert [float(s) for s in SIGMAS.split(",")] == [
        1.0, 0.978453, 0.95418, 0.926626, 0.89508, 0.845148, 0.704534, 0.414568, 0.0,
    ]  # fmt: skip
    sampler = graph["8"]["inputs"]
    assert sampler["cfg"] == 1.0 and sampler["noise_seed"] == 7 and sampler["latent_image"] == ["11", 0]
    assert graph["11"]["inputs"] == {"width": p.width, "height": p.height, "batch_size": 1}
    assert graph["10"]["inputs"]["filename_prefix"] == "pre/fix"
    if preset_id == "s25":
        assert graph["12"]["inputs"] == {
            "image": ["9", 0],
            "upscale_method": "lanczos",
            "width": 1080,
            "height": 2340,
            "crop": "disabled",
        }
        assert graph["10"]["inputs"]["images"] == ["12", 0]
    else:
        assert graph["10"]["inputs"]["images"] == ["9", 0]


def test_png_dimensions_validates_magic_and_ihdr():
    assert png_dimensions(make_png(320, 64)) == (320, 64)
    with pytest.raises(RenderError, match="invalid PNG"):
        png_dimensions(b"GIF89a" + b"\x00" * 40)
    with pytest.raises(RenderError, match="invalid PNG"):
        png_dimensions(PNG_MAGIC)


# -- request normalization -------------------------------------------------------


def test_seed_draw_vs_record_provenance(monkeypatch):
    monkeypatch.setattr(jobs.secrets, "randbits", lambda bits: 2**bits - 5)
    drawn, drawn_prov = jobs.normalize_request(RenderJobRequest(prompt="x"))
    assert drawn_prov == {"seed": "draw"}
    assert drawn["seed"] == 2**53 - 5 <= MAX_SEED == 2**53 - 1

    recorded, recorded_prov = jobs.normalize_request(RenderJobRequest(prompt="x", seed=123))
    assert recorded_prov == {"seed": "record"}
    assert recorded["seed"] == 123


def test_drawn_seeds_are_javascript_safe_integers():
    for _ in range(200):
        params, provenance = jobs.normalize_request(RenderJobRequest(prompt="x"))
        assert 0 <= params["seed"] < 2**53
        assert provenance == {"seed": "draw"}
    assert jobs.normalize_request(RenderJobRequest(prompt="x", seed=2**53 - 1))[0]["seed"] == 2**53 - 1
    with pytest.raises(ValueError):
        RenderJobRequest(prompt="x", seed=2**53)


def test_normalized_params_echo_request():
    params, _ = jobs.normalize_request(RenderJobRequest(prompt="  Tara  ", preset="s25", seed=1, working_id="w9"))
    assert params == {
        "prompt": "Tara",
        "preset": "s25",
        "width": 1080,
        "height": 2340,
        "generate_width": 1152,
        "generate_height": 2496,
        "seed": 1,
        "backend": BACKEND_NAME,
        "working_id": "w9",
        "purpose": "free",
        "reference_id": None,
    }
    custom, _ = jobs.normalize_request(RenderJobRequest(prompt="x", width=512, height=768, seed=1))
    assert (custom["preset"], custom["width"], custom["height"], custom["generate_width"]) == (None, 512, 768, 512)
    default, _ = jobs.normalize_request(RenderJobRequest(prompt="x", seed=1))
    assert default["preset"] == "square-1024"
    # preset wins over width/height
    both, _ = jobs.normalize_request(RenderJobRequest(prompt="x", preset="desktop-19-9", width=512, height=512))
    assert (both["width"], both["height"]) == (2432, 1152)


def test_submit_creates_queued_render_operation():
    op = submit(seed=5, purpose="witness", working_id="folio-1")
    assert op["kind"] == "render" and op["status"] == "queued"
    assert op["working_id"] == "folio-1"
    assert op["provenance"] == {"seed": "record"}
    assert op["params"]["seed"] == 5 and op["params"]["purpose"] == "witness"


# -- worker -------------------------------------------------------------------


async def test_happy_path_writes_png_sidecar_and_success(fake, tmp_path):
    seen: list[dict[str, Any]] = []
    operations.add_listener(seen.append)
    try:
        op = submit(prompt="Green Tara, dawn light", preset="s25", seed=42)
        fake.complete_on_poll = 2  # pending for two polls, so a queue position is reported
        assert await RenderWorker(timeout_seconds=5).drain() == 1
    finally:
        operations.remove_listener(seen.append)

    done = operations.get_operation(op["id"])
    assert done["status"] == "success", done["error"]
    assert done["elapsed_seconds"] is not None
    result = done["result"]
    rel = f"generated/renders/{op['created_at'][:10]}/{op['id']}.png"
    png = tmp_path / rel
    assert result["artifact_path"] == rel
    assert result["image_url"] == f"/api/v1/render/jobs/{op['id']}/image"
    assert (result["width"], result["height"]) == (1080, 2340)  # measured from the PNG
    assert result["seed"] == 42
    assert result["backend_prompt_id"] == "p1"
    assert result["sha256"] == hashlib.sha256(png.read_bytes()).hexdigest()
    assert png_dimensions(png.read_bytes()) == (1080, 2340)

    sidecar = json.loads(png.with_suffix(".json").read_text(encoding="utf-8"))
    assert sidecar["prompt"] == "Green Tara, dawn light"
    assert sidecar["seed"] == 42 and sidecar["seed_provenance"] == "record"
    assert sidecar["generate"] == {"width": 1152, "height": 2496}
    assert sidecar["export"] == sidecar["measured"] == {"width": 1080, "height": 2340}
    assert sidecar["graph"] == fake.prompts["p1"]["prompt"]
    assert sidecar["history"]["status"]["status_str"] == "success"
    assert sidecar["sha256"] == result["sha256"]

    assert fake.prompts["p1"]["client_id"] == op["id"]
    assert fake.view_params == [{"filename": "vajra render_00001_.png", "subfolder": "vajra-render", "type": "output"}]
    statuses = [(o["status"], (o["result"] or {}).get("queue_position", "-")) for o in seen if o["id"] == op["id"]]
    assert statuses[0] == ("queued", "-") and statuses[-1][0] == "success"
    assert ("running", 0) in statuses


async def test_jobs_run_one_at_a_time_in_created_order(fake):
    first = submit(prompt="first", width=256, height=256, seed=1)
    second = submit(prompt="second", width=256, height=256, seed=2)
    assert await RenderWorker(timeout_seconds=5).drain() == 2
    assert [p["prompt"]["4"]["inputs"]["prompt"] for p in fake.prompts.values()] == ["first", "second"]
    assert fake.max_concurrent == 1
    assert {operations.get_operation(o["id"])["status"] for o in (first, second)} == {"success"}


async def test_node_errors_end_as_error_with_backend_message(fake):
    fake.submit_reply = (
        400,
        {
            "error": {"type": "prompt_outputs_failed_validation", "message": "Prompt outputs failed validation"},
            "node_errors": {
                "1": {
                    "class_type": "UNETLoader",
                    "errors": [{"message": "Value not in list", "details": "unet_name: 'qwen_image_2.1_turbo'"}],
                }
            },
        },
    )
    op = submit(width=256, height=256)
    await RenderWorker(timeout_seconds=5).drain()
    failed = operations.get_operation(op["id"])
    assert failed["status"] == "error"
    assert "HTTP 400" in failed["error"]
    assert "node 1 (UNETLoader): Value not in list" in failed["error"]
    assert "Prompt outputs failed validation" in failed["error"]


async def test_node_errors_on_200_also_fail(fake):
    fake.submit_reply = (200, {"prompt_id": "x", "node_errors": {"8": {"class_type": "SamplerCustom", "errors": []}}})
    op = submit(width=256, height=256)
    await RenderWorker(timeout_seconds=5).drain()
    assert "rejected the graph: node 8 (SamplerCustom)" in operations.get_operation(op["id"])["error"]


async def test_execution_error_in_history_is_reported(fake):
    fake.exec_error = {
        "node_id": "8",
        "node_type": "SamplerCustom",
        "exception_type": "torch.OutOfMemoryError",
        "exception_message": "CUDA out of memory",
    }
    op = submit(width=256, height=256)
    await RenderWorker(timeout_seconds=5).drain()
    failed = operations.get_operation(op["id"])
    assert failed["status"] == "error"
    assert failed["error"] == (
        "ComfyUI execution error in node 8 (SamplerCustom): torch.OutOfMemoryError: CUDA out of memory"
    )
    assert failed["result"] == {"backend_prompt_id": "p1", "queue_position": 0}


async def test_timeout_fails_and_stops_the_backend_job(fake):
    fake.hold = True
    op = submit(width=256, height=256)
    await RenderWorker(timeout_seconds=0.05).drain()
    failed = operations.get_operation(op["id"])
    assert failed["status"] == "error"
    assert "timed out after 0.05 s" in failed["error"]
    assert "backend job interrupted" in failed["error"]
    assert fake.interrupts == ["p1"]


async def test_invalid_png_fails(fake):
    fake.png_bytes = b"<html>not an image</html>"
    op = submit(width=256, height=256)
    await RenderWorker(timeout_seconds=5).drain()
    failed = operations.get_operation(op["id"])
    assert failed["status"] == "error" and "invalid PNG" in failed["error"]


async def test_dimension_mismatch_fails(fake, tmp_path):
    fake.png_size = (512, 512)
    op = submit(width=256, height=256)
    await RenderWorker(timeout_seconds=5).drain()
    failed = operations.get_operation(op["id"])
    assert failed["status"] == "error"
    assert failed["error"] == "expected a 256x256 PNG, backend returned 512x512"
    assert not (tmp_path / "generated").exists()


async def test_unreachable_backend_fails_with_message(fake):
    fake.down = True
    op = submit(width=256, height=256)
    await RenderWorker(timeout_seconds=5).drain()
    failed = operations.get_operation(op["id"])
    assert failed["status"] == "error"
    assert "ComfyUI unreachable at http://comfy.test" in failed["error"]


async def test_cancel_queued_job_never_reaches_backend(fake):
    op = submit(width=256, height=256)
    cancelled = await jobs.cancel_job(op["id"])
    assert cancelled["status"] == "cancelled"
    assert await RenderWorker(timeout_seconds=5).drain() == 0
    assert fake.calls == []
    with pytest.raises(jobs.JobNotCancellable):
        await jobs.cancel_job(op["id"])


async def test_cancel_running_job_interrupts_comfyui(fake):
    fake.hold = True
    op = submit(width=256, height=256)
    worker = RenderWorker(timeout_seconds=30)
    task = asyncio.create_task(worker.drain())

    def submitted() -> bool:
        current = operations.get_operation(op["id"])
        return current["status"] == "running" and bool((current["result"] or {}).get("backend_prompt_id"))

    await wait_for(submitted)
    cancelled = await jobs.cancel_job(op["id"])
    assert cancelled["status"] == "cancelled"
    assert cancelled["result"]["backend_cancel"] == "interrupted"
    assert fake.interrupts == ["p1"]
    assert await asyncio.wait_for(task, 3) == 1
    assert operations.get_operation(op["id"])["status"] == "cancelled"  # worker did not overwrite it


async def test_cancel_pending_backend_job_deletes_it_from_comfy_queue(fake):
    fake.hold = True
    op = submit(width=256, height=256)
    operations.start_operation(op["id"])
    fake.pending.append("p-wait")
    operations.update_operation_result(op["id"], {"backend_prompt_id": "p-wait"})
    cancelled = await jobs.cancel_job(op["id"])
    assert cancelled["result"]["backend_cancel"] == "dequeued"
    assert fake.deleted == ["p-wait"] and fake.interrupts == []


async def test_reattach_after_restart_completes_finished_job(fake):
    op = submit(prompt="survivor", width=256, height=256, seed=9)
    operations.start_operation(op["id"])
    operations.update_operation_result(op["id"], {"backend_prompt_id": "p-old", "queue_position": 0})
    fake.prompts["p-old"] = {"prompt": build_graph("survivor", 256, 256, 256, 256, 9, "x")}
    fake.finish("p-old")

    assert await RenderWorker(timeout_seconds=5).recover() == 1
    done = operations.get_operation(op["id"])
    assert done["status"] == "success", done["error"]
    assert done["result"]["backend_prompt_id"] == "p-old"
    assert ("POST", "/prompt") not in fake.calls  # re-attached, not resubmitted


async def test_reattach_waits_for_still_running_job(fake):
    op = submit(width=256, height=256, seed=3)
    operations.start_operation(op["id"])
    operations.update_operation_result(op["id"], {"backend_prompt_id": "p-live"})
    fake.prompts["p-live"] = {"prompt": build_graph("x", 256, 256, 256, 256, 3, "x")}
    fake.running.append("p-live")
    fake.complete_on_poll = 3

    await RenderWorker(timeout_seconds=5).recover()
    assert operations.get_operation(op["id"])["status"] == "success"


async def test_reattach_failures_are_explicit(fake):
    lost = submit(width=256, height=256)
    operations.start_operation(lost["id"])
    operations.update_operation_result(lost["id"], {"backend_prompt_id": "p-gone"})
    orphan = submit(width=256, height=256)
    operations.start_operation(orphan["id"])

    assert await RenderWorker(timeout_seconds=5).recover() == 2
    lost_op = operations.get_operation(lost["id"])
    assert lost_op["status"] == "error"
    assert "could not re-attach to backend prompt p-gone" in lost_op["error"]
    assert lost_op["result"] == {"backend_prompt_id": "p-gone"}
    orphan_op = operations.get_operation(orphan["id"])
    assert orphan_op["status"] == "error" and "cannot be re-attached" in orphan_op["error"]


async def test_reattach_with_backend_down_fails_explicitly(fake):
    op = submit(width=256, height=256)
    operations.start_operation(op["id"])
    operations.update_operation_result(op["id"], {"backend_prompt_id": "p1"})
    fake.down = True
    await RenderWorker(timeout_seconds=5).recover()
    failed = operations.get_operation(op["id"])
    assert failed["status"] == "error" and "unreachable" in failed["error"]


async def test_run_recovers_then_drains_and_wakes_on_submit(fake):
    worker = worker_mod.get_render_worker()
    worker._timeout_seconds = 5
    queued_before_start = submit(prompt="waiting since before the restart", width=256, height=256)
    task = asyncio.create_task(worker.run())
    try:
        await wait_for(lambda: operations.get_operation(queued_before_start["id"])["status"] == "success")
        later = submit(prompt="submitted while idle", width=256, height=256)  # wake() must pick it up
        await wait_for(lambda: operations.get_operation(later["id"])["status"] == "success")
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


async def test_shutdown_leaves_inflight_job_running_for_reattach(fake):
    fake.hold = True
    op = submit(width=256, height=256)
    task = asyncio.create_task(RenderWorker(timeout_seconds=30).drain())
    await wait_for(lambda: bool((operations.get_operation(op["id"])["result"] or {}).get("backend_prompt_id")))
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert operations.get_operation(op["id"])["status"] == "running"


# -- health -------------------------------------------------------------------


async def test_health_reports_down_backend_without_raising():
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    adapter = ComfyUIQwenImage21Adapter("http://comfy.test/", transport=httpx.MockTransport(refuse))
    report = await adapter.health()
    assert report == {
        "backend": BACKEND_NAME,
        "reachable": False,
        "base_url": "http://comfy.test",
        "detail": "ComfyUI unreachable at http://comfy.test: connection refused",
        "queue_remaining": None,
    }


async def test_health_reports_up_backend(fake):
    fake.running.append("someone-else")
    fake.pending.extend(["a", "b"])
    report = await jobs.get_backend().health()
    assert report["reachable"] is True
    assert report["queue_remaining"] == 3
    assert "ComfyUI 0.3.99" in report["detail"] and "Test GPU" in report["detail"]


# -- API ----------------------------------------------------------------------


@pytest.fixture
def client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from backend.app.api.v1.endpoints.operations import router as operations_router
    from backend.app.api.v1.endpoints.render import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.include_router(operations_router, prefix="/api/v1")
    return TestClient(app)


def test_api_submit_returns_202_and_lists_under_operations(client):
    response = client.post("/api/v1/render/jobs", json={"prompt": "White Tara", "preset": "desktop-19-10"})
    assert response.status_code == 202
    op = response.json()["operation"]
    assert op["kind"] == "render" and op["status"] == "queued"
    assert op["params"]["width"] == 2432 and op["params"]["height"] == 1280
    assert isinstance(op["params"]["seed"], int)
    assert op["provenance"] == {"seed": "draw"}
    listed = client.get("/api/v1/operations", params={"kind": "render"}).json()
    assert [o["id"] for o in listed["operations"]] == [op["id"]]


@pytest.mark.parametrize(
    "body",
    [
        {"prompt": "   "},
        {},
        {"prompt": "x", "width": 300, "height": 256},
        {"prompt": "x", "width": 4096, "height": 256},
        {"prompt": "x", "width": 256},
        {"prompt": "x", "seed": -1},
        {"prompt": "x", "seed": 2**53},
        {"prompt": "x", "seed": 2**63},
        {"prompt": "x", "preset": "a4-poster"},
        {"prompt": "x", "backend": "dall-e"},
        {"prompt": "x", "purpose": "curse"},
    ],
)
def test_api_validation_errors_are_422(client, body):
    assert client.post("/api/v1/render/jobs", json=body).status_code == 422


def test_api_image_404_until_success_then_png(client, fake):
    op = client.post("/api/v1/render/jobs", json={"prompt": "x", "width": 256, "height": 256}).json()["operation"]
    assert client.get(f"/api/v1/render/jobs/{op['id']}/image").status_code == 404
    assert client.get("/api/v1/render/jobs/nope/image").status_code == 404

    asyncio.run(RenderWorker(timeout_seconds=5).drain())
    image = client.get(f"/api/v1/render/jobs/{op['id']}/image")
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/png"
    assert png_dimensions(image.content) == (256, 256)
    done = client.get(f"/api/v1/operations/{op['id']}").json()
    assert done["result"]["image_url"] == f"/api/v1/render/jobs/{op['id']}/image"
    assert hashlib.sha256(image.content).hexdigest() == done["result"]["sha256"]


def test_api_image_refuses_paths_outside_renders_dir(client, tmp_path):
    op = operations.create_operation("render", "forged")
    operations.start_operation(op["id"])
    (tmp_path / "secret.png").write_bytes(make_png(256, 256))
    operations.complete_operation(op["id"], {"artifact_path": "secret.png"})
    assert client.get(f"/api/v1/render/jobs/{op['id']}/image").status_code == 404


def test_api_cancel(client):
    op = client.post("/api/v1/render/jobs", json={"prompt": "x"}).json()["operation"]
    response = client.post(f"/api/v1/render/jobs/{op['id']}/cancel")
    assert response.status_code == 200
    assert response.json()["operation"]["status"] == "cancelled"
    assert client.post(f"/api/v1/render/jobs/{op['id']}/cancel").status_code == 409
    assert client.post("/api/v1/render/jobs/nope/cancel").status_code == 404
    other = operations.create_operation("broadcast", "not a render")
    assert client.post(f"/api/v1/render/jobs/{other['id']}/cancel").status_code == 404


def test_api_presets_and_health(client, fake):
    presets = client.get("/api/v1/render/presets").json()
    assert [p["id"] for p in presets] == ["square-1024", "desktop-19-10", "desktop-19-9", "s25"]
    assert presets[3] == {
        "id": "s25",
        "width": 1152,
        "height": 2496,
        "export_width": 1080,
        "export_height": 2340,
        "label": "Phone S25 (1080 x 2340)",
    }
    health = client.get("/api/v1/render/health").json()
    assert set(health) == {"backend", "reachable", "base_url", "detail", "queue_remaining"}
    assert health["reachable"] is True
    fake.down = True
    down = client.get("/api/v1/render/health")
    assert down.status_code == 200 and down.json()["reachable"] is False


def test_settings_expose_render_config():
    from config.backend_settings import BackendSettings as Settings

    assert Settings.model_fields["RENDER_TIMEOUT_SECONDS"].default == 1800
    assert Settings.model_fields["COMFYUI_BASE_URL"].default == "http://127.0.0.1:8188"


# -- backend execution time (live-render finding, 2026-10-15) ---------------


def test_backend_execution_seconds_from_comfyui_history():
    from backend.core.services.render.worker import backend_execution_seconds

    # Shape and values taken from a real ComfyUI 0.39.0 history entry.
    history = {
        "status": {
            "status_str": "success",
            "messages": [
                ["execution_start", {"prompt_id": "p", "timestamp": 1792051740485}],
                ["execution_cached", {"nodes": [], "prompt_id": "p", "timestamp": 1792051740485}],
                ["execution_success", {"prompt_id": "p", "timestamp": 1792051900318}],
            ],
        }
    }
    assert backend_execution_seconds(history) == 159.833


@pytest.mark.parametrize(
    "history",
    [
        {},
        {"status": {}},
        {"status": {"messages": [["execution_start", {"timestamp": 10}]]}},
        {"status": {"messages": [["execution_start", {"timestamp": 20}], ["execution_success", {"timestamp": 10}]]}},
        {"status": {"messages": ["garbage", ["execution_success"]]}},
    ],
)
def test_backend_execution_seconds_absent_or_malformed(history):
    from backend.core.services.render.worker import backend_execution_seconds

    assert backend_execution_seconds(history) is None
