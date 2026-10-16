"""Deity iconography API: the curated data (knowledge/iconography.json) and
the optional user thangka reference pinned to each deity.

- ``GET /iconography`` -- every deity with its forms, sources and pinned reference
- ``GET /iconography/{deity}`` -- one entry, its prompt clause and caption facts
- ``PUT /iconography/{deity}/reference`` -- pin an uploaded reference (``POST /render/references``)
- ``DELETE /iconography/{deity}/reference`` -- unpin it (the image itself is kept)
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.core.services.render import deity_references, references
from core import iconography

router = APIRouter(prefix="/iconography", tags=["iconography"])


class DeityReferenceRequest(BaseModel):
    reference_id: str = Field(..., min_length=64, max_length=64, description="sha256 from POST /render/references")


@router.get("")
async def list_deities() -> dict[str, Any]:
    pinned = deity_references.all_references()
    return {"deities": [{**row, "reference": pinned.get(row["id"])} for row in iconography.list_deities()]}


@router.get("/{deity}")
async def get_deity(deity: str, form: str | None = None) -> dict[str, Any]:
    ref = iconography.resolve(deity, form)
    if ref is None:
        raise HTTPException(status_code=404, detail=f"unknown deity or form: {deity!r} {form or ''}".strip())
    return {
        "deity": ref.entry,
        "form": ref.form_id,
        "prompt_clause": iconography.ref_prompt_clause(ref),
        "caption_facts": iconography.deity_caption_facts(ref.entry, ref.form),
        "sources": iconography.source_citations(ref.entry),
        "reference_id": deity_references.reference_for(ref.id),
    }


@router.put("/{deity}/reference")
async def pin_reference(deity: str, request: DeityReferenceRequest) -> dict[str, Any]:
    try:
        return deity_references.set_reference(deity, request.reference_id)
    except deity_references.UnknownDeity as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except references.InvalidReference as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@router.delete("/{deity}/reference")
async def unpin_reference(deity: str) -> dict[str, Any]:
    entry = iconography.lookup(deity)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"unknown deity {deity!r}")
    return {"deity": entry["id"], "removed": deity_references.clear_reference(entry["id"])}
