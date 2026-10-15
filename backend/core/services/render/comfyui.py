"""ComfyUI + Qwen-Image 2.1 Turbo render backend.

The graph is a port of ``build_graph`` from the DataForge garden harness
(``athena-generator/src/local_render.py``, 156 successful renders): the same
node types, model files, eight official sigmas, CFG 1 and euler sampler, with
Lanczos scaling when the export size differs from the generated size.

HTTP surface used (ComfyUI's own API, nothing added):

* ``POST /prompt`` ``{"prompt": graph, "client_id": job_id}`` -> ``prompt_id``
* ``GET /history/<prompt_id>`` until the entry appears
* ``GET /view?filename=..&subfolder=..&type=..`` for the PNG
* ``GET /queue`` for position, re-attach and cancel targeting
* ``POST /interrupt`` ``{"prompt_id": ..}`` (executing) / ``POST /queue`` ``{"delete": [..]}`` (pending)
* ``GET /system_stats`` for health
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import httpx

from backend.core.services.render.base import (
    BackendJob,
    QueueCallback,
    RenderError,
    RenderSpec,
    RenderTimeout,
    StillWanted,
)

BACKEND_NAME = "comfyui-qwen-image-2.1"
OUTPUT_NODE = "10"
SIGMAS = "1.0, 0.978453, 0.95418, 0.926626, 0.89508, 0.845148, 0.704534, 0.414568, 0.0"
UNET_NAME = "qwen_image_2.1_turbo_bf16.safetensors"
CLIP_NAME = "qwen3vl_8b_bf16.safetensors"
VAE_NAME = "qwen_image_2.1_vae_bf16.safetensors"


class BackendUnavailable(RenderError):
    """The backend could not be reached (connection refused, timeout). May be transient while polling."""


def build_graph(
    prompt: str,
    width: int,
    height: int,
    export_width: int,
    export_height: int,
    seed: int,
    prefix: str,
) -> dict[str, Any]:
    """ComfyUI API-format graph for one Qwen-Image 2.1 Turbo render."""
    graph: dict[str, Any] = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": UNET_NAME, "weight_dtype": "default"}},
        "2": {
            "class_type": "CLIPLoader",
            "inputs": {"clip_name": CLIP_NAME, "type": "qwen_image", "device": "default"},
        },
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": VAE_NAME}},
        "4": {
            "class_type": "TextEncodeQwenImage21",
            "inputs": {"clip": ["2", 0], "prompt": prompt, "negative_prompt": "", "resolution": 1024},
        },
        "5": {"class_type": "QwenImage21Cache", "inputs": {"model": ["1", 0], "device": "auto", "dtype": "default"}},
        "6": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "7": {"class_type": "ManualSigmas", "inputs": {"sigmas": SIGMAS}},
        "8": {
            "class_type": "SamplerCustom",
            "inputs": {
                "model": ["5", 0],
                "add_noise": True,
                "noise_seed": seed,
                "cfg": 1.0,
                "positive": ["4", 0],
                "negative": ["4", 1],
                "sampler": ["6", 0],
                "sigmas": ["7", 0],
                "latent_image": ["11", 0],
            },
        },
        "9": {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["3", 0]}},
        OUTPUT_NODE: {"class_type": "SaveImage", "inputs": {"images": ["9", 0], "filename_prefix": prefix}},
        "11": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
    }
    if (width, height) != (export_width, export_height):
        graph["12"] = {
            "class_type": "ImageScale",
            "inputs": {
                "image": ["9", 0],
                "upscale_method": "lanczos",
                "width": export_width,
                "height": export_height,
                "crop": "disabled",
            },
        }
        graph[OUTPUT_NODE]["inputs"]["images"] = ["12", 0]
    return graph


def format_node_errors(node_errors: dict[str, Any]) -> str:
    """Flatten ComfyUI's ``node_errors`` into one readable line per node."""
    parts = []
    for node_id, info in node_errors.items():
        if not isinstance(info, dict):
            parts.append(f"node {node_id}: {info}")
            continue
        messages = []
        for err in info.get("errors") or []:
            if isinstance(err, dict):
                text = err.get("message") or err.get("type") or json.dumps(err)
                if err.get("details"):
                    text += f" ({err['details']})"
                messages.append(text)
            else:
                messages.append(str(err))
        parts.append(f"node {node_id} ({info.get('class_type', '?')}): {'; '.join(messages) or json.dumps(info)}")
    return " | ".join(parts)


