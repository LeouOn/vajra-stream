"""
Character Journey Arc
6-stage autonomous ritual progression powered by the RitualSequencer.

Stages: INITIATION → TRAINING → WORKING → OVERCOMING → UTOPIA → MULTIVERSE

Each stage generates unique blessings, attunes rates, and broadcasts
through the operator. The entire journey is driven by RNG-guided
character growth and LLM narrative generation.
"""

import random
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


# ─── Fallback Narrative Blessings ──────────────────────────
# Used when the LLM operator is unavailable or fails to generate a blessing.
# Each stage carries 2-3 evocative, dharma-infused narrative beats so that
# every journey produces meaningful text even without an LLM configured.
# Templates use {name} and {element} placeholders.

FALLBACK_BLESSINGS: dict[JourneyStage, list[str]] = {
    JourneyStage.INITIATION: [
        "{name} opened their eyes to a world unseen. The {element} within them stirred for the first time — a recognition older than memory. This was the beginning that had always been waiting.",
        "A whisper from the silence between thoughts: *You are needed.* {name} did not yet know what they would become, only that the path had chosen them as surely as they would choose it.",
        "Light threaded through the {element} of their being, and {name} heard their true name spoken by something vast and patient. The ordinary world fell away like a curtain, and the work revealed itself.",
    ],
    JourneyStage.TRAINING: [
        "Day after day, {name} returned to the practice. The {element} in them was hammered on the anvil of discipline until what was rough became keen, what was scattered became one-pointed. They were being forged into an instrument.",
        "The teacher within the {element} showed {name} a thousand small failures, and in each failure, a teaching. Mastery was not arrival — it was the willingness to begin again, one breath closer to clarity.",
        "{name} learned that the {element} does not yield to force, but to attention. Each repetition was a knot untied, each silence a door opened. The forge burned away what was not essential.",
    ],
    JourneyStage.WORKING: [
        "{name} walked out into the world with the {element} as their companion and the work as their burden. There were lives to touch, wounds to mend, choices that could not be unmade. They chose, and chose again.",
        "The {element} moved through {name}'s hands into the suffering of the world. What had been training became service; what had been practice became real. There was no rehearsal now — only the moment and the need.",
        "{name} met the consequences of their own power. The {element} is not gentle when it works through a willing vessel, and the world is not kind to those who carry it. Still, they did not turn away.",
    ],
    JourneyStage.OVERCOMING: [
        "The darkest hour came without warning. {name} stood alone before the shadow of the {element} — every fear they had refused, every truth they had postponed. There was nowhere to hide, and nothing left to do but face it.",
        "In the cold heart of the trial, {name} saw their own reflection wearing the face of the enemy. The {element} taught its hardest lesson: that the shadow is also a part of the work, and what is faced is freed.",
        "Broken open, {name} found the small unextinguishable light at the center — the same {element} that had first called them. They rose not in spite of the wound, but through it. The trial had been a gate all along.",
    ],
    JourneyStage.UTOPIA: [
        "Victory arrived not as a shout but as a hush. {name} looked out on a world touched by the {element}, and saw that the merit of the journey flowed outward in every direction, blessing beings they would never meet.",
        "The {element} sang through {name} in golden harmonics. Gratitude so vast it could not be contained — only given. Every step of the path revealed itself now as a gift received on behalf of all.",
        "{name} rested in the radiance of completion, but it was not the completion of one life. The {element} had woven them into a larger story, and the celebration belonged to everyone who had ever walked beside them.",
    ],
    JourneyStage.MULTIVERSE: [
        "The boundaries of {name} softened, then dissolved. The {element} that had been theirs was now everywhere — in every timeline, every version, every reflection. What they had called 'self' revealed itself as a single note in an infinite chord.",
        "{name} saw the journey from above: every stage, every shadow, every victory — already complete, always beginning. The {element} was the spiral itself, and they were both the walker and the path.",
        "The circle closed, and in closing, opened. {name} returned as the {element} returning to itself — timeless, formless, eternally available. Wherever there is need, the story begins again, and the work is never truly done.",
    ],
}

