"""
Outlook Module
Thin adapter wrapping core/outlook_generator.py for the DI container.
Supports background broadcast loops.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.core.services.rng_attunement_service import get_rng_service
from core.ritual_sequencer import RitualContext, RitualSequencer
from modules.interfaces import BlessingGenerated, EventBus

logger = logging.getLogger(__name__)


def get_project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists() or (parent / "vajra_stream.db").exists():
            return parent
    return current.parent


class OutlookService:
    """Outlook generation service — wraps core OutlookGenerator."""

    def __init__(self, event_bus: EventBus | None = None):
        self.event_bus = event_bus
        self._generator = None
        self.container = None
        self._loop_task: asyncio.Task | None = None
        self._loop_running = False
        self._loop_interval = 5
        self._loop_config = {}
        self._last_generated_narrative: dict | None = None

    def initialize(self, container: Any = None):
        """Initialize with dependencies from the container."""
        self.container = container
        llm_integration = None
        if container:
            llm_service = (
                getattr(container, "llm", None)
                or getattr(container, "llm_service", None)
                or getattr(container, "enhanced_llm_service", None)
            )
            if llm_service:
                llm_integration = getattr(llm_service, "llm", None) or llm_service
            else:
                llm_integration = getattr(container, "llm_integration", None)

        from core.outlook_generator import OutlookGenerator

        self._generator = OutlookGenerator(llm_integration=llm_integration)

    @property
    def generator(self):
        if self._generator is None:
            from core.outlook_generator import OutlookGenerator

            self._generator = OutlookGenerator()
        return self._generator

    def generate_single(
        self,
        lat: float,
        lon: float,
        languages: list[str] = None,
        genre: str = "healing",
        date: datetime = None,
        custom_context: str | None = None,
        realm_id: str | None = None,
        population_ids: list[str] | None = None,
        character_ids: list[str] | None = None,
        excluded_forces: list[str] | None = None,
        include_dialogue: bool = False,
        model: str | None = None,
        include_astrology: bool = True,
        include_tarot: bool = True,
        include_iching: bool = True,
        include_geomancy: bool = True,
        randomize_realm: bool = False,
        randomize_characters: bool = False,
    ) -> dict[str, Any]:
        """Generate a single-pass narrative outlook."""
        if languages is None:
            languages = ["English"]

        sensor_context = None
        try:
            rng = get_rng_service()
            sessions = rng.get_all_sessions()
            if sessions:
                summary = rng.get_session_summary(sessions[-1])
                if summary:
                    sensor_context = f"Entropy: {summary.get('avg_entropy', 0):.2f}, Coherence: {summary.get('avg_coherence', 0):.2f}, Floating Needles: {summary.get('floating_needle_count', 0)}"
        except Exception as e:
            logger.error(f"Failed to gather sensor context for single outlook: {e}")

        result = self.generator.generate_single_outlook(
            lat=lat,
            lon=lon,
            languages=languages,
            genre=genre,
            date=date,
            custom_context=custom_context,
            realm_id=realm_id,
            population_ids=population_ids,
            character_ids=character_ids,
            excluded_forces=excluded_forces,
            include_dialogue=include_dialogue,
            model=model,
            include_astrology=include_astrology,
            include_tarot=include_tarot,
            include_iching=include_iching,
            include_geomancy=include_geomancy,
            randomize_realm=randomize_realm,
            randomize_characters=randomize_characters,
            sensor_context=sensor_context,
        )

        if self.event_bus:
            event = BlessingGenerated(
                timestamp=datetime.now(),
                event_id=str(uuid.uuid4()),
                target_name=f"Outlook ({genre})",
                blessing_text=result.get("narrative", "")[:500],
                tradition=languages[0] if languages else "English",
            )
            self.event_bus.publish(event)

        return result

    def generate_epic(
        self,
        lat: float,
        lon: float,
        languages: list[str] = None,
        genre: str = "alchemist",
        stages: int = 9,
        date: datetime = None,
        custom_context: str | None = None,
        realm_id: str | None = None,
        population_ids: list[str] | None = None,
        character_ids: list[str] | None = None,
        excluded_forces: list[str] | None = None,
        include_dialogue: bool = False,
        model: str | None = None,
        include_astrology: bool = True,
        include_tarot: bool = True,
        include_iching: bool = True,
        include_geomancy: bool = True,
        randomize_realm: bool = False,
        randomize_characters: bool = False,
    ) -> dict[str, Any]:
        """Generate an epic multi-stage narrative outlook."""
        if languages is None:
            languages = ["English"]

        sensor_context = None
        try:
            rng = get_rng_service()
            sessions = rng.get_all_sessions()
            if sessions:
                summary = rng.get_session_summary(sessions[-1])
                if summary:
                    sensor_context = f"Entropy: {summary.get('avg_entropy', 0):.2f}, Coherence: {summary.get('avg_coherence', 0):.2f}, Floating Needles: {summary.get('floating_needle_count', 0)}"
        except Exception as e:
            logger.error(f"Failed to gather sensor context for epic outlook: {e}")

        result = self.generator.generate_epic_outlook(
            lat=lat,
            lon=lon,
            languages=languages,
            genre=genre,
            stages=stages,
            date=date,
            custom_context=custom_context,
            realm_id=realm_id,
            population_ids=population_ids,
            character_ids=character_ids,
            excluded_forces=excluded_forces,
            include_dialogue=include_dialogue,
            model=model,
            include_astrology=include_astrology,
            include_tarot=include_tarot,
            include_iching=include_iching,
            include_geomancy=include_geomancy,
            randomize_realm=randomize_realm,
            randomize_characters=randomize_characters,
            sensor_context=sensor_context,
        )

        if self.event_bus:
            narratives = [s.get("narrative", "") for s in result.get("stages", [])]
            combined_text = "\n\n".join(narratives)
            event = BlessingGenerated(
                timestamp=datetime.now(),
                event_id=str(uuid.uuid4()),
                target_name=f"Epic Outlook ({genre}, {stages} stages)",
                blessing_text=combined_text[:500],
                tradition=languages[0] if languages else "English",
            )
            self.event_bus.publish(event)

        return result

    def get_status(self) -> dict[str, Any]:
        return {
            "available": True,
            "genres": self.generator.genres,
            "supported_languages": self.generator.supported_languages,
        }

    # ----------------- LOOP METHODS -----------------
    def start_broadcast_loop(self, interval_minutes: int, **config) -> bool:
        if self._loop_running:
            return False

        self._loop_interval = interval_minutes
        self._loop_config = config
        self._loop_config["genre_index"] = 0  # Initialize for cycling
        self._loop_running = True

        # Start async task
        loop = asyncio.get_running_loop()
        self._loop_task = loop.create_task(self._run_broadcast_loop())
        logger.info(f"Broadcast narrative loop started (interval: {interval_minutes}m)")
        return True

    def stop_broadcast_loop(self) -> bool:
        if not self._loop_running:
            return False

        self._loop_running = False
        if self._loop_task:
            self._loop_task.cancel()
            self._loop_task = None

        logger.info("Broadcast narrative loop stopped")
        return True

    def get_loop_status(self) -> dict:
        return {
            "active": self._loop_running,
            "interval_minutes": self._loop_interval,
            "config": self._loop_config,
            "last_generated": self._last_generated_narrative,
        }

    async def _run_broadcast_loop(self):
        try:
            while self._loop_running:
                logger.info("Executing scheduled narrative broadcast generation...")
                try:
                    config = self._loop_config.copy()
                    config["date"] = datetime.now()

                    # Cycle genre if enabled
                    if config.get("cycle_genres", False) and self.generator.genres:
                        genres = self.generator.genres
                        idx = self._loop_config.get("genre_index", 0)
                        current_genre = genres[idx % len(genres)]
                        config["genre"] = current_genre
                        self._loop_config["genre_index"] = idx + 1
                        logger.info(f"Cycling genre: {current_genre}")

                    # Create the context for the sequencer
                    context = RitualContext(
                        genre=config.get("genre", "healing"),
                        lat=config.get("lat", 34.0522),
                        lon=config.get("lon", -118.2437),
                        target_intention=config.get("custom_context") or "",
                    )

                    # Instantiate and execute the workflow engine sequence
                    sequencer = RitualSequencer(outlook_generator=self.generator, event_bus=self.event_bus)
                    final_context = await sequencer.execute_ritual(context)

                    # Store last generated narrative
                    self._last_generated_narrative = final_context.invocation_narrative
                    logger.info(
                        f"Ritual Broadcast completed successfully. Narrative Length: {len(self._last_generated_narrative)}"
                    )

                    # Save to DB
                    try:
                        import os
                        import sqlite3

                        from backend.app.config import settings

                        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
                        if not os.path.isabs(db_path):
                            db_path = str((get_project_root() / db_path).resolve())

                        conn = sqlite3.connect(db_path)
                        cursor = conn.cursor()
                        cursor.execute(
                            """
                            INSERT INTO outlook_narratives
                            (type, genre, languages, lat, lon, date_generated, content, astrology_context, divination_context, divination_raw, entities_invoked)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                            (
                                "single",
                                final_context.genre,
                                json.dumps(config.get("languages", ["English"])),
                                config.get("lat", 34.0522),
                                config.get("lon", -118.2437),
                                datetime.now().isoformat(),
                                final_context.invocation_narrative,
                                json.dumps(final_context.astrology_results),
                                json.dumps(final_context.divination_results),
                                json.dumps(final_context.divination_results),
                                "",  # entities
                            ),
                        )
                        conn.commit()
                        conn.close()
                    except Exception as db_err:
                        logger.error(f"Error saving loop outlook to db: {db_err}")

                except Exception as e:
                    logger.error(f"Error in broadcast loop generation step: {e}")

                # Determine next sleep interval based on loop_mode: sequential_delay or consecutive
                mode = self._loop_config.get("loop_mode", "sequential_delay")
                if mode == "consecutive":
                    sleep_seconds = 5.0
                    logger.info("Consecutive loop mode: waiting 5 seconds before next narrative generation.")
                else:
                    sleep_seconds = self._loop_interval * 60.0
                    logger.info(f"Sequential delay mode: sleeping for {self._loop_interval} minutes.")

                await asyncio.sleep(sleep_seconds)
        except asyncio.CancelledError:
            logger.info("Broadcast loop task cancelled")
        except Exception as e:
            logger.error(f"Broadcast loop task encountered fatal error: {e}")
            self._loop_running = False
