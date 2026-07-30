"""
MOPS Telemetry API — real-time scalar wave performance endpoints.

Exposes REST and WebSocket endpoints for monitoring MOPS throughput,
scalar wave generation metrics, thermal state, and system load
from the Terra MOPS engine.
"""

import time

from fastapi import APIRouter, HTTPException

from backend.core.services.mops_engine import mops_engine

router = APIRouter(prefix="/mops", tags=["mops"])

_CACHE_TTL_SECONDS = 1.0
_cache: dict[str, tuple[float, dict]] = {}


def _cached_response(key: str, producer) -> dict:
    now = time.time()
    entry = _cache.get(key)
    if entry and now - entry[0] < _CACHE_TTL_SECONDS:
        return entry[1]
    value = producer()
    _cache[key] = (now, value)
    return value


@router.get("/current")
async def get_current_mops():
    """Get current rolling averages for MOPS telemetry"""
    try:
        return _cached_response(
            "current",
            lambda: {"status": "success", "mops": mops_engine.get_rolling_averages(), "timestamp": time.time()},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_mops_history():
    """Get cumulative session statistics for MOPS"""
    try:
        return _cached_response(
            "history", lambda: {"status": "success", "history": mops_engine.get_history(), "timestamp": time.time()}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
