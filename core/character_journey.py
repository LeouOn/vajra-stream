"""
Character Journey Arc
6-stage autonomous ritual progression powered by the RitualSequencer.

Stages: INITIATION → TRAINING → WORKING → OVERCOMING → UTOPIA → MULTIVERSE

Each stage generates unique blessings, attunes rates, and broadcasts
through the operator. The entire journey is driven by RNG-guided
character growth and LLM narrative generation.
"""

import time
from datetime import datetime
from enum import Enum
from typing import Any

from core.ritual_sequencer import RitualPhase, RitualSequencer


class JourneyStage(Enum):
    INITIATION = "initiation"
    TRAINING = "training"
    WORKING = "working"
    OVERCOMING = "overcoming"
    UTOPIA = "utopia"
    MULTIVERSE = "multiverse"


STAGE_CONFIG = [
    {
        "stage": JourneyStage.INITIATION,
        "name": "The Awakening",
        "description": "The character awakens to their calling. First contact with the sacred.",
        "frequency_shift": 0,
        "blessing_theme": "discovery and purpose",
        "duration_hint": "brief — a spark of recognition",
        "stat_growth": {"vitality": 1, "resonance": 2},
    },
    {
        "stage": JourneyStage.TRAINING,
        "name": "The Forge",
        "description": "Rigorous training. The character hones their gifts through discipline.",
        "frequency_shift": 36,
        "blessing_theme": "discipline and mastery",
        "duration_hint": "sustained — like hammer on anvil",
        "stat_growth": {"focus": 2, "wisdom": 1},
    },
    {
        "stage": JourneyStage.WORKING,
        "name": "The Great Work",
        "description": "The character applies their power. Real quests, real consequences.",
        "frequency_shift": 72,
        "blessing_theme": "service and action",
        "duration_hint": "intense — the world needs you now",
        "stat_growth": {"courage": 2, "vitality": 1},
    },
    {
        "stage": JourneyStage.OVERCOMING,
        "name": "The Shadow Trial",
        "description": "The darkest hour. The character faces their greatest fear or enemy.",
        "frequency_shift": -24,
        "blessing_theme": "protection and breakthrough",
        "duration_hint": "critical — everything hangs in the balance",
        "stat_growth": {"courage": 2, "resonance": 1},
    },
    {
        "stage": JourneyStage.UTOPIA,
        "name": "The Golden Age",
        "description": "Victory achieved. The character basks in the light of accomplishment.",
        "frequency_shift": 108,
        "blessing_theme": "celebration and gratitude",
        "duration_hint": "radiant — the world is transformed",
        "stat_growth": {"empathy": 2, "wisdom": 1},
    },
    {
        "stage": JourneyStage.MULTIVERSE,
        "name": "The Infinite Return",
        "description": "The character transcends form. Their story echoes across all timelines.",
        "frequency_shift": 144,
        "blessing_theme": "transcendence and eternal return",
        "duration_hint": "eternal — the circle completes and begins again",
        "stat_growth": {"resonance": 3, "wisdom": 2},
    },
]


