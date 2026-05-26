"""
Vajra.Stream MOPS (Magical Operations Per Second) Telemetry Engine
"""

import threading
import time
from collections import defaultdict
from typing import Any


class MOPSEngine:
    """
    Telemetry engine to track and calculate Magical Operations Per Second (MOPS).
    Subscribes to the system event bus and maintains rolling averages.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # History bucketed by second: timestamp -> counts dict
        self.history: dict[int, dict[str, float]] = defaultdict(
            lambda: {"scalar_pulses": 0.0, "mantras": 0.0, "crystals": 0.0, "divination": 0.0, "tuning": 0.0}
        )
        self.lock = threading.Lock()

        # Cumulative session statistics
        self.totals: dict[str, float] = {
            "scalar_pulses": 0.0,
            "mantras": 0.0,
            "crystals": 0.0,
            "divination": 0.0,
            "tuning": 0.0,
        }

        # Active broadcast tracking
        self.active_crystal_count = 0
        self.is_broadcasting_scalar = False

        # Start background baseline emitter thread
        self.running = True
        self.baseline_thread = threading.Thread(target=self._baseline_emitter_loop, daemon=True)
        self.baseline_thread.start()

        # Hook into global event bus if container is loaded
        self._subscribe_to_event_bus()

        self._initialized = True

    def _subscribe_to_event_bus(self):
        """Subscribe to the main event bus for automatic telemetry tracking"""
        try:
            from container import container
            from modules.interfaces import BlessingGenerated, BroadcastStarted, BroadcastStopped, ScalarWavesGenerated

            # Helper handlers
            def on_scalar_waves(event: ScalarWavesGenerated):
                self.record_event("scalar_pulses", event.count)

            def on_blessing(event: BlessingGenerated):
                # Traditional repetitions per blessing = 108
                self.record_event("mantras", 108)

            def on_broadcast_start(event: BroadcastStarted):
                # Count the number of active frequencies
                self.active_crystal_count = len(event.frequencies) if event.frequencies else 1
                self.is_broadcasting_scalar = True

            def on_broadcast_stop(event: BroadcastStopped):
                self.active_crystal_count = 0
                self.is_broadcasting_scalar = False

            # Subscribing
            container.event_bus.subscribe(ScalarWavesGenerated, on_scalar_waves)
            container.event_bus.subscribe(BlessingGenerated, on_blessing)
            container.event_bus.subscribe(BroadcastStarted, on_broadcast_start)
            container.event_bus.subscribe(BroadcastStopped, on_broadcast_stop)
            print("🚀 MOPSEngine subscribed to Event Bus successfully.")
        except Exception as e:
            print(f"⚠️ MOPSEngine event bus subscription deferred or failed: {e}")

    def record_event(self, category: str, count: float):
        """Record an operation count for a category"""
        if category not in self.totals:
            return

        now = int(time.time())
        with self.lock:
            self.history[now][category] += count
            self.totals[category] += count

    def _baseline_emitter_loop(self):
        """Background thread to add baseline counts for active broadcasts (10Hz tick)"""
        tick_rate = 0.1  # 100ms
        while self.running:
            time.sleep(tick_rate)
            now = int(time.time())

            # Baseline additions:
            # 1. Crystals: 120 ops/sec per active crystal
            # 2. Scalar waves: 17.73M ops/sec if active
            crystal_ops = 120 * self.active_crystal_count * tick_rate
            scalar_ops = 17730000 * tick_rate if self.is_broadcasting_scalar else 0

            if crystal_ops > 0 or scalar_ops > 0:
                with self.lock:
                    if crystal_ops > 0:
                        self.history[now]["crystals"] += crystal_ops
                        self.totals["crystals"] += crystal_ops
                    if scalar_ops > 0:
                        self.history[now]["scalar_pulses"] += scalar_ops
                        self.totals["scalar_pulses"] += scalar_ops

            # Periodically prune history (keep last 300 seconds)
            if now % 10 == 0:
                self._prune_history(now)

    def _prune_history(self, now: int):
        """Prune entries older than 300 seconds"""
        limit = now - 300
        old_keys = [k for k in self.history.keys() if k < limit]
        with self.lock:
            for k in old_keys:
                del self.history[k]

    def get_rolling_averages(self) -> dict[str, dict[str, float]]:
        """Calculate averages per second for 1s, 10s, 60s, and 5m (300s) windows"""
        now = int(time.time())
        windows = {"1s": 1, "10s": 10, "60s": 60, "5m": 300}

        categories = ["scalar_pulses", "mantras", "crystals", "divination", "tuning"]
        averages = {cat: {} for cat in categories}

        with self.lock:
            for cat in categories:
                for window_name, seconds in windows.items():
                    start_time = now - seconds
                    total_in_window = sum(self.history[t][cat] for t in self.history if t > start_time)
                    averages[cat][window_name] = round(total_in_window / seconds, 2)

        return averages

    def get_history(self) -> dict[str, Any]:
        """Return cumulative totals and current state"""
        return {
            "totals": {k: int(v) for k, v in self.totals.items()},
            "active_crystal_count": self.active_crystal_count,
            "is_broadcasting_scalar": self.is_broadcasting_scalar,
            "timestamp": time.time(),
        }

    def shutdown(self):
        """Stop background baseline emitter"""
        self.running = False


# Global instance
mops_engine = MOPSEngine()
