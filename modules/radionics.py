"""
Radionics Module
Adapter wrapping core.integrated_scalar_radionics

Integrates with:
- core.rate_to_audio for rate→frequency mapping
- modules.crystal.CrystalService for prayer bowl audio output
- core.integrated_scalar_radionics for scalar wave generation
"""

import sys
import uuid
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.integrated_scalar_radionics import BroadcastConfiguration, IntegratedScalarRadionicsBroadcaster, IntentionType
from core.rate_to_audio import CarrierFrequencySet, map_rate_to_carriers
from modules.interfaces import EventBus, RadionicsBroadcaster


class RadionicsService(RadionicsBroadcaster):
    """Radionics broadcasting service.

    Wires the integrated scalar-radionics broadcaster with the crystal
    bowl hardware layer. When a broadcast is initiated, the service:

    1. Maps the radionics rate to prayer bowl carrier frequencies
    2. Invokes the crystal service for audio output (prayer bowl synthesis)
    3. Invokes the integrated broadcaster for scalar wave generation
    """

    def __init__(self, event_bus: EventBus = None, crystal_service=None):
        self.event_bus = event_bus
        self.broadcaster = IntegratedScalarRadionicsBroadcaster()
        self.crystal_service = crystal_service  # Injected by container

    def broadcast_healing(
        self,
        target_name: str,
        duration_minutes: int = 10,
        frequency_hz: float = 528.0,
        intensity: float = 0.8,
        rate_values: list[int] | None = None,
    ) -> dict[str, Any]:
        """Broadcast healing to target.

        When ``rate_values`` are provided (from the radionics engine),
        they are mapped to prayer bowl carrier frequencies via
        :func:`~core.rate_to_audio.map_rate_to_carriers`. When not
        provided, the ``frequency_hz`` parameter is used directly.

        The crystal service (if available) plays the prayer bowl audio
        through the hardware grid. The integrated broadcaster generates
        scalar waves in parallel.
        """
        session_id = str(uuid.uuid4())

        # Derive carrier frequencies from rate or use the provided frequency
        if rate_values:
            carriers = map_rate_to_carriers(rate_values, potency=intensity)
            freq_list = carriers.frequencies
            amplitude = carriers.amplitude
            freq_source = "radionics_rate"
        else:
            freq_list = [7.83, frequency_hz]
            amplitude = 0.3
            carriers = None
            freq_source = "manual"

        # Build broadcast configuration for the scalar-radionics engine
        config = BroadcastConfiguration(
            intention=IntentionType.HEALING,
            target_count=1,
            duration_seconds=duration_minutes * 60,
            scalar_intensity=intensity,
            frequency_hz=freq_list[1] if len(freq_list) > 1 else frequency_hz,
            mantra="Om Mani Padme Hum",
            use_chakras=True,
        )

        # Invoke crystal service for prayer bowl audio (if available)
        crystal_result = None
        if self.crystal_service:
            try:
                crystal_result = self.crystal_service.broadcast_intention(
                    intention=f"Healing: {target_name}",
                    frequencies=freq_list,
                    duration=duration_minutes * 60,
                    hardware_level=2,
                    prayer_bowl_mode=True,
                    amplitude=amplitude,
                )
            except Exception as e:
                crystal_result = {"status": "failed", "error": str(e)}

        # Invoke scalar-radionics broadcaster for scalar wave generation
        scalar_result = None
        try:
            scalar_result = self.broadcaster.broadcast_to_targets(config)
        except Exception as e:
            scalar_result = {"status": "failed", "error": str(e)}

        return {
            "session_id": session_id,
            "target": target_name,
            "frequencies": freq_list,
            "frequency_source": freq_source,
            "amplitude": amplitude,
            "solfeggio_names": carriers.solfeggio_names if carriers else [],
            "duration_minutes": duration_minutes,
            "status": "active",
            "crystal_output": crystal_result,
            "scalar_output": scalar_result,
        }

    def broadcast_liberation(
        self,
        event_name: str,
        souls_count: int = 1000,
        duration_minutes: int = 108,
        rate_values: list[int] | None = None,
    ) -> dict[str, Any]:
        """Broadcast liberation protocol.

        Uses liberation frequency (396 Hz) or rate-derived carriers.
        """
        session_id = str(uuid.uuid4())

        # Derive carriers
        if rate_values:
            carriers = map_rate_to_carriers(rate_values, potency=1.0)
            freq_list = carriers.frequencies
            amplitude = carriers.amplitude
            freq_source = "radionics_rate"
        else:
            freq_list = [7.83, 396.0]
            amplitude = 0.3
            carriers = None
            freq_source = "manual"

        config = BroadcastConfiguration(
            intention=IntentionType.LIBERATION,
            target_count=souls_count,
            duration_seconds=duration_minutes * 60,
            scalar_intensity=1.0,
            frequency_hz=396.0,
            mantra="Namo Amitabha Buddha",
            use_chakras=True,
            use_meridians=True,
        )

        # Crystal service
        crystal_result = None
        if self.crystal_service:
            try:
                crystal_result = self.crystal_service.broadcast_intention(
                    intention=f"Liberation: {event_name} ({souls_count} beings)",
                    frequencies=freq_list,
                    duration=duration_minutes * 60,
                    hardware_level=2,
                    prayer_bowl_mode=True,
                    amplitude=amplitude,
                )
            except Exception as e:
                crystal_result = {"status": "failed", "error": str(e)}

        # Scalar-radionics broadcaster
        scalar_result = None
        try:
            scalar_result = self.broadcaster.broadcast_to_targets(config)
        except Exception as e:
            scalar_result = {"status": "failed", "error": str(e)}

        return {
            "session_id": session_id,
            "event": event_name,
            "souls_count": souls_count,
            "frequencies": freq_list,
            "frequency_source": freq_source,
            "amplitude": amplitude,
            "solfeggio_names": carriers.solfeggio_names if carriers else [],
            "duration_minutes": duration_minutes,
            "status": "active",
            "crystal_output": crystal_result,
            "scalar_output": scalar_result,
        }

    def get_available_intentions(self) -> list[dict[str, Any]]:
        """Get list of available intention types"""
        return [
            {"id": "healing", "name": "Healing", "frequency": 528},
            {"id": "liberation", "name": "Liberation", "frequency": 396},
            {"id": "empowerment", "name": "Empowerment", "frequency": 528},
            {"id": "protection", "name": "Protection", "frequency": 741},
            {"id": "peace", "name": "Peace", "frequency": 852},
            {"id": "love", "name": "Love", "frequency": 528},
            {"id": "wisdom", "name": "Wisdom", "frequency": 963},
        ]

    def get_sacred_frequencies(self) -> dict[str, list[dict[str, Any]]]:
        """Get sacred frequency mappings"""
        return {
            "solfeggio": [
                {"hz": 396, "name": "Liberation from Guilt & Fear"},
                {"hz": 417, "name": "Undoing Situations"},
                {"hz": 528, "name": "DNA Repair, Love"},
                {"hz": 639, "name": "Connecting Relationships"},
                {"hz": 741, "name": "Awakening Intuition"},
                {"hz": 852, "name": "Spiritual Order"},
                {"hz": 963, "name": "Divine Consciousness"},
            ],
            "planetary": [
                {"hz": 136.10, "name": "Earth (OM)"},
                {"hz": 126.22, "name": "Sun"},
                {"hz": 210.42, "name": "Moon"},
            ],
        }
