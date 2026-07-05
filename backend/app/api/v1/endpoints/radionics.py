"""
Radionics API Endpoints for Vajra.Stream
Integrated scalar-radionics broadcasting system
"""

import asyncio
import json
import logging
import os
import sqlite3
import sys
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../../../../"))

from backend.core.orchestrator_bridge import orchestrator_bridge
from core.integrated_scalar_radionics import BroadcastConfiguration, IntegratedScalarRadionicsBroadcaster, IntentionType
from core.schema import get_db_path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Global instance
broadcaster = IntegratedScalarRadionicsBroadcaster()


# Request Models
class BroadcastRequest(BaseModel):
    intention: str = Field(..., description="Intention type: healing, liberation, empowerment, protection, etc.")
    target_names: list[str] = Field(..., description="Names of targets for broadcast")
    duration_minutes: int = Field(default=10, ge=1, le=120, description="Duration in minutes")
    frequency_hz: float | None = Field(None, description="Specific frequency (optional, auto-selected if not provided)")
    scalar_intensity: float = Field(default=0.8, ge=0.0, le=1.0, description="Scalar wave intensity")
    use_chakras: bool = Field(default=True, description="Activate chakra system")
    use_meridians: bool = Field(default=False, description="Activate meridian system")
    mantra: str | None = Field(None, description="Optional mantra for broadcast")
    breathing_pattern: bool = Field(default=True, description="Use sacred breathing cycles")
    rate_values: list[int] | None = Field(None, description="Radionics dial values (0-100). When provided, mapped to Solfeggio carrier frequencies via rate_to_audio bridge.")


class HealingProtocolRequest(BaseModel):
    target_name: str = Field(..., description="Name of person/situation to heal")
    duration_minutes: int = Field(default=10, ge=1, le=120, description="Duration")
    specific_intention: str | None = Field(None, description="Specific healing intention")


class LiberationProtocolRequest(BaseModel):
    event_name: str = Field(..., description="Name of event/situation")
    souls_count: int = Field(default=1, ge=1, description="Estimated number of souls")
    duration_minutes: int = Field(default=30, ge=10, le=180, description="Duration")


class RitualBroadcastRequest(BaseModel):
    intention: str = Field(..., description="Intention text — prayer, dedication, or suffering")
    target: str = Field(default="all beings", description="Who/what the ritual is dedicated to")
    rate_values: list[int] | None = Field(
        default=None, description="Radionics dial values (0-100) mapped to Solfeggio carrier frequencies"
    )
    direct_freq: float | None = Field(default=None, description="Direct carrier frequency in Hz (skips rate mapping)")
    duration_minutes: int = Field(default=10, ge=1, le=180, description="Broadcast duration in minutes")
    ritual_type: str = Field(default="universal", description="Ritual archetype (universal, earthquake, war, illness, death, displacement, dedication_of_endeavors)")
    tradition: str = Field(default="vajrayana", description="Liturgical tradition (vajrayana, theravada, mahayana, zen)")
    recite_with_tts: bool = Field(default=True, description="Speak the ritual via TTS (Sanskrit preprocessed for pronunciation)")


# Response Models
class BroadcastResponse(BaseModel):
    status: str
    session_id: str
    intention: str
    targets: list[str]
    frequency_hz: float
    duration_seconds: float
    scalar_mops: float
    chakras_activated: list[str]
    meridians_activated: list[str]
    dedication: str
    frequencies: list[float] | None = None
    solfeggio_names: list[str] | None = None
    crystal_output: dict | None = None
    scalar_output: dict | None = None


class RitualBroadcastResponse(BaseModel):
    status: str
    session_id: str
    ritual_markdown: str
    frequencies: list[float]
    solfeggio_names: list[str]
    crystal_output: dict | None = None
    archived_narrative_id: int | None = None
    tts_result: dict | None = None


class SutraRecitationRequest(BaseModel):
    sutra_id: str | None = Field(
        None,
        description="Passage ID from sutra_passages.json (e.g., 'heart_sutra_essence', 'diamond_impermanence')",
    )
    theme: str | None = Field(
        None,
        description="Theme to select by if sutra_id is not given (protection, healing, dedication, impermanence, emptiness, loss)",
    )
    duration_minutes: int = Field(default=5, ge=1, le=60, description="Crystal bowl accompaniment duration")
    rate_values: list[int] | None = Field(
        None, description="Radionics dial values (0-100) mapped to Solfeggio carriers"
    )
    direct_freq: float | None = Field(
        None, description="Direct carrier frequency in Hz (skips rate mapping)"
    )
    recite_with_tts: bool = Field(default=True, description="Generate TTS audio for the passage")
    repeat_count: int = Field(default=1, ge=1, le=108, description="Times to recite (1, 3, 7, 108)")


class SutraRecitationResponse(BaseModel):
    status: str
    session_id: str
    sutra: str
    sanskrit_name: str
    chapter: str
    theme: str
    tags: list[str]
    passage: str
    passage_tts_friendly: str
    context: str | None = None
    frequencies: list[float]
    solfeggio_names: list[str]
    crystal_output: dict | None = None
    tts_result: dict | None = None


# Endpoints


