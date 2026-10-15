"""Reference images for render jobs (spec Contract W2-1).

A reference is an uploaded PNG, JPEG or WebP that conditions a render
(``RenderJobRequest.reference_id``). Files are content-addressed:

    generated/renders/references/<sha256>.<ext>

so the same image is stored once and its ``reference_id`` *is* its SHA-256.
The stored file is never modified; the adapter uploads a copy to the backend.
The type is decided by decoding the file's own header, never by its name.
"""

from __future__ import annotations

import hashlib
import os
import re
import struct
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from backend.core.services.render.base import PNG_MAGIC

MAX_REFERENCE_BYTES = 20 * 1024 * 1024
REFERENCES_SUBDIR = "references"
_REFERENCE_ID = re.compile(r"^[0-9a-f]{64}$")

MEDIA_TYPES = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp"}

# JPEG start-of-frame markers carry the image size (C4 = DHT, C8 = JPG, CC = DAC are not frames).
_JPEG_SOF = frozenset({0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF})
# Markers without a length field.
_JPEG_STANDALONE = frozenset({0x01, *range(0xD0, 0xD8)})


class InvalidReference(ValueError):
    """The upload is not an acceptable reference image (message is shown to the user)."""


class ReferenceTooLarge(InvalidReference):
    pass


class UnsupportedImage(InvalidReference):
    pass


@dataclass(frozen=True)
class ImageInfo:
    ext: str  # png | jpg | webp
    width: int
    height: int

    @property
    def media_type(self) -> str:
        return MEDIA_TYPES[self.ext]


# -- header decoding -------------------------------------------------------------


def _png_info(data: bytes) -> ImageInfo:
    if len(data) < 24 or data[12:16] != b"IHDR":
        raise UnsupportedImage("PNG is truncated or its first chunk is not IHDR")
    width, height = struct.unpack(">II", data[16:24])
    return ImageInfo("png", width, height)


def _jpeg_info(data: bytes) -> ImageInfo:
    pos, size = 2, len(data)
    while pos < size:
        if data[pos] != 0xFF:
            raise UnsupportedImage("JPEG marker stream is corrupt")
        while pos < size and data[pos] == 0xFF:  # fill bytes
            pos += 1
        if pos >= size:
            break
        marker = data[pos]
        pos += 1
        if marker in _JPEG_STANDALONE:
            continue
        if marker in (0xD9, 0xDA):  # end of image / start of scan before any frame header
            break
        if pos + 2 > size:
            break
        (length,) = struct.unpack(">H", data[pos : pos + 2])
        if length < 2:
            raise UnsupportedImage("JPEG segment length is invalid")
        if marker in _JPEG_SOF:
            if pos + 7 > size:
                break
            height, width = struct.unpack(">HH", data[pos + 3 : pos + 7])
            return ImageInfo("jpg", width, height)
        pos += length
    raise UnsupportedImage("JPEG has no frame header (SOF) before its image data")


def _webp_info(data: bytes) -> ImageInfo:
    if len(data) < 30:
        raise UnsupportedImage("WebP is truncated")
    chunk = data[12:16]
    if chunk == b"VP8 ":
        if data[23:26] != b"\x9d\x01\x2a":
            raise UnsupportedImage("WebP (lossy) frame start code is missing")
        width, height = struct.unpack("<HH", data[26:30])
        return ImageInfo("webp", width & 0x3FFF, height & 0x3FFF)
    if chunk == b"VP8L":
        if data[20] != 0x2F:
            raise UnsupportedImage("WebP (lossless) signature is missing")
        (bits,) = struct.unpack("<I", data[21:25])
        return ImageInfo("webp", (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1)
    if chunk == b"VP8X":
        width = int.from_bytes(data[24:27], "little") + 1
        height = int.from_bytes(data[27:30], "little") + 1
        return ImageInfo("webp", width, height)
    raise UnsupportedImage(f"WebP has an unknown first chunk {chunk!r}")


def sniff_image(data: bytes) -> ImageInfo:
    """Identify PNG / JPEG / WebP from the bytes and read the stored pixel size."""
    if data[:8] == PNG_MAGIC:
        info = _png_info(data)
    elif data[:3] == b"\xff\xd8\xff":
        info = _jpeg_info(data)
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        info = _webp_info(data)
    else:
        raise UnsupportedImage("not a PNG, JPEG or WebP image (checked the file header, not its name)")
    if info.width <= 0 or info.height <= 0:
        raise UnsupportedImage(f"image header reports an invalid size {info.width}x{info.height}")
    return info


# -- storage ---------------------------------------------------------------------


def references_relpath() -> PurePosixPath:
    from backend.core.services.render import jobs

    return jobs.RENDERS_DIR / REFERENCES_SUBDIR


def references_dir() -> Path:
    from backend.core.services.render import jobs

    return jobs.artifact_base() / references_relpath()


def is_reference_id(value: str) -> bool:
    return bool(_REFERENCE_ID.match(value or ""))


def find_reference(reference_id: str) -> Path | None:
    """The stored file for ``reference_id``, or ``None``."""
    if not is_reference_id(reference_id):
        return None
    folder = references_dir()
    for ext in MEDIA_TYPES:
        path = folder / f"{reference_id}.{ext}"
        if path.is_file():
            return path
    return None


def store_reference(data: bytes) -> dict[str, Any]:
    """Validate and store an uploaded image; the same bytes are only ever stored once."""
    if len(data) > MAX_REFERENCE_BYTES:
        raise ReferenceTooLarge(f"reference image is {len(data)} bytes; the limit is {MAX_REFERENCE_BYTES} (20 MB)")
    if not data:
        raise UnsupportedImage("reference image is empty")
    info = sniff_image(data)
    digest = hashlib.sha256(data).hexdigest()
    folder = references_dir()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{digest}.{info.ext}"
    if not path.is_file():
        tmp = path.with_name(f"{path.name}.{os.getpid()}.part")
        tmp.write_bytes(data)
        os.replace(tmp, path)
    return {
        "reference_id": digest,
        "sha256": digest,
        "filename": path.name,
        "width": info.width,
        "height": info.height,
    }


def load_reference(reference_id: str) -> tuple[bytes, str]:
    """``(bytes, stored filename)``; raises :class:`InvalidReference` if missing or altered on disk."""
    path = find_reference(reference_id)
    if path is None:
        raise InvalidReference(f"reference {reference_id} is not stored (upload it again)")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != reference_id:
        raise InvalidReference(f"reference {reference_id} on disk no longer matches its SHA-256")
    return data, path.name
