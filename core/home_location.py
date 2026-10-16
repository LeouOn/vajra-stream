"""The user's home location: where a working is sealed unless it is told otherwise.

A working's witness shows the true sky at ``sealed_at`` (core/sky.py), and the
sky depends on where the observer stands. This module keeps one place, the
"home location", in a small JSON file in the per-user data directory
(``~/.vajra-stream/home_location.json``, like the other per-user stores; the
``VAJRA_HOME_LOCATION_PATH`` environment variable overrides it, which the test
suite uses). It is never written into the repo or the database.

A location is ``{"latitude", "longitude", "label", "source"}``:

* ``latitude`` / ``longitude`` in degrees (east positive), validated to range
  and stored to :data:`STORED_DECIMALS` places (about 11 m; more is noise and
  only makes the record more identifying);
* ``label``: what the user called the place (``"Kathmandu"``), or ``None``;
* ``source``: how it was set (:data:`SOURCES`): the browser's geolocation, typed
  coordinates, or a typed place name geocoded on the server.

Location is personal data. Exact coordinates stay in the stored record and in
the folio JSON; everything shown (caption facts, the sky record on a witness,
the Gallery) goes through :func:`public_coords` / :func:`describe`, which round
to :data:`PUBLIC_DECIMALS` place (about 11 km), and :func:`strip_location_pii`
removes the place from a folio altogether for a "Strip PII" copy. Coordinates
are never logged at info level.

Pure stdlib on purpose: ``core.sky`` and ``core.working`` both import it.
"""

from __future__ import annotations

import copy
import json
import logging
import math
import os
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

#: How a location was set.
SOURCES: tuple[str, ...] = ("browser", "typed", "geocoded")
#: Places kept for stored coordinates (~11 m).
STORED_DECIMALS = 4
#: Places shown anywhere a person can see or share them (~11 km).
PUBLIC_DECIMALS = 1
#: Longest label kept.
LABEL_MAX_CHARS = 120
#: Overrides the store's path (the test suite points it at a temp file).
PATH_ENV_VAR = "VAJRA_HOME_LOCATION_PATH"

_KEYS = ("latitude", "longitude", "label", "source")


def store_path() -> Path:
    """Where the home location is kept (read on every call, so the env override is live)."""
    override = os.environ.get(PATH_ENV_VAR)
    if override:
        return Path(override)
    return Path.home() / ".vajra-stream" / "home_location.json"


def _coordinate(raw: Mapping[str, Any], names: tuple[str, ...], lo: float, hi: float, what: str) -> float:
    value = next((raw.get(k) for k in names if raw.get(k) is not None), None)
    if value is None or isinstance(value, bool):
        raise ValueError(f"{what} is required")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{what} must be a number") from None
    if not math.isfinite(number) or not lo <= number <= hi:
        raise ValueError(f"{what} must be between {lo:g} and {hi:g}")
    return round(number, STORED_DECIMALS)


def normalize_location(raw: Mapping[str, Any], *, default_source: str = "typed") -> dict[str, Any]:
    """A validated ``{latitude, longitude, label, source}``; raises ``ValueError`` if it is not one.

    Accepts ``lat``/``lon``/``lng`` spellings too. ``source`` must be one of
    :data:`SOURCES` (``default_source`` when absent).
    """
    if not isinstance(raw, Mapping):
        raise ValueError("location must be an object with latitude and longitude")
    lat = _coordinate(raw, ("latitude", "lat"), -90.0, 90.0, "latitude")
    lon = _coordinate(raw, ("longitude", "lon", "lng"), -180.0, 180.0, "longitude")
    label_raw = raw.get("label")
    label = " ".join(str(label_raw).split())[:LABEL_MAX_CHARS] if label_raw is not None else ""
    source = raw.get("source") or default_source
    if source not in SOURCES:
        raise ValueError(f"source must be one of {', '.join(SOURCES)}")
    return {"latitude": lat, "longitude": lon, "label": label or None, "source": source}


