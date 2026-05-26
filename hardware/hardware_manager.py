"""
Hardware Manager
Lifecycle manager for hardware devices — crystal broadcasters, amplifiers, transducers.

Delegates to CrystalService and hardware/crystal_broadcaster, adding:
- Device discovery and status
- Broadcast session lifecycle
- Hardware level selection (Level 2 passive, Level 3 amplified)
"""

import time
from typing import Any

from modules.interfaces import EventBus


class HardwareManager:
    """
    Manages hardware device lifecycle for crystal broadcasting.

    Provides a clean API over the CrystalService and hardware layer.
    """

    def __init__(self, event_bus: EventBus | None = None):
        self.event_bus = event_bus
        self._crystal_service = None
        self._level2 = None
        self._level3 = None
        self._active_broadcasts: dict[str, dict[str, Any]] = {}
        self._hardware_level = 2  # Default: passive crystal grid
        self._amplifier_connected = False

    @property
    def crystal_service(self):
        if self._crystal_service is None:
            from modules.crystal import CrystalService

            self._crystal_service = CrystalService(event_bus=self.event_bus)
        return self._crystal_service

    @property
    def level2(self):
        if self._level2 is None:
            try:
                from hardware.crystal_broadcaster import Level2CrystalBroadcaster

                self._level2 = Level2CrystalBroadcaster()
            except ImportError:
                self._level2 = None
        return self._level2

    @property
    def level3(self):
        if self._level3 is None:
            try:
                from hardware.crystal_broadcaster import Level3CrystalBroadcaster

                self._level3 = Level3CrystalBroadcaster()
            except ImportError:
                self._level3 = None
        return self._level3

    def discover_devices(self) -> dict[str, Any]:
        """Discover available hardware devices."""
        devices = {
            "level2_passive": self.level2 is not None,
            "level3_amplified": self.level3 is not None,
            "amplifier_connected": self._amplifier_connected,
        }
        return {
            "devices": devices,
            "recommended_level": 3 if devices["level3_amplified"] else 2 if devices["level2_passive"] else 0,
        }

    def set_hardware_level(self, level: int) -> dict[str, Any]:
        """Set the active hardware level."""
        if level not in (2, 3):
            return {"error": "Hardware level must be 2 (passive) or 3 (amplified)"}
        self._hardware_level = level
        return {"hardware_level": level, "status": "configured"}

    def broadcast_intention(
        self, intention: str, duration: int = 3600, frequencies: list[float] | None = None
    ) -> dict[str, Any]:
        """Start a crystal broadcast with an intention."""
        if frequencies is None:
            frequencies = [7.83, 136.1, 528.0]

        broadcast_id = f"hw_{int(time.time())}"

        result = self.crystal_service.broadcast_intention(
            intention=intention,
            duration=duration,
            hardware_level=self._hardware_level,
        )

        self._active_broadcasts[broadcast_id] = {
            "id": broadcast_id,
            "intention": intention,
            "duration": duration,
            "frequencies": frequencies,
            "hardware_level": self._hardware_level,
            "started_at": time.time(),
            "status": "active",
        }

        return {"broadcast_id": broadcast_id, **result}

    def stop_broadcast(self, broadcast_id: str) -> dict[str, Any]:
        """Stop an active broadcast."""
        broadcast = self._active_broadcasts.pop(broadcast_id, None)
        if not broadcast:
            return {"error": f"Broadcast {broadcast_id} not found"}

        broadcast["status"] = "stopped"
        broadcast["ended_at"] = time.time()
        runtime = broadcast["ended_at"] - broadcast["started_at"]
        broadcast["runtime_seconds"] = runtime

        return broadcast

    def list_active_broadcasts(self) -> list[dict[str, Any]]:
        """List all active broadcasts."""
        return list(self._active_broadcasts.values())

    def get_status(self) -> dict[str, Any]:
        """Get overall hardware status."""
        devices = self.discover_devices()
        return {
            "hardware_level": self._hardware_level,
            "active_broadcasts": len(self._active_broadcasts),
            "devices": devices["devices"],
            "recommended_level": devices["recommended_level"],
        }
