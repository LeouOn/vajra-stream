"""Gallery API — one view of every real image the system has made.

``GET /gallery`` lists local renders, hosted saves and inline folio witnesses
together, newest first (see backend/core/services/gallery.py for the rules).
The two byte routes below serve the stores that had no route of their own;
local renders keep theirs (``GET /render/jobs/{id}/image``).
"""

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response

from backend.app.api.v1.endpoints import image_generation
from backend.core.services import gallery
from core import working

router = APIRouter(prefix="/gallery", tags=["gallery"])

GallerySource = Literal["local-render", "hosted", "witness"]


@router.get("")
async def list_gallery(
    source: GallerySource | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(48, ge=1, le=200),
) -> dict[str, Any]:
    """``{items, total, offset, limit, counts, skipped}``; ``skipped`` names files that are not images."""
    return gallery.list_gallery(
        hosted_dir=image_generation.hosted_output_dir(),
        workings_dir=working.WORKINGS_DIR,
        source=source,
        offset=offset,
        limit=limit,
    )


@router.get("/hosted/{filename}")
async def get_hosted_image(filename: str) -> FileResponse:
    """A saved hosted image, by its exact ``img_<ts>_<hash>.<ext>`` name (nothing else is served)."""
    try:
        path, checked = gallery.hosted_file(image_generation.hosted_output_dir(), filename)
    except gallery.GalleryNotFound:
        raise HTTPException(status_code=404, detail="image not found") from None
    except gallery.UnreadableImage as exc:
        raise HTTPException(status_code=415, detail=f"not a servable image: {exc}") from None
    return FileResponse(path, media_type=checked.media_type, filename=path.name)


@router.get("/witness/{working_id}/image")
async def get_witness_image(working_id: str) -> Response:
    """The inline hosted witness of a folio, decoded (local witnesses are render jobs)."""
    folio = working.load_working(working_id) if gallery.WORKING_ID.fullmatch(working_id) else None
    if folio is None:
        raise HTTPException(status_code=404, detail="working not found")
    try:
        data, checked = gallery.witness_image(folio)
    except gallery.GalleryNotFound:
        raise HTTPException(status_code=404, detail="this working has no inline witness image") from None
    except gallery.UnreadableImage as exc:
        raise HTTPException(status_code=415, detail=f"not a servable image: {exc}") from None
    return Response(content=data, media_type=checked.media_type)
