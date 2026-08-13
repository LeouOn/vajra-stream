"""
Radionics Module
Adapter wrapping core.integrated_scalar_radionics

Integrates with:
- core.rate_to_audio for rate→frequency mapping
- modules.crystal.CrystalService for prayer bowl audio output
- core.integrated_scalar_radionics for scalar wave generation
"""

import sys
import time
import uuid
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

from core.integrated_scalar_radionics import BroadcastConfiguration, IntegratedScalarRadionicsBroadcaster, IntentionType
from core.rate_to_audio import map_rate_to_carriers
from modules.interfaces import EventBus, RadionicsBroadcaster
from modules.radionics_enhancer import RadionicsEnhancer

logger = logging.getLogger(__name__)

# Global mute for prayer-bowl / singing-bowl audio broadcasts. When True,
# broadcast_healing skips the crystal audio playback but still runs the
# scalar broadcaster and returns a marker so callers/UI know.
_AUDIO_MUTED: bool = False


def set_audio_broadcasts_muted(muted: bool) -> None:
    global _AUDIO_MUTED
    _AUDIO_MUTED = bool(muted)


def audio_broadcasts_muted() -> bool:
    return _AUDIO_MUTED


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
        self.crystal_service = crystal_service  # Injected by container
        self.broadcaster = IntegratedScalarRadionicsBroadcaster(crystal_service=crystal_service)
        self.enhancer = RadionicsEnhancer()

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

        # Derive carrier frequencies from rate, enhancer auto-tune, or manual
        if rate_values:
            carriers = map_rate_to_carriers(rate_values, potency=intensity)
            freq_list = carriers.frequencies
            amplitude = carriers.amplitude
            freq_source = "radionics_rate"
        else:
            # Auto-tune: use RadionicsEnhancer to derive 5 dial values from
            # the target/intention text, then snap to Solfeggio carriers.
            # This replaces the old "manual" fallback that always used [7.83, freq].
            auto_intention = f"{target_name} healing {frequency_hz}"
            base_rate = self.enhancer.attune_rate(auto_intention)
            # Derive 5 correlated dial values from the base rate + intention hash
            import hashlib

            intention_hash = hashlib.sha256(auto_intention.encode()).digest()
            auto_values = [
                int(base_rate),
                int((base_rate + intention_hash[0]) % 100),
                int((base_rate + intention_hash[1]) % 100),
                int((base_rate + intention_hash[2]) % 100),
                int((base_rate + intention_hash[3]) % 100),
            ]
            carriers = map_rate_to_carriers(auto_values, potency=intensity)
            freq_list = carriers.frequencies
            amplitude = carriers.amplitude
            freq_source = "enhancer_auto_tune"

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

        # Notify the UI FIRST so users aren't surprised by the singing bowls
        # (and a muted broadcast still shows a toast). Fires before any
        # blocking audio/scalar work so the toast is immediate.
        self._broadcast_ws(
            "HEALING_BROADCAST_STARTED",
            {
                "target": target_name,
                "frequency_hz": freq_list[1] if len(freq_list) > 1 else frequency_hz,
                "frequencies": freq_list,
                "duration_minutes": duration_minutes,
                "audio_muted": bool(_AUDIO_MUTED),
            },
        )

        # Invoke crystal service for prayer bowl audio (if available)
        crystal_result = None
        if self.crystal_service and not _AUDIO_MUTED:
            try:
                crystal_result = self.crystal_service.broadcast_intention(
                    intention=f"Healing: {target_name}",
                    frequencies=freq_list,
                    duration=duration_minutes * 60,
                    hardware_level=2,
                    prayer_bowl_mode=True,
                    amplitude=amplitude,
                    blocking=False,
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
            "audio_muted": bool(_AUDIO_MUTED),
            "crystal_output": crystal_result,
            "scalar_output": scalar_result,
        }

    def _broadcast_ws(self, event_type: str, data: dict[str, Any]) -> None:
        """Best-effort WebSocket broadcast to all clients.

        Safe to call from worker threads: uses the connection manager's
        recorded main loop via run_coroutine_threadsafe. Silently no-ops if
        the manager is unavailable or the loop isn't running.
        """
        try:
            from backend.websocket.connection_manager import (
                stable_connection_manager_v2,
            )
        except Exception as e:  # noqa: BLE001
            logger.debug("WS connection manager unavailable: %s", e)
            return

        payload = {
            "type": event_type,
            "data": data,
            "timestamp": time.time(),
        }
        try:
            import asyncio

            loop = stable_connection_manager_v2.main_loop or asyncio.get_event_loop()
            if not loop.is_running():
                return
            asyncio.run_coroutine_threadsafe(stable_connection_manager_v2.broadcast(payload), loop)
        except Exception as e:  # noqa: BLE001
            logger.debug("WS broadcast failed for %s: %s", event_type, e)

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
