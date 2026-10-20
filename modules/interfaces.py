"""
Module Interfaces (Ports)
Define clear contracts between modules
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

# ============================================================================
# Domain Events
# ============================================================================


@dataclass(kw_only=True)
class DomainEvent:
    """Base class for all domain events.

    ``timestamp`` and ``event_id`` are optional, so a subclass can be built
    from only its OWN fields and every event still identifies itself.

    ``kw_only`` keeps the base fields keyword-only, which is what allows the
    subclasses to keep their own fields required AND positional (a plain
    dataclass with defaults on the base would raise "non-default argument
    follows default argument").

    The explicit ``__init__`` below exists for one reason: ``@dataclass``
    does not overwrite an ``__init__`` defined in the class body, so this one
    survives. It accepts the two base fields POSITIONALLY as well as by
    keyword, because callers outside this module subclass ``DomainEvent``
    directly and call ``super().__init__(timestamp, event_id)`` positionally.
    Both paths produce the same defaults: the dataclass field factories are
    used when a dataclass subclass is built, and this ``__init__`` is used for
    a direct ``DomainEvent(...)`` or a ``super().__init__`` call.

    The default timestamp is timezone-aware UTC, but a caller-supplied
    timestamp is stored as given and may be NAIVE: several call sites pass a
    bare ``datetime.now()``, so a mixed tree exists today. The aware default
    makes the majority case unambiguous; it is a default, NOT a guarantee that
    every value is aware.

    Consequently: do not compare, subtract or sort timestamps across call
    sites without normalising first. A naive and an aware value raise
    ``TypeError`` on comparison, and sorting a mixed list raises rather than
    producing a stable order. One pre-existing consumer already sidesteps this
    by comparing ISO strings instead -- ``EnhancedEventBus.replay_events``.
    """

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __init__(self, timestamp: datetime | None = None, event_id: str | None = None) -> None:
        self.timestamp = timestamp if timestamp is not None else datetime.now(timezone.utc)
        self.event_id = event_id if event_id is not None else str(uuid.uuid4())


@dataclass
class HealingSessionStarted(DomainEvent):
    """Event: Healing session has started"""

    target_name: str
    intention: str
    duration_minutes: int
    location: str | None = None
    lat: float | None = None
    lon: float | None = None


@dataclass
class HealingBroadcastStarted(DomainEvent):
    """Event: Radionics healing broadcast has started"""

    target_name: str
    frequency_hz: float
    frequencies: list[float]
    duration_minutes: int
    location: str | None = None
    lat: float | None = None
    lon: float | None = None
    audio_muted: bool = False


@dataclass
class HealingSessionCompleted(DomainEvent):
    """Event: Healing dialogue session has completed.

    Emitted when the multi-turn healing dialogue reaches the ``COMPLETED``
    phase (after the Dedication phase lands). Carries the session id, the
    generated summary text, and the structured key insights so downstream
    consumers (OutlookService feedback loop, event log, etc.) can react
    without re-querying the DB.
    """

    session_id: str
    summary: str
    key_insights: dict


@dataclass
class RecitationStarted(DomainEvent):
    """Event: 88-Buddha recitation loop has started.

    Emitted by :meth:`BuddhaRecitationLoop.start` after the DB session row
    has been inserted. ``session_id`` is the integer primary key of the new
    ``buddha_recitation_sessions`` row.
    """

    intention: str
    session_id: int


@dataclass
class RecitationCompleted(DomainEvent):
    """Event: 88-Buddha recitation loop has stopped.

    Emitted by :meth:`BuddhaRecitationLoop.stop` after the DB row has been
    finalized with ``ended_at`` + ``summary``. Carries the final counters
    and the dedication text so downstream consumers (DailyStreak, event log)
    can react without re-querying the DB.
    """

    session_id: int
    cycles_completed: int
    total_recited: int
    dedication_text: str | None


@dataclass
class ScalarWavesGenerated(DomainEvent):
    """Event: Scalar waves have been generated"""

    method: str
    count: int
    generation_seconds: float


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
