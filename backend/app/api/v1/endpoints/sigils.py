"""
Sigil Forging & Broadcasting Endpoints
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.services.mops_engine import mops_engine
from backend.core.services.sigil_service import sigil_service
from backend.core.services.vajra_service import vajra_service

router = APIRouter(prefix="/sigils", tags=["sigils"])


class ForgeRequest(BaseModel):
    intention: str
    kamea: str | None = "saturn"


class BroadcastRequest(BaseModel):
    intention: str
    sigil_id: str | None = None
    frequency_hz: float | None = 528.0
    duration_minutes: int | None = 5


@router.post("/forge")
async def forge_sigil(payload: ForgeRequest):
    """Generate a sigil from an intention text (SVG + AI Prompt)"""
    try:
        # Increment MOPS for divination/forging operations
        mops_engine.record_event("divination", 1)  # Forge operation acts as divination-strength focus

        result = await sigil_service.forge_sigil(payload.intention, payload.kamea)
        return {"status": "success", "sigil": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/broadcast")
async def broadcast_sigil(payload: BroadcastRequest):
    """Broadcast the energetic vibration of a forged sigil"""
    try:
        # Increment tuning events
        mops_engine.record_event("tuning", 1)

        # Trigger broadcast through vajra_service
        session_id = await vajra_service.create_session(
            name=f"Sigil Broadcast: {payload.intention[:30]}",
            intention=payload.intention,
            audio_frequency=payload.frequency_hz,
            duration=payload.duration_minutes * 60,
            astrology_enabled=True,
            hardware_enabled=True,
            visuals_enabled=True,
        )

        # Start session
        started = await vajra_service.start_session(session_id)

        if not started:
            raise HTTPException(status_code=500, detail="Failed to initiate scalar signal broadcast.")

        return {
            "status": "success",
            "session_id": session_id,
            "message": f"Broadcast of sigil '{payload.intention[:30]}...' initiated at {payload.frequency_hz} Hz.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
