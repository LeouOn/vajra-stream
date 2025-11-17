"""
RNG Attunement API Endpoints
Provides REST API access to RNG attunement readings
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum

from backend.core.services.rng_attunement_service import (
    get_rng_service,
    NeedleState,
    ReadingQuality
)

router = APIRouter(prefix="/rng-attunement", tags=["rng-attunement"])


# Request/Response Models
class CreateSessionRequest(BaseModel):
    """Request to create new RNG session"""
    session_id: Optional[str] = Field(None, description="Optional custom session ID")
    baseline_tone_arm: float = Field(5.0, ge=0, le=10, description="Starting tone arm position (0-10)")
    sensitivity: float = Field(1.0, ge=0.1, le=5.0, description="Reading sensitivity multiplier")

    class Config:
        json_schema_extra = {
            "example": {
                "baseline_tone_arm": 5.0,
                "sensitivity": 1.0
            }
        }


class SessionResponse(BaseModel):
    """Response with session ID"""
    session_id: str
    message: str


class ReadingResponse(BaseModel):
    """Single attunement reading"""
    timestamp: float
    raw_value: float
    tone_arm: float
    needle_position: float
    needle_state: str
    quality: str
    entropy: float
    coherence: float
    trend: float
    floating_needle_score: float

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": 1700000000.0,
                "raw_value": 0.523,
                "tone_arm": 5.1,
                "needle_position": 2.3,
                "needle_state": "floating",
                "quality": "excellent",
                "entropy": 0.45,
                "coherence": 0.78,
                "trend": 0.05,
                "floating_needle_score": 0.85
            }
        }


class SessionSummaryResponse(BaseModel):
    """Summary statistics for a session"""
    session_id: str
    total_readings: int
    floating_needle_count: int
    last_fn_time: Optional[float]
    duration_seconds: float
    avg_tone_arm: float
    avg_coherence: float
    avg_entropy: float
    needle_state_distribution: Dict[str, int]
    quality_distribution: Dict[str, int]
    is_active: bool


class NeedleStateInfo(BaseModel):
    """Information about needle states"""
    state: str
    description: str


class QualityInfo(BaseModel):
    """Information about reading quality levels"""
    quality: str
    description: str


# Endpoints
@router.post("/session/create", response_model=SessionResponse)
async def create_session(request: CreateSessionRequest):
    """
    Create a new RNG attunement session

    This initializes a new session for generating attunement readings.
    Each session maintains its own baseline and history of readings.

    **Purpose**: Similar to starting an E-meter session in auditing,
    this begins tracking subtle energetic fluctuations that may be
    influenced by consciousness, intention, or paranormal activity.
    """
    service = get_rng_service()

    session_id = service.create_session(
        session_id=request.session_id,
        baseline_tone_arm=request.baseline_tone_arm,
        sensitivity=request.sensitivity
    )

    return SessionResponse(
        session_id=session_id,
        message="RNG attunement session created successfully"
    )


@router.get("/reading/{session_id}", response_model=ReadingResponse)
async def get_reading(session_id: str):
    """
    Get a new attunement reading for a session

    This generates a quantum-random reading that radionics practitioners
    believe may be influenced by psychic or paranormal activity.

    **Interpretation Guide**:
    - **Tone Arm** (0-10): Overall charge level. Ideally stays 2-6.
    - **Needle Position** (-100 to +100): Momentary fluctuations. Watch for patterns.
    - **Needle State**: Key indicator:
        - FLOATING: Indicates release, end phenomenon (good sign!)
        - RISING: Building charge (resistance/charge on item)
        - FALLING: Releasing charge (processing occurring)
        - ROCKSLAM: Heavy charge (significant item being addressed)
        - THETA_BOP: Rhythmic pattern (may indicate specific type of charge)
        - STUCK: No movement (neutral or blocked)
    - **Coherence** (0-1): Higher = more organized/patterned (vs chaotic)
    - **Entropy** (0-1): Higher = more random/chaotic
    - **FN Score** (0-1): Likelihood of genuine Floating Needle (release indicator)

    **Similar to**: Scientology E-meter reads, galvanic skin response,
    but based on RNG fluctuations rather than electrical resistance.
    """
    service = get_rng_service()

    reading = service.get_reading(session_id)

    if reading is None:
        raise HTTPException(status_code=404, detail="Session not found or inactive")

    return ReadingResponse(
        timestamp=reading.timestamp,
        raw_value=reading.raw_value,
        tone_arm=reading.tone_arm,
        needle_position=reading.needle_position,
        needle_state=reading.needle_state.value,
        quality=reading.quality.value,
        entropy=reading.entropy,
        coherence=reading.coherence,
        trend=reading.trend,
        floating_needle_score=reading.floating_needle_score
    )


@router.get("/session/{session_id}/summary", response_model=SessionSummaryResponse)
async def get_session_summary(session_id: str):
    """
    Get summary statistics for an attunement session

    Provides aggregate data about the session including:
    - Total readings taken
    - Number of floating needles detected
    - Average values
    - Distribution of needle states and quality
    """
    service = get_rng_service()

    summary = service.get_session_summary(session_id)

    if summary is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionSummaryResponse(**summary)


@router.post("/session/{session_id}/stop")
async def stop_session(session_id: str):
    """
    Stop an active attunement session

    Marks the session as inactive. No new readings can be generated
    for stopped sessions, but historical data remains accessible.
    """
    service = get_rng_service()

    success = service.stop_session(session_id)

    if not success:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"message": "Session stopped successfully", "session_id": session_id}


@router.get("/sessions", response_model=List[str])
async def get_all_sessions():
    """
    Get list of all session IDs

    Returns all sessions (both active and stopped).
    """
    service = get_rng_service()
    return service.get_all_sessions()


@router.get("/info/needle-states", response_model=List[NeedleStateInfo])
async def get_needle_states_info():
    """
    Get information about all needle states

    Provides descriptions of what each needle state means
    in the context of attunement readings.
    """
    return [
        NeedleStateInfo(
            state=NeedleState.FLOATING.value,
            description="Small rhythmic oscillations. Indicates release, end phenomenon (EP). Good indicator to end process."
        ),
        NeedleStateInfo(
            state=NeedleState.RISING.value,
            description="Consistent upward movement. Indicates increasing charge, resistance on item being addressed."
        ),
        NeedleStateInfo(
            state=NeedleState.FALLING.value,
            description="Consistent downward movement. Indicates releasing charge, processing occurring."
        ),
        NeedleStateInfo(
            state=NeedleState.ROCKSLAM.value,
            description="Violent rapid oscillations. Indicates heavy charge on item. Significant material being addressed."
        ),
        NeedleStateInfo(
            state=NeedleState.THETA_BOP.value,
            description="Regular rhythmic movement. May indicate specific type of charge or pattern."
        ),
        NeedleStateInfo(
            state=NeedleState.STUCK.value,
            description="Little to no movement. Neutral state or blocked/stuck state."
        )
    ]


@router.get("/info/quality-levels", response_model=List[QualityInfo])
async def get_quality_levels_info():
    """
    Get information about reading quality levels

    Describes what each quality level indicates about the reading.
    """
    return [
        QualityInfo(
            quality=ReadingQuality.EXCELLENT.value,
            description="Clear, stable signal with high coherence. Optimal conditions for attunement work."
        ),
        QualityInfo(
            quality=ReadingQuality.GOOD.value,
            description="Stable signal with minor fluctuations. Good conditions for most applications."
        ),
        QualityInfo(
            quality=ReadingQuality.FAIR.value,
            description="Moderate noise present. Usable but less reliable readings."
        ),
        QualityInfo(
            quality=ReadingQuality.POOR.value,
            description="High noise, unstable signal. May indicate environmental interference or lack of attunement."
        ),
        QualityInfo(
            quality=ReadingQuality.DISRUPTED.value,
            description="External interference or extreme fluctuations. May indicate rockslam or environmental disruption."
        )
    ]


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    service = get_rng_service()
    return {
        "status": "healthy",
        "service": "rng_attunement",
        "active_sessions": len(service.get_all_sessions())
    }
