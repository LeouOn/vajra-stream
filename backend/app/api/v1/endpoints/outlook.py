"""
Outlook API — narrative healing and astrological outlook endpoints.

Exposes REST endpoints for generating personalised healing narratives,
sutra-style blessings, and astrological outlooks for individuals based
on their birth chart, current transits, and divination results.
"""

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.config import settings
from backend.core.services.character_manager import CharacterRole, CharacterSourceType, get_character_manager
from backend.core.services.location_manager import LocationSourceType, LocationType, get_location_manager

# Assume container handles our DI
from container import container

router = APIRouter()


def get_project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists() or (parent / "vajra_stream.db").exists():
            return parent
    return current.parent


class OutlookRequest(BaseModel):
    lat: float = Field(34.0522, description="Latitude of the target location")
    lon: float = Field(-118.2437, description="Longitude of the target location")
    languages: list[str] = Field(default=["English"], description="Target languages to weave into the narrative")
    genre: str = Field(
        default="healing", description="Narrative genre (healing, victory, alchemist, fun_parable, dharani)"
    )
    date: datetime | None = Field(default=None, description="Target time for the astrological chart")
    custom_context: str | None = Field(default=None, description="Custom aspirations or intention text")
    realm_id: str | None = Field(default=None, description="Esoteric location or realm ID")
    population_ids: list[str] | None = Field(default=None, description="Target population IDs receiving the blessing")
    character_ids: list[str] | None = Field(default=None, description="Characters present in the narrative")
    excluded_forces: list[str] | None = Field(default=None, description="Negative forces to pacify")
    include_dialogue: bool = Field(default=False, description="Whether to include active dialogue")
    model: str | None = Field(default=None, description="Selected LLM model for generation")
    randomize_realm: bool = Field(default=False, description="Whether to select a random active setting/realm")
    randomize_characters: bool = Field(default=False, description="Whether to select 2-3 random active characters")


class EpicOutlookRequest(OutlookRequest):
    stages: int = Field(default=9, description="Number of narrative stages to generate")


