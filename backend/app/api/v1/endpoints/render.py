"""Local render API — render jobs are operations (``kind="render"``).

Contract: docs/specs/2026-10-14-operations-and-local-render.md ("Render contract").
Listing is ``GET /operations?kind=render``; progress arrives over the WebSocket
as ``operation_update``.
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.core.services.render import jobs
from backend.core.services.render.base import PRESETS

router = APIRouter(prefix="/render", tags=["render"])


@router.post("/jobs", status_code=202)
async def submit_render_job(request: jobs.RenderJobRequest) -> dict[str, Any]:
    return {"operation": jobs.submit_job(request)}


@router.get("/jobs/{op_id}/image")
async def get_render_image(op_id: str) -> FileResponse:
    try:
        op = jobs.get_job(op_id)
    except jobs.JobNotFound:
        raise HTTPException(status_code=404, detail="render job not found") from None
    path = jobs.image_file(op)
    if path is None:
        raise HTTPException(status_code=404, detail=f"no image: render job is {op['status']}")
    return FileResponse(path, media_type="image/png", filename=path.name)


@router.post("/jobs/{op_id}/cancel")
async def cancel_render_job(op_id: str) -> dict[str, Any]:
    try:
        op = await jobs.cancel_job(op_id)
    except jobs.JobNotFound:
        raise HTTPException(status_code=404, detail="render job not found") from None
    except jobs.JobNotCancellable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    return {"operation": op}


@router.get("/health")
async def render_health(backend: str = jobs.DEFAULT_BACKEND) -> dict[str, Any]:
    if backend not in jobs.BACKENDS:
        raise HTTPException(status_code=422, detail=f"unknown backend {backend!r}")
    return await jobs.get_backend(backend).health()


@router.get("/presets")
async def list_presets() -> list[dict[str, Any]]:
    return [preset.as_dict() for preset in PRESETS.values()]
