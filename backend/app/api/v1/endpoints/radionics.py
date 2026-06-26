"""
Radionics API Endpoints for Vajra.Stream
Integrated scalar-radionics broadcasting system
"""

import asyncio
import json
import logging
import os
import sys

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../../../../"))

from backend.core.orchestrator_bridge import orchestrator_bridge
from core.integrated_scalar_radionics import BroadcastConfiguration, IntegratedScalarRadionicsBroadcaster, IntentionType

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
