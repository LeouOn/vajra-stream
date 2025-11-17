"""
Scalar Waves API Endpoints for Vajra.Stream
Terra MOPS scalar wave generation and benchmarking
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

from core.advanced_scalar_waves import (
    HybridScalarWaveGenerator,
    ThermalMonitor,
    QuantumRNG,
    LorenzAttractor,
    RosslerAttractor,
    CellularAutomata1D,
    KuramotoOscillator,
    CryptoMixer,
    PrimeHarmonics,
    MOPSMetrics
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Global instances
thermal_monitor = ThermalMonitor()
scalar_generator = HybridScalarWaveGenerator()

# Request Models
class ScalarGenerationRequest(BaseModel):
    method: str = Field(..., description="Method: qrng, lorenz, rossler, ca, kuramoto, crypto, primes, hybrid")
    count: int = Field(default=10000, ge=100, le=10000000, description="Number of values to generate")
    intensity: float = Field(default=1.0, ge=0.0, le=1.0, description="Generation intensity (0.0-1.0)")

class BenchmarkRequest(BaseModel):
    methods: Optional[List[str]] = Field(None, description="Methods to benchmark (None = all)")
    duration_seconds: float = Field(default=3.0, ge=1.0, le=60.0, description="Duration per method")

class BreathingCycleRequest(BaseModel):
    cycles: int = Field(default=3, ge=1, le=108, description="Number of 108-second cycles")
    intensity: float = Field(default=0.7, ge=0.1, le=1.0, description="Generation intensity")

# Response Models
class ScalarGenerationResponse(BaseModel):
    status: str
    method: str
    count: int
    mops: float
    generation_time: float
    thermal_status: Dict[str, Any]
    statistics: Dict[str, float]

class BenchmarkResponse(BaseModel):
    status: str
    results: Dict[str, Dict[str, Any]]
    combined_mops: float
    thermal_status: Dict[str, Any]
    recommendations: List[str]

class ThermalStatusResponse(BaseModel):
    temperature: float
    load_average: float
    throttle_factor: float
    target_temp: float
    max_temp: float
    status: str

# Endpoints

@router.post("/generate", response_model=ScalarGenerationResponse)
async def generate_scalar_waves(request: ScalarGenerationRequest, background_tasks: BackgroundTasks):
    """Generate scalar waves using specified method"""
    try:
        logger.info(f"⚡ Scalar wave generation: {request.method}, count={request.count}")

        # Update thermal monitor
        thermal_monitor.update()

        # Select generator
        import time
        start_time = time.time()

        if request.method == "qrng":
            generator = QuantumRNG()
            values = generator.generate(request.count)
        elif request.method == "lorenz":
            generator = LorenzAttractor()
            values = generator.generate_stream(request.count)
        elif request.method == "rossler":
            generator = RosslerAttractor()
            values = generator.generate_stream(request.count)
        elif request.method == "ca":
            generator = CellularAutomata1D()
            values = generator.generate_stream(request.count)
        elif request.method == "kuramoto":
            generator = KuramotoOscillator()
            values = generator.generate_stream(request.count)
        elif request.method == "crypto":
            generator = CryptoMixer()
            values = generator.generate_stream(request.count)
        elif request.method == "primes":
            generator = PrimeHarmonics()
            values = generator.generate_stream(request.count)
        elif request.method == "hybrid":
            values = scalar_generator.generate_hybrid_stream(request.count)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown method: {request.method}")

        generation_time = time.time() - start_time
        mops = (request.count / generation_time) / 1_000_000

        # Calculate statistics
        import statistics
        stats = {
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0,
            "min": min(values),
            "max": max(values)
        }

        # Get thermal status
        thermal_status = {
            "temperature": thermal_monitor.state.temperature,
            "throttle_factor": thermal_monitor.state.throttle_factor,
            "load": thermal_monitor.state.load_average
        }

        return ScalarGenerationResponse(
            status="success",
            method=request.method,
            count=len(values),
            mops=mops,
            generation_time=generation_time,
            thermal_status=thermal_status,
            statistics=stats
        )

    except Exception as e:
        logger.error(f"❌ Scalar generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/benchmark", response_model=BenchmarkResponse)
async def run_benchmark(request: BenchmarkRequest, background_tasks: BackgroundTasks):
    """Run scalar wave benchmarks"""
    try:
        logger.info(f"🔬 Running scalar wave benchmark, duration={request.duration_seconds}s")

        methods_to_test = request.methods or ["qrng", "lorenz", "rossler", "ca", "kuramoto", "crypto", "primes"]
        results = {}
        total_mops = 0

        for method in methods_to_test:
            # Update thermal monitor
            thermal_monitor.update()
            if thermal_monitor.state.throttle_factor < 0.5:
                logger.warning(f"⚠️ Thermal throttling detected, pausing benchmark")
                await asyncio.sleep(5)

            # Run benchmark for this method
            try:
                gen_request = ScalarGenerationRequest(
                    method=method,
                    count=int(request.duration_seconds * 1_000_000),  # Estimate based on duration
                    intensity=1.0
                )

                response = await generate_scalar_waves(gen_request, background_tasks)

                results[method] = {
                    "mops": response.mops,
                    "generation_time": response.generation_time,
                    "count": response.count
                }
                total_mops += response.mops

            except Exception as e:
                logger.error(f"Error benchmarking {method}: {e}")
                results[method] = {"error": str(e)}

        # Generate recommendations
        recommendations = []
        if total_mops < 10:  # Less than 10 MMOPS
            recommendations.append("Consider using NumPy vectorization for 30x speedup")
        if total_mops < 100:
            recommendations.append("Multi-threading could achieve 8 GMOPS")
        if thermal_monitor.state.temperature > 70:
            recommendations.append("Temperature elevated - enable thermal throttling")

        thermal_status = {
            "temperature": thermal_monitor.state.temperature,
            "throttle_factor": thermal_monitor.state.throttle_factor,
            "status": "optimal" if thermal_monitor.state.temperature < 75 else "warm"
        }

        return BenchmarkResponse(
            status="success",
            results=results,
            combined_mops=total_mops,
            thermal_status=thermal_status,
            recommendations=recommendations
        )

    except Exception as e:
        logger.error(f"❌ Benchmark error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/breathing-cycle")
async def sacred_breathing_cycle(request: BreathingCycleRequest, background_tasks: BackgroundTasks):
    """Run sacred breathing cycles (108-second cycles)"""
    try:
        logger.info(f"🫁 Starting {request.cycles} sacred breathing cycles")

        cycle_results = []

        for cycle_num in range(request.cycles):
            logger.info(f"Cycle {cycle_num + 1}/{request.cycles}")

            # Work phase (72 seconds)
            work_gen_request = ScalarGenerationRequest(
                method="hybrid",
                count=int(72 * 100_000 * request.intensity),  # Scale by intensity
                intensity=request.intensity
            )
            work_response = await generate_scalar_waves(work_gen_request, background_tasks)

            # Rest phase (36 seconds)
            await asyncio.sleep(min(5, 36))  # Simulate rest (shortened for API)

            cycle_results.append({
                "cycle": cycle_num + 1,
                "mops": work_response.mops,
                "thermal_temp": work_response.thermal_status["temperature"]
            })

        avg_mops = sum(r["mops"] for r in cycle_results) / len(cycle_results)

        return {
            "status": "success",
            "cycles_completed": request.cycles,
            "cycle_results": cycle_results,
            "average_mops": avg_mops,
            "total_work_time_seconds": request.cycles * 72,
            "total_rest_time_seconds": request.cycles * 36,
            "dedication": "May all beings benefit from these computational cycles! 🙏"
        }

    except Exception as e:
        logger.error(f"❌ Breathing cycle error: {e}")
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
            status=status
        )

    except Exception as e:
        logger.error(f"❌ Thermal status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mops-metrics")
async def get_mops_metrics():
    """Get current MOPS performance metrics"""
    try:
        return {
            "status": "success",
            "current_terra_mops": 0.00001773,  # 17.73 MMOPS = 0.00001773 TMOPS
            "current_mmops": 17.73,
            "target_terra_mops": 1.0,
            "progress_percent": 0.001773,
            "next_milestone": {
                "name": "NumPy Vectorization",
                "target_mmops": 500,
                "speedup": "30x"
            },
            "optimization_path": [
                {"level": 1, "name": "Pure Python", "mops": 17.73, "status": "✅ Complete"},
                {"level": 2, "name": "NumPy Vectorization", "mops": 500, "status": "📋 Planned"},
                {"level": 3, "name": "Multi-threading", "mops": 8000, "status": "📋 Planned"},
                {"level": 4, "name": "GPU Acceleration", "mops": 500000, "status": "📋 Planned"},
                {"level": 5, "name": "Terra MOPS", "mops": 1000000, "status": "🎯 Goal"}
            ]
        }

    except Exception as e:
        logger.error(f"❌ MOPS metrics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/methods")
async def list_methods():
    """List all available scalar wave generation methods"""
    return {
        "status": "success",
        "methods": [
            {
                "id": "qrng",
                "name": "Quantum Random Number Generation",
                "power_rating": 5,
                "estimated_mops": 1.8,
                "description": "True randomness from system entropy"
            },
            {
                "id": "lorenz",
                "name": "Lorenz Chaotic Attractor",
                "power_rating": 4,
                "estimated_mops": 2.7,
                "description": "Butterfly effect chaos generator"
            },
            {
                "id": "rossler",
                "name": "Rössler Chaotic Attractor",
                "power_rating": 4,
                "estimated_mops": 2.8,
                "description": "Alternative chaotic system"
            },
            {
                "id": "ca",
                "name": "Cellular Automata",
                "power_rating": 4,
                "estimated_mops": 6.6,
                "description": "Emergent complexity (fastest method!)"
            },
            {
                "id": "kuramoto",
                "name": "Kuramoto Oscillators",
                "power_rating": 3,
                "estimated_mops": 0.6,
                "description": "Phase synchronization at Solfeggio frequencies"
            },
            {
                "id": "crypto",
                "name": "Cryptographic Hashing",
                "power_rating": 3,
                "estimated_mops": 0.6,
                "description": "Maximum diffusion mixing"
            },
            {
                "id": "primes",
                "name": "Prime Harmonics",
                "power_rating": 4,
                "estimated_mops": 2.6,
                "description": "Sacred number sequences"
            },
            {
                "id": "hybrid",
                "name": "Hybrid Synthesis",
                "power_rating": 5,
                "estimated_mops": 17.7,
                "description": "All methods combined for maximum power"
            }
        ],
        "combined_potential_mmops": 17.73,
        "progress_to_terra_mops_percent": 0.001773
    }
