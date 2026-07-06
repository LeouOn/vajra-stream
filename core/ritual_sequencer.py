"""
Ritual Sequencer
State machine that chains magical ritual phases with RNG-guided transitions.

Phases: PREPARATION → INVOCATION → BROADCAST → DEDICATION
Each phase has on_enter, on_tick, on_exit callbacks.
State carries the character, rates, sigils, blessings, and timestamps
through the entire ritual lifecycle.
"""

import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class RitualPhase(Enum):
    IDLE = "idle"
    PREPARATION = "preparation"
    INVOCATION = "invocation"
    BROADCAST = "broadcast"
    DEDICATION = "dedication"
    COMPLETED = "completed"
    ABORTED = "aborted"


@dataclass
class RitualState:
    """Mutable state carried through the ritual."""

    ritual_id: str = ""
    phase: RitualPhase = RitualPhase.IDLE
    intention: str = ""
    tradition: str = "universal"
    character: dict[str, Any] | None = None
    rates: list[int] | None = None
    frequency: float = 528.0
    sigil: dict[str, Any] | None = None
    blessings: list[str] = field(default_factory=list)
    rng_readings: list[dict[str, Any]] = field(default_factory=list)
    phase_started: dict[str, float] = field(default_factory=dict)
    phase_durations: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    completed_at: str | None = None

    # Fields added for outlook.py integration
    invocation_narrative: str = ""
    astrology_results: dict[str, Any] = field(default_factory=dict)
    divination_results: dict[str, Any] = field(default_factory=dict)
    # Raw divination data (merged with radionics rates + sigil coordinates)
    # and the sacred-entity invocation text — both returned by
    # generate_single_outlook but previously NOT captured by execute_ritual,
    # so the broadcast loop wrote empty values into the DB.
    divination_raw: dict[str, Any] = field(default_factory=dict)
    entities_used: str = ""
    genre: str = "healing"

    def to_dict(self) -> dict[str, Any]:
        return {
            "ritual_id": self.ritual_id,
            "phase": self.phase.value,
            "intention": self.intention,
            "tradition": self.tradition,
            "character": self.character,
            "rates": self.rates,
            "frequency": self.frequency,
            "sigil": self.sigil,
            "blessings_count": len(self.blessings),
            "rng_readings_count": len(self.rng_readings),
            "phase_durations": self.phase_durations,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "invocation_narrative": self.invocation_narrative,
            "genre": self.genre,
        }


