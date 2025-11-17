"""
Automation/Scheduler API Endpoints

Control automated blessing rotation through populations.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from backend.core.services.blessing_scheduler import (
    get_scheduler,
    SchedulerMode,
    SchedulerConfig
)

router = APIRouter(prefix="/automation", tags=["automation"])


# Request/Response Models
class StartAutomationRequest(BaseModel):
    """Request to start automation"""
    mode: SchedulerMode = SchedulerMode.ROUND_ROBIN
    duration_per_population: int = Field(1800, ge=60, le=86400, description="Seconds per population (1 min - 24 hours)")
    transition_pause: int = Field(30, ge=0, le=600, description="Pause between populations (0-10 min)")
    link_rng: bool = Field(True, description="Create RNG session per population")
    auto_dedicate: bool = Field(True, description="Automatic merit dedication")
    continuous_mode: bool = Field(True, description="Run indefinitely (loop)")
    only_active: bool = Field(True, description="Only include active populations")
    min_priority: int = Field(1, ge=1, le=10, description="Minimum priority to include")

    class Config:
        json_schema_extra = {
            "example": {
                "mode": "round_robin",
                "duration_per_population": 1800,
                "link_rng": True,
                "continuous_mode": True
            }
        }


class AutomationSessionResponse(BaseModel):
    """Automation session information"""
    session_id: str
    message: str
    populations_in_queue: int


class SessionStatsResponse(BaseModel):
    """Session statistics"""
    session_id: str
    status: str
    mode: str
    start_time: float
    total_duration: float
    cycle_count: int
    populations_in_queue: int
    current_index: int
    current_population_id: Optional[str]
    current_slideshow_id: Optional[str]
    current_rng_id: Optional[str]
    completed_sessions: int
    total_photos_blessed: int
    total_mantras: int
    total_rng_floating_needles: int
    session_history: List[Dict[str, Any]]


class CurrentStatusResponse(BaseModel):
    """Current status"""
    session_id: str
    status: str
    current_population: Optional[Dict[str, Any]]
    elapsed_seconds: float
    target_duration: int
    progress_percentage: float


class QueueItemResponse(BaseModel):
    """Queue item information"""
    position: int
    is_current: bool
    id: str
    name: str
    category: str
    priority: int
    is_urgent: bool
    photo_count: int
    last_blessed: Optional[float]


# Endpoints

@router.post("/start", response_model=AutomationSessionResponse)
async def start_automation(request: StartAutomationRequest):
    """
    Start automated blessing rotation

    This begins continuous cycling through populations, blessing each
    for the configured duration.

    **Modes** (Phase 1: round_robin only):
    - round_robin: Equal time to all populations (fair distribution)

    **continuous_mode**:
    - True: Loops back to start after completing all populations
    - False: Stops after one complete cycle

    **Example Use Cases**:
    - 24/7 operation: continuous=True, duration=30min each
    - Daily practice: continuous=False, duration=20min each
    - Intensive work: continuous=True, duration=60min each

    **Integration**:
    - Creates blessing slideshow for each population
    - Links RNG monitoring if link_rng=True
    - Automatically transitions between populations
    - Records all statistics

    **Returns**: session_id to control automation
    """
    scheduler = get_scheduler()

    config = SchedulerConfig(
        mode=request.mode,
        duration_per_population=request.duration_per_population,
        transition_pause=request.transition_pause,
        link_rng=request.link_rng,
        auto_dedicate=request.auto_dedicate,
        continuous_mode=request.continuous_mode,
        only_active=request.only_active,
        min_priority=request.min_priority
    )

    try:
        session_id = scheduler.start_automation(config)

        # Get initial stats
        stats = scheduler.get_session_stats(session_id)

        return AutomationSessionResponse(
            session_id=session_id,
            message="Automated blessing rotation started successfully",
            populations_in_queue=stats['populations_in_queue']
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start automation: {str(e)}")


@router.post("/{session_id}/stop", response_model=SessionStatsResponse)
async def stop_automation(session_id: str):
    """
    Stop automated rotation

    Stops the current population's blessing, ends automation,
    and returns complete statistics.

    Safe to call at any time. Will gracefully stop current blessing
    and record all data.
    """
    scheduler = get_scheduler()

    stats = scheduler.stop_automation(session_id)

    if not stats:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionStatsResponse(**stats)


@router.post("/{session_id}/pause")
async def pause_automation(session_id: str):
    """
    Pause automated rotation

    Pauses current population's blessing. Can be resumed later
    without losing progress.

    Useful for:
    - Taking breaks
    - Reviewing current population manually
    - Adjusting settings
    """
    scheduler = get_scheduler()

    success = scheduler.pause_automation(session_id)

    if not success:
        raise HTTPException(status_code=404, detail="Session not found or not running")

    return {"message": "Automation paused", "session_id": session_id}


@router.post("/{session_id}/resume")
async def resume_automation(session_id: str):
    """
    Resume paused automation

    Continues from where it was paused.
    """
    scheduler = get_scheduler()

    success = scheduler.resume_automation(session_id)

    if not success:
        raise HTTPException(status_code=404, detail="Session not found or not paused")

    return {"message": "Automation resumed", "session_id": session_id}


@router.get("/{session_id}/stats", response_model=SessionStatsResponse)
async def get_session_stats(session_id: str):
    """
    Get session statistics

    Returns comprehensive statistics including:
    - Overall session info
    - Populations blessed
    - Total mantras sent
    - RNG data
    - Complete history of all population sessions

    Can be called while session is active for real-time monitoring.
    """
    scheduler = get_scheduler()

    stats = scheduler.get_session_stats(session_id)

    if not stats:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionStatsResponse(**stats)


@router.get("/{session_id}/status", response_model=CurrentStatusResponse)
async def get_current_status(session_id: str):
    """
    Get current status

    Lightweight endpoint for real-time updates.

    Returns:
    - Current population being blessed
    - Time elapsed
    - Progress percentage
    - Session status

    Call this frequently (every 5-10 seconds) for UI updates.
    """
    scheduler = get_scheduler()

    status = scheduler.get_current_status(session_id)

    if not status:
        raise HTTPException(status_code=404, detail="Session not found")

    return CurrentStatusResponse(**status)


@router.get("/{session_id}/queue", response_model=List[QueueItemResponse])
async def get_queue(session_id: str):
    """
    Get upcoming populations in queue

    Shows what populations will be blessed next,
    in order, with their details.

    Useful for:
    - Preview upcoming blessings
    - Plan manual interventions
    - Monitor rotation order
    """
    scheduler = get_scheduler()

    queue = scheduler.get_queue(session_id)

    if queue is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return [QueueItemResponse(**item) for item in queue]


@router.get("/modes/list")
async def list_modes():
    """
    Get list of available scheduler modes

    **Phase 1**: Only round_robin available
    **Phase 2**: All modes enabled
    """
    return [
        {
            "value": SchedulerMode.ROUND_ROBIN.value,
            "name": "Round Robin",
            "description": "Equal time to all populations (fair distribution)",
            "available": True
        },
        {
            "value": SchedulerMode.PRIORITY_BASED.value,
            "name": "Priority Based",
            "description": "More time to higher priority populations",
            "available": False,  # Phase 2
            "phase": 2
        },
        {
            "value": SchedulerMode.TIME_WEIGHTED.value,
            "name": "Time Weighted",
            "description": "Prioritize populations that haven't been blessed recently",
            "available": False,  # Phase 2
            "phase": 2
        },
        {
            "value": SchedulerMode.RNG_GUIDED.value,
            "name": "RNG Guided",
            "description": "Extend sessions showing strong RNG response",
            "available": False,  # Phase 2
            "phase": 2
        },
        {
            "value": SchedulerMode.HYBRID.value,
            "name": "Hybrid",
            "description": "Intelligently combine multiple factors",
            "available": False,  # Phase 2
            "phase": 2
        },
        {
            "value": SchedulerMode.MANUAL.value,
            "name": "Manual",
            "description": "User controls all transitions",
            "available": False,  # Phase 2
            "phase": 2
        }
    ]


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    scheduler = get_scheduler()

    return {
        "status": "healthy",
        "service": "automation",
        "active_sessions": len(scheduler.sessions)
    }