@router.post("/broadcast", response_model=BroadcastResponse)
async def start_broadcast(request: BroadcastRequest, background_tasks: BackgroundTasks):
    """Start integrated scalar-radionics broadcast"""
    try:
        logger.info(f"📡 Starting broadcast: {request.intention} for {len(request.target_names)} targets")

        # Use OrchestratorBridge to create session
        targets = [{"type": "individual", "identifier": name} for name in request.target_names]
        modalities = []
        if request.use_chakras:
            modalities.append("chakras")
        if request.use_meridians:
            modalities.append("meridians")
        if request.scalar_intensity > 0:
            modalities.append("scalar")

        # Create session via orchestrator
        # Note: This is a synchronous call wrapped in async in the bridge
        session_id = await orchestrator_bridge.create_session(
            intention=request.intention, targets=targets, modalities=modalities, duration=request.duration_minutes * 60
        )

        # Map intention string to IntentionType enum
        intention_map = {
            "healing": IntentionType.HEALING,
            "liberation": IntentionType.LIBERATION,
            "empowerment": IntentionType.EMPOWERMENT,
            "protection": IntentionType.PROTECTION,
            "reconciliation": IntentionType.RECONCILIATION,
            "peace": IntentionType.PEACE,
            "love": IntentionType.LOVE,
            "wisdom": IntentionType.WISDOM,
        }

        intention_type = intention_map.get(request.intention.lower(), IntentionType.HEALING)

        # Auto-select frequency if not provided
        frequency_mapping = {
            "healing": 528,  # DNA repair
            "liberation": 396,  # Liberation from fear
            "empowerment": 528,
            "protection": 741,  # Awakening intuition
            "reconciliation": 639,  # Connecting relationships
            "peace": 852,  # Spiritual order
            "love": 528,
            "wisdom": 963,  # Divine consciousness
        }

        frequency_hz = request.frequency_hz or frequency_mapping.get(request.intention.lower(), 432)

        # Invoke the real RadionicsService (not the old mock).
        # The service maps the intention to prayer bowl carrier frequencies,
        # invokes the crystal broadcaster for audio, and the integrated
        # scalar-radionics engine for scalar wave generation.
        from container import container

        radionics_service = getattr(container, "radionics", None)
        crystal_result = None
        scalar_result = None
        actual_freqs = [7.83, frequency_hz]

        if radionics_service:
            try:
                result = radionics_service.broadcast_healing(
                    target_name=request.target_names[0] if request.target_names else "all beings",
                    duration_minutes=request.duration_minutes,
                    frequency_hz=frequency_hz,
                    intensity=request.scalar_intensity,
                    rate_values=request.rate_values,
                )
                actual_freqs = result.get("frequencies", actual_freqs)
                crystal_result = result.get("crystal_output")
                scalar_result = result.get("scalar_output")
            except Exception as exc:
                logger.warning(f"RadionicsService broadcast failed: {exc}")

        duration = request.duration_minutes * 60

        # Estimate scalar MOPS from actual broadcast
        estimated_mops = 17.73 * request.scalar_intensity

        # Get activated systems
        chakras_activated = (
            ["muladhara", "svadhisthana", "manipura", "anahata", "vishuddha", "ajna", "sahasrara"]
            if request.use_chakras
            else []
        )

        meridians_activated = (
            [
                "lung", "large_intestine", "stomach", "spleen",
                "heart", "small_intestine", "bladder", "kidney",
                "pericardium", "triple_warmer", "gallbladder", "liver",
            ]
            if request.use_meridians
            else []
        )

        dedication = f"May all beings benefit! Dedicated to {', '.join(request.target_names)}"

        return BroadcastResponse(
            status="success",
            session_id=session_id,
            intention=request.intention,
            targets=request.target_names,
            frequency_hz=frequency_hz,
            duration_seconds=duration,
            scalar_mops=estimated_mops,
            chakras_activated=chakras_activated,
            meridians_activated=meridians_activated,
            dedication=dedication,
            frequencies=actual_freqs,
            solfeggio_names=result.get("solfeggio_names") if radionics_service else None,
            crystal_output=crystal_result,
            scalar_output=scalar_result,
        )

    except Exception as e:
        logger.error(f"❌ Broadcast error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/healing-protocol")
async def healing_protocol(request: HealingProtocolRequest, background_tasks: BackgroundTasks):
    """Run healing protocol (528 Hz, DNA repair)"""
    try:
        logger.info(f"💚 Healing protocol for {request.target_name}")

        broadcast_request = BroadcastRequest(
            intention="healing",
            target_names=[request.target_name],
            duration_minutes=request.duration_minutes,
            frequency_hz=528,  # DNA repair frequency
            scalar_intensity=0.8,
            use_chakras=True,
            use_meridians=False,
            mantra="Om Mani Padme Hum",
            breathing_pattern=True,
        )

        response = await start_broadcast(broadcast_request, background_tasks)

        return {
            **response.dict(),
            "protocol": "healing",
            "frequency_name": "528 Hz - Solfeggio DNA Repair",
            "specific_intention": request.specific_intention,
        }

    except Exception as e:
        logger.error(f"❌ Healing protocol error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/liberation-protocol")
async def liberation_protocol(request: LiberationProtocolRequest, background_tasks: BackgroundTasks):
    """Run liberation protocol (396 Hz, liberation from fear)"""
    try:
        logger.info(f"🕊️ Liberation protocol for {request.event_name}, {request.souls_count} souls")

        broadcast_request = BroadcastRequest(
            intention="liberation",
            target_names=[request.event_name],
            duration_minutes=request.duration_minutes,
            frequency_hz=396,  # Liberation frequency
            scalar_intensity=1.0,  # Maximum intensity for liberation
            use_chakras=True,
            use_meridians=True,  # Full meridian activation
            mantra="Namo Amitabha Buddha",  # Liberation mantra
            breathing_pattern=True,
        )

        response = await start_broadcast(broadcast_request, background_tasks)

        return {
            **response.dict(),
            "protocol": "liberation",
            "frequency_name": "396 Hz - Liberation from Guilt & Fear",
            "souls_count": request.souls_count,
            "event": request.event_name,
            "special_dedication": f"May the {request.souls_count} souls find peace, liberation, and the highest rebirth",
        }

    except Exception as e:
        logger.error(f"❌ Liberation protocol error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ritual-broadcast", response_model=RitualBroadcastResponse)
