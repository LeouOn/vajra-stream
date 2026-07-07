"""
Outlook API — narrative healing and astrological outlook endpoints.

Exposes REST endpoints for generating personalised healing narratives,
sutra-style blessings, and astrological outlooks for individuals based
on their birth chart, current transits, and divination results.
"""

import json
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from dateutil import parser as _dt_parser
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.config import settings
from backend.core.services.character_manager import CharacterRole, CharacterSourceType, get_character_manager
from backend.core.services.location_manager import LocationSourceType, LocationType, get_location_manager

logger = logging.getLogger(__name__)

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
    include_geomancy: bool = Field(default=True, description="Whether to include geomancy in the divination context")
    randomize_realm: bool = Field(default=False, description="Whether to select a random active setting/realm")
    randomize_characters: bool = Field(default=False, description="Whether to select 2-3 random active characters")
    natal_date_iso: str | None = Field(default=None, description="Natal birth datetime for transit-to-natal aspects")
    natal_lat: float | None = Field(default=None, description="Natal birth latitude")
    natal_lon: float | None = Field(default=None, description="Natal birth longitude")


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
    from core.schema import init_db as _core_init_db  # noqa: WPS433

    _core_init_db()


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
        natal_dt = None
        if request.natal_date_iso:
            try:
                natal_dt = _dt_parser.parse(request.natal_date_iso)
            except Exception:
                pass
        natal_location: tuple[float, float] | None = None
        if request.natal_lat is not None and request.natal_lon is not None:
            natal_location = (request.natal_lat, request.natal_lon)

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
            include_geomancy=request.include_geomancy,
            randomize_realm=request.randomize_realm,
            randomize_characters=request.randomize_characters,
            natal_dt=natal_dt,
            natal_location=natal_location,
        )

        # Save to database
        db_save_error: str | None = None
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
            # Previously swallowed silently with a bare ``print`` — the
            # frontend received HTTP 200 with no ``id`` and could not tell
            # the save failed. Now we surface the failure as a flag on the
            # response payload so the client can warn the user that the
            # narrative was generated but not persisted.
            logger.warning("Outlook single save failed: %s", db_err)
            db_save_error = str(db_err)

        if db_save_error:
            result["persisted"] = False
            result["persist_error"] = db_save_error
        else:
            result["persisted"] = True

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
            include_geomancy=request.include_geomancy,
            randomize_realm=request.randomize_realm,
            randomize_characters=request.randomize_characters,
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
            # Previously swallowed silently — see /generate_single for the
            # rationale. Surface as ``persisted: False`` + ``persist_error``
            # so the client can warn that the epic was generated but not
            # persisted to the history list.
            logger.warning("Outlook epic save failed: %s", db_err)
            result["persisted"] = False
            result["persist_error"] = str(db_err)
        else:
            result["persisted"] = True

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
            except Exception:
                langs = [row["languages"]]

            content_val = row["content"]
            if row["type"] == "epic":
                try:
                    content_val = json.loads(row["content"])
                except Exception:
                    pass

            div_raw = {}
            if row["divination_raw"]:
                try:
                    div_raw = json.loads(row["divination_raw"])
                except Exception:
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


# ----------------- TTS / NARRATIVE RECITATION -----------------

# Language → voice mapping. Outlook narratives mix English prose with
# CJK astrological / panchanga terms (丙午年, 马, Horse) and Sanskrit
# mantras (Om Mani Padme Hum). Reading the whole narrative with one
# voice — typically zh-CN-YunxiNeural — gives Chinese-accented English
# or English-accented Chinese. Per-chunk language detection lets each
# chunk pick a native-sounding voice.
LANGUAGE_VOICE_MAP: dict[str, str] = {
    "zh": "zh-CN-YunxiNeural",     # Male, warm — traditional sutra feel
    "en": "en-US-AriaNeural",      # Female, warm and engaging
}


