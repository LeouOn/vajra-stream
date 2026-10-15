"""The render worker: one job at a time, in ``created_at`` order, surviving restarts.

The GPU is serial, so a single asyncio task drains queued ``render``
operations. At startup it first re-attaches ``running`` jobs through their
stored ``backend_prompt_id`` (ComfyUI keeps executing while this server
restarts), failing any it cannot find with an explicit error, then drains the
queue. When the task is cancelled (server shutdown) the in-flight operation is
deliberately left ``running`` so the next start can re-attach to it.
"""

from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from backend.core.services.render import jobs, references
from backend.core.services.render.base import (
    BackendJob,
    RenderBackend,
    RenderError,
    RenderSpec,
    RenderTimeout,
    png_dimensions,
)
from core import operations

logger = logging.getLogger(__name__)

IDLE_RECHECK_SECONDS = 30.0


def install_result_listeners() -> None:
    """Register the ledger listeners that deliver finished renders to their consumers.

    Today that is the folio witness writer (``core.working.apply_witness_render``,
    spec Contract W2-2). Installed when the worker starts, before it re-attaches
    or drains anything, so no completion is missed; ``add_listener`` ignores
    duplicates, so calling this again is harmless.
    """
    try:
        from core.working import install_witness_listener

        install_witness_listener()
    except Exception:
        logger.exception("render worker: could not install the witness listener")


