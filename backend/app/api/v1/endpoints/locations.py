"""
Astrology Locations API — CRUD endpoints for the ``astrology_locations`` table.

Exposes REST endpoints to list, fetch, create, update, delete, and seed a
small library of named locations used by the batch extraction tool
(sacred sites + astrocartography anchor cities + user-defined "custom"
locations).

The table is defined centrally in :mod:`core.schema` (Task 1 of the
astrology-extraction sweep). This module is the only place that talks to
the table from the API side; the seed loader is idempotent — it loads
``data/astrology_locations.json`` only when the table is empty.
"""

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.config import settings

router = APIRouter()


# ---------------------------------------------------------------------------
# Project root + DB connection helpers (mirrors the pattern in outlook.py)
# ---------------------------------------------------------------------------


def _get_project_root() -> Path:
    """Locate the project root (directory holding ``pyproject.toml``).

    Walks up from this file's location. Falls back to the closest directory
    containing a ``vajra_stream.db`` if no ``pyproject.toml`` is found.
    """
    current = Path(__file__).resolve()
    for parent in [current, *current.parents]:
        if (parent / "pyproject.toml").is_file():
            return parent
    for parent in [current, *current.parents]:
        if (parent / "vajra_stream.db").is_file():
            return parent
    return current.parent


def get_db_connection():
    """Open a SQLite connection to the project DB with row-dict access."""
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    if not os.path.isabs(db_path):
        db_path = str((_get_project_root() / db_path).resolve())
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Delegate to the central schema runner (``core.schema.init_db``)."""
    from core.schema import init_db as _core_init_db  # noqa: WPS433

    _core_init_db()


# Initialize the DB on module load (idempotent — see core/schema.py).
try:
    init_db()
except Exception as exc:  # noqa: BLE001
    print(f"Error initializing astrology_locations database: {exc}")


# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------

CATEGORY_PATTERN = r"^(sacred_site|astrocartography_anchor|custom)$"


class LocationCreate(BaseModel):
    """Body for ``POST /astrology/locations``."""

    name: str = Field(..., min_length=1, description="Display name of the location")
    lat: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    lon: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")
    category: str = Field(..., pattern=CATEGORY_PATTERN, description="Category bucket")
    timezone: str = Field(default="UTC", description="IANA timezone name")
    tags: list[str] = Field(default_factory=list, description="Free-form tag list")
    notes: str = Field(default="", description="Free-form notes")


class LocationUpdate(BaseModel):
    """Body for ``PUT /astrology/locations/{id}``.

    All fields are optional — only the ones supplied are updated.
    """

    name: str | None = Field(default=None, min_length=1)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    category: str | None = Field(default=None, pattern=CATEGORY_PATTERN)
    timezone: str | None = None
    tags: list[str] | None = None
    notes: str | None = None


# ---------------------------------------------------------------------------
# Row serialization
# ---------------------------------------------------------------------------


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a ``astrology_locations`` row into a JSON-safe dict.

    The table stores tags as a JSON blob (``tags_json``) — decode it for the
    response. ``created_at`` is returned as the raw ISO string.
    """
    out = dict(row)
    tags_json = out.pop("tags_json", None)
    if tags_json:
        try:
            out["tags"] = json.loads(tags_json)
        except (ValueError, TypeError):
            out["tags"] = []
    else:
        out["tags"] = []
    return out


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", summary="List all astrology locations")
async def list_locations(category: str | None = None):
    """Return every location, optionally filtered by ``?category=``."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if category is not None:
            cursor.execute(
                "SELECT * FROM astrology_locations WHERE category = ? ORDER BY name ASC",
                (category,),
            )
        else:
            cursor.execute("SELECT * FROM astrology_locations ORDER BY name ASC")
        rows = cursor.fetchall()
        conn.close()
        return [_row_to_dict(row) for row in rows]
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{loc_id}", summary="Fetch a single astrology location")
async def get_location(loc_id: int):
    """Return the location with the given integer primary key."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM astrology_locations WHERE id = ?", (loc_id,))
        row = cursor.fetchone()
        conn.close()
        if row is None:
            raise HTTPException(status_code=404, detail=f"Location {loc_id} not found")
        return _row_to_dict(row)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("", status_code=201, summary="Create a new astrology location")