def _detect_dominant_language(text: str) -> str:
    """Detect the dominant script/language of a text chunk.

    Counts CJK (Chinese, Japanese kana, Korean Hangul) characters and
    returns ``"zh"`` when they exceed 30% of the non-whitespace content,
    otherwise ``"en"``. Sanskrit/Tibetan (Latin transliteration or
    Devanagari) and pure Latin scripts fall through to ``"en"``.
    """
    if not text:
        return "en"
    non_ws = [c for c in text if not c.isspace()]
    if not non_ws:
        return "en"
    cjk_count = sum(
        1
        for c in non_ws
        if (
            "\u4e00" <= c <= "\u9fff"      # CJK Unified Ideographs (Chinese)
            or "\u3040" <= c <= "\u30ff"   # Hiragana + Katakana (Japanese)
            or "\uac00" <= c <= "\ud7af"   # Hangul Syllables (Korean)
        )
    )
    if cjk_count / len(non_ws) > 0.30:
        return "zh"
    return "en"


class OutlookSpeakRequest(BaseModel):
    text: str = Field(
        ..., description="Narrative text to speak (single string or joined epic parts)", min_length=1, max_length=20000
    )
    voice: str | None = Field(default=None, description="Voice/speaker override (bypasses role)")
    rate: str | None = Field(default=None, description="Speech rate (Edge TTS only, e.g. '-25%')")
    language: str | None = Field(default=None, description="Language override (Qwen3-TTS only)")
    role: str | None = Field(
        default=None, description="Ritual role for auto-speaker mapping (default: outlook_narrative / outlook_epic)"
    )
    project_id: str | None = Field(default=None, description="Project id for per-project speaker overrides")
    chunk_max_chars: int = Field(default=900, description="Max characters per chunk for long narratives")
    voice_preset: str | None = Field(
        default=None,
        description=(
            "Qwen3-TTS voice design preset name (Qwen backend only). "
            "Options: compassionate_bodhisattva, meditation_master, "
            "sutra_chanter, zen_teacher, english_sacred."
        ),
    )


@router.post("/speak", summary="Speak a generated outlook narrative via TTS")
async def speak_narrative(request: OutlookSpeakRequest):
    """
    Stream a generated outlook narrative through the unified TTS provider.

    Long narratives are chunked (default ~900 chars) so each chunk can be
    rendered quickly and the browser can begin playback without waiting
    for the full generation to finish.
    """
    from fastapi.responses import Response

    from core.tts_provider import get_tts_provider

    provider = get_tts_provider()
    original_project = provider.config.project_id
    if request.project_id is not None:
        provider.config.project_id = request.project_id

    try:
        # Pick a sensible default role based on the front-end flag
        role = request.role or "outlook_narrative"

        # Strip markdown before TTS — previously headings (#), bold (**),
        # italic (*), code (``), and list markers (- / * / 1.) were read
        # aloud literally by both Edge TTS and Qwen3-TTS, producing
        # garbled-sounding narration like "hash hash hash Invocatio".
        import re

        def _strip_markdown(s: str) -> str:
            s = re.sub(r"^#{1,6}\s+", "", s, flags=re.MULTILINE)  # headings
            s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)  # bold
            s = re.sub(r"\*(.+?)\*", r"\1", s)  # italic
            s = re.sub(r"__(.+?)__", r"\1", s)  # underline
            s = re.sub(r"`(.+?)`", r"\1", s)  # inline code
            s = re.sub(r"^\s*[-*+]\s+", "", s, flags=re.MULTILINE)  # bullet lists
            s = re.sub(r"^\s*\d+\.\s+", "", s, flags=re.MULTILINE)  # numbered lists
            s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)  # links → text
            return s

        text = _strip_markdown(request.text).strip()
        if not text:
            raise HTTPException(status_code=400, detail="Empty narrative text after markdown stripping")
        # Chunk the text on paragraph boundaries; cap chunk size
        chunks: list[str] = []
        # Try paragraph-aware splitting first
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        current = ""
        for p in paragraphs:
            if len(current) + len(p) + 2 <= request.chunk_max_chars:
                current = f"{current}\n\n{p}" if current else p
            else:
                if current:
                    chunks.append(current)
                if len(p) <= request.chunk_max_chars:
                    current = p
                else:
                    # Long paragraph — hard split
                    for i in range(0, len(p), request.chunk_max_chars):
                        chunks.append(p[i : i + request.chunk_max_chars])
                    current = ""
        if current:
            chunks.append(current)
        if not chunks:
            chunks = [text[: request.chunk_max_chars]]

        # Resolve voice design preset → instruct string for Qwen3-TTS.
        # The 5 presets (compassionate_bodhisattva, meditation_master, etc.)
        # were defined in core/qwen_tts.py but unreachable from /speak.
        instruct_text: str | None = None
        if request.voice_preset:
            try:
                from core.qwen_tts import VOICE_DESIGN_PRESETS

                preset = VOICE_DESIGN_PRESETS.get(request.voice_preset)
                if preset:
                    instruct_text = preset.get("instruct")
                    if preset.get("language") and not request.language:
                        request.language = preset["language"]
            except Exception:
                pass  # preset lookup is best-effort

        # Render all chunks and concatenate
        all_audio: list[bytes] = []
        mime_type = "audio/mpeg"
        backend_id = provider.active_backend.value
        for chunk_idx, chunk in enumerate(chunks):
            # Per-chunk language-aware voice selection. If the caller
            # explicitly set `voice`, respect their choice for ALL chunks
            # (user override wins). Otherwise detect the dominant script
            # of this chunk and pick a matching native voice, falling
            # back to the provider's default (None) for unmapped langs.
            if request.voice is not None:
                chunk_voice = request.voice
                chunk_lang = request.language
            else:
                chunk_lang = _detect_dominant_language(chunk)
                chunk_voice = LANGUAGE_VOICE_MAP.get(chunk_lang)
            result = await provider.speak_stream(
                text=chunk,
                voice=chunk_voice,
                rate=request.rate,
                language=request.language or chunk_lang,
                role=role,
                instruct=instruct_text,
            )
            if result is None:
                # Previously silently skipped — now logged so operators can
                # diagnose partial TTS failures (missing audio gaps the user
                # hears as silent sections in the narration).
                logger.warning(
                    "TTS chunk %d/%d returned None (backend=%s, chars=%d)",
                    chunk_idx + 1,
                    len(chunks),
                    backend_id,
                    len(chunk),
                )
                continue
            audio_bytes, mtype, bid = result
            mime_type = mtype
            backend_id = bid
            all_audio.append(audio_bytes)
        if not all_audio:
            raise HTTPException(status_code=500, detail="TTS generation failed — check backend availability")

        return Response(
            content=b"".join(all_audio),
            media_type=mime_type,
            headers={
                "X-TTS-Backend": backend_id,
                "X-TTS-Chunks": str(len(all_audio)),
                "X-TTS-Chars": str(len(request.text)),
                "Cache-Control": "no-store",
            },
        )
    finally:
        provider.config.project_id = original_project