class RenderWorker:
    def __init__(self, *, timeout_seconds: float | None = None) -> None:
        self._timeout_seconds = timeout_seconds
        self._loop: asyncio.AbstractEventLoop | None = None
        self._wake: asyncio.Event | None = None
        self.current_op_id: str | None = None

    # -- control -----------------------------------------------------------

    def wake(self) -> None:
        """Tell the worker there is new work (or a cancellation). Safe from any thread."""
        loop, event = self._loop, self._wake
        if loop is None or event is None or loop.is_closed():
            return
        try:
            if asyncio.get_running_loop() is loop:
                event.set()
                return
        except RuntimeError:
            pass
        loop.call_soon_threadsafe(event.set)

    async def run(self) -> None:
        """Recover, then drain forever. Cancel the task to stop."""
        self._loop = asyncio.get_running_loop()
        self._wake = asyncio.Event()
        install_result_listeners()
        try:
            await self.recover()
        except Exception:
            logger.exception("render worker: recovery failed")
        while True:
            try:
                await self.drain()
            except Exception:
                logger.exception("render worker: drain failed")
            try:
                await asyncio.wait_for(self._wake.wait(), IDLE_RECHECK_SECONDS)
            except asyncio.TimeoutError:
                pass
            self._wake.clear()

    async def recover(self) -> int:
        """Re-attach render jobs left ``running`` by a previous process. Returns how many were handled."""
        running = operations.list_operations(kind="render", status="running", limit=500)
        for op in sorted(running, key=lambda o: o["created_at"]):
            prompt_id = (op.get("result") or {}).get("backend_prompt_id")
            if not prompt_id:
                self._fail(
                    op["id"],
                    "server restarted before this job reached the render backend; it cannot be re-attached",
                    None,
                )
                continue
            try:
                backend = jobs.get_backend((op.get("params") or {}).get("backend", jobs.DEFAULT_BACKEND))
                where = await backend.locate(prompt_id)
            except RenderError as exc:
                self._fail(op["id"], f"could not re-attach to backend prompt {prompt_id} after restart: {exc}", None)
                continue
            if where == "unknown":
                self._fail(
                    op["id"],
                    f"could not re-attach to backend prompt {prompt_id} after restart: "
                    "the backend has no record of it (it was probably restarted)",
                    {"backend_prompt_id": prompt_id},
                )
                continue
            logger.info("render %s: re-attaching to %s prompt %s (%s)", op["id"], backend.name, prompt_id, where)
            await self._execute(op, prompt_id)
        return len(running)

    async def drain(self) -> int:
        """Run queued jobs oldest first until none are left. Returns how many were started."""
        count = 0
        while (op := self._next_queued()) is not None:
            try:
                op = operations.start_operation(op["id"])
            except operations.OperationError:
                continue  # cancelled between listing and starting
            count += 1
            await self._execute(op, None)
        return count

    # -- internals ---------------------------------------------------------

    @staticmethod
    def _next_queued() -> dict[str, Any] | None:
        queued = operations.list_operations(kind="render", status="queued", limit=500)
        return min(queued, key=lambda o: o["created_at"]) if queued else None

    @staticmethod
    def _is_running(op_id: str) -> bool:
        op = operations.get_operation(op_id)
        return op is not None and op["status"] == "running"

    @staticmethod
    def _fail(op_id: str, message: str, result: dict[str, Any] | None) -> None:
        logger.warning("render %s failed: %s", op_id, message)
        try:
            operations.fail_operation(op_id, message, result=result or None)
        except operations.OperationError:
            pass  # cancelled meanwhile; the cancellation stands

    def _timeout(self) -> float:
        return self._timeout_seconds if self._timeout_seconds is not None else jobs.render_timeout_seconds()

    @staticmethod
    async def _reference_fields(
        backend: RenderBackend, op: dict[str, Any], reference_id: str, reattach: bool
    ) -> dict[str, Any]:
        """Upload a copy of the job's reference image, or on re-attach reuse the recorded upload."""
        if reattach:
            prior = op.get("result") or {}
            if not prior.get("reference_image"):
                raise RenderError(f"cannot re-attach: the upload of reference {reference_id} was not recorded")
            return {"reference_sha256": prior.get("reference_sha256"), "reference_image": prior["reference_image"]}
        try:
            data, filename = references.load_reference(reference_id)
        except references.InvalidReference as exc:
            raise RenderError(str(exc)) from exc
        uploaded = await backend.upload_reference(data, f"vajra-reference-{filename}")
        return {"reference_sha256": hashlib.sha256(data).hexdigest(), "reference_image": uploaded}

    async def _execute(self, op: dict[str, Any], prompt_id: str | None) -> None:
        op_id = op["id"]
        self.current_op_id = op_id
        result: dict[str, Any] = {"backend_prompt_id": prompt_id} if prompt_id else {}
        backend: RenderBackend | None = None
        try:
            params = op.get("params") or {}
            backend = jobs.get_backend(params.get("backend", jobs.DEFAULT_BACKEND))
            spec = RenderSpec.from_params(op_id, params)
            reference: dict[str, Any] = {}
            if params.get("reference_id"):
                reference = await self._reference_fields(backend, op, params["reference_id"], prompt_id is not None)
                spec = dataclasses.replace(spec, reference_image=reference["reference_image"])
                result.update(reference)
            graph = backend.build_graph(spec)
            if prompt_id is None:
                prompt_id = await backend.submit(spec)
                result = {"backend_prompt_id": prompt_id, "queue_position": None, **reference}
                try:
                    operations.update_operation_result(op_id, result)
                except operations.OperationError:
                    await self._abandon(backend, op_id, prompt_id)  # cancelled while submitting
                    return

            async def on_queue_position(position: int | None) -> None:
                result["queue_position"] = position
                try:
                    operations.update_operation_result(op_id, dict(result))
                except operations.OperationError:
                    pass  # cancelled; the wait loop notices on its next check

            job = await backend.wait(
                prompt_id,
                timeout=self._timeout(),
                on_queue_position=on_queue_position,
                still_wanted=lambda: self._is_running(op_id),
            )
            if job is None or not self._is_running(op_id):
                return  # cancelled; cancel_job already stopped it at the backend
            width, height = png_dimensions(job.image)
            if (width, height) != (spec.export_width, spec.export_height):
                raise RenderError(
                    f"expected a {spec.export_width}x{spec.export_height} PNG, backend returned {width}x{height}"
                )
            final = self._write_artifacts(op, spec, graph, job, backend, (width, height), reference)
            try:
                operations.complete_operation(op_id, final)
            except operations.OperationError:
                logger.info("render %s finished after it was cancelled; artifacts kept", op_id)
        except RenderTimeout as exc:
            message = str(exc)
            if backend is not None and prompt_id:
                message += "; " + await self._abandon(backend, op_id, prompt_id)
            self._fail(op_id, message, result)
        except RenderError as exc:
            self._fail(op_id, str(exc), result)
        except asyncio.CancelledError:
            raise  # shutdown: leave the op running so the next start re-attaches
        except Exception as exc:
            logger.exception("render %s: unexpected failure", op_id)
            self._fail(op_id, f"unexpected render failure: {type(exc).__name__}: {exc}", result)
        finally:
            self.current_op_id = None

    @staticmethod
    async def _abandon(backend: RenderBackend, op_id: str, prompt_id: str) -> str:
        """Best-effort stop of a backend job nobody is waiting for any more."""
        try:
            action = await backend.cancel(prompt_id)
        except RenderError as exc:
            logger.warning("render %s: could not stop backend prompt %s: %s", op_id, prompt_id, exc)
            return f"stopping it at the backend failed: {exc}"
        return f"backend job {action}"

    @staticmethod
    def _write_artifacts(
        op: dict[str, Any],
        spec: RenderSpec,
        graph: dict[str, Any],
        job: BackendJob,
        backend: RenderBackend,
        measured: tuple[int, int],
        reference: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        rel = jobs.artifact_relpath(op)
        png_path = jobs.artifact_base() / rel
        png_path.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(job.image).hexdigest()
        params = op.get("params") or {}
        tmp = png_path.with_suffix(".png.part")
        tmp.write_bytes(job.image)
        os.replace(tmp, png_path)
        sidecar_rel = rel.with_suffix(".json")
        sidecar = {
            "operation_id": op["id"],
            "backend": backend.name,
            "base_url": backend.base_url,
            "backend_prompt_id": job.prompt_id,
            "prompt": spec.prompt,
            "seed": spec.seed,
            "seed_provenance": (op.get("provenance") or {}).get("seed"),
            "preset": params.get("preset"),
            "purpose": params.get("purpose"),
            "working_id": params.get("working_id"),
            "caption_facts": params.get("caption_facts") or [],
            "generate": {"width": spec.width, "height": spec.height},
            "export": {"width": spec.export_width, "height": spec.export_height},
            "measured": {"width": measured[0], "height": measured[1]},
            "reference": (
                {
                    "reference_id": params.get("reference_id"),
                    "sha256": reference.get("reference_sha256"),
                    "backend_image": reference.get("reference_image"),
                }
                if reference
                else None
            ),
            "sha256": digest,
            "bytes": len(job.image),
            "image": str(rel),
            "created_at": op.get("created_at"),
            "started_at": op.get("started_at"),
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "graph": graph,
            "history": job.history,
        }
        (jobs.artifact_base() / sidecar_rel).write_text(
            json.dumps(sidecar, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        final: dict[str, Any] = {
            "backend_prompt_id": job.prompt_id,
            "image_url": f"/api/v1/render/jobs/{op['id']}/image",
            "width": measured[0],
            "height": measured[1],
            "seed": spec.seed,
            "sha256": digest,
            "artifact_path": str(rel),
            "sidecar_path": str(sidecar_rel),
        }
        execution = backend_execution_seconds(job.history)
        if execution is not None:
            final["backend_execution_seconds"] = execution
        if reference:
            final["reference_sha256"] = reference.get("reference_sha256")
        return final


def backend_execution_seconds(history: dict[str, Any]) -> float | None:
    """Seconds the backend itself spent executing the job, from its own timestamps.

    The ledger's ``elapsed_seconds`` is wall clock from our start to our
    completion record, so it also counts queue waiting and, after a restart
    re-attach, the time the server was down. ComfyUI's history carries
    ``execution_start``/``execution_success`` timestamps (ms) in
    ``status.messages``; their difference is the render itself. ``None``
    when the backend did not report them.
    """
    messages = (history.get("status") or {}).get("messages") or []
    stamps: dict[str, float] = {}
    for message in messages:
        if isinstance(message, list | tuple) and len(message) == 2 and isinstance(message[1], dict):
            stamp = message[1].get("timestamp")
            if isinstance(stamp, int | float):
                stamps[str(message[0])] = float(stamp)
    start, end = stamps.get("execution_start"), stamps.get("execution_success")
    if start is None or end is None or end < start:
        return None
    return round((end - start) / 1000.0, 3)


_worker: RenderWorker | None = None


def get_render_worker() -> RenderWorker:
    """The process-wide worker (started by ``backend/app/main.py`` warmup)."""
    global _worker
    if _worker is None:
        _worker = RenderWorker()
    return _worker
