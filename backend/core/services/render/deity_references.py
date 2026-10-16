"""Deity -> user thangka reference image (spec Contract W2-1 references, by deity).

A user can upload a thangka they trust (``POST /render/references``) and pin
it to a deity id from ``knowledge/iconography.json``. A witness render for a
folio sealed with that deity then passes the image as ``reference_id``, so the
model is conditioned on a real depiction as well as the curated prompt clause.

The mapping is one small JSON file beside the references themselves:

    generated/renders/references/deity_references.json
    {"green_tara": {"reference_id": "<sha256>", "set_at": "<iso>"}}
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.core.services.render import references
from core import iconography

logger = logging.getLogger(__name__)

MAPPING_FILENAME = "deity_references.json"
_lock = threading.Lock()


class UnknownDeity(LookupError):
    pass


def mapping_path() -> Path:
    return references.references_dir() / MAPPING_FILENAME


def _read() -> dict[str, dict[str, Any]]:
    path = mapping_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logger.warning("deity reference mapping %s is unreadable; treating it as empty", path)
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): v for k, v in data.items() if isinstance(v, dict) and v.get("reference_id")}


def _write(data: dict[str, dict[str, Any]]) -> None:
    path = mapping_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.part")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def _deity_id(deity: str) -> str:
    entry = iconography.lookup(deity)
    if entry is None:
        raise UnknownDeity(f"unknown deity {deity!r}")
    return str(entry["id"])


def all_references() -> dict[str, dict[str, Any]]:
    """Every pinned deity reference (stale entries whose image is gone are included, flagged)."""
    out = {}
    for deity_id, row in _read().items():
        out[deity_id] = {**row, "available": references.find_reference(str(row["reference_id"])) is not None}
    return out


def reference_for(deity: str) -> str | None:
    """The reference id pinned to ``deity`` if its image is still stored, else ``None``."""
    try:
        deity_id = _deity_id(deity)
    except UnknownDeity:
        return None
    row = _read().get(deity_id)
    if not row:
        return None
    ref_id = str(row["reference_id"])
    if references.find_reference(ref_id) is None:
        logger.warning("deity %s: pinned reference %s is no longer stored; rendering without it", deity_id, ref_id)
        return None
    return ref_id


def set_reference(deity: str, reference_id: str) -> dict[str, Any]:
    """Pin an uploaded reference to a deity. Raises :class:`UnknownDeity` or ``references.InvalidReference``."""
    deity_id = _deity_id(deity)
    ref_id = (reference_id or "").strip().lower()
    if not references.is_reference_id(ref_id) or references.find_reference(ref_id) is None:
        raise references.InvalidReference(
            f"unknown reference_id {reference_id!r}; upload it with POST /render/references"
        )
    row = {"reference_id": ref_id, "set_at": datetime.now(timezone.utc).isoformat()}
    with _lock:
        data = _read()
        data[deity_id] = row
        _write(data)
    return {"deity": deity_id, **row}


def clear_reference(deity: str) -> bool:
    """Unpin a deity's reference; ``False`` if none was pinned. The stored image itself is kept."""
    deity_id = _deity_id(deity)
    with _lock:
        data = _read()
        if deity_id not in data:
            return False
        del data[deity_id]
        _write(data)
    return True