class RitualSequencer:
    """
    State machine for magical ritual workflows.

    Usage:
        seq = RitualSequencer(operator)
        seq.start(intention="Healing for the world", tradition="buddhist")
        while not seq.is_complete:
            seq.tick()
        result = seq.finalize()
    """

    PHASE_ORDER = [
        RitualPhase.PREPARATION,
        RitualPhase.INVOCATION,
        RitualPhase.BROADCAST,
        RitualPhase.DEDICATION,
    ]

    def __init__(self, operator=None, outlook_generator=None, event_bus=None, **kwargs):
        self._operator = operator
        self.outlook_generator = outlook_generator
        self.event_bus = event_bus
        self.kwargs = kwargs
        self.state = RitualState()
        self._phase_index = 0
        self._on_phase_callbacks: dict[RitualPhase, list[Callable]] = {p: [] for p in RitualPhase}
        self._running = False

    # ─── Public API ───────────────────────────────────────────

    def start(self, intention: str = "", tradition: str = "universal", character: dict | None = None) -> RitualState:
        """Initialize and begin the ritual."""
        self.state = RitualState(
            ritual_id=f"ritual_{int(time.time())}_{uuid.uuid4().hex[:8]}",
            phase=RitualPhase.IDLE,
            intention=intention,
            tradition=tradition,
            character=character,
            created_at=datetime.now().isoformat(),
        )
        self._phase_index = 0
        self._running = True
        self._advance_phase()
        return self.state

    def tick(self) -> RitualState:
        """Advance the ritual by one tick. Call in a loop."""
        if not self._running:
            return self.state
        current = self.state.phase
        if current in (RitualPhase.COMPLETED, RitualPhase.ABORTED):
            return self.state

        # Run on_tick for current phase
        self._fire_callbacks("tick", current)
        return self.state

    def advance(self) -> RitualState:
        """Manually advance to the next phase."""
        current = self.state.phase
        if current in (RitualPhase.COMPLETED, RitualPhase.ABORTED):
            return self.state

        self._complete_current_phase()
        if self._phase_index < len(self.PHASE_ORDER):
            self._advance_phase()
        else:
            self._finish_ritual()
        return self.state

    def abort(self, reason: str = "") -> RitualState:
        """Abort the ritual."""
        self._running = False
        self.state.phase = RitualPhase.ABORTED
        self.state.metadata["abort_reason"] = reason
        self._fire_callbacks("exit", RitualPhase.ABORTED)
        return self.state

    def finalize(self) -> dict[str, Any]:
        """Complete the ritual and return final state."""
        if self.state.phase not in (RitualPhase.COMPLETED, RitualPhase.ABORTED):
            self._finish_ritual()
        return self.state.to_dict()

    def on_phase(self, phase: RitualPhase, callback: Callable):
        """Register a callback for a phase event (enter/tick/exit)."""
        self._on_phase_callbacks[phase].append(callback)

    async def execute_ritual(self, context: RitualState) -> RitualState:
        """Autonomously drive the ritual state machine through all phases."""
        self.state = context
        self.state.phase = RitualPhase.PREPARATION
        self.state.created_at = datetime.now().isoformat()
        self._phase_index = 0
        self._running = True

        while not self.is_complete:
            current = self.state.phase

            if current == RitualPhase.PREPARATION:
                # Gather baseline entropy or prep sigils if needed
                pass

            elif current == RitualPhase.INVOCATION:
                if self.outlook_generator:
                    lat = self.state.metadata.get("lat", 34.0522)
                    lon = self.state.metadata.get("lon", -118.2437)
                    res = self.outlook_generator.generate_single(
                        lat=lat, lon=lon, genre=self.state.genre, custom_context=self.state.intention
                    )
                    self.state.invocation_narrative = res.get("narrative", "")
                    # Key mismatch: generate_single returns ``astrology_used``
                    # and ``divination_used``, NOT ``astrology`` / ``divination``.
                    # The previous keys silently returned ``{}`` every time.
                    self.state.astrology_results = res.get("astrology_used", res.get("astrology", {}))
                    self.state.divination_results = res.get("divination_used", res.get("divination", {}))
                    # Also capture the raw divination data (with merged
                    # radionics rates + sigil coords) and the entity
                    # invocation text so the broadcast loop can persist them.
                    self.state.divination_raw = res.get("divination_raw", {})
                    self.state.entities_used = res.get("entities_used", "")

            elif current == RitualPhase.BROADCAST:
                if self.event_bus:
                    from modules.interfaces import BlessingGenerated

                    event = BlessingGenerated(
                        timestamp=datetime.now(),
                        event_id=str(uuid.uuid4()),
                        target_name=self.state.intention or "Automated Ritual",
                        blessing_text=self.state.invocation_narrative[:500],
                        tradition="Universal",
                    )
                    self.event_bus.publish(event)

            elif current == RitualPhase.DEDICATION:
                pass

            self.advance()

        return self.state

    @property
    def is_complete(self) -> bool:
        return self.state.phase in (RitualPhase.COMPLETED, RitualPhase.ABORTED)

    @property
    def is_running(self) -> bool:
        return self._running and not self.is_complete

    # ─── Internals ────────────────────────────────────────────

    def _advance_phase(self):
        """Move to the next phase and fire on_enter."""
        phase = self.PHASE_ORDER[self._phase_index]
        self.state.phase = phase
        self.state.phase_started[phase.value] = time.time()
        self._fire_callbacks("enter", phase)

    def _complete_current_phase(self):
        """Complete the current phase, record duration, and fire on_exit."""
        phase = self.state.phase
        if phase.value in self.state.phase_started:
            elapsed = time.time() - self.state.phase_started[phase.value]
            self.state.phase_durations[phase.value] = elapsed
        self._fire_callbacks("exit", phase)
        self._phase_index += 1

    def _finish_ritual(self):
        """Mark ritual as completed."""
        self.state.phase = RitualPhase.COMPLETED
        self.state.completed_at = datetime.now().isoformat()
        self._running = False
        self._fire_callbacks("exit", RitualPhase.COMPLETED)

    def _fire_callbacks(self, event: str, phase: RitualPhase):
        """Fire all registered callbacks for a phase event."""
        for cb in self._on_phase_callbacks.get(phase, []):
            try:
                cb(event, self.state, self._operator)
            except Exception as e:
                print(f"RitualSequencer callback error ({phase.value}.{event}): {e}")

    def inject_operator(self, operator):
        """Set the operator for LLM-guided phases."""
        self._operator = operator

    def check_timing(self, genre: str = "healing") -> dict[str, Any]:
        """Check auspicious timing for this ritual. Always returns go=true with approach guidance."""
        try:
            from core.auspicious_timing import check_auspicious_window

            window = check_auspicious_window(genre)
            self.state.metadata["timing"] = window.to_dict()
            return window.to_dict()
        except Exception:
            return {"go": True, "quality": "neutral", "recommended_approach": "direct"}

    def get_tradition_context(self) -> dict[str, Any]:
        """Get tradition-specific astrological context for the current ritual."""
        tradition = self.state.tradition or "universal"
        result = {"tradition": tradition}

        try:
            from datetime import datetime

            import pytz

            from core.astrology import AstrologicalCalculator

            astro = AstrologicalCalculator()
            now = datetime.now(pytz.UTC)
            data = astro.get_comprehensive_astrology(now, (37.7749, -122.4194))

            if tradition in ("vedic", "universal"):
                panchanga = data.get("indian", {}).get("panchanga", {})
                result["vedic"] = {
                    "tithi": panchanga.get("tithi", {}).get("name", ""),
                    "nakshatra": panchanga.get("nakshatra", {}).get("name", ""),
                    "yoga": panchanga.get("yoga", {}).get("name", ""),
                    "vara": panchanga.get("vara", {}).get("name", ""),
                    "lagna": data.get("indian", {})
                    .get("sidereal_positions", {})
                    .get("ascendant", {})
                    .get("rashi_name", ""),
                    "invocation_mantra": f"Om {panchanga.get('nakshatra', {}).get('name', '')}aya Namah",
                }

            if tradition in ("chinese", "universal"):
                chinese = data.get("chinese", {})
                result["chinese"] = {
                    "zodiac": chinese.get("zodiac_animal", ""),
                    "solar_term": chinese.get("solar_term", ""),
                    "shichen": chinese.get("shichen", {}).get("name", ""),
                    "bazi_year": chinese.get("bazi", {}).get("year", ""),
                    "invocation_mantra": "Tai Shang Lao Jun Ji Ji Ru Lv Ling",
                }

            if tradition in ("western", "universal"):
                hours = data.get("planetary_hours", {})
                western = data.get("western", {})
                result["western"] = {
                    "planetary_hour": hours.get("current_planetary_hour", ""),
                    "day_ruler": hours.get("day_ruler", ""),
                    "dominant_element": western.get("dominant_element", ""),
                    "invocation_mantra": f"By the power of {hours.get('current_planetary_hour', 'the stars')}, I invoke the celestial forces",
                }

            self.state.metadata["tradition_context"] = result
        except Exception:
            self.state.metadata["tradition_context"] = {"tradition": tradition, "error": "unavailable"}

        return self.state.metadata.get("tradition_context", {})


# Backward compatibility alias for modules expecting RitualContext
RitualContext = RitualState