@router.post("/speak/{narrative_id}", summary="Stream a stored outlook narrative by ID")
async def speak_stored_narrative(
    narrative_id: int, role: str | None = None, voice: str | None = None, project_id: str | None = None
):
    """Look up a previously generated narrative and speak it."""
    from fastapi.responses import Response

    from core.tts_provider import get_tts_provider

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT type, content FROM outlook_narratives WHERE id = ?",
            (narrative_id,),
        )
        row = cursor.fetchone()
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")
    if not row:
        raise HTTPException(status_code=404, detail="Narrative not found")

    text = row["content"] or ""
    if row["type"] == "epic":
        try:
            import json as _json

            parts = _json.loads(text) if text else []
            text = "\n\n".join(p.get("content", "") if isinstance(p, dict) else str(p) for p in parts)
        except Exception:
            pass
    if not text.strip():
        raise HTTPException(status_code=400, detail="Stored narrative is empty")

    # Reuse the speak endpoint logic
    provider = get_tts_provider()
    original_project = provider.config.project_id
    if project_id is not None:
        provider.config.project_id = project_id
    try:
        effective_role = role or ("outlook_epic" if row["type"] == "epic" else "outlook_narrative")
        result = await provider.speak_stream(
            text=text,
            voice=voice,
            role=effective_role,
        )
    finally:
        provider.config.project_id = original_project
    if result is None:
        raise HTTPException(status_code=500, detail="TTS generation failed — check backend availability")
    audio_bytes, mime_type, backend_id = result
    return Response(
        content=audio_bytes,
        media_type=mime_type,
        headers={
            "X-TTS-Backend": backend_id,
            "X-TTS-Chars": str(len(text)),
            "Cache-Control": "no-store",
        },
    )


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
    include_geomancy: bool = True
    cycle_genres: bool = False
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
        include_geomancy=req.include_geomancy,
        cycle_genres=req.cycle_genres,
        randomize_realm=req.randomize_realm,
        randomize_characters=req.randomize_characters,
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
