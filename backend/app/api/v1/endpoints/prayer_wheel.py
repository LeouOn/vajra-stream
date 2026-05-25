"""
Digital Prayer Wheel API Endpoints for Vajra.Stream
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from container import container

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/prayer-wheel", tags=["prayer-wheel"])


class SpinRequest(BaseModel):
    mantra: str = Field("Om Mani Padme Hum", description="Mantra to spin on the wheel")
    rotations: int = Field(108, description="Number of rotations")
    speed: float = Field(1.0, description="Spinning speed multiplier")


class ContinuousRequest(BaseModel):
    mantras: List[str] = Field(["Om Mani Padme Hum"], description="List of mantras to spin")
    duration_minutes: int = Field(60, description="Duration in minutes")


class GeneratePrayerRequest(BaseModel):
    intention: str = Field("peace", description="Intention of the prayer")
    use_llm: bool = Field(True, description="Whether to use LLM for generation")
    tradition: str = Field("universal", description="Prayer tradition style")


@router.get("/status")
async def get_status():
    """Get prayer wheel status"""
    try:
        status = container.prayer_wheel.get_status()
        return status
    except Exception as e:
        logger.error(f"Error getting prayer wheel status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mantras")
async def get_mantras():
    """Get list of traditional mantras"""
    try:
        mantras = container.prayer_wheel.get_traditional_mantras()
        return {"mantras": mantras}
    except Exception as e:
        logger.error(f"Error getting traditional mantras: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/spin")
async def spin_wheel(request: SpinRequest):
    """Spin the digital prayer wheel"""
    try:
        result = container.prayer_wheel.spin_wheel(
            mantra=request.mantra,
            rotations=request.rotations,
            speed=request.speed
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        logger.error(f"Error spinning prayer wheel: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/continuous")
async def continuous_spinning(request: ContinuousRequest):
    """Start continuous prayer wheel spinning"""
    try:
        result = container.prayer_wheel.continuous_spinning(
            mantras=request.mantras,
            duration_minutes=request.duration_minutes
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        logger.error(f"Error starting continuous spinning: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-prayer")
async def generate_prayer(request: GeneratePrayerRequest):
    """Generate a prayer based on intention"""
    try:
        prayer = container.prayer_wheel.generate_prayer(
            intention=request.intention,
            use_llm=request.use_llm,
            tradition=request.tradition
        )
        return {"prayer": prayer}
    except Exception as e:
        logger.error(f"Error generating prayer: {e}")
        raise HTTPException(status_code=500, detail=str(e))