def get_home_location() -> dict[str, Any] | None:
    """The stored home location, or ``None`` if none is set (or the file is unreadable)."""
    path = store_path()
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        location = normalize_location(data)
    except (OSError, ValueError) as exc:
        logger.warning("ignoring unreadable home location file %s: %s", path, type(exc).__name__)
        return None
    if isinstance(data, dict) and data.get("updated_at"):
        location["updated_at"] = str(data["updated_at"])
    return location


def set_home_location(raw: Mapping[str, Any], *, default_source: str = "typed") -> dict[str, Any]:
    """Validate and store the home location; returns what was stored."""
    location = normalize_location(raw, default_source=default_source)
    location["updated_at"] = datetime.now(timezone.utc).isoformat()
    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    tmp.write_text(json.dumps(location, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, path)
    logger.info("home location set (source=%s)", location["source"])
    return location


def clear_home_location() -> bool:
    """Forget the home location. Returns True if one was stored."""
    path = store_path()
    try:
        path.unlink()
    except FileNotFoundError:
        return False
    logger.info("home location cleared")
    return True


def folio_location(explicit: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """The location a new working is sealed at: ``explicit`` wins, else the home location, else ``None``.

    An explicit location is validated (``ValueError`` if it is not one); its
    ``source`` defaults to ``"typed"``.
    """
    if explicit is not None:
        return normalize_location(explicit)
    home = get_home_location()
    if home is None:
        return None
    return {k: home[k] for k in _KEYS}


# -- what may be shown -----------------------------------------------------------------


def public_coords(lat: float, lon: float) -> tuple[float, float]:
    """Coordinates rounded for display (:data:`PUBLIC_DECIMALS` place)."""
    return round(float(lat), PUBLIC_DECIMALS), round(float(lon), PUBLIC_DECIMALS)


def format_coords(lat: float, lon: float) -> str:
    """``"27.7°, 85.3°"``: rounded, never full precision."""
    plat, plon = public_coords(lat, lon)
    return f"{plat:.{PUBLIC_DECIMALS}f}°, {plon:.{PUBLIC_DECIMALS}f}°"


def describe(location: Mapping[str, Any] | None) -> str:
    """``"Kathmandu (27.7°, 85.3°)"``, or the rounded coordinates alone when there is no label."""
    if not location:
        return "no location"
    lat = location.get("latitude", location.get("lat"))
    lon = location.get("longitude", location.get("lon"))
    label = location.get("label")
    try:
        coords = format_coords(float(lat), float(lon))
    except (TypeError, ValueError):
        return str(label) if label else "unknown location"
    return f"{label} ({coords})" if label else coords


_REDACTED = "[location redacted]"


def strip_location_pii(folio: Mapping[str, Any]) -> dict[str, Any]:
    """A deep copy of a folio with its place removed, for a "Strip PII" copy.

    Drops ``location`` (label and coordinates) and top-level
    ``latitude``/``longitude``, the observer coordinates and local sidereal
    time in any witness sky record (LST encodes longitude), and redacts the
    "Sky observer" caption fact. The sky itself (Moon phase, altitudes) stays.
    """
    out = copy.deepcopy(dict(folio))
    out.pop("location", None)
    out.pop("latitude", None)
    out.pop("longitude", None)
    if isinstance(out.get("provenance"), dict):
        out["provenance"].pop("location", None)
    for key in ("witness", "manifestation"):
        block = out.get(key)
        if not isinstance(block, dict):
            continue
        facts = block.get("caption_facts")
        if isinstance(facts, list):
            block["caption_facts"] = [
                {**f, "value": _REDACTED} if isinstance(f, dict) and f.get("label") == "Sky observer" else f
                for f in facts
            ]
        sky = block.get("sky")
        if isinstance(sky, dict):
            sky.pop("local_sidereal_deg", None)
            if isinstance(sky.get("observer"), dict):
                sky["observer"] = {"source": sky["observer"].get("source"), "redacted": True}
    return out