async def ritual_broadcast(request: RitualBroadcastRequest):
    """Generate a complete sacred ritual + start crystal bowl broadcast + archive to DB.

    Pipeline:
        1. Resolve carrier frequencies (rate_values / direct_freq / auto-tune)
        2. Fetch live astrology data
        3. Generate full ritual via RitualGenerator
        4. Start crystal bowl broadcast via container's crystal service
        5. Archive ritual markdown to outlook_narratives table

    Each step is wrapped in try/except so the ritual_markdown is returned even
    if downstream stages (astrology fetch, crystal broadcast, DB archive) fail.
    """
    logger.info(f"🪷 Ritual broadcast: '{request.intention[:80]}' for {request.target}")

    # ── Session id (best-effort via orchestrator; fallback to UUID) ────────
    session_id = f"ritual_{uuid.uuid4().hex[:12]}"
    try:
        session_id = await orchestrator_bridge.create_session(
            intention=request.intention,
            targets=[{"type": "individual", "identifier": request.target}],
            modalities=["ritual", "crystal_bowl"],
            duration=request.duration_minutes * 60,
        )
    except Exception as exc:
        logger.warning(f"orchestrator_bridge.create_session failed, using local id: {exc}")

    # ── 1. Resolve carrier frequencies ─────────────────────────────────────
    frequencies: list[float] = []
    solfeggio_names: list[str] = []
    carrier_amplitude: float = 0.3

    try:
        from core.rate_to_audio import map_rate_to_carriers

        rate_values = request.rate_values
        if not rate_values:
            # No explicit dial values — try direct_freq first, then auto-tune
            if request.direct_freq is not None:
                frequencies = [7.83, float(request.direct_freq)]
                solfeggio_names = ["Schumann Base", f"{float(request.direct_freq):.2f} Hz"]
            else:
                # Auto-tune: derive a single dial value from the intention via
                # RadionicsEnhancer (entropy + hash) and snap to a Solfeggio tone.
                try:
                    from modules.radionics_enhancer import RadionicsEnhancer

                    enhancer = RadionicsEnhancer()
                    auto_rate = int(round(enhancer.attune_rate(request.intention)))
                    logger.info(f"Auto-tuned rate value for intention: {auto_rate}")
                except Exception as exc:
                    logger.warning(f"RadionicsEnhancer auto-tune failed, falling back to 50: {exc}")
                    auto_rate = 50
                rate_values = [auto_rate]

        if rate_values and not frequencies:
            carriers = map_rate_to_carriers(rate_values, potency=1.0)
            frequencies = list(carriers.frequencies)
            solfeggio_names = list(carriers.solfeggio_names)
            carrier_amplitude = carriers.amplitude
    except Exception as exc:
        logger.warning(f"Frequency resolution failed, using fallback [7.83, 528.0]: {exc}")
        frequencies = [7.83, 528.0]
        solfeggio_names = ["Schumann Base", "Mi (Transformation)"]

    # ── 2. Fetch live astrology data ───────────────────────────────────────
    astrology_data: dict | None = None
    try:
        from backend.core.services.vajra_service import vajra_service

        astrology_data = await vajra_service._get_astrology_data()
    except Exception as exc:
        logger.warning(f"Astrology fetch failed, continuing without it: {exc}")

    # ── 3. Generate full ritual ────────────────────────────────────────────
    try:
        from core.ritual_generator import RitualGenerator

        ritual_gen = RitualGenerator()
        # Best-effort: pull the global LLM from the container for richer prayers/teachings
        try:
            from container import container as _container
            llm = _container.llm
        except Exception:
            llm = None

        ritual = ritual_gen.generate_full_ritual(
            intention=request.intention,
            targets=[request.target],
            carrier_frequencies=frequencies,
            solfeggio_names=solfeggio_names,
            mantras_dedicated=108,
            astrology_data=astrology_data,
            tradition=request.tradition,
            llm=llm,
        )
        ritual_md = ritual.to_markdown()
    except Exception as exc:
        logger.error(f"Ritual generation failed: {exc}")
        # Hard fallback — return a minimal so the caller still gets a session_id + frequencies
        ritual_md = (
            f"# Sacred Ritual: {request.intention}\n\n"
            f"*Generated {datetime.now().isoformat()}*\n\n"
            f"Om Mani Padme Hum — may all beings benefit.\n"
        )
        frequencies = frequencies or [7.83, 528.0]
        solfeggio_names = solfeggio_names or ["Schumann Base", "Mi (Transformation)"]

    # ── 4. Start crystal bowl broadcast (non-fatal if it fails) ────────────
    crystal_output: dict | None = None
    try:
        from container import container as _container

        crystal_output = _container.crystal.broadcast_intention(
            intention=request.intention,
            frequencies=frequencies,
            duration=request.duration_minutes * 60,
            hardware_level=2,
            prayer_bowl_mode=True,
            amplitude=carrier_amplitude,
        )
    except Exception as exc:
        logger.warning(f"Crystal broadcast failed (continuing without audio): {exc}")

    # ── 5. Archive ritual to outlook_narratives table (non-fatal) ─────────
    narrative_id: int | None = None
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO outlook_narratives (type, genre, content, date_generated) VALUES (?, ?, ?, ?)",
            ("ritual", request.ritual_type, ritual_md, datetime.now().isoformat()),
        )
        conn.commit()
        narrative_id = cursor.lastrowid
        conn.close()
        logger.info(f"Archived ritual to outlook_narratives id={narrative_id}")
    except Exception as exc:
        logger.warning(f"Failed to archive ritual to outlook_narratives: {exc}")

    # ── 6. TTS recitation (non-fatal, fire-and-forget) ────────────────────
    tts_result: dict | None = None
    if request.recite_with_tts:
        try:
            # recite_ritual() needs the RitualText object (not just markdown).
            # It splits into 6 sections, preprocesses Sanskrit via sanskrit_tts,
            # and speaks each section via the TTS provider. Runs async.
            tts_result = ritual_gen.recite_ritual(ritual)
            logger.info(f"TTS recitation: {tts_result.get('status', 'unknown')} "
                        f"({tts_result.get('sections_recited', 0)} sections)")
        except Exception as exc:
            logger.warning(f"TTS recitation failed (ritual text still returned): {exc}")
            tts_result = {"status": "failed", "error": str(exc)}

    return RitualBroadcastResponse(
        status="success",
        session_id=session_id,
        ritual_markdown=ritual_md,
        frequencies=frequencies,
        solfeggio_names=solfeggio_names,
        crystal_output=crystal_output,
        archived_narrative_id=narrative_id,
        tts_result=tts_result,
    )


