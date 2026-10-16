"""Gallery: one view of every real image the system has made.

Images live in three stores; each item names its ``source``:

``local-render``
    Successful render operations (``core.operations``, ``kind="render"``). The
    bytes are ``generated/renders/YYYY-MM-DD/<op_id>.png``, served by
    ``GET /render/jobs/{id}/image``. Seed, its provenance and the measured size
    come from the ledger record, which mirrors the ``<op_id>.json`` sidecar.
    A witness render with the true sky drawn on (``core/sky_composite.py``)
    is listed as that composite, ``<op_id>.sky.png`` served by
    ``GET /gallery/sky/{id}/image``, with the caption facts of its
    ``<op_id>.sky.json``; the plain scene stays at ``scene_image_url``.
``hosted``
    Hosted-provider saves, ``img_<unix>_<prompthash>.<ext>`` in the image
    output directory, served by ``GET /gallery/hosted/{filename}``. Saves made
    since 2026-10-15 carry an ``img_<...>.json`` sidecar (prompt, provider,
    model, size, sha256); older ones only have their file name.
``witness``
    A folio's hosted witness held inline as ``image_data_url``, served by
    ``GET /gallery/witness/{working_id}/image``. A hosted witness is also saved
    as a hosted file, so when a hosted save holds the same bytes (same size and
    sha256) the folio link is put on that item and no second item is listed.
    A *local* witness is its render operation, which already links the folio.

Only decodable images are listed. A file that is too small, has no PNG / JPEG
/ WebP header, or is visibly truncated is left out and reported in
``skipped`` with the reason, so a broken file never shows as a broken
thumbnail and is never silently lost either.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.core.services.render import jobs, references
from core import operations, sky_composite

logger = logging.getLogger(__name__)

SOURCES = ("local-render", "hosted", "witness")

# Smaller than any real encoded image this system makes; the 15-24 byte test stubs
# that once polluted generated/images fall well below it (and fail the header check).
MIN_IMAGE_BYTES = 64
# Enough of the file to find a JPEG frame header behind EXIF / ICC segments.
HEADER_BYTES = 256 * 1024
_TAIL_BYTES = 64
_PNG_IEND = b"IEND\xaeB`\x82"
_JPEG_EOI = b"\xff\xd9"

# Exactly what ImageGenerationService._save_image writes; nothing else is served.
HOSTED_FILENAME = re.compile(r"^img_(\d{1,12})_([0-9a-f]{8})\.(png|jpg|jpeg|webp)$")
WORKING_ID = re.compile(r"^wrk_[A-Za-z0-9]{1,64}$")
_DATA_URL = re.compile(r"^data:(image/[a-z0-9.+-]+)?(;[^,]*)?;base64,", re.IGNORECASE)

_RENDER_PAGE = 500
_CACHE_LIMIT = 4096


class UnreadableImage(ValueError):
    """Bytes that are not a decodable PNG / JPEG / WebP (the message says why)."""


class GalleryNotFound(LookupError):
    """No servable image under that name."""


@dataclass(frozen=True)
class CheckedImage:
    media_type: str
    width: int
    height: int
    size: int


# -- image checks ------------------------------------------------------------------


def check_image_bytes(head: bytes, tail: bytes, size: int) -> CheckedImage:
    """Validate an image from its first bytes, its last bytes and its total size."""
    if size < MIN_IMAGE_BYTES:
        raise UnreadableImage(f"only {size} bytes, too small to be an image")
    try:
        info = references.sniff_image(head)
    except references.InvalidReference as exc:
        raise UnreadableImage(str(exc)) from None
    if info.ext == "png" and not tail.endswith(_PNG_IEND):
        raise UnreadableImage("PNG is truncated (it does not end with an IEND chunk)")
    if info.ext == "jpg" and _JPEG_EOI not in tail[-_TAIL_BYTES:]:
        raise UnreadableImage("JPEG is truncated (no end-of-image marker)")
    return CheckedImage(info.media_type, info.width, info.height, size)


def check_image_data(data: bytes) -> CheckedImage:
    return check_image_bytes(data[:HEADER_BYTES], data[-_TAIL_BYTES:], len(data))


_file_checks: dict[tuple[str, int, int], CheckedImage | str] = {}
_file_hashes: dict[tuple[str, int, int], str] = {}


def _stat_key(path: Path) -> tuple[str, int, int]:
    st = path.stat()
    return (str(path), st.st_size, st.st_mtime_ns)


def _remember(cache: dict[Any, Any], key: Any, value: Any) -> None:
    if len(cache) >= _CACHE_LIMIT:
        cache.clear()
    cache[key] = value


def check_image_file(path: Path) -> CheckedImage:
    """Validate an image file (cached per path, size and mtime)."""
    key = _stat_key(path)
    cached = _file_checks.get(key)
    if cached is None:
        try:
            with path.open("rb") as fh:
                head = fh.read(HEADER_BYTES)
                if key[1] > len(head):
                    fh.seek(-_TAIL_BYTES, 2)
                    tail = fh.read()
                else:
                    tail = head[-_TAIL_BYTES:]
            cached = check_image_bytes(head, tail, key[1])
        except UnreadableImage as exc:
            cached = str(exc)
        _remember(_file_checks, key, cached)
    if isinstance(cached, str):
        raise UnreadableImage(cached)
    return cached


def _file_sha256(path: Path) -> str:
    key = _stat_key(path)
    digest = _file_hashes.get(key)
    if digest is None:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        _remember(_file_hashes, key, digest)
    return digest


def decode_data_url(data_url: str) -> bytes:
    """The bytes of a base64 ``data:image/...`` URL."""
    match = _DATA_URL.match(data_url)
    if not match:
        raise UnreadableImage("witness is not a base64 data URL")
    try:
        return base64.b64decode(data_url[match.end() :], validate=False)
    except (binascii.Error, ValueError) as exc:
        raise UnreadableImage(f"witness data URL is not valid base64: {exc}") from None


# -- helpers -----------------------------------------------------------------------


def _iso_utc(value: Any) -> str | None:
    if not value:
        return None
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp.astimezone(timezone.utc).isoformat()


def _str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _with_caption_facts(item: dict[str, Any], *records: Any) -> dict[str, Any]:
    """Pass ``caption_facts`` through from the first record that has them."""
    for record in records:
        if isinstance(record, dict) and record.get("caption_facts") is not None:
            item["caption_facts"] = record["caption_facts"]
            break
    return item


def _skip(skipped: list[dict[str, str]], source: str, ref: str, reason: str) -> None:
    skipped.append({"source": source, "ref": ref, "reason": reason})


# -- local renders -----------------------------------------------------------------


def _render_ops() -> list[dict[str, Any]]:
    ops: list[dict[str, Any]] = []
    while True:
        page = operations.list_operations(kind="render", status="success", limit=_RENDER_PAGE, offset=len(ops))
        ops.extend(page)
        if len(page) < _RENDER_PAGE:
            return ops


def collect_renders(skipped: list[dict[str, str]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for op in _render_ops():
        op_id = str(op["id"])
        path = jobs.image_file(op)
        if path is None:
            _skip(skipped, "local-render", op_id, "image file is missing")
            continue
        try:
            checked = check_image_file(path)
        except (UnreadableImage, OSError) as exc:
            _skip(skipped, "local-render", op_id, str(exc))
            continue
        params = op.get("params") or {}
        result = op.get("result") or {}
        provenance = op.get("provenance") or {}
        item = {
            "id": f"render:{op_id}",
            "source": "local-render",
            "created_at": _iso_utc(op.get("finished_at")) or _iso_utc(op.get("created_at")),
            "prompt": _str(params.get("prompt")),
            "width": result.get("width") or checked.width,
            "height": result.get("height") or checked.height,
            "media_type": checked.media_type,
            "bytes": checked.size,
            "image_url": _str(result.get("image_url")) or f"/api/v1/render/jobs/{op_id}/image",
            "purpose": _str(params.get("purpose")),
            "links": {"operation_id": op_id, "working_id": op.get("working_id") or params.get("working_id")},
            "origin": {
                "seed": result.get("seed", params.get("seed")),
                "seed_provenance": provenance.get("seed"),
                "sha256": result.get("sha256"),
                "backend_execution_seconds": result.get("backend_execution_seconds"),
                "elapsed_seconds": op.get("elapsed_seconds"),
                "reference_sha256": result.get("reference_sha256"),
            },
            "settings": {
                "backend": params.get("backend"),
                "preset": params.get("preset"),
                "generate_width": params.get("generate_width"),
                "generate_height": params.get("generate_height"),
                "reference_id": params.get("reference_id"),
            },
        }
        items.append(_with_sky_composite(_with_caption_facts(item, result, params), path, skipped))
    return items


def _with_sky_composite(item: dict[str, Any], scene: Path, skipped: list[dict[str, str]]) -> dict[str, Any]:
    """Show a render's true-sky composite (if it has one) in place of its plain scene."""
    sidecar = sky_composite.read_sidecar(scene)
    if sidecar is None:
        return item
    op_id = item["links"]["operation_id"]
    composite, _ = sky_composite.composite_paths(scene)
    try:
        checked = check_image_file(composite)
    except (UnreadableImage, OSError) as exc:
        _skip(skipped, "local-render", f"{op_id} (sky composite)", str(exc))
        return item
    item.update(
        scene_image_url=item["image_url"],
        image_url=sky_composite.composite_image_url(op_id),
        media_type=checked.media_type,
        bytes=checked.size,
    )
    if isinstance(sidecar.get("caption_facts"), list):
        item["caption_facts"] = sidecar["caption_facts"]
    return item


