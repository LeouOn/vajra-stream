"""
Scalar Waves Module
Adapter wrapping core.advanced_scalar_waves
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional
import time
import uuid
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.advanced_scalar_waves import (
    HybridScalarWaveGenerator,
    ThermalMonitor,
    QuantumRNG,
    LorenzAttractor,
    RosslerAttractor,
    CellularAutomata1D
)
from modules.interfaces import ScalarWaveGenerator, ScalarWavesGenerated, EventBus


class ScalarWaveService(ScalarWaveGenerator):
    """Scalar wave generation service - adapts core module to interface"""

    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus
        self.hybrid_generator = HybridScalarWaveGenerator()
        self.thermal_monitor = ThermalMonitor()
        self._generators = {}

    def _get_generator(self, method: str):
        """Get or create generator for method"""
        if method not in self._generators:
            generators = {
                'qrng': QuantumRNG,
                'lorenz': LorenzAttractor,
                'rossler': RosslerAttractor,
                'ca': CellularAutomata1D
            }
            if method in generators:
                self._generators[method] = generators[method]()
            elif method == 'hybrid':
                return self.hybrid_generator
            else:
                raise ValueError(f"Unknown method: {method}")
        return self._generators.get(method)

    def generate(
        self,
        method: str,
        count: int,
        intensity: float = 1.0
    ) -> Dict[str, Any]:
        """Generate scalar waves"""

        # Update thermal monitor
        self.thermal_monitor.update()

        # Apply throttling based on intensity
        actual_count = int(count * intensity * self.thermal_monitor.state.throttle_factor)

        # Generate
        start_time = time.time()

        if method == "hybrid":
            values = self.hybrid_generator.generate_hybrid_stream(actual_count)
        else:
            generator = self._get_generator(method)
            if hasattr(generator, 'generate_stream'):
                values = generator.generate_stream(actual_count)
            else:
                values = generator.generate(actual_count)

        generation_time = time.time() - start_time
        mops = (actual_count / generation_time) / 1_000_000

        result = {
            'values': values,
            'count': len(values),
            'method': method,
            'mops': mops,
            'generation_time': generation_time,
            'temperature': self.thermal_monitor.state.temperature,
            'throttle_factor': self.thermal_monitor.state.throttle_factor
        }

        # Publish event
        if self.event_bus:
            event = ScalarWavesGenerated(
                timestamp=datetime.now(),
                event_id=str(uuid.uuid4()),
                method=method,
                count=len(values),
                mops=mops
            )
            self.event_bus.publish(event)

        return result

    def benchmark(self, duration: float = 3.0) -> Dict[str, Dict[str, float]]:
        """Benchmark all methods"""
        methods = ["qrng", "lorenz", "rossler", "ca"]
        results = {}

        for method in methods:
            try:
                # Estimate count based on expected performance
                count = int(duration * 2_000_000)  # Conservative estimate
                result = self.generate(method, count, 1.0)
                results[method] = {
                    'mops': result['mops'],
                    'generation_time': result['generation_time'],
                    'count': result['count']
                }
            except Exception as e:
                results[method] = {'error': str(e)}

        return results

    def get_thermal_status(self) -> Dict[str, Any]:
        """Get thermal monitoring status"""
        self.thermal_monitor.update()

        status = "optimal"
        if self.thermal_monitor.state.temperature > 85:
            status = "critical"
        elif self.thermal_monitor.state.temperature > 75:
            status = "warm"
        elif self.thermal_monitor.state.temperature > 65:
            status = "normal"

        return {
            'temperature': self.thermal_monitor.state.temperature,
            'load_average': self.thermal_monitor.state.load_average,
            'throttle_factor': self.thermal_monitor.state.throttle_factor,
            'target_temp': self.thermal_monitor.state.target_temp,
            'max_temp': self.thermal_monitor.state.max_temp,
            'status': status
        }