@router.get("/dharanis")
async def list_dharanis():
    """List all available dharanis for recitation.

    Returns entries from knowledge/dharanis.json with their IDs, deity,
    purpose, frequency, and IAST Sanskrit text so the caller can choose
    one for /dharani-recitation.
    """
    import json as _json
    from pathlib import Path as _Path

    path = _Path(__file__).resolve().parent.parent.parent.parent.parent / "knowledge" / "dharanis.json"
    if not path.exists():
        return {"status": "error", "detail": "dharanis.json not found", "dharanis": []}
    try:
        entries = _json.loads(path.read_text(encoding="utf-8"))
    except (_json.JSONDecodeError, OSError) as exc:
        raise HTTPException(status_code=500, detail=f"Failed to parse dharanis.json: {exc}")

    return {
        "status": "success",
        "total": len(entries),
        "dharanis": [
            {
                "id": e.get("id"),
                "name": e.get("name"),
                "sanskrit": e.get("sanskrit", ""),
                "deity": e.get("deity", ""),
                "tradition": e.get("tradition", ""),
                "purpose": e.get("purpose", ""),
                "times": e.get("times", 108),
                "frequency_hz": e.get("frequency_hz", 528),
                "chakra": e.get("chakra", "heart"),
                "has_sanskrit": bool(e.get("text_sanskrit")),
                "has_tibetan": bool(e.get("text_tibetan")),
                "has_chinese": bool(e.get("text_chinese")),
                "text_sanskrit_preview": (e.get("text_sanskrit", "")[:120] + "...") if len(e.get("text_sanskrit", "")) > 120 else e.get("text_sanskrit", ""),
            }
            for e in entries
        ],
    }


@router.post("/dharani-recitation")
async def dharani_recitation(
    dharani_id: str,
    duration_minutes: int = 5,
    recite_with_tts: bool = True,
    repeat_count: int = 1,
):
    """Recite a dharani with crystal bowl accompaniment and optional TTS.

    Pipeline mirrors /sutra-recitation but loads from dharanis.json:
        1. Look up the dharani by ID
        2. Convert IAST Sanskrit to TTS-friendly phonetics
        3. Use the dharani's prescribed frequency for crystal bowls
        4. Recite via TTS (optional)

    The dharani's ``frequency_hz`` and ``chakra`` fields drive the carrier
    frequency selection, so each deity's dharani resonates at its traditional
    Solfeggio tone.
    """
    import json as _json
    from pathlib import Path as _Path
    from core.sanskrit_tts import preprocess_for_tts

    logger.info(f"📿 Dharani recitation: {dharani_id}, repeat={repeat_count}, tts={recite_with_tts}")

    # ── Session id ────────────────────────────────────────────────────────
    session_id = f"dharani_{uuid.uuid4().hex[:12]}"
    try:
        session_id = await orchestrator_bridge.create_session(
            intention=f"dharani_recitation:{dharani_id}",
            targets=[{"type": "universal", "identifier": "all beings"}],
            modalities=["dharani", "crystal_bowl"],
            duration=duration_minutes * 60,
        )
    except Exception as exc:
        logger.warning(f"orchestrator_bridge.create_session failed: {exc}")

    # ── 1. Load dharani ───────────────────────────────────────────────────
    path = _Path(__file__).resolve().parent.parent.parent.parent.parent / "knowledge" / "dharanis.json"
    if not path.exists():
        raise HTTPException(status_code=503, detail="dharanis.json not available")
    try:
        entries = _json.loads(path.read_text(encoding="utf-8"))
    except (_json.JSONDecodeError, OSError) as exc:
        raise HTTPException(status_code=500, detail=f"Failed to parse dharanis.json: {exc}")

    selected = next((e for e in entries if e.get("id") == dharani_id), None)
    if selected is None:
        available = [e.get("id") for e in entries]
        raise HTTPException(
            status_code=404,
            detail=f"dharani_id '{dharani_id}' not found. Available: {available}",
        )

    name = selected.get("name", "")
    sanskrit_name = selected.get("sanskrit", "")
    deity = selected.get("deity", "")
    purpose = selected.get("purpose", "")
    frequency_hz = selected.get("frequency_hz", 528)
    chakra = selected.get("chakra", "heart")
    text_sanskrit = selected.get("text_sanskrit", "").strip()

    if not text_sanskrit:
        raise HTTPException(status_code=500, detail=f"Dharani '{dharani_id}' has no Sanskrit text")

    # ── 2. Convert to TTS-friendly phonetics ──────────────────────────────
    try:
        text_tts = preprocess_for_tts(text_sanskrit)
    except Exception as exc:
        logger.warning(f"preprocess_for_tts failed, using raw text: {exc}")
        text_tts = text_sanskrit

    # ── 3. Crystal bowl broadcast at the dharani's frequency ──────────────
    frequencies = [7.83, float(frequency_hz)]
    solfeggio_names = ["Schumann Base", f"{frequency_hz} Hz"]
    crystal_output: dict | None = None
    try:
        from container import container as _container

        crystal_output = _container.crystal.broadcast_intention(
            intention=f"Recitation of {name}",
            frequencies=frequencies,
            duration=duration_minutes * 60,
            hardware_level=2,
            prayer_bowl_mode=True,
            amplitude=0.3,
        )
    except Exception as exc:
        logger.warning(f"Crystal broadcast failed: {exc}")

    # ── 4. TTS recitation (non-fatal) ─────────────────────────────────────
    tts_result: dict | None = None
    if recite_with_tts:
        try:
            from core.tts_provider import get_tts_provider

            provider = get_tts_provider()
            if provider is not None:
                recitation_text = (text_tts + "\n\n") * repeat_count
                tts_result = {
                    "status": "queued",
                    "text_length": len(recitation_text),
                    "repeat_count": repeat_count,
                    "provider": getattr(provider, "name", "unknown"),
                }

                import asyncio as _asyncio

                async def _speak():
                    try:
                        await provider.speak_async(recitation_text, role="buddhist_chant")
                        tts_result["status"] = "completed"
                    except Exception as exc:
                        tts_result["status"] = "failed"
                        tts_result["error"] = str(exc)

                try:
                    loop = _asyncio.get_running_loop()
                    _asyncio.ensure_future(_speak())
                except RuntimeError:
                    import threading

                    def _run():
                        try:
                            _asyncio.run(_speak())
                        except Exception as exc:
                            tts_result["status"] = "failed"
                            tts_result["error"] = str(exc)

                    threading.Thread(target=_run, daemon=True).start()
            else:
                tts_result = {"status": "no_provider"}
        except Exception as exc:
            logger.warning(f"TTS recitation failed: {exc}")
            tts_result = {"status": "failed", "error": str(exc)}

    return {
        "status": "success",
        "session_id": session_id,
        "dharani_id": dharani_id,
        "name": name,
        "sanskrit_name": sanskrit_name,
        "deity": deity,
        "purpose": purpose,
        "frequency_hz": frequency_hz,
        "chakra": chakra,
        "passage": text_sanskrit,
        "passage_tts_friendly": text_tts,
        "frequencies": frequencies,
        "solfeggio_names": solfeggio_names,
        "crystal_output": crystal_output,
        "tts_result": tts_result,
    }