def sky_composite_file(op_id: str) -> Path:
    """The true-sky composite of a successful render, or :class:`GalleryNotFound`."""
    op = operations.get_operation(op_id)
    scene = jobs.image_file(op) if op is not None else None
    if scene is None or sky_composite.read_sidecar(scene) is None:
        raise GalleryNotFound(op_id)
    composite, _ = sky_composite.composite_paths(scene)
    check_image_file(composite)
    return composite


# -- hosted saves ------------------------------------------------------------------


def _read_sidecar(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def hosted_file(directory: Path, filename: str) -> tuple[Path, CheckedImage]:
    """Resolve a hosted save by exact file name; never leaves ``directory``."""
    if not HOSTED_FILENAME.fullmatch(filename):
        raise GalleryNotFound(filename)
    root = directory.resolve()
    path = (root / filename).resolve()
    if path.parent != root or not path.is_file():
        raise GalleryNotFound(filename)
    return path, check_image_file(path)


def collect_hosted(directory: Path | None, skipped: list[dict[str, str]]) -> list[dict[str, Any]]:
    if directory is None or not directory.is_dir():
        return []
    items: list[dict[str, Any]] = []
    for path in sorted(directory.iterdir()):
        match = HOSTED_FILENAME.fullmatch(path.name)
        if not match or not path.is_file():
            continue
        try:
            checked = check_image_file(path)
        except (UnreadableImage, OSError) as exc:
            _skip(skipped, "hosted", path.name, str(exc))
            continue
        sidecar = _read_sidecar(path.with_suffix(".json")) or {}
        saved_at = datetime.fromtimestamp(int(match.group(1)), tz=timezone.utc).isoformat()
        item = {
            "id": f"hosted:{path.name}",
            "source": "hosted",
            "created_at": _iso_utc(sidecar.get("created_at")) or saved_at,
            "prompt": _str(sidecar.get("prompt")),
            "width": checked.width,
            "height": checked.height,
            "media_type": checked.media_type,
            "bytes": checked.size,
            "image_url": f"/api/v1/gallery/hosted/{path.name}",
            "purpose": None,
            "links": {"operation_id": None, "working_id": None},
            "origin": {
                "provider": _str(sidecar.get("provider")),
                "model": _str(sidecar.get("model")),
                "cost_usd": sidecar.get("cost_usd"),
                "revised_prompt": _str(sidecar.get("revised_prompt")),
                "sha256": _str(sidecar.get("sha256")),
                "sidecar": bool(sidecar),
            },
            "settings": {
                "size": sidecar.get("size"),
                "quality": sidecar.get("quality"),
                "aspect_ratio": sidecar.get("aspect_ratio"),
            },
            "_path": path,
        }
        items.append(_with_caption_facts(item, sidecar))
    return items


# -- folio witnesses ---------------------------------------------------------------

_witness_cache: dict[tuple[str, int, int], dict[str, Any] | None] = {}


def _witness_summary(path: Path) -> dict[str, Any] | None:
    """The inline hosted witness of a folio file, without its payload (cached by mtime)."""
    key = _stat_key(path)
    if key in _witness_cache:
        return _witness_cache[key]
    summary: dict[str, Any] | None = None
    try:
        folio = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        folio = None
    witness = folio.get("witness") if isinstance(folio, dict) else None
    if isinstance(folio, dict) and isinstance(witness, dict) and _str(witness.get("image_data_url")):
        summary = {
            "working_id": _str(folio.get("working_id")) or path.stem,
            "hidden": bool(folio.get("hidden")),
            "sealed_at": folio.get("sealed_at"),
            "created_at": witness.get("created_at"),
            "prompt": _str(witness.get("prompt")),
            "provider": _str(witness.get("provider_used")),
            "model": _str(witness.get("model")),
            "cost_usd": witness.get("cost_usd"),
            "caption_facts": witness.get("caption_facts"),
        }
        try:
            data = decode_data_url(witness["image_data_url"])
            checked = check_image_data(data)
            summary.update(checked=checked, sha256=hashlib.sha256(data).hexdigest())
        except UnreadableImage as exc:
            summary["error"] = str(exc)
    _remember(_witness_cache, key, summary)
    return summary


def witness_image(folio: dict[str, Any]) -> tuple[bytes, CheckedImage]:
    """Bytes of a folio's inline hosted witness."""
    witness = folio.get("witness")
    data_url = witness.get("image_data_url") if isinstance(witness, dict) else None
    if not isinstance(data_url, str) or not data_url:
        raise GalleryNotFound(str(folio.get("working_id")))
    data = decode_data_url(data_url)
    return data, check_image_data(data)


def _same_bytes(item: dict[str, Any], size: int, sha256: str) -> bool:
    if item["bytes"] != size:
        return False
    known = item["origin"].get("sha256")
    if known:
        return bool(known == sha256)
    try:
        return _file_sha256(item["_path"]) == sha256
    except OSError:
        return False


def collect_witnesses(
    workings_dir: Path, hosted: list[dict[str, Any]], skipped: list[dict[str, str]]
) -> list[dict[str, Any]]:
    """Inline witnesses with no hosted twin; a twin gets the folio link instead."""
    if not workings_dir.is_dir():
        return []
    by_size: dict[int, list[dict[str, Any]]] = {}
    for item in hosted:
        by_size.setdefault(item["bytes"], []).append(item)
    items: list[dict[str, Any]] = []
    for path in sorted(workings_dir.glob("wrk_*.json")):
        summary = _witness_summary(path)
        if summary is None or summary["hidden"]:
            continue
        wid = summary["working_id"]
        if "error" in summary:
            _skip(skipped, "witness", wid, summary["error"])
            continue
        checked: CheckedImage = summary["checked"]
        twin = next(
            (h for h in by_size.get(checked.size, []) if _same_bytes(h, checked.size, summary["sha256"])),
            None,
        )
        if twin is not None:
            twin["links"]["working_id"] = wid
            twin["purpose"] = "witness"
            twin["prompt"] = twin["prompt"] or summary["prompt"]
            for field in ("provider", "model", "cost_usd"):
                if twin["origin"].get(field) is None:
                    twin["origin"][field] = summary[field]
            continue
        item = {
            "id": f"witness:{wid}",
            "source": "witness",
            "created_at": _iso_utc(summary["created_at"]) or _iso_utc(summary["sealed_at"]),
            "prompt": summary["prompt"],
            "width": checked.width,
            "height": checked.height,
            "media_type": checked.media_type,
            "bytes": checked.size,
            "image_url": f"/api/v1/gallery/witness/{wid}/image",
            "purpose": "witness",
            "links": {"operation_id": None, "working_id": wid},
            "origin": {
                "provider": summary["provider"],
                "model": summary["model"],
                "cost_usd": summary["cost_usd"],
                "sha256": summary["sha256"],
            },
            "settings": {},
        }
        items.append(_with_caption_facts(item, summary))
    return items


# -- listing -----------------------------------------------------------------------


def _sort_key(item: dict[str, Any]) -> tuple[str, str]:
    return (item.get("created_at") or "", item["id"])


def list_gallery(
    *,
    hosted_dir: Path | None,
    workings_dir: Path,
    source: str | None = None,
    offset: int = 0,
    limit: int = 48,
) -> dict[str, Any]:
    """Every image, newest first, paged; ``counts`` cover all sources whatever the filter."""
    if source is not None and source not in SOURCES:
        raise ValueError(f"unknown source {source!r}; choose one of {list(SOURCES)}")
    skipped: list[dict[str, str]] = []
    renders = collect_renders(skipped)
    hosted = collect_hosted(hosted_dir, skipped)
    witnesses = collect_witnesses(workings_dir, hosted, skipped)
    everything = renders + hosted + witnesses
    for item in hosted:
        item.pop("_path", None)
    everything.sort(key=_sort_key, reverse=True)
    counts = {name: sum(1 for item in everything if item["source"] == name) for name in SOURCES}
    chosen = everything if source is None else [item for item in everything if item["source"] == source]
    offset = max(0, offset)
    return {
        "items": chosen[offset : offset + limit],
        "total": len(chosen),
        "offset": offset,
        "limit": limit,
        "counts": counts,
        "skipped": skipped,
    }
