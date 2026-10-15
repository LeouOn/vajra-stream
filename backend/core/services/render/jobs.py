"""Render jobs as operations: request validation, submission, cancellation, artifacts.

A render job *is* an operation (``kind="render"``) in :mod:`core.operations`.
This module turns an API request into normalized operation ``params`` and owns
the paths of the artifacts the worker writes. The worker
(:mod:`backend.core.services.render.worker`) does the actual rendering.
"""

from __future__ import annotations

import logging
import secrets
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.core.services.render.base import (
    MAX_SEED,
    MAX_SIDE,
    MIN_SIDE,
    PRESETS,
    SEED_BITS,
    SIDE_MULTIPLE,
    RenderBackend,
    RenderError,
)
from backend.core.services.render.comfyui import BACKEND_NAME, ComfyUIQwenImage21Adapter
from core import operations
from core.schema import get_project_root

logger = logging.getLogger(__name__)

DEFAULT_BACKEND = BACKEND_NAME
DEFAULT_PRESET = "square-1024"
RENDERS_DIR = PurePosixPath("generated/renders")


# -- backends ----------------------------------------------------------------


def _comfyui_from_settings() -> RenderBackend:
    from backend.app.config import settings

    return ComfyUIQwenImage21Adapter(settings.COMFYUI_BASE_URL)


# Name -> factory. Built fresh per use so a changed setting takes effect; tests swap entries.
BACKENDS: dict[str, Callable[[], RenderBackend]] = {BACKEND_NAME: _comfyui_from_settings}


def get_backend(name: str = DEFAULT_BACKEND) -> RenderBackend:
    try:
        factory = BACKENDS[name]
    except KeyError:
        raise RenderError(f"unknown render backend {name!r}; available: {sorted(BACKENDS)}") from None
    return factory()


def render_timeout_seconds() -> float:
    from backend.app.config import settings

    return float(settings.RENDER_TIMEOUT_SECONDS)


# -- artifacts ---------------------------------------------------------------


def artifact_base() -> Path:
    """Directory that ``artifact_path`` values are relative to (the project root; tests redirect it)."""
    return get_project_root()


def artifact_relpath(op: dict[str, Any]) -> PurePosixPath:
    """``generated/renders/YYYY-MM-DD/<op_id>.png``, dated by the job's (UTC) creation day."""
    return RENDERS_DIR / str(op["created_at"])[:10] / f"{op['id']}.png"


def image_file(op: dict[str, Any]) -> Path | None:
    """The PNG of a successful render job, or ``None`` if there is none (yet)."""
    if op.get("kind") != "render" or op.get("status") != "success":
        return None
    rel = (op.get("result") or {}).get("artifact_path")
    if not rel:
        return None
    renders_root = (artifact_base() / RENDERS_DIR).resolve()
    path = (artifact_base() / str(rel)).resolve()
    if renders_root not in path.parents or not path.is_file():
        return None
    return path


# -- requests ----------------------------------------------------------------


class RenderJobRequest(BaseModel):
    """``POST /render/jobs`` body (docs/specs/2026-10-14-operations-and-local-render.md)."""

    prompt: str = Field(..., max_length=20000)
    preset: str | None = None
    width: int | None = Field(None, ge=MIN_SIDE, le=MAX_SIDE, multiple_of=SIDE_MULTIPLE)
    height: int | None = Field(None, ge=MIN_SIDE, le=MAX_SIDE, multiple_of=SIDE_MULTIPLE)
    seed: int | None = Field(None, ge=0, le=MAX_SEED)
    backend: str = DEFAULT_BACKEND
    working_id: str | None = Field(None, max_length=200)
    purpose: Literal["free", "witness", "sigil"] = "free"

    @field_validator("prompt")
    @classmethod
    def _prompt_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("prompt must not be empty")
        return value

    @field_validator("preset")
    @classmethod
    def _known_preset(cls, value: str | None) -> str | None:
        if value is not None and value not in PRESETS:
            raise ValueError(f"unknown preset {value!r}; choose one of {list(PRESETS)}")
        return value

    @field_validator("backend")
    @classmethod
    def _known_backend(cls, value: str) -> str:
        if value not in BACKENDS:
            raise ValueError(f"unknown backend {value!r}; available: {sorted(BACKENDS)}")
        return value

    @model_validator(mode="after")
    def _size_given_once(self) -> RenderJobRequest:
        if self.preset is None and (self.width is None) != (self.height is None):
            raise ValueError("give both width and height, or a preset")
        return self