def _describe_error_body(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text[:1000] or response.reason_phrase
    if not isinstance(body, dict):
        return json.dumps(body)[:1000]
    parts = []
    error = body.get("error")
    if isinstance(error, dict):
        parts.append(": ".join(str(error[k]) for k in ("message", "details") if error.get(k)) or json.dumps(error))
    elif error:
        parts.append(str(error))
    if body.get("node_errors"):
        parts.append(format_node_errors(body["node_errors"]))
    return " - ".join(parts) or json.dumps(body)[:1000]


def describe_status(status: dict[str, Any]) -> str:
    """Turn a failed ``/history`` status into the backend's own explanation."""
    for message in status.get("messages") or []:
        if not (isinstance(message, list | tuple) and len(message) == 2 and isinstance(message[1], dict)):
            continue
        event, data = message
        if event == "execution_error":
            exc = ": ".join(str(data[k]) for k in ("exception_type", "exception_message") if data.get(k))
            return f"ComfyUI execution error in node {data.get('node_id', '?')} ({data.get('node_type', '?')}): {exc}"
        if event == "execution_interrupted":
            return "ComfyUI execution was interrupted"
    return f"ComfyUI reported status {status.get('status_str')!r}: {json.dumps(status)[:1500]}"


class ComfyUIQwenImage21Adapter:
    """:class:`~backend.core.services.render.base.RenderBackend` for a local ComfyUI."""

    name = BACKEND_NAME

    def __init__(
        self,
        base_url: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        request_timeout: float = 30.0,
        health_timeout: float = 5.0,
        poll_interval: float = 1.0,
        max_poll_failures: int = 3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._transport = transport
        self._request_timeout = request_timeout
        self._health_timeout = health_timeout
        self.poll_interval = poll_interval
        self.max_poll_failures = max_poll_failures

    # -- graph -------------------------------------------------------------

    def build_graph(self, spec: RenderSpec) -> dict[str, Any]:
        return build_graph(
            spec.prompt,
            spec.width,
            spec.height,
            spec.export_width,
            spec.export_height,
            spec.seed,
            prefix=f"vajra-render/{spec.job_id}",
        )

    # -- HTTP plumbing -----------------------------------------------------

    def _client(self, timeout: float | None = None) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            transport=self._transport,
            timeout=timeout or self._request_timeout,
        )

    async def _request(self, client: httpx.AsyncClient, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            response = await client.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            raise BackendUnavailable(f"ComfyUI at {self.base_url} timed out on {method} {path}") from exc
        except httpx.HTTPError as exc:
            raise BackendUnavailable(f"ComfyUI unreachable at {self.base_url}: {exc or type(exc).__name__}") from exc
        if response.status_code != 200:
            raise RenderError(
                f"ComfyUI HTTP {response.status_code} on {method} {path}: {_describe_error_body(response)}"
            )
        return response

    async def _json(self, client: httpx.AsyncClient, method: str, path: str, **kwargs: Any) -> Any:
        response = await self._request(client, method, path, **kwargs)
        try:
            return response.json()
        except ValueError as exc:
            raise RenderError(f"ComfyUI returned non-JSON for {method} {path}: {response.text[:300]!r}") from exc

    @staticmethod
    def _queue_lists(queue: dict[str, Any]) -> tuple[list[Any], list[Any]]:
        running = [item for item in queue.get("queue_running") or [] if isinstance(item, list) and len(item) > 1]
        pending = [item for item in queue.get("queue_pending") or [] if isinstance(item, list) and len(item) > 1]
        pending.sort(key=lambda item: item[0])
        return running, pending

    async def _queue_state(self, client: httpx.AsyncClient, prompt_id: str) -> tuple[str, int | None]:
        """``("running", 0)``, ``("pending", n)`` (1-based) or ``("absent", None)``."""
        running, pending = self._queue_lists(await self._json(client, "GET", "/queue"))
        if any(item[1] == prompt_id for item in running):
            return "running", 0
        for index, item in enumerate(pending, start=1):
            if item[1] == prompt_id:
                return "pending", index
        return "absent", None

    # -- RenderBackend -----------------------------------------------------

    async def submit(self, spec: RenderSpec) -> str:
        async with self._client() as client:
            body = await self._json(
                client, "POST", "/prompt", json={"prompt": self.build_graph(spec), "client_id": spec.job_id}
            )
        if not isinstance(body, dict):
            raise RenderError(f"ComfyUI /prompt returned {json.dumps(body)[:500]}")
        if body.get("node_errors"):
            raise RenderError(f"ComfyUI rejected the graph: {format_node_errors(body['node_errors'])}")
        prompt_id = body.get("prompt_id")
        if not prompt_id:
            raise RenderError(f"ComfyUI /prompt returned no prompt_id: {json.dumps(body)[:500]}")
        return str(prompt_id)

    async def locate(self, prompt_id: str) -> str:
        async with self._client() as client:
            history = await self._json(client, "GET", f"/history/{prompt_id}")
            if isinstance(history, dict) and prompt_id in history:
                return "done"
            where, _ = await self._queue_state(client, prompt_id)
        return "unknown" if where == "absent" else "pending"

    async def wait(
        self,
        prompt_id: str,
        *,
        timeout: float,
        on_queue_position: QueueCallback | None = None,
        still_wanted: StillWanted | None = None,
    ) -> BackendJob | None:
        deadline = time.monotonic() + timeout
        last_position: object = object()
        failures = 0
        async with self._client() as client:
            while True:
                if still_wanted is not None and not still_wanted():
                    return None
                try:
                    history = await self._json(client, "GET", f"/history/{prompt_id}")
                    entry = history.get(prompt_id) if isinstance(history, dict) else None
                    if entry:
                        return await self._collect(client, prompt_id, entry)
                    if on_queue_position is not None:
                        _, position = await self._queue_state(client, prompt_id)
                        if position != last_position:
                            last_position = position
                            await on_queue_position(position)
                    failures = 0
                except BackendUnavailable:
                    failures += 1
                    if failures >= self.max_poll_failures:
                        raise
                if time.monotonic() >= deadline:
                    raise RenderTimeout(
                        f"timed out after {timeout:g} s waiting for ComfyUI prompt {prompt_id} "
                        "(it may still be queued or running in ComfyUI)"
                    )
                await asyncio.sleep(self.poll_interval)

    async def _collect(self, client: httpx.AsyncClient, prompt_id: str, entry: dict[str, Any]) -> BackendJob:
        status = entry.get("status") or {}
        if status.get("status_str") != "success":
            raise RenderError(describe_status(status))
        images = ((entry.get("outputs") or {}).get(OUTPUT_NODE) or {}).get("images") or []
        if not images:
            raise RenderError("ComfyUI completed without a saved image")
        saved = images[0]
        params = {key: saved.get(key, "") for key in ("filename", "subfolder", "type")}
        response = await self._request(client, "GET", "/view", params=params)
        return BackendJob(prompt_id=prompt_id, image=response.content, history=entry)

    async def cancel(self, prompt_id: str) -> str:
        """Interrupt the prompt if it is executing, delete it if pending. Other clients' jobs are untouched."""
        async with self._client() as client:
            where, _ = await self._queue_state(client, prompt_id)
            if where == "running":
                await self._request(client, "POST", "/interrupt", json={"prompt_id": prompt_id})
                return "interrupted"
            if where == "pending":
                await self._request(client, "POST", "/queue", json={"delete": [prompt_id]})
                return "dequeued"
        return "not-found"

    async def health(self) -> dict[str, Any]:
        report: dict[str, Any] = {
            "backend": self.name,
            "reachable": False,
            "base_url": self.base_url,
            "detail": "",
            "queue_remaining": None,
        }
        try:
            async with self._client(self._health_timeout) as client:
                stats = await self._json(client, "GET", "/system_stats")
                running, pending = self._queue_lists(await self._json(client, "GET", "/queue"))
        except Exception as exc:  # health must never raise
            report["detail"] = str(exc) or type(exc).__name__
            return report
        report["reachable"] = True
        report["queue_remaining"] = len(running) + len(pending)
        report["detail"] = _describe_stats(stats)
        return report


def _describe_stats(stats: Any) -> str:
    if not isinstance(stats, dict):
        return "ComfyUI reachable"
    system = stats.get("system") or {}
    parts = [f"ComfyUI {system.get('comfyui_version', '?')}"]
    for device in stats.get("devices") or []:
        if not isinstance(device, dict):
            continue
        text = str(device.get("name") or device.get("type") or "device")
        total, free = device.get("vram_total"), device.get("vram_free")
        if isinstance(total, int | float) and isinstance(free, int | float) and total:
            text += f", VRAM free {free / 2**30:.1f}/{total / 2**30:.1f} GiB"
        parts.append(text)
    return "; ".join(parts)
