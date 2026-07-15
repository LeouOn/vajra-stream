"""Knowledge Index (RAG) Endpoints.

Upload documents, search the indexed knowledge base, and inspect index status.
Backed by :class:`core.knowledge_index.KnowledgeIndex` — a lightweight
character-ngram RAG that requires no external vector database.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from core.knowledge_index import get_knowledge_index

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

_ALLOWED_TEXT_EXTS = {".txt", ".md", ".markdown", ".json"}
_MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MiB


def _extension(filename: str | None) -> str:
    if not filename:
        return ""
    dot = filename.rfind(".")
    return filename[dot:].lower() if dot >= 0 else ""


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    category: str = Query(default="document", description="Chunk category label"),
) -> dict[str, Any]:
    """Upload a text/markdown/json document and index it for RAG search.

    Accepted extensions: ``.txt``, ``.md``, ``.markdown``, ``.json``.
    Max size 5 MiB. JSON files are indexed one chunk per top-level entry when
    possible (via the upload chunker), otherwise treated as plain text.
    """
    ext = _extension(file.filename)
    if ext not in _ALLOWED_TEXT_EXTS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{ext}'. Allowed: {sorted(_ALLOWED_TEXT_EXTS)}",
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(raw) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(raw)} bytes). Max {_MAX_UPLOAD_BYTES} bytes.",
        )

    try:
        text = raw.decode("utf-8", errors="replace")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Could not decode as UTF-8: {exc}") from exc

    source = f"upload:{file.filename or 'unnamed'}"
    idx = get_knowledge_index()

    metadata = {"filename": file.filename or "unnamed", "content_type": file.content_type or ""}

    try:
        if ext == ".json":
            chunk_count = _index_json_upload(idx, text, source, category, metadata)
        else:
            chunk_count = idx.add_document(
                text, source=source, category=category, metadata=metadata
            )
    except Exception as exc:
        logger.exception("knowledge upload indexing failed")
        raise HTTPException(status_code=500, detail=f"Indexing failed: {exc}") from exc

    return {
        "status": "success",
        "filename": file.filename,
        "category": category,
        "chunks_added": chunk_count,
        "total_chunks": len(idx.chunks),
    }


def _index_json_upload(
    idx, text: str, source: str, category: str, metadata: dict[str, Any]
) -> int:
    """Index a JSON upload.

    If the payload is a list of objects or a dict of objects, each entry
    becomes its own chunk (preserving structure). Otherwise, fall back to
    treating the raw JSON text as a single document.
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return idx.add_document(text, source=source, category=category, metadata=metadata)

    if isinstance(data, list) and data and isinstance(data[0], dict):
        total = 0
        for i, entry in enumerate(data):
            if not isinstance(entry, dict):
                continue
            chunk_text = json.dumps(entry, ensure_ascii=False)
            total += idx.add_document(
                chunk_text,
                source=f"{source}#{i}",
                category=category,
                metadata={**metadata, "index": i},
            )
        return total
    if isinstance(data, dict) and data:
        return idx.add_document(
            json.dumps(data, ensure_ascii=False, indent=2),
            source=source,
            category=category,
            metadata=metadata,
        )
    return idx.add_document(text, source=source, category=category, metadata=metadata)


@router.get("/search")
async def search_knowledge(
    q: str = Query(..., min_length=1, description="Natural language query"),
    top_k: int = Query(default=5, ge=1, le=50),
    category: str | None = Query(default=None, description="Filter by category"),
) -> dict[str, Any]:
    """Search the knowledge index for chunks relevant to ``q``."""
    idx = get_knowledge_index()
    results = idx.search(q, top_k=top_k, category=category)
    return {
        "query": q,
        "category": category,
        "count": len(results),
        "results": results,
    }


@router.get("/status")
async def index_status() -> dict[str, Any]:
    """Return knowledge index statistics and per-source chunk counts."""
    idx = get_knowledge_index()
    stats = idx.get_stats()

    sources: dict[str, int] = {}
    categories: dict[str, int] = {}
    for chunk in idx.chunks:
        sources[chunk.source] = sources.get(chunk.source, 0) + 1
        categories[chunk.category] = categories.get(chunk.category, 0) + 1

    return {
        "total_chunks": len(idx.chunks),
        "built": stats.get("built", idx._built),
        "categories": categories,
        "sources": sources,
        "source_count": len(sources),
    }
