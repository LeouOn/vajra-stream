"""
Scalar Waves API Endpoints for Vajra.Stream

Scalar wave value generation (RNG / chaotic streams) with thermal monitoring.

The MOPS throughput endpoints (``/benchmark``, ``/breathing-cycle`` and
``/mops-metrics``) were retired on 2026-10-14; see the "Decisions" section of
docs/DEVELOPMENT_ROADMAP.md. Work that takes real time is recorded in the
operations ledger (``/api/v1/operations``) instead of as a rate.
"""

import logging
import time
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.advanced_scalar_waves import ThermalMonitor

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Global instances
thermal_monitor = ThermalMonitor()


# Request Models
class ScalarGenerationRequest(BaseModel):
    method: str = Field(..., description="Method: qrng, lorenz, rossler, ca, hybrid")
    count: int = Field(default=10000, ge=100, le=10000000, description="Number of values to generate")
    intensity: float = Field(default=1.0, ge=0.0, le=1.0, description="Generation intensity (0.0-1.0)")


# Response Models
class ScalarGenerationResponse(BaseModel):
    status: str
    method: str
    count: int
    generation_time: float
    thermal_status: dict[str, Any]
    statistics: dict[str, float]


class ThermalStatusResponse(BaseModel):
    temperature: float
    load_average: float
    throttle_factor: float
    target_temp: float
    max_temp: float
    status: str


# Endpoints


@router.post("/generate", response_model=ScalarGenerationResponse)
async def generate_scalar_waves(request: ScalarGenerationRequest):
    """Generate scalar wave values using the specified method.

    Returns how many values were generated and the measured generation time.
    """
    try:
        logger.info(f"⚡ Scalar wave generation: {request.method}, count={request.count}")

        # Update thermal monitor
        thermal_monitor.update()

        start_time = time.time()

        # Use the container service to ensure events are emitted
        from container import container

        result = container.scalar_waves.generate(
            method=request.method, count=request.count, intensity=request.intensity
        )

        # The container service returns a dict like:
        # {'values': [...], 'count': N, 'generation_time': seconds, ...}
        generation_time = result.get("generation_time", time.time() - start_time)
        count = result.get("count", request.count)

        # The raw values are not returned (they can be millions of floats),
        # so no statistics are computed here.
        stats = {
            "mean": 0,
            "median": 0,
            "stdev": 0,
            "min": 0,
            "max": 0,
        }

        # Get thermal status
        thermal_status = {
            "temperature": thermal_monitor.state.temperature,
            "throttle_factor": thermal_monitor.state.throttle_factor,
            "load": thermal_monitor.state.load_average,
        }

        return ScalarGenerationResponse(
            status="success",
            method=request.method,
            count=count,
            generation_time=generation_time,
            thermal_status=thermal_status,
            statistics=stats,
        )

    except Exception as e:
        logger.error(f"❌ Scalar generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/thermal-status", response_model=ThermalStatusResponse)
async def get_thermal_status():
    """Get current thermal monitoring status"""
    try:
        thermal_monitor.update()

        status = "optimal"
        if thermal_monitor.state.temperature > 85:
            status = "critical"
        elif thermal_monitor.state.temperature > 75:
            status = "warm"
        elif thermal_monitor.state.temperature > 65:
            status = "normal"

        return ThermalStatusResponse(
            temperature=thermal_monitor.state.temperature,
            load_average=thermal_monitor.state.load_average,
            throttle_factor=thermal_monitor.state.throttle_factor,
            target_temp=thermal_monitor.state.target_temp,
            max_temp=thermal_monitor.state.max_temp,
            status=status,
        )

    except Exception as e:
        logger.error(f"❌ Thermal status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/methods")
async def list_methods():
    """List the scalar wave generation methods accepted by ``/generate``."""
    return {
        "status": "success",
        "methods": [
            {
                "id": "qrng",
                "name": "Quantum Random Number Generation",
                "description": "Randomness from system entropy",
            },
            {
                "id": "lorenz",
                "name": "Lorenz Chaotic Attractor",
                "description": "Butterfly effect chaos generator",
            },
            {
                "id": "rossler",
                "name": "Rössler Chaotic Attractor",
                "description": "Alternative chaotic system",
            },
            {
                "id": "ca",
                "name": "Cellular Automata",
                "description": "Emergent complexity (Rule 110)",
            },
            {
                "id": "hybrid",
                "name": "Hybrid Synthesis",
                "description": "All methods combined",
            },
        ],
    }