@router.get("/mantras")
async def list_mantras():
    """List all available mantras grouped by tradition.

    Reads ``knowledge/mantras.json`` (a nested map of tradition → mantra id →
    mantra dict) and flattens it into a single list. Each flattened mantra
    carries its ``tradition`` key as an explicit field so the Library UI can
    render it without re-grouping.

    The top-level ``aspirations`` section (which contains verse arrays rather
    than mantra objects) is exposed separately under ``aspirations`` so the
    Library page can render the Four Immeasurables, bodhisattva vows, and
    dedication verses alongside the mantras.

    Each mantra in the response has:
      - tradition, key, name, sanskrit, sanskrit_iast, meaning, purpose,
        times, chakra, plus optional language fields (tibetan, chinese,
        pinyin, arabic, transliteration, etc.) preserved from the source.
    """
    import json as _json
    from pathlib import Path as _Path

    path = _Path(__file__).resolve().parent.parent.parent.parent.parent / "knowledge" / "mantras.json"
    if not path.exists():
        return {"status": "error", "detail": "mantras.json not found", "mantras": [], "aspirations": {}}

    try:
        raw = _json.loads(path.read_text(encoding="utf-8"))
    except (_json.JSONDecodeError, OSError) as exc:
        raise HTTPException(status_code=500, detail=f"Failed to parse mantras.json: {exc}")

    # Whitelist of top-level keys that map to mantra dictionaries. Any other
    # top-level key (e.g. ``aspirations``) is exposed separately.
    tradition_keys = {
        "buddhist",
        "chinese_buddhist",
        "taoist",
        "hindu",
        "sufi",
        "christian",
        "shamanic",
        "universal",
    }

    mantras: list[dict] = []
    for tradition, entries in raw.items():
        if tradition not in tradition_keys:
            continue
        if not isinstance(entries, dict):
            continue
        for mantra_key, mantra in entries.items():
            if not isinstance(mantra, dict):
                continue
            mantras.append(
                {
                    "tradition": tradition,
                    "key": mantra_key,
                    "name": mantra.get("name", ""),
                    "sanskrit": mantra.get("sanskrit", ""),
                    "sanskrit_iast": mantra.get("sanskrit_iast", ""),
                    "tibetan": mantra.get("tibetan", ""),
                    "chinese": mantra.get("chinese", ""),
                    "pinyin": mantra.get("pinyin", ""),
                    "pali": mantra.get("pali", ""),
                    "arabic": mantra.get("arabic", ""),
                    "hebrew": mantra.get("hebrew", ""),
                    "greek": mantra.get("greek", ""),
                    "native": mantra.get("native", ""),
                    "lakota": mantra.get("lakota", ""),
                    "celtic": mantra.get("celtic", ""),
                    "punjabi": mantra.get("punjabi", ""),
                    "japanese": mantra.get("japanese", ""),
                    "transliteration": mantra.get("transliteration", ""),
                    "meaning": mantra.get("meaning", ""),
                    "purpose": mantra.get("purpose", ""),
                    "times": mantra.get("times", 108),
                    "chakra": mantra.get("chakra", ""),
                    "source_tradition": mantra.get("tradition", ""),
                }
            )

    return {
        "status": "success",
        "total": len(mantras),
        "traditions": sorted({m["tradition"] for m in mantras}),
        "mantras": mantras,
        "aspirations": raw.get("aspirations", {}),
    }


