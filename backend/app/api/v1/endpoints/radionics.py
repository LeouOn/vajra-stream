"""
Radionics API Endpoints for Vajra.Stream
Integrated scalar-radionics broadcasting system
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../../../'))

from core.integrated_scalar_radionics import (
    IntegratedScalarRadionicsBroadcaster,
    IntentionType,
    BroadcastConfiguration
)
from backend.core.orchestrator_bridge import orchestrator_bridge

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Global instance
broadcaster = IntegratedScalarRadionicsBroadcaster()

# Request Models
class BroadcastRequest(BaseModel):
    intention: str = Field(..., description="Intention type: healing, liberation, empowerment, protection, etc.")
    target_names: List[str] = Field(..., description="Names of targets for broadcast")
    duration_minutes: int = Field(default=10, ge=1, le=120, description="Duration in minutes")
    frequency_hz: Optional[float] = Field(None, description="Specific frequency (optional, auto-selected if not provided)")
    scalar_intensity: float = Field(default=0.8, ge=0.0, le=1.0, description="Scalar wave intensity")
    use_chakras: bool = Field(default=True, description="Activate chakra system")
    use_meridians: bool = Field(default=False, description="Activate meridian system")
    mantra: Optional[str] = Field(None, description="Optional mantra for broadcast")
    breathing_pattern: bool = Field(default=True, description="Use sacred breathing cycles")

class HealingProtocolRequest(BaseModel):
    target_name: str = Field(..., description="Name of person/situation to heal")
    duration_minutes: int = Field(default=10, ge=1, le=120, description="Duration")
    specific_intention: Optional[str] = Field(None, description="Specific healing intention")

class LiberationProtocolRequest(BaseModel):
    event_name: str = Field(..., description="Name of event/situation")
    souls_count: int = Field(default=1, ge=1, description="Estimated number of souls")
    duration_minutes: int = Field(default=30, ge=10, le=180, description="Duration")

# Response Models
class BroadcastResponse(BaseModel):
    status: str
    session_id: str
    intention: str
    targets: List[str]
    frequency_hz: float
    duration_seconds: float
    scalar_mops: float
    chakras_activated: List[str]
    meridians_activated: List[str]
    dedication: str

# Endpoints

@router.post("/broadcast", response_model=BroadcastResponse)
async def start_broadcast(request: BroadcastRequest, background_tasks: BackgroundTasks):
    """Start integrated scalar-radionics broadcast"""
    try:
        logger.info(f"📡 Starting broadcast: {request.intention} for {len(request.target_names)} targets")

        # Use OrchestratorBridge to create session
        targets = [{"type": "individual", "identifier": name} for name in request.target_names]
        modalities = []
        if request.use_chakras: modalities.append("chakras")
        if request.use_meridians: modalities.append("meridians")
        if request.scalar_intensity > 0: modalities.append("scalar")
        
        # Create session via orchestrator
        # Note: This is a synchronous call wrapped in async in the bridge
        session_id = await orchestrator_bridge.create_session(
            intention=request.intention,
            targets=targets,
            modalities=modalities,
            duration=request.duration_minutes * 60
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
            "wisdom": IntentionType.WISDOM
        }

        intention_type = intention_map.get(request.intention.lower(), IntentionType.HEALING)

        # Auto-select frequency if not provided
        frequency_mapping = {
            "healing": 528,      # DNA repair
            "liberation": 396,   # Liberation from fear
            "empowerment": 528,
            "protection": 741,   # Awakening intuition
            "reconciliation": 639,  # Connecting relationships
            "peace": 852,        # Spiritual order
            "love": 528,
            "wisdom": 963        # Divine consciousness
        }

        frequency_hz = request.frequency_hz or frequency_mapping.get(request.intention.lower(), 432)

        # Create broadcast configuration
        config = BroadcastConfiguration(
            intention=intention_type,
            frequency_hz=frequency_hz,
            target_names=request.target_names,
            duration_minutes=request.duration_minutes,
            scalar_intensity=request.scalar_intensity,
            use_chakras=request.use_chakras,
            use_meridians=request.use_meridians,
            mantra=request.mantra,
            breathing_pattern=request.breathing_pattern
        )

        # Simulate broadcast (in real implementation, this would run in background)
        import time
        # import uuid

        # session_id = str(uuid.uuid4())
        start_time = time.time()

        # Simulate broadcast processing
        await asyncio.sleep(min(2, request.duration_minutes))  # Shortened for API response

        duration = time.time() - start_time

        # Estimate scalar MOPS
        estimated_mops = 17.73 * request.scalar_intensity

        # Get activated systems
        chakras_activated = ["muladhara", "svadhisthana", "manipura", "anahata", "vishuddha", "ajna", "sahasrara"] if request.use_chakras else []

        meridians_activated = ["lung", "large_intestine", "stomach", "spleen", "heart", "small_intestine",
                              "bladder", "kidney", "pericardium", "triple_warmer", "gallbladder", "liver"] if request.use_meridians else []

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
            dedication=dedication
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
            breathing_pattern=True
        )

        response = await start_broadcast(broadcast_request, background_tasks)

        return {
            **response.dict(),
            "protocol": "healing",
            "frequency_name": "528 Hz - Solfeggio DNA Repair",
            "specific_intention": request.specific_intention
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
            breathing_pattern=True
        )

        response = await start_broadcast(broadcast_request, background_tasks)

        return {
            **response.dict(),
            "protocol": "liberation",
            "frequency_name": "396 Hz - Liberation from Guilt & Fear",
            "souls_count": request.souls_count,
            "event": request.event_name,
            "special_dedication": f"May the {request.souls_count} souls find peace, liberation, and the highest rebirth"
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
                "description": "Physical, emotional, and spiritual healing"
            },
            {
                "id": "liberation",
                "name": "Liberation",
                "frequency": 396,
                "frequency_name": "396 Hz - Liberation from Guilt & Fear",
                "description": "Freedom from suffering and negative patterns"
            },
            {
                "id": "empowerment",
                "name": "Empowerment",
                "frequency": 528,
                "frequency_name": "528 Hz - Transformation",
                "description": "Personal power and positive change"
            },
            {
                "id": "protection",
                "name": "Protection",
                "frequency": 741,
                "frequency_name": "741 Hz - Awakening Intuition",
                "description": "Spiritual and energetic protection"
            },
            {
                "id": "reconciliation",
                "name": "Reconciliation",
                "frequency": 639,
                "frequency_name": "639 Hz - Connecting Relationships",
                "description": "Harmony and mending relationships"
            },
            {
                "id": "peace",
                "name": "Peace",
                "frequency": 852,
                "frequency_name": "852 Hz - Spiritual Order",
                "description": "Inner and outer peace"
            },
            {
                "id": "love",
                "name": "Love",
                "frequency": 528,
                "frequency_name": "528 Hz - Love Frequency",
                "description": "Universal compassion and loving-kindness"
            },
            {
                "id": "wisdom",
                "name": "Wisdom",
                "frequency": 963,
                "frequency_name": "963 Hz - Divine Consciousness",
                "description": "Higher wisdom and enlightenment"
            }
        ]
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
            {"hz": 963, "name": "Divine Consciousness, Pineal Activation"}
        ],
        "planetary_frequencies": [
            {"hz": 136.10, "name": "Earth (OM)", "chakra": "Heart"},
            {"hz": 126.22, "name": "Sun", "chakra": "Third Eye"},
            {"hz": 210.42, "name": "Moon", "chakra": "Sacral"},
            {"hz": 144.72, "name": "Mars", "chakra": "Solar Plexus"},
            {"hz": 183.58, "name": "Jupiter", "chakra": "Throat"},
            {"hz": 147.85, "name": "Saturn", "chakra": "Root"},
            {"hz": 207.36, "name": "Uranus", "chakra": "Third Eye"},
            {"hz": 221.23, "name": "Neptune", "chakra": "Crown"}
        ],
        "other_sacred_frequencies": [
            {"hz": 432, "name": "Cosmic A (Verdi's A, Natural Tuning)"},
            {"hz": 111, "name": "Holy Frequency (Cellular Regeneration)"},
            {"hz": 7.83, "name": "Schumann Resonance (Earth's Heartbeat)"}
        ]
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
            "thermal_status": "optimal"
        }

    except Exception as e:
        logger.error(f"❌ Status check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
