"""
Time Cycle Broadcaster API Endpoints for Vajra.Stream
"""

import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from container import container

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/time-cycles", tags=["time-cycles"])


class TimeBroadcastRequest(BaseModel):
    event_id: str = Field(..., description="ID of the historical event")
    target_date: Optional[str] = Field(None, description="Target date in YYYY-MM-DD format (uses event default if None)")
    duration_seconds: int = Field(60, description="Duration of the broadcast in seconds")
    create_visualization: bool = Field(True, description="Whether to generate a daily Rothko visualization")


class RunCycleRequest(BaseModel):
    event_id: str = Field(..., description="ID of the historical event")
    start_date: Optional[str] = Field(None, description="Override start date YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="Override end date YYYY-MM-DD")
    step_days: int = Field(1, description="Step size in days between broadcasts")
    duration_per_day: int = Field(10, description="Duration per simulated day in seconds")
    create_visualizations: bool = Field(True, description="Whether to create visual representations")


@router.get("/status")
async def get_status():
    """Get time cycle service status"""
    try:
        status = container.time_cycles.get_status()
        return status
    except Exception as e:
        logger.error(f"Error getting time cycle status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events")
async def get_events():
    """Get list of historical suffering periods"""
    try:
        broadcaster = container.time_cycles.broadcaster
        if broadcaster is None:
            return {"events": []}
        return {"events": broadcaster.list_events()}
    except Exception as e:
        logger.error(f"Error getting historical events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/broadcast")
async def broadcast_to_date(request: TimeBroadcastRequest):
    """Broadcast healing energy to a specific event and date"""
    try:
        broadcaster = container.time_cycles.broadcaster
        if broadcaster is None:
            raise HTTPException(status_code=500, detail="Time cycle broadcaster not available")

        event = broadcaster.get_event_by_id(request.event_id)
        if not event:
            raise HTTPException(status_code=404, detail=f"Event {request.event_id} not found")

        if request.target_date:
            date_val = datetime.strptime(request.target_date, "%Y-%m-%d")
        else:
            date_val = datetime.strptime(event["start_date"], "%Y-%m-%d")

        result = broadcaster.broadcast_to_date(
            event=event,
            date=date_val,
            duration_seconds=request.duration_seconds,
            create_visualization=request.create_visualization
        )
        return result
    except Exception as e:
        logger.error(f"Error broadcasting to time cycle: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-cycle")
async def run_cycle(request: RunCycleRequest):
    """Run a full cycle through an event period"""
    try:
        broadcaster = container.time_cycles.broadcaster
        if broadcaster is None:
            raise HTTPException(status_code=500, detail="Time cycle broadcaster not available")

        event = broadcaster.get_event_by_id(request.event_id)
        if not event:
            raise HTTPException(status_code=404, detail=f"Event {request.event_id} not found")

        # Run daily cycle
        results = broadcaster.run_daily_cycle(
            event_id=request.event_id,
            start_date=request.start_date,
            end_date=request.end_date,
            step_days=request.step_days,
            duration_per_day=request.duration_per_day,
            create_visualizations=request.create_visualizations
        )
        return {"status": "success", "results": results}
    except Exception as e:
        logger.error(f"Error running daily time cycle: {e}")
        raise HTTPException(status_code=500, detail=str(e))
