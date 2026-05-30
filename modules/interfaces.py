"""
Module Interfaces (Ports)
Define clear contracts between modules
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

# ============================================================================
# Domain Events
# ============================================================================


@dataclass
class DomainEvent:
    """Base class for all domain events"""

    timestamp: datetime
    event_id: str


@dataclass
class HealingSessionStarted(DomainEvent):
    """Event: Healing session has started"""

    target_name: str
    intention: str
    duration_minutes: int


@dataclass
class ScalarWavesGenerated(DomainEvent):
    """Event: Scalar waves have been generated"""

    method: str
    count: int
    mops: float


@dataclass
class BlessingGenerated(DomainEvent):
    """Event: Blessing has been created"""

    target_name: str
    blessing_text: str
    tradition: str


@dataclass
class SessionCreated(DomainEvent):
    """Event: A blessing session has been created"""

    session_id: str
    name: str
    intention: str
    duration: int
    audio_frequency: float


@dataclass
class SessionStarted(DomainEvent):
    """Event: A session has started broadcasting"""

    session_id: str
    name: str


@dataclass
class SessionStopped(DomainEvent):
    """Event: A session has been stopped"""

    session_id: str
    name: str
    runtime_seconds: float


@dataclass
class BroadcastStarted(DomainEvent):
    """Event: Crystal/radionics broadcast has started"""

    session_id: str
    hardware_level: int
    frequencies: list[float]


@dataclass
class BroadcastStopped(DomainEvent):
    """Event: Crystal/radionics broadcast has stopped"""

    session_id: str
    actual_runtime: float


@dataclass
class RNGReadingEvent(DomainEvent):
    """Event: Significant RNG Reading captured"""

    session_id: str
    coherence: float
    entropy: float
    floating_needle_score: float

# ============================================================================
# Module Interfaces (Ports)
# ============================================================================


class ScalarWaveGenerator(Protocol):
    """Port for scalar wave generation"""

    def generate(self, method: str, count: int, intensity: float = 1.0) -> dict[str, Any]:
        """Generate scalar waves

        Args:
            method: Generation method (qrng, lorenz, rossler, ca, hybrid)
            count: Number of values to generate
            intensity: Generation intensity (0.0-1.0)

        Returns:
            Dictionary with wave data and metrics
        """
        ...

    def benchmark(self, duration: float = 3.0) -> dict[str, dict[str, float]]:
        """Benchmark all methods"""
        ...

    def get_thermal_status(self) -> dict[str, Any]:
        """Get thermal monitoring status"""
        ...


class RadionicsBroadcaster(Protocol):
    """Port for radionics broadcasting"""

    def broadcast_healing(
        self, target_name: str, duration_minutes: int = 10, frequency_hz: float = 528.0, intensity: float = 0.8
    ) -> dict[str, Any]:
        """Broadcast healing to target"""
        ...

    def broadcast_liberation(
        self, event_name: str, souls_count: int = 1000, duration_minutes: int = 108
    ) -> dict[str, Any]:
        """Broadcast liberation protocol"""
        ...

    def get_available_intentions(self) -> list[dict[str, Any]]:
        """Get list of available intention types"""
        ...

    def get_sacred_frequencies(self) -> dict[str, list[dict[str, Any]]]:
        """Get sacred frequency mappings"""
        ...


class AnatomyVisualizer(Protocol):
    """Port for energetic anatomy visualization"""

    def visualize_chakras(self, width: int = 1200, height: int = 1600, output_path: str | None = None) -> str:
        """Generate chakra diagram"""
        ...

    def visualize_meridians(self, width: int = 1200, height: int = 1600, output_path: str | None = None) -> str:
        """Generate meridian map"""
        ...

    def visualize_central_channel(self, width: int = 1200, height: int = 1800, output_path: str | None = None) -> str:
        """Generate central channel diagram"""
        ...

    def get_chakra_info(self) -> list[dict[str, Any]]:
        """Get chakra information"""
        ...

    def get_meridian_info(self) -> list[dict[str, Any]]:
        """Get meridian information"""
        ...


class BlessingGenerator(Protocol):
    """Port for blessing generation"""

    def generate_blessing(
        self,
        target_name: str,
        intention: str = "peace and happiness",
        tradition: str = "universal",
        include_mantra: bool = True,
        include_dedication: bool = True,
    ) -> dict[str, Any]:
        """Generate a blessing"""
        ...

    def generate_mass_liberation(
        self, event_name: str, location: str, souls_count: int = 1000, duration_minutes: int = 108
    ) -> dict[str, Any]:
        """Generate mass liberation blessing"""
        ...

    def get_available_traditions(self) -> list[dict[str, Any]]:
        """Get available blessing traditions"""
        ...


class AstrologyCalculator(Protocol):
    """Port for astrological calculations"""

    def calculate_natal_chart(
        self, date: datetime, latitude: float, longitude: float, name: str | None = None
    ) -> dict[str, Any]:
        """Calculate natal chart"""
        ...

    def calculate_transits(self, natal_chart_data: dict[str, Any], transit_date: datetime) -> dict[str, Any]:
        """Calculate current transits"""
        ...

    def get_planetary_positions(self, date: datetime) -> dict[str, Any]:
        """Get current planetary positions"""
        ...


# ============================================================================
# Event Bus Interface
# ============================================================================


class EventBus(Protocol):
    """Port for event bus (in-process)"""

    def subscribe(self, event_type: type, handler: callable) -> None:
        """Subscribe to an event type"""
        ...

    def publish(self, event: DomainEvent) -> None:
        """Publish an event"""
        ...

    def unsubscribe(self, event_type: type, handler: callable) -> None:
        """Unsubscribe from an event type"""
        ...