# Dedication blessings — appended at the close of each stage's ritual.
FALLBACK_DEDICATIONS: list[str] = [
    "{name} dedicates the merit of this stage to all beings who walk the path unseen.",
    "May the {element} of this work ripple outward, easing suffering wherever it is heard.",
    "Whatever was gained here is given freely. {name} holds nothing back.",
    "By this practice, may every threshold become a gate, and every gate a homecoming.",
    "This merit, born of {element} and effort, flows to all who suffer, all who seek, all who serve.",
    "The work is offered. The fruit is released. The circle remains open for the next traveler.",
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

        # NOTE: RitualState.to_dict() exposes `blessings_count` but NOT the
        # `blessings` list itself, so we read it directly off the live state
        # object. Without this, the stage result would always show 0 blessings
        # even though the phase callbacks populated state.blessings correctly.
        stage_blessings = list(getattr(self._sequencer.state, "blessings", []))

        # Capture frequency BEFORE the shift so we can show "528→396 Hz" in the UI.
        freq_before = self._character.frequency if hasattr(self._character, "frequency") else None

        result = {
            "stage": stage_cfg["stage"].value,
            "name": stage_cfg["name"],
            "description": stage_cfg["description"],
            "blessing_theme": stage_cfg["blessing_theme"],
            "blessings_count": len(stage_blessings),
            "blessings": stage_blessings[:3],  # actual blessing texts (max 3)
            "stat_changes": dict(stage_cfg.get("stat_growth", {})),  # what stats grew
            "frequency_before": freq_before,
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

        # Record the frequency AFTER the shift so the UI can show the transition.
        result["frequency_after"] = (
            self._character.frequency if hasattr(self._character, "frequency") else None
        )

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

    def _resolve_element_name(self) -> str:
        """Best-effort resolution of the character's element name (lowercase)."""
        if not self._character or not hasattr(self._character, "element"):
            return "light"
        el = self._character.element
        if isinstance(el, dict):
            return str(el.get("name", "light")).lower()
        if isinstance(el, str):
            return el.lower()
        return "light"

    def _resolve_character_name(self) -> str:
        """Best-effort resolution of the character's name for narrative use."""
        if self._character and hasattr(self._character, "name") and self._character.name:
            return self._character.name
        return "The Seeker"

    def _on_preparation(self, event: str, state, operator):
        if event == "enter":
            blessing_text: str | None = None
            # Try the LLM operator first.
            if operator and hasattr(operator, "generate_next_blessing"):
                try:
                    blessing = operator.generate_next_blessing()
                    if blessing:
                        blessing_text = blessing.get("text", "")
                except Exception:
                    pass

            # Fallback: use pre-written narrative for this stage.
            if not blessing_text:
                stage_cfg = STAGE_CONFIG[self._current_stage_index]
                fallbacks = FALLBACK_BLESSINGS.get(stage_cfg["stage"], [])
                if fallbacks:
                    template = random.choice(fallbacks)
                    try:
                        blessing_text = template.format(
                            name=self._resolve_character_name(),
                            element=self._resolve_element_name(),
                        )
                    except (KeyError, IndexError):
                        blessing_text = template

            if blessing_text:
                state.blessings.append(blessing_text)

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
            blessing_text: str | None = None
            # Try the LLM operator first for a dedicated closing blessing.
            if operator and hasattr(operator, "generate_next_blessing"):
                try:
                    blessing = operator.generate_next_blessing()
                    if blessing:
                        blessing_text = blessing.get("text", "")
                except Exception:
                    pass

            # Fallback: use a pre-written dedication line.
            if not blessing_text:
                if FALLBACK_DEDICATIONS:
                    template = random.choice(FALLBACK_DEDICATIONS)
                    try:
                        blessing_text = template.format(
                            name=self._resolve_character_name(),
                            element=self._resolve_element_name(),
                        )
                    except (KeyError, IndexError):
                        blessing_text = template

            if blessing_text:
                state.blessings.append(f"Dedication: {blessing_text}")
            else:
                state.blessings.append("May the merit of this journey benefit all beings throughout space and time. ✨")