class CharacterJourney:
    """
    Autonomous 6-stage character progression through the RitualSequencer.

    Usage:
        journey = CharacterJourney(operator)
        journey.begin(character_sheet)
        while not journey.is_complete:
            journey.advance()
        result = journey.harvest()
    """

    def __init__(self, operator=None):
        self._operator = operator
        self._sequencer = RitualSequencer(operator)
        self._character = None
        self._current_stage_index = 0
        self._stage_results: list[dict[str, Any]] = []
        self._journey_started: str = ""
        self._journey_completed: str = ""
        self._total_blessings = 0

        # Wire phase callbacks
        self._sequencer.on_phase(RitualPhase.PREPARATION, self._on_preparation)
        self._sequencer.on_phase(RitualPhase.INVOCATION, self._on_invocation)
        self._sequencer.on_phase(RitualPhase.BROADCAST, self._on_broadcast)
        self._sequencer.on_phase(RitualPhase.DEDICATION, self._on_dedication)

    # ─── Public API ───────────────────────────────────────────

    @property
    def is_complete(self) -> bool:
        return self._current_stage_index >= len(STAGE_CONFIG)

    @property
    def current_stage(self) -> JourneyStage | None:
        if self._current_stage_index < len(STAGE_CONFIG):
            return STAGE_CONFIG[self._current_stage_index]["stage"]
        return None

    @property
    def character(self):
        return self._character

    @property
    def stage_results(self) -> list[dict[str, Any]]:
        return self._stage_results

    def begin(self, character: Any) -> dict[str, Any]:
        """Start the character journey arc."""
        self._character = character
        self._current_stage_index = 0
        self._stage_results = []
        self._journey_started = datetime.now().isoformat()
        self._total_blessings = 0

        return {
            "status": "journey_begun",
            "character": character.to_dict() if hasattr(character, "to_dict") else character,
            "stages_total": len(STAGE_CONFIG),
            "first_stage": STAGE_CONFIG[0]["name"],
        }

    def _broadcast_ws(self, event_type: str, data: dict):
        """Broadcast a journey event to all WebSocket clients."""
        try:
            import asyncio

            from backend.websocket.connection_manager import stable_connection_manager_v2

            payload = {"type": event_type, "data": data, "timestamp": time.time()}
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(stable_connection_manager_v2.broadcast(payload))
            except RuntimeError:
                pass
        except Exception:
            pass

    def advance(self) -> dict[str, Any]:
        """Advance through one complete stage (all 4 phases)."""
        if self.is_complete:
            return {"status": "complete", "message": "Journey already completed"}

        stage_cfg = STAGE_CONFIG[self._current_stage_index]
        # Broadcast stage start
        self._broadcast_ws(
            "JOURNEY_STAGE_STARTED",
            {
                "stage": stage_cfg["stage"].value,
                "name": stage_cfg["name"],
                "character": self._character.to_dict()
                if hasattr(self._character, "to_dict") and self._character
                else {},
            },
        )
        # Part 2: The World Reacts Model (Astrological Reactivity)
        from core.auspicious_timing import check_auspicious_window

        window = check_auspicious_window("wisdom")

        elemental_bonus = ""
        if hasattr(self._character, "element") and isinstance(self._character.element, dict):
            el_name = self._character.element.get("name", "")
            # Simple favorable mapping
            favorable_map = {
                "Fire": ["Sun", "Mars", "Jupiter"],
                "Water": ["Moon", "Venus"],
                "Earth": ["Saturn", "Venus", "Moon"],
                "Air": ["Mercury", "Jupiter"],
                "Wood": ["Jupiter", "Venus"],
                "Metal": ["Saturn", "Mars"],
            }
            if window.planetary_hour in favorable_map.get(el_name, []):
                elemental_bonus = f" [SYNCHRONICITY BONUS: The planetary hour of {window.planetary_hour} perfectly aligns with their {el_name} nature, warping reality to aid them.]"
            else:
                elemental_bonus = f" [SHADOW TRIAL: The planetary hour of {window.planetary_hour} actively resists their {el_name} nature. The environment turns hostile.]"

        intention = f"{self._character.name}'s {stage_cfg['name']}: {stage_cfg['blessing_theme']}{elemental_bonus}"

        # Start ritual for this stage
        self._sequencer.start(
            intention=intention,
            tradition="universal",
            character=self._character.to_dict() if hasattr(self._character, "to_dict") else {},
        )

        # Run through all 4 phases
        for _ in range(4):
            if self._sequencer.is_complete:
                break
            time.sleep(0.5)  # Brief pause between phases
            self._sequencer.advance()
            self._sequencer.tick()

        # Record stage result
        final = self._sequencer.finalize()
        result = {
            "stage": stage_cfg["stage"].value,
            "name": stage_cfg["name"],
            "description": stage_cfg["description"],
            "blessings_count": len(final.get("blessings", [])),
            "phase_durations": final.get("phase_durations", {}),
            "completed_at": datetime.now().isoformat(),
        }
        self._stage_results.append(result)
        self._total_blessings += result["blessings_count"]

        # Apply stat growth
        for stat, growth in stage_cfg.get("stat_growth", {}).items():
            if hasattr(self._character, "stats") and stat in self._character.stats:
                self._character.stats[stat] = min(10, self._character.stats[stat] + growth)

        # Shift frequency for next stage
        if hasattr(self._character, "frequency"):
            shift = stage_cfg.get("frequency_shift", 0)
            sacred = [136.1, 396, 417, 528, 639, 741, 852, 963]
            current = self._character.frequency + shift
            # Snap to nearest sacred
            nearest = min(sacred, key=lambda f: abs(f - current))
            self._character.frequency = nearest

        self._current_stage_index += 1

        if self.is_complete:
            self._journey_completed = datetime.now().isoformat()
            self._broadcast_ws(
                "JOURNEY_COMPLETED",
                {
                    "total_stages": len(STAGE_CONFIG),
                    "total_blessings": self._total_blessings,
                    "character": self._character.to_dict()
                    if hasattr(self._character, "to_dict") and self._character
                    else {},
                },
            )
        else:
            self._broadcast_ws(
                "JOURNEY_STAGE_COMPLETED",
                {
                    "stage": result["stage"],
                    "name": result["name"],
                    "blessings_count": result["blessings_count"],
                    "next_stage": STAGE_CONFIG[self._current_stage_index]["name"]
                    if self._current_stage_index < len(STAGE_CONFIG)
                    else None,
                },
            )

        return result

    def harvest(self) -> dict[str, Any]:
        """Collect the final journey results."""
        return {
            "status": "complete" if self.is_complete else "in_progress",
            "character": self._character.to_dict() if hasattr(self._character, "to_dict") else self._character,
            "stages_completed": self._current_stage_index,
            "stages_total": len(STAGE_CONFIG),
            "stage_results": self._stage_results,
            "total_blessings": self._total_blessings,
            "started_at": self._journey_started,
            "completed_at": self._journey_completed,
        }

    def run_full_journey(self, character: Any, operator=None) -> dict[str, Any]:
        """Run the entire 6-stage journey synchronously."""
        if operator:
            self._operator = operator
            self._sequencer._operator = operator
        self.begin(character)
        while not self.is_complete:
            self.advance()
        return self.harvest()

    # ─── Phase Callbacks ──────────────────────────────────────

    def _on_preparation(self, event: str, state, operator):
        if event == "enter":
            # Generate a blessing for the preparation
            if operator and hasattr(operator, "generate_next_blessing"):
                blessing = operator.generate_next_blessing()
                if blessing:
                    state.blessings.append(blessing.get("text", ""))

    def _on_invocation(self, event: str, state, operator):
        if event == "enter":
            # Attune rate from character frequency
            if state.character:
                freq = state.character.get("frequency", 528)
                state.frequency = freq
                state.rates = [int(freq % 100), int((freq * 1.5) % 100), int((freq * 0.5) % 100)]

    def _on_broadcast(self, event: str, state, operator):
        if event == "enter" and operator:
            # Try to forge a sigil for the character
            try:
                if hasattr(operator, "_container") and operator._container:
                    name = state.character.get("name", "character") if state.character else "character"
                    operator._container.radionics.broadcast_healing(
                        target_name=name,
                        frequency_hz=state.frequency,
                        duration_minutes=1,
                    )
            except Exception:
                pass

    def _on_dedication(self, event: str, state, operator):
        if event == "enter":
            # Generate final dedication blessing
            if operator and hasattr(operator, "generate_next_blessing"):
                blessing = operator.generate_next_blessing()
                if blessing:
                    state.blessings.append(f"Dedication: {blessing.get('text', 'May all beings benefit.')}")
            else:
                state.blessings.append("May the merit of this journey benefit all beings throughout space and time. ✨")
