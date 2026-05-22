"""
Crystal Service Module
Wraps hardware crystal broadcaster functionality
"""

import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from hardware.crystal_broadcaster import Level2CrystalBroadcaster, Level3AmplifiedBroadcaster
from modules.interfaces import DomainEvent, EventBus


@dataclass
class CrystalBroadcastStarted(DomainEvent):
    """Event: Crystal broadcast has started"""

    intention: str
    hardware_level: int


@dataclass
class CrystalBroadcastCompleted(DomainEvent):
    """Event: Crystal broadcast has completed"""

    intention: str
    duration: int


class CrystalService:
    """Service wrapper for crystal broadcasting hardware"""

    def __init__(self, event_bus: EventBus | None = None):
        self.event_bus = event_bus
        self.level2 = Level2CrystalBroadcaster()
        self.level3 = Level3AmplifiedBroadcaster()

    def broadcast_intention(
        self,
        intention: str,
        frequencies: list[float] | None = None,
        duration: int = 300,
        hardware_level: int = 2,
        prayer_bowl_mode: bool = True,
    ) -> dict[str, Any]:
        """Broadcast intention through crystal grid"""

        event_id = str(uuid.uuid4())

        # Publish start event
        if self.event_bus:
            self.event_bus.publish(
                CrystalBroadcastStarted(
                    timestamp=datetime.now(), event_id=event_id, intention=intention, hardware_level=hardware_level
                )
            )

        # Execute broadcast
        try:
            # Initialize broadcaster with correct mode
            pure_sine = not prayer_bowl_mode

            if hardware_level == 3:
                broadcaster = Level3AmplifiedBroadcaster(pure_sine=pure_sine)
                broadcaster.generate_amplified_blessing(intention, duration)
            else:
                broadcaster = Level2CrystalBroadcaster(pure_sine=pure_sine)
                broadcaster.generate_5_channel_blessing(intention, duration)

            status = "completed"
            error = None
        except Exception as e:
            status = "failed"
            error = str(e)

        # Publish completion event
        if self.event_bus:
            self.event_bus.publish(
                CrystalBroadcastCompleted(
                    timestamp=datetime.now(), event_id=str(uuid.uuid4()), intention=intention, duration=duration
                )
            )

        return {
            "intention": intention,
            "duration": duration,
            "hardware_level": hardware_level,
            "status": status,
            "error": error,
        }

    def chakra_healing(self, chakra: str, duration: int = 300, hardware_level: int = 2) -> dict[str, Any]:
        """Focused chakra healing through crystals"""
        # Map chakra to intention/frequencies
        intention = f"Healing and balancing {chakra} chakra"

        return self.broadcast_intention(intention=intention, duration=duration, hardware_level=hardware_level)