def normalize_request(request: RenderJobRequest) -> tuple[dict[str, Any], dict[str, str]]:
    """Return ``(params, provenance)`` for the operation.

    ``params.width``/``height`` are the delivered PNG size; ``generate_*`` is what
    the model renders before export scaling (they differ only for ``s25``).
    """
    if request.preset is not None or request.width is None:
        preset = PRESETS[request.preset or DEFAULT_PRESET]
        preset_id: str | None = preset.id
        gen_w, gen_h, out_w, out_h = preset.width, preset.height, preset.export_width, preset.export_height
    else:
        assert request.height is not None
        preset_id = None
        gen_w = out_w = request.width
        gen_h = out_h = request.height
    if request.seed is None:
        seed, seed_provenance = secrets.randbits(SEED_BITS), "draw"
    else:
        seed, seed_provenance = request.seed, "record"
    params = {
        "prompt": request.prompt,
        "preset": preset_id,
        "width": out_w,
        "height": out_h,
        "generate_width": gen_w,
        "generate_height": gen_h,
        "seed": seed,
        "backend": request.backend,
        "working_id": request.working_id,
        "purpose": request.purpose,
    }
    return params, {"seed": seed_provenance}


def _title(params: dict[str, Any]) -> str:
    size = params["preset"] or f"{params['width']}x{params['height']}"
    prompt = " ".join(params["prompt"].split())
    if len(prompt) > 60:
        prompt = prompt[:59].rstrip() + "…"
    return f"Render {size}: {prompt}"


def submit_job(request: RenderJobRequest) -> dict[str, Any]:
    """Record a queued render operation and nudge the worker. Returns the operation."""
    params, provenance = normalize_request(request)
    op = operations.create_operation(
        "render", _title(params), params=params, provenance=provenance, working_id=request.working_id
    )
    from backend.core.services.render.worker import get_render_worker

    get_render_worker().wake()
    return op


class JobNotFound(LookupError):
    pass


class JobNotCancellable(RuntimeError):
    pass


def get_job(op_id: str) -> dict[str, Any]:
    op = operations.get_operation(op_id)
    if op is None or op["kind"] != "render":
        raise JobNotFound(op_id)
    return op


async def cancel_job(op_id: str) -> dict[str, Any]:
    """queued -> cancelled; running -> stop it at the backend, then cancelled."""
    op = get_job(op_id)
    if op["status"] not in operations.ACTIVE_STATUSES:
        raise JobNotCancellable(f"render job {op_id} is already {op['status']}")
    result = dict(op.get("result") or {})
    prompt_id = result.get("backend_prompt_id")
    if op["status"] == "running" and prompt_id:
        backend_name = (op.get("params") or {}).get("backend", DEFAULT_BACKEND)
        try:
            action = await get_backend(backend_name).cancel(prompt_id)
        except RenderError as exc:
            logger.warning("render %s: backend cancel of %s failed: %s", op_id, prompt_id, exc)
            action = f"failed: {exc}"
        result["backend_cancel"] = action
        try:
            operations.update_operation_result(op_id, result)
        except operations.OperationError:
            pass  # finished meanwhile; cancel_operation below reports it
    try:
        cancelled = operations.cancel_operation(op_id)
    except operations.OperationError as exc:
        raise JobNotCancellable(str(exc)) from exc
    from backend.core.services.render.worker import get_render_worker

    get_render_worker().wake()
    return cancelled
