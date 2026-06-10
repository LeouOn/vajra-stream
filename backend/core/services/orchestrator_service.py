import asyncio
import logging
from datetime import datetime

from backend.core.services.character_manager import CharacterManager
from core.auspicious_timing import AuspiciousTiming
from core.models.practice import Practice
from core.outlook_generator import OutlookGenerator

logger = logging.getLogger(__name__)


class OrchestratorService:
    """Continuous orchestration loop that triggers Sadhanas based on celestial timing."""

    def __init__(
        self,
        astro_engine: AuspiciousTiming,
        char_manager: CharacterManager,
        outlook_gen: OutlookGenerator,
        practices: list[Practice] = None,
    ):
        self.astro_engine = astro_engine
        self.char_manager = char_manager
        self.outlook_gen = outlook_gen
        self.practices = practices or []
        self._running = False
        self.current_planetary_hour = None

    async def start(self):
        """Starts the continuous event loop."""
        self._running = True
        logger.info("Vajra Stream Orchestrator started. Watching the heavens...")

        while self._running:
            await self._tick()
            # Check every 60 seconds (simulated or real time depending on config)
            await asyncio.sleep(60)

    async def _tick(self):
        """One cycle of the orchestration loop."""
        now = datetime.now()
        # For our local location or a default global location (e.g., Mount Kailash)
        lat, lon = 31.0651, 81.3129

        # Guard: engine may be None if AstrologyEngine import failed
        if self.astro_engine.engine is None:
            logger.warning("AstrologyEngine unavailable — skipping planetary hour check")
            return
        chart = self.astro_engine.engine.calculate_chart(now, lat, lon)
        planetary_hours = chart.get("planetary_hours", {})
        current_hour = planetary_hours.get("current_hour", {}).get("planet", "Unknown")

        # Did the planetary hour just shift?
        if current_hour != self.current_planetary_hour:
            logger.info(f"Astrological Shift Detected: Entering the hour of {current_hour}")
            self.current_planetary_hour = current_hour
            await self._trigger_practices_for_hour(current_hour, lat, lon)

        # We can also check characters recovering energy over time
        self._recover_character_energy()

    def _recover_character_energy(self):
        """Slowly recover energy for all resting/idle characters."""
        for char in self.char_manager.get_all_characters():
            if char.state in ["Resting", "Idle"]:
                self.char_manager.update_state(char.id, new_state=char.state, energy_change=5)
            if char.state == "Resting" and char.energy >= 100:
                self.char_manager.update_state(char.id, new_state="Idle", energy_change=0)

    async def _trigger_practices_for_hour(self, planet: str, lat: float, lon: float):
        """Find an eligible practice and dispatch characters to perform it."""
        for practice in self.practices:
            if not practice.preferred_planetary_hours or planet.lower() in [
                p.lower() for p in practice.preferred_planetary_hours
            ]:
                logger.info(f"Auspicious match! Practice '{practice.name}' aligns with {planet} hour.")

                # Find available characters
                available_chars = [
                    c for c in self.char_manager.get_active_characters() if c.state == "Idle" and c.energy >= 50
                ]

                eligible, reason = practice.is_eligible(available_chars, {})
                if not eligible:
                    logger.debug(f"Practice '{practice.name}' cannot be performed: {reason}")
                    continue

                # We have a match! Let's trigger it.
                logger.info(f"Dispatching characters {[c.name for c in available_chars]} for {practice.name}")

                # Update state
                for c in available_chars:
                    self.char_manager.update_state(c.id, new_state="Practicing", energy_change=-50)

                # Generate Ritual
                logger.info(f"Generating {practice.tradition} Ritual...")

                # In a real async loop we might want to run this in an executor
                try:
                    result = self.outlook_gen.generate_single_outlook(
                        lat=lat,
                        lon=lon,
                        languages=["English", "Sanskrit", "Tibetan"],
                        genre=practice.genre,
                        character_ids=[c.id for c in available_chars],
                        custom_context=practice.base_prompt_template,
                        include_dialogue=True,
                    )

                    if result and "narrative" in result:
                        logger.info(f"Sadhana {practice.name} completed successfully.")

                        # Evaluate and Award EXP
                        critic_result = self.outlook_gen.evaluate_ritual(result["narrative"], practice.genre)
                        score = critic_result.get("score", 5)
                        logger.info(f"Critic Score: {score}/10")

                        for c in available_chars:
                            exp_gained = score * practice.merit_multiplier * 5
                            self.char_manager.add_exp_and_log(
                                c.id,
                                exp_amount=exp_gained,
                                event_summary=f"Performed {practice.name} during {planet} hour. Score: {score}/10.",
                            )
                            # Maybe they found a relic?
                            if score >= 9:
                                self.char_manager.add_relic(c.id, f"Essence of {planet}")

                            self.char_manager.update_state(c.id, new_state="Resting", energy_change=0)

                except Exception as e:
                    logger.error(f"Failed to perform practice {practice.name}: {e}")
                    # Revert state
                    for c in available_chars:
                        self.char_manager.update_state(c.id, new_state="Idle", energy_change=50)