def get_db_connection():
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    if not os.path.isabs(db_path):
        db_path = str((get_project_root() / db_path).resolve())
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS outlook_narratives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            genre TEXT,
            languages TEXT,
            lat REAL,
            lon REAL,
            date_generated TIMESTAMP,
            content TEXT,
            astrology_context TEXT,
            divination_context TEXT,
            divination_raw TEXT,
            entities_invoked TEXT
        )
    """)
    conn.commit()
    conn.close()


# Initialize DB on endpoint load
try:
    init_db()
except Exception as e:
    print(f"Error initializing outlook database: {e}")


@router.post("/generate_single", summary="Generate a dense, single-pass blessing narrative")
async def generate_single(request: OutlookRequest):
    """
    Generates a dense narrative outlook (300-3000 tokens) that weaves astrological,
    divinatory, and sacred entity contexts into a localized blessing.
    """
    try:
        result = container.outlook.generate_single(
            lat=request.lat,
            lon=request.lon,
            languages=request.languages,
            genre=request.genre,
            date=request.date,
            custom_context=request.custom_context,
            realm_id=request.realm_id,
            population_ids=request.population_ids,
            character_ids=request.character_ids,
            excluded_forces=request.excluded_forces,
            include_dialogue=request.include_dialogue,
            model=request.model,
            randomize_realm=request.randomize_realm,
            randomize_characters=request.randomize_characters
        )

        # Save to database
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO outlook_narratives
                (type, genre, languages, lat, lon, date_generated, content, astrology_context, divination_context, divination_raw, entities_invoked)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    "single",
                    result.get("genre"),
                    json.dumps(result.get("languages")),
                    request.lat,
                    request.lon,
                    (request.date or datetime.now()).isoformat(),
                    result.get("narrative"),
                    result.get("astrology_used"),
                    result.get("divination_used"),
                    json.dumps(result.get("divination_raw")),
                    result.get("entities_used"),
                ),
            )
            conn.commit()
            inserted_id = cursor.lastrowid
            result["id"] = inserted_id
            conn.close()
        except Exception as db_err:
            print(f"Error saving outlook to db: {db_err}")

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate_epic", summary="Generate an epic, multi-stage blessing narrative")
async def generate_epic(request: EpicOutlookRequest):
    """
    Generates a multi-stage epic narrative outlook (9-12 generations) over an extended arc.
    """
    try:
        result = container.outlook.generate_epic(
            lat=request.lat,
            lon=request.lon,
            languages=request.languages,
            genre=request.genre,
            stages=request.stages,
            date=request.date,
            custom_context=request.custom_context,
            realm_id=request.realm_id,
            population_ids=request.population_ids,
            character_ids=request.character_ids,
            excluded_forces=request.excluded_forces,
            include_dialogue=request.include_dialogue,
            model=request.model,
            randomize_realm=request.randomize_realm,
            randomize_characters=request.randomize_characters
        )

        # Save to database
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO outlook_narratives
                (type, genre, languages, lat, lon, date_generated, content, astrology_context, divination_context, divination_raw, entities_invoked)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    "epic",
                    request.genre,
                    json.dumps(request.languages),
                    request.lat,
                    request.lon,
                    (request.date or datetime.now()).isoformat(),
                    json.dumps(result.get("narrative_parts")),
                    result.get("astrology_used"),
                    result.get("divination_used"),
                    json.dumps(result.get("divination_raw")),
                    result.get("entities_used"),
                ),
            )
            conn.commit()
            inserted_id = cursor.lastrowid
            result["id"] = inserted_id
            conn.close()
        except Exception as db_err:
            print(f"Error saving epic outlook to db: {db_err}")

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", summary="Get Outlook Generation History")
async def get_history(limit: int = 20):
    """
    Fetches the history of generated narrative outlooks.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, type, genre, languages, lat, lon, date_generated, content, astrology_context, divination_context, divination_raw, entities_invoked
            FROM outlook_narratives
            ORDER BY date_generated DESC
            LIMIT ?
        """,
            (limit,),
        )
        rows = cursor.fetchall()
        conn.close()

        history = []
        for row in rows:
            langs = []
            try:
                langs = json.loads(row["languages"])
            except:
                langs = [row["languages"]]

            content_val = row["content"]
            if row["type"] == "epic":
                try:
                    content_val = json.loads(row["content"])
                except:
                    pass

            div_raw = {}
            if row["divination_raw"]:
                try:
                    div_raw = json.loads(row["divination_raw"])
                except:
                    pass

            history.append(
                {
                    "id": row["id"],
                    "type": row["type"],
                    "genre": row["genre"],
                    "languages": langs,
                    "lat": row["lat"],
                    "lon": row["lon"],
                    "date_generated": row["date_generated"],
                    "content": content_val,
                    "astrology_context": row["astrology_context"],
                    "divination_context": row["divination_context"],
                    "divination_raw": div_raw,
                    "entities_invoked": row["entities_invoked"],
                }
            )
        return {"status": "success", "history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", summary="Get Outlook Generator Status")
async def get_status():
    """Return the status of the outlook generator subsystem."""
    return container.outlook.get_status()


# ----------------- CHARACTERS CRUD -----------------
class CharacterCreate(BaseModel):
    name: str
    role: CharacterRole
    description: str
    source_type: CharacterSourceType
    dialogue_style: str = "cryptic and profound"
    associated_realms: list[str] = []
    mantra_preference: str | None = None
    elemental_anchor: str = "space"
    priority: int = 5
    is_active: bool = True
    tags: list[str] = []
    notes: str = ""


@router.get("/characters", summary="Get all characters")
async def list_characters():
    mgr = get_character_manager()
    mgr.reload()
    return [c.to_dict() for c in mgr.get_all_characters()]


@router.post("/characters", summary="Create character")
async def create_character(char: CharacterCreate):
    c = get_character_manager().create_character(**char.dict())
    return c.to_dict()


@router.get("/characters/{id}", summary="Get character details")
async def get_character(id: str):
    mgr = get_character_manager()
    mgr.reload()
    c = mgr.get_character(id)
    if not c:
        raise HTTPException(status_code=404, detail="Character not found")
    return c.to_dict()


@router.put("/characters/{id}", summary="Update character")
async def update_character(id: str, updates: dict[str, Any]):
    c = get_character_manager().update_character(id, **updates)
    if not c:
        raise HTTPException(status_code=404, detail="Character not found")
    return c.to_dict()


@router.delete("/characters/{id}", summary="Delete character")
async def delete_character(id: str):
    success = get_character_manager().delete_character(id)
    if not success:
        raise HTTPException(status_code=404, detail="Character not found")
    return {"message": "Character deleted successfully"}


@router.get("/characters/roles/list", summary="Get available roles")
async def list_roles():
    return [r.value for r in CharacterRole]


# ----------------- LOCATIONS CRUD -----------------
class LocationCreate(BaseModel):
    name: str
    description: str
    location_type: LocationType
    source_type: LocationSourceType
    is_metaphysical: bool = False
    latitude: float | None = None
    longitude: float | None = None
    timezone: str = "UTC"
    celestial_coordinates: str | None = None
    dimension_frequency: float | None = None
    realm_governor: str | None = None
    astrological_anchor: str | None = None
    elemental_affinity: str | None = None
    priority: int = 5
    is_active: bool = True
    tags: list[str] = []
    notes: str = ""


@router.get("/locations", summary="Get all locations")
async def list_locations():
    mgr = get_location_manager()
    mgr.reload()
    return [l.to_dict() for l in mgr.get_all_locations()]


@router.post("/locations", summary="Create location")
async def create_location(loc: LocationCreate):
    l = get_location_manager().create_location(**loc.dict())
    return l.to_dict()


@router.get("/locations/{id}", summary="Get location details")
async def get_location(id: str):
    mgr = get_location_manager()
    mgr.reload()
    l = mgr.get_location(id)
    if not l:
        raise HTTPException(status_code=404, detail="Location not found")
    return l.to_dict()


@router.put("/locations/{id}", summary="Update location")
async def update_location(id: str, updates: dict[str, Any]):
    l = get_location_manager().update_location(id, **updates)
    if not l:
        raise HTTPException(status_code=404, detail="Location not found")
    return l.to_dict()


@router.delete("/locations/{id}", summary="Delete location")
async def delete_location(id: str):
    success = get_location_manager().delete_location(id)
    if not success:
        raise HTTPException(status_code=404, detail="Location not found")
    return {"message": "Location deleted successfully"}


@router.get("/locations/types/list", summary="Get available location types")
async def list_location_types():
    return [t.value for t in LocationType]


# ----------------- LOOP CONTROL -----------------
class LoopStartRequest(BaseModel):
    interval_minutes: int = Field(5, ge=1, le=1440)
    lat: float = 34.0522
    lon: float = -118.2437
    languages: list[str] = ["English"]
    genre: str = "healing"
    custom_context: str | None = None
    realm_id: str | None = None
    population_ids: list[str] | None = None
    character_ids: list[str] | None = None
    excluded_forces: list[str] | None = None
    include_dialogue: bool = False
    loop_mode: str | None = "sequential_delay"  # "sequential_delay" or "consecutive"
    model: str | None = None
    include_astrology: bool = True
    include_tarot: bool = True
    include_iching: bool = True
    randomize_realm: bool = False
    randomize_characters: bool = False


@router.post("/loop/start", summary="Start background narrative loop")
async def start_loop(req: LoopStartRequest):
    success = container.outlook.start_broadcast_loop(
        interval_minutes=req.interval_minutes,
        lat=req.lat,
        lon=req.lon,
        languages=req.languages,
        genre=req.genre,
        custom_context=req.custom_context,
        realm_id=req.realm_id,
        population_ids=req.population_ids,
        character_ids=req.character_ids,
        excluded_forces=req.excluded_forces,
        include_dialogue=req.include_dialogue,
        loop_mode=req.loop_mode,
        model=req.model,
        include_astrology=req.include_astrology,
        include_tarot=req.include_tarot,
        include_iching=req.include_iching,
        randomize_realm=req.randomize_realm,
        randomize_characters=req.randomize_characters
    )
    if not success:
        raise HTTPException(status_code=400, detail="Loop already running or failed to start")
    return {
        "status": "success",
        "message": f"Broadcast loop started. Mode: {req.loop_mode}. Executing every {req.interval_minutes} minutes.",
    }


@router.post("/loop/stop", summary="Stop background narrative loop")
async def stop_loop():
    success = container.outlook.stop_broadcast_loop()
    if not success:
        return {"status": "warning", "message": "Loop was not active"}
    return {"status": "success", "message": "Broadcast loop stopped successfully"}


@router.get("/loop/status", summary="Get background narrative loop status")
async def get_loop_status():
    return container.outlook.get_loop_status()


# ----------------- NARRATIVES IMPORT/EXPORT -----------------
class OutlookNarrativeImportSchema(BaseModel):
    type: str
    genre: str | None = None
    languages: list[str] | str | None = None
    lat: float | None = None
    lon: float | None = None
    date_generated: str | None = None
    content: str | dict | list | None = None
    astrology_context: str | None = None
    divination_context: str | None = None
    divination_raw: dict | list | str | None = None
    entities_invoked: str | None = None


@router.get("/export", summary="Export all outlook narratives")
async def export_narratives():
    """Export all generated outlook narratives from the database as a JSON list."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT type, genre, languages, lat, lon, date_generated, content, astrology_context, divination_context, divination_raw, entities_invoked
            FROM outlook_narratives
            ORDER BY date_generated DESC
            """
        )
        rows = cursor.fetchall()
        conn.close()

        narratives = []
        for row in rows:
            langs = []
            if row["languages"]:
                try:
                    langs = json.loads(row["languages"])
                except Exception:
                    langs = [row["languages"]]

            content_val = row["content"]
            if row["type"] == "epic" and content_val:
                try:
                    content_val = json.loads(content_val)
                except Exception:
                    pass

            div_raw = {}
            if row["divination_raw"]:
                try:
                    div_raw = json.loads(row["divination_raw"])
                except Exception:
                    pass

            narratives.append(
                {
                    "type": row["type"],
                    "genre": row["genre"],
                    "languages": langs,
                    "lat": row["lat"],
                    "lon": row["lon"],
                    "date_generated": row["date_generated"],
                    "content": content_val,
                    "astrology_context": row["astrology_context"],
                    "divination_context": row["divination_context"],
                    "divination_raw": div_raw,
                    "entities_invoked": row["entities_invoked"],
                }
            )
        return {"status": "success", "narratives": narratives}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import", summary="Import outlook narratives")
async def import_narratives(narratives: list[OutlookNarrativeImportSchema]):
    """Import a list of generated outlook narratives into the database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        count = 0
        for n in narratives:
            # Normalize languages to text
            langs_val = ""
            if isinstance(n.languages, list):
                langs_val = json.dumps(n.languages)
            elif isinstance(n.languages, str):
                langs_val = n.languages

            # Normalize content to text
            content_val = ""
            if isinstance(n.content, (dict, list)):
                content_val = json.dumps(n.content)
            elif isinstance(n.content, str):
                content_val = n.content

            # Normalize divination_raw
            div_raw_val = ""
            if isinstance(n.divination_raw, (dict, list)):
                div_raw_val = json.dumps(n.divination_raw)
            elif isinstance(n.divination_raw, str):
                div_raw_val = n.divination_raw

            cursor.execute(
                """
                INSERT INTO outlook_narratives
                (type, genre, languages, lat, lon, date_generated, content, astrology_context, divination_context, divination_raw, entities_invoked)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    n.type,
                    n.genre,
                    langs_val,
                    n.lat,
                    n.lon,
                    n.date_generated,
                    content_val,
                    n.astrology_context,
                    n.divination_context,
                    div_raw_val,
                    n.entities_invoked,
                ),
            )
            count += 1
        conn.commit()
        conn.close()
        return {"status": "success", "imported": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