@router.get("/sutras")
async def list_sutras():
    """List all available sutra passages for recitation and study.

    Returns passages from knowledge/sutra_passages.json with IDs, themes,
    tags, ``provenance`` (canonical/paraphrased/thematic/composed), the
    full ``passage`` text, and surrounding context — enough for the
    Library page to render a read-only contemplation view, while the
    /sutra-recitation endpoint still uses the same dataset to drive
    crystal-bowl broadcast + TTS recitation.
    """
    from core.ritual_generator import _load_sutra_db

    db = _load_sutra_db()
    passages = db.get("sutra_passages", [])
    return {
        "status": "success",
        "total": len(passages),
        "sutras": [
            {
                "id": p.get("id"),
                "sutra": p.get("sutra"),
                "sanskrit_name": p.get("sanskrit_name", ""),
                "chapter": p.get("chapter", ""),
                "theme": p.get("theme", ""),
                "provenance": p.get("provenance", "unknown"),
                "tags": p.get("tags", []),
                "passage": p.get("passage", ""),
                "context": p.get("context", ""),
            }
            for p in passages
        ],
    }


@router.post("/sutra-recitation", response_model=SutraRecitationResponse)
async def sutra_recitation(request: SutraRecitationRequest):
    """Recite a sutra passage with crystal bowl accompaniment and optional TTS.

    Pipeline:
        1. Select passage by ``sutra_id`` (exact) or ``theme`` (tag match)
        2. Convert IAST Sanskrit → TTS-friendly phonetics
        3. Resolve carrier frequencies (rate_values / direct_freq / auto-tune)
        4. Start crystal bowl broadcast
        5. Recite via TTS (optional, controlled by ``recite_with_tts``)

    Each downstream stage is wrapped in try/except so the passage text and
    TTS-friendly version are always returned, even if crystal broadcast or
    TTS fail.
    """
    from core.ritual_generator import _load_sutra_db
    from core.sanskrit_tts import preprocess_for_tts

    logger.info(
        f"📜 Sutra recitation: sutra_id={request.sutra_id}, theme={request.theme}, "
        f"repeat={request.repeat_count}, tts={request.recite_with_tts}"
    )

    # ── Session id (best-effort via orchestrator; fallback to UUID) ────────
    session_id = f"sutra_{uuid.uuid4().hex[:12]}"
    try:
        session_id = await orchestrator_bridge.create_session(
            intention=f"sutra_recitation:{request.sutra_id or request.theme or 'auto'}",
            targets=[{"type": "universal", "identifier": "all beings"}],
            modalities=["sutra", "crystal_bowl"],
            duration=request.duration_minutes * 60,
        )
    except Exception as exc:
        logger.warning(f"orchestrator_bridge.create_session failed, using local id: {exc}")

    # ── 1. Select passage ─────────────────────────────────────────────────
    db = _load_sutra_db()
    passages = db.get("sutra_passages", [])
    if not passages:
        raise HTTPException(status_code=503, detail="sutra_passages.json not available")

    selected: dict | None = None
    if request.sutra_id:
        selected = next((p for p in passages if p.get("id") == request.sutra_id), None)
        if selected is None:
            available_ids = [p.get("id") for p in passages]
            raise HTTPException(
                status_code=404,
                detail=f"sutra_id '{request.sutra_id}' not found. Available: {available_ids}",
            )
    else:
        # Theme-based selection: score by tag overlap, pick from top tier
        target_tags = {t.strip().lower() for t in (request.theme or "dedication").split(",")}
        scored: list[tuple[int, dict]] = []
        for p in passages:
            passage_tags = {t.lower() for t in p.get("tags", [])}
            overlap = len(passage_tags & target_tags)
            if overlap > 0:
                scored.append((overlap, p))
        if not scored:
            # Fall back to first passage
            selected = passages[0]
        else:
            scored.sort(key=lambda kv: -kv[0])
            top_score = scored[0][0]
            top_tier = [p for score, p in scored if score == top_score]
            import random as _random

            selected = _random.choice(top_tier)

    sutra = selected.get("sutra", "the Sutras")
    sanskrit_name = selected.get("sanskrit_name", "")
    chapter = selected.get("chapter", "")
    theme = selected.get("theme", request.theme or "universal")
    tags = selected.get("tags", [])
    passage = selected.get("passage", "").strip()
    context = selected.get("context", "").strip() or None

    if not passage:
        raise HTTPException(status_code=500, detail=f"Selected passage '{selected.get('id')}' has empty text")

    # ── 2. Convert to TTS-friendly phonetics ──────────────────────────────
    try:
        passage_tts = preprocess_for_tts(passage)
    except Exception as exc:
        logger.warning(f"sanskrit_tts.preprocess_for_tts failed, using raw passage: {exc}")
        passage_tts = passage

    # ── 3. Resolve carrier frequencies ────────────────────────────────────
    frequencies: list[float] = []
    solfeggio_names: list[str] = []
    carrier_amplitude: float = 0.3

    try:
        from core.rate_to_audio import map_rate_to_carriers

        rate_values = request.rate_values
        if not rate_values:
            if request.direct_freq is not None:
                frequencies = [7.83, float(request.direct_freq)]
                solfeggio_names = ["Schumann Base", f"{float(request.direct_freq):.2f} Hz"]
            else:
                # Auto-tune from sutra theme + name
                theme_freq_map = {
                    "protection": 396,
                    "healing": 528,
                    "dedication": 639,
                    "loss": 417,
                    "impermanence": 852,
                    "emptiness": 963,
                    "generosity": 639,
                }
                auto_freq = theme_freq_map.get(theme, 528)
                frequencies = [7.83, float(auto_freq)]
                solfeggio_names = ["Schumann Base", f"{auto_freq} Hz"]
        elif rate_values and not frequencies:
            carriers = map_rate_to_carriers(rate_values, potency=1.0)
            frequencies = list(carriers.frequencies)
            solfeggio_names = list(carriers.solfeggio_names)
            carrier_amplitude = carriers.amplitude
    except Exception as exc:
        logger.warning(f"Frequency resolution failed, using fallback [7.83, 528.0]: {exc}")
        frequencies = [7.83, 528.0]
        solfeggio_names = ["Schumann Base", "Mi (Transformation)"]

    # ── 4. Crystal bowl broadcast (non-fatal) ─────────────────────────────
    crystal_output: dict | None = None
    try:
        from container import container as _container

        crystal_output = _container.crystal.broadcast_intention(
            intention=f"Recitation of {sutra}",
            frequencies=frequencies,
            duration=request.duration_minutes * 60,
            hardware_level=2,
            prayer_bowl_mode=True,
            amplitude=carrier_amplitude,
        )
    except Exception as exc:
        logger.warning(f"Crystal broadcast failed (continuing without audio): {exc}")

    # ── 5. TTS recitation (non-fatal) ─────────────────────────────────────
    tts_result: dict | None = None
    if request.recite_with_tts:
        try:
            from core.tts_provider import get_tts_provider

            provider = get_tts_provider()
            if provider is not None:
                # Build the recitation text — may repeat the passage
                recitation_text = (passage_tts + "\n\n") * request.repeat_count
                recitation_text = recitation_text.strip()

                tts_result = {
                    "status": "queued",
                    "text_length": len(recitation_text),
                    "repeat_count": request.repeat_count,
                    "provider": getattr(provider, "name", "unknown"),
                }

                # Fire-and-forget async recitation (same pattern as recite_ritual)
                import asyncio as _asyncio

                async def _speak():
                    try:
                        await provider.speak_async(recitation_text, role="dharma_teaching")
                        tts_result["status"] = "completed"
                    except Exception as exc:
                        tts_result["status"] = "failed"
                        tts_result["error"] = str(exc)

                try:
                    loop = _asyncio.get_running_loop()
                    _asyncio.ensure_future(_speak())
                except RuntimeError:
                    # No running loop — run synchronously in a thread
                    import threading

                    def _run():
                        try:
                            _asyncio.run(_speak())
                        except Exception as exc:
                            tts_result["status"] = "failed"
                            tts_result["error"] = str(exc)

                    threading.Thread(target=_run, daemon=True).start()
            else:
                tts_result = {"status": "no_provider", "error": "TTS provider unavailable"}
        except Exception as exc:
            logger.warning(f"TTS recitation failed (continuing without audio): {exc}")
            tts_result = {"status": "failed", "error": str(exc)}

    return SutraRecitationResponse(
        status="success",
        session_id=session_id,
        sutra=sutra,
        sanskrit_name=sanskrit_name,
        chapter=chapter,
        theme=theme,
        tags=tags,
        passage=passage,
        passage_tts_friendly=passage_tts,
        context=context,
        frequencies=frequencies,
        solfeggio_names=solfeggio_names,
        crystal_output=crystal_output,
        tts_result=tts_result,
    )