async def create_location(loc: LocationCreate):
    """Insert a new row and return it with the assigned ``id``."""
    try:
        now_str = _now_iso()
        tags_json = json.dumps(loc.tags)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO astrology_locations
                (name, lat, lon, category, timezone, tags_json, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                loc.name,
                loc.lat,
                loc.lon,
                loc.category,
                loc.timezone,
                tags_json,
                loc.notes,
                now_str,
            ),
        )
        new_id = cursor.lastrowid
        conn.commit()
        cursor.execute("SELECT * FROM astrology_locations WHERE id = ?", (new_id,))
        row = cursor.fetchone()
        conn.close()
        return _row_to_dict(row)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put("/{loc_id}", summary="Update an existing astrology location")
async def update_location(loc_id: int, updates: LocationUpdate):
    """Apply a partial update to the row identified by ``loc_id``."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM astrology_locations WHERE id = ?", (loc_id,))
        existing = cursor.fetchone()
        if existing is None:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Location {loc_id} not found")

        current = dict(existing)
        payload = updates.model_dump(exclude_unset=True)

        # Decode existing tags_json → list, then re-encode if updated.
        try:
            current["tags"] = json.loads(current.get("tags_json") or "[]")
        except (ValueError, TypeError):
            current["tags"] = []

        merged = {**current, **payload}
        if "tags" in payload and payload["tags"] is not None:
            merged["tags_json"] = json.dumps(payload["tags"])
        else:
            merged["tags_json"] = current.get("tags_json") or json.dumps(current.get("tags", []))

        cursor.execute(
            """
            UPDATE astrology_locations
            SET name = ?, lat = ?, lon = ?, category = ?, timezone = ?,
                tags_json = ?, notes = ?
            WHERE id = ?
            """,
            (
                merged["name"],
                merged["lat"],
                merged["lon"],
                merged["category"],
                merged["timezone"],
                merged["tags_json"],
                merged.get("notes", ""),
                loc_id,
            ),
        )
        conn.commit()
        cursor.execute("SELECT * FROM astrology_locations WHERE id = ?", (loc_id,))
        row = cursor.fetchone()
        conn.close()
        return _row_to_dict(row)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/{loc_id}", summary="Delete an astrology location")
async def delete_location(loc_id: int):
    """Remove the row with the given id. Returns 404 if it doesn't exist."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM astrology_locations WHERE id = ?", (loc_id,))
        if cursor.fetchone() is None:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Location {loc_id} not found")
        cursor.execute("DELETE FROM astrology_locations WHERE id = ?", (loc_id,))
        conn.commit()
        conn.close()
        return {"status": "success", "message": f"Location {loc_id} deleted.", "id": loc_id}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/seed", summary="Seed the location library from data/astrology_locations.json")
async def seed_locations():
    """Load ``data/astrology_locations.json`` if the table is empty.

    Idempotent: returns ``{"status": "skipped"}`` (with the existing row
    count) if the table is already populated. Otherwise inserts every
    entry from the seed file and returns ``{"status": "loaded", "count": N}``.
    """
    try:
        # Resolve data/astrology_locations.json from the project root.
        # locations.py lives at backend/app/api/v1/endpoints/locations.py
        # so we need 6 parents to reach the project root.
        project_root = _get_project_root()
        seed_path = project_root / "data" / "astrology_locations.json"
        if not seed_path.is_file():
            raise HTTPException(
                status_code=500,
                detail=f"Seed file not found: {seed_path}",
            )

        with seed_path.open("r", encoding="utf-8") as fh:
            seed_data = json.load(fh)
        locations = seed_data.get("locations", [])
        if not isinstance(locations, list) or not locations:
            raise HTTPException(
                status_code=500,
                detail="Seed file is malformed: 'locations' must be a non-empty list",
            )

        now_str = _now_iso()
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) AS n FROM astrology_locations")
        existing_count = cursor.fetchone()["n"]
        if existing_count > 0:
            conn.close()
            return {
                "status": "skipped",
                "reason": "table already populated",
                "existing_count": existing_count,
            }

        inserted = 0
        for entry in locations:
            tags = entry.get("tags", []) or []
            cursor.execute(
                """
                INSERT INTO astrology_locations
                    (name, lat, lon, category, timezone, tags_json, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.get("name"),
                    entry.get("lat"),
                    entry.get("lon"),
                    entry.get("category"),
                    entry.get("timezone", "UTC"),
                    json.dumps(tags),
                    entry.get("notes", ""),
                    now_str,
                ),
            )
            inserted += 1
        conn.commit()
        conn.close()
        return {"status": "loaded", "count": inserted}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
