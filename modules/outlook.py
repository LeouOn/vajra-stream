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
from typing import Any

from modules.interfaces import BlessingGenerated, EventBus

logger = logging.getLogger(__name__)


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
    ) -> dict[str, Any]:
        """Generate a single-pass narrative outlook."""
        if languages is None:
            languages = ["English"]

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
    ) -> dict[str, Any]:
        """Generate an epic multi-stage narrative outlook."""
        if languages is None:
            languages = ["English"]

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
            loop = asyncio.get_running_loop()
            while self._loop_running:
                logger.info("Executing scheduled narrative broadcast generation...")
                try:
                    config = self._loop_config.copy()
                    config["date"] = datetime.now()

                    # Run generation in a separate thread/executor to prevent blocking FastAPI uvicorn thread
                    result = await loop.run_in_executor(
                        None,
                        lambda: self.generate_single(
                            lat=config.get("lat", 34.0522),
                            lon=config.get("lon", -118.2437),
                            languages=config.get("languages", ["English"]),
                            genre=config.get("genre", "healing"),
                            date=config.get("date"),
                            custom_context=config.get("custom_context"),
                            realm_id=config.get("realm_id"),
                            population_ids=config.get("population_ids"),
                            character_ids=config.get("character_ids"),
                            excluded_forces=config.get("excluded_forces"),
                            include_dialogue=config.get("include_dialogue", False),
                        ),
                    )

                    self._last_generated_narrative = result

                    # Save to DB
                    try:
                        import os
                        import sqlite3

                        from backend.app.config import settings

                        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
                        if not os.path.isabs(db_path):
                            from pathlib import Path

                            root_dir = Path(__file__).parent.parent.parent
                            db_path = str((root_dir / db_path).resolve())

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
                                result.get("genre"),
                                json.dumps(result.get("languages")),
                                config.get("lat", 34.0522),
                                config.get("lon", -118.2437),
                                datetime.now().isoformat(),
                                result.get("narrative"),
                                result.get("astrology_used"),
                                result.get("divination_used"),
                                json.dumps(result.get("divination_raw")),
                                result.get("entities_used"),
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
