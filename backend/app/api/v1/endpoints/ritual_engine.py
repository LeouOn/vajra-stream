"""
Ritual Engine API — start, stop, configure, and monitor the autonomous ritual engine.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class RitualConfigUpdate(BaseModel):
    enabled: bool | None = None
    min_timing_quality: str | None = None
    tts_enabled: bool | None = None
    max_per_hour: int | None = None
    pause_between_seconds: int | None = None
    favored_genres: list[str] | None = None


@router.get("/status", summary="Get ritual engine status")
async def get_status():
    """Current engine state, history, schedule, and merit stats."""
    from core.ritual_engine import get_ritual_engine

    engine = get_ritual_engine()
    return {
        "status": engine.status,
        "history": engine.get_history(20),
        "merit": engine.get_merit_stats(),
    }


@router.post("/start", summary="Start autonomous ritual engine")
async def start_engine():
    """Begin autonomous 24/7 ritual orchestration."""
    from core.ritual_engine import get_ritual_engine

    engine = get_ritual_engine()
    await engine.start()
    return {"status": "started", "state": engine.state.value}


@router.post("/stop", summary="Stop autonomous ritual engine")
async def stop_engine():
    """Pause the autonomous engine."""
    from core.ritual_engine import get_ritual_engine

    engine = get_ritual_engine()
    await engine.stop()
    return {"status": "stopped", "state": engine.state.value}


@router.post("/trigger", summary="Manually trigger a ritual now")
async def trigger_ritual():
    """Immediately select and execute the best practice for this moment."""
    from core.ritual_engine import get_ritual_engine

    engine = get_ritual_engine()
    record = await engine.trigger_now()
    if record is None:
        return {"status": "no_suitable_practice", "message": "No practice scored above threshold"}
    return {"status": "executed", "ritual": record.to_dict()}


@router.post("/config", summary="Update engine configuration")
async def update_config(config: RitualConfigUpdate):
    """Update engine settings."""
    from core.ritual_engine import get_ritual_engine

    engine = get_ritual_engine()
    updates = config.model_dump(exclude_none=True)
    engine.update_config(**updates)
    return {"status": "updated", "config": engine.status["config"]}


@router.get("/schedule", summary="Get upcoming ritual schedule")
async def get_schedule():
    """Predicted favorable hours for the next 24 hours."""
    from core.ritual_engine import get_ritual_engine

    engine = get_ritual_engine()
    return {"schedule": engine.status.get("schedule", [])}


@router.get("/merit", summary="Get merit accumulation stats")
async def get_merit():
    """Today's and total merit accumulation."""
    from core.ritual_engine import get_ritual_engine

    engine = get_ritual_engine()
    return engine.get_merit_stats()