@router.get("/intentions")
async def list_intentions():
    """List all available intention types"""
    return {
        "status": "success",
        "intentions": [
            {
                "id": "healing",
                "name": "Healing",
                "frequency": 528,
                "frequency_name": "528 Hz - DNA Repair, Love, Transformation",
                "description": "Physical, emotional, and spiritual healing",
            },
            {
                "id": "liberation",
                "name": "Liberation",
                "frequency": 396,
                "frequency_name": "396 Hz - Liberation from Guilt & Fear",
                "description": "Freedom from suffering and negative patterns",
            },
            {
                "id": "empowerment",
                "name": "Empowerment",
                "frequency": 528,
                "frequency_name": "528 Hz - Transformation",
                "description": "Personal power and positive change",
            },
            {
                "id": "protection",
                "name": "Protection",
                "frequency": 741,
                "frequency_name": "741 Hz - Awakening Intuition",
                "description": "Spiritual and energetic protection",
            },
            {
                "id": "reconciliation",
                "name": "Reconciliation",
                "frequency": 639,
                "frequency_name": "639 Hz - Connecting Relationships",
                "description": "Harmony and mending relationships",
            },
            {
                "id": "peace",
                "name": "Peace",
                "frequency": 852,
                "frequency_name": "852 Hz - Spiritual Order",
                "description": "Inner and outer peace",
            },
            {
                "id": "love",
                "name": "Love",
                "frequency": 528,
                "frequency_name": "528 Hz - Love Frequency",
                "description": "Universal compassion and loving-kindness",
            },
            {
                "id": "wisdom",
                "name": "Wisdom",
                "frequency": 963,
                "frequency_name": "963 Hz - Divine Consciousness",
                "description": "Higher wisdom and enlightenment",
            },
        ],
    }


