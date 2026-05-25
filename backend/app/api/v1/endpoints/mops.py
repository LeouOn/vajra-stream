"""
MOPS Telemetry API Endpoints
"""

import asyncio
from fastapi import APIRouter, HTTPException
from backend.core.services.mops_engine import mops_engine

router = APIRouter(prefix="/mops", tags=["mops"])

@router.get("/current")
async def get_current_mops():
    """Get current rolling averages for MOPS telemetry"""
    try:
        averages = mops_engine.get_rolling_averages()
        return {
            "status": "success",
            "mops": averages,
            "timestamp": asyncio.get_event_loop().time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
async def get_mops_history():
    """Get cumulative session statistics for MOPS"""
    try:
        history = mops_engine.get_history()
        return {
            "status": "success",
            "history": history,
            "timestamp": asyncio.get_event_loop().time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