@router.get("/frequencies")
async def list_frequencies():
    """List all sacred frequencies"""
    return {
        "status": "success",
        "solfeggio_frequencies": [
            {"hz": 396, "name": "Liberation from Guilt & Fear"},
            {"hz": 417, "name": "Undoing Situations & Facilitating Change"},
            {"hz": 528, "name": "DNA Repair, Love, Transformation"},
            {"hz": 639, "name": "Connecting Relationships"},
            {"hz": 741, "name": "Awakening Intuition"},
            {"hz": 852, "name": "Returning to Spiritual Order"},
            {"hz": 963, "name": "Divine Consciousness, Pineal Activation"},
        ],
        "planetary_frequencies": [
            {"hz": 136.10, "name": "Earth (OM)", "chakra": "Heart"},
            {"hz": 126.22, "name": "Sun", "chakra": "Third Eye"},
            {"hz": 210.42, "name": "Moon", "chakra": "Sacral"},
            {"hz": 144.72, "name": "Mars", "chakra": "Solar Plexus"},
            {"hz": 183.58, "name": "Jupiter", "chakra": "Throat"},
            {"hz": 147.85, "name": "Saturn", "chakra": "Root"},
            {"hz": 207.36, "name": "Uranus", "chakra": "Third Eye"},
            {"hz": 221.23, "name": "Neptune", "chakra": "Crown"},
        ],
        "other_sacred_frequencies": [
            {"hz": 432, "name": "Cosmic A (Verdi's A, Natural Tuning)"},
            {"hz": 111, "name": "Holy Frequency (Cellular Regeneration)"},
            {"hz": 7.83, "name": "Schumann Resonance (Earth's Heartbeat)"},
        ],
    }


@router.get("/rates/search")
async def search_rates(query: str = "", category: str | None = None, limit: int = 20):
    """Search radionics rates by name, description, or category"""
    try:
        all_rates = []
        rate_dirs = [
            os.path.join(os.path.dirname(__file__), "../../../../knowledge/radionics_rates"),
        ]

        for rate_dir in rate_dirs:
            rate_dir = os.path.normpath(rate_dir)
            if os.path.exists(rate_dir):
                for fname in os.listdir(rate_dir):
                    if fname.endswith(".json"):
                        fpath = os.path.join(rate_dir, fname)
                        try:
                            with open(fpath, encoding="utf-8") as f:
                                data = json.load(f)
                            cat_name = fname.replace(".json", "").replace("_", " ")
                            if isinstance(data, list):
                                for entry in data:
                                    name = entry.get("name", entry.get("rate_name", ""))
                                    desc = entry.get("description", entry.get("notes", ""))
                                    values = entry.get("rate", entry.get("values", []))
                                    if isinstance(values, str):
                                        try:
                                            values = [int(v.strip()) for v in values.split("-")]
                                        except ValueError:
                                            values = []
                                    rate_cat = entry.get("category", cat_name)
                                    if (
                                        query.lower() in name.lower()
                                        or query.lower() in desc.lower()
                                        or query.lower() in rate_cat.lower()
                                    ):
                                        if category and category.lower() not in rate_cat.lower():
                                            continue
                                        all_rates.append(
                                            {"name": name, "description": desc, "values": values, "category": rate_cat}
                                        )
                        except Exception:
                            continue

        return {"status": "success", "results": all_rates[:limit], "total": len(all_rates), "query": query}
    except Exception as e:
        logger.error(f"Rate search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rates/categories")
async def list_rate_categories():
    """List available rate categories"""
    try:
        categories = []
        rate_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "../../../../knowledge/radionics_rates"))
        if os.path.exists(rate_dir):
            for fname in os.listdir(rate_dir):
                if fname.endswith(".json"):
                    cat_name = fname.replace(".json", "").replace("_", " ")
                    categories.append({"id": fname.replace(".json", ""), "name": cat_name.title()})
        return {"status": "success", "categories": categories}
    except Exception as e:
        logger.error(f"Rate categories error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rates/generate-signature")
async def generate_signature_rate(name: str, num_dials: int = 3, algorithm: str = "mixed"):
    """Generate a radionics signature rate from a name/intention"""
    try:
        from core.radionics_engine import SignatureCalculator

        calc = SignatureCalculator()
        rate = calc.text_to_rate(name, num_dials=num_dials, max_value=100, algorithm=algorithm)
        return {"status": "success", "rate": rate.to_dict()}
    except Exception as e:
        logger.error(f"Signature generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Crystal Grid & Programming ───


@router.get("/crystal/grid")
async def get_crystal_grid():
    """Get current crystal grid configuration."""
    return {
        "status": "success",
        "grid": {
            "type": "double-hexagon",
            "crystalType": "quartz",
            "radius": 4,
            "showEnergyField": True,
            "intention": "May all beings be happy",
            "crystalCount": 13,
            "active": False,
        },
        "crystals": [
            {"id": "quartz", "name": "Clear Quartz", "color": "#ffffff", "properties": ["amplification", "clarity"]},
            {"id": "amethyst", "name": "Amethyst", "color": "#9966ff", "properties": ["protection", "spiritual"]},
            {"id": "rose-quartz", "name": "Rose Quartz", "color": "#ffb6c1", "properties": ["love", "compassion"]},
            {"id": "citrine", "name": "Citrine", "color": "#ffd700", "properties": ["abundance", "energy"]},
        ],
    }


@router.post("/crystal/program")
async def program_crystal(crystal_id: str = "quartz", intention: str = "Universal Peace"):
    """Program a crystal with an intention."""
    return {
        "status": "success",
        "crystal_id": crystal_id,
        "intention": intention,
        "programmed_at": __import__("time").time(),
        "message": f"Crystal {crystal_id} programmed with intention: {intention}",
    }


@router.get("/status/{session_id}")
async def get_broadcast_status(session_id: str):
    """Get status of a broadcast session"""
    try:
        # In real implementation, would query session database
        return {
            "status": "success",
            "session_id": session_id,
            "state": "active",
            "progress_percent": 75,
            "estimated_time_remaining_seconds": 120,
            "current_mops": 17.73,
            "thermal_status": "optimal",
        }

    except Exception as e:
        logger.error(f"❌ Status check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
