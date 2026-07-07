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

    def _fetch_healing_context(self) -> tuple[int | None, str | None]:
        """Fetch the latest completed healing dialogue summary for outlook enrichment.

        Mirrors the RNG sensor fetch pattern — pulls the most recent completed
        healing session summary from the DB and formats it as additional context
        for the outlook generator.

        Returns:
            ``(session_id, context_str)`` tuple. ``session_id`` is the row id of
            the healing session whose summary was used (or ``None`` if no
            completed session exists). ``context_str`` is the formatted context
            (or ``None``). The ``session_id`` is returned so callers can later
            stamp ``linked_outlook_id`` back into the healing session row via
            :meth:`_stamp_linked_outlook`.
        """
        try:
            import sqlite3

            from core.schema import get_db_path

            conn = sqlite3.connect(get_db_path())
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """SELECT id, summary, key_insights_json, phases_completed, started_at
                   FROM healing_dialogue_sessions
                   WHERE summary IS NOT NULL AND ended_at IS NOT NULL
                   ORDER BY ended_at DESC LIMIT 1""",
            )
            row = cursor.fetchone()
            conn.close()
            if not row:
                return None, None

            session_id = row["id"]
            summary = row["summary"] or ""
            insights_raw = row["key_insights_json"]
            insights_text = ""
            if insights_raw:
                try:
                    insights = json.loads(insights_raw)
                    if isinstance(insights, dict):
                        parts = []
                        for key, val in insights.items():
                            if val:
                                parts.append(f"  {key}: {val}")
                        if parts:
                            insights_text = "\nKey insights:\n" + "\n".join(parts)
                except (json.JSONDecodeError, TypeError):
                    pass

            healing_context = f"Recent healing dialogue summary: {summary}{insights_text}"
            return session_id, healing_context
        except Exception as e:
            logger.debug(f"No healing context available for outlook: {e}")
            return None, None

    def _stamp_linked_outlook(self, session_id: int | None, outlook_info: dict | None) -> bool:
        """Stamp the generated outlook's identifier back into the healing session row.

        Writes to ``healing_dialogue_sessions.linked_outlook_id`` so future
        queries can tell which outlook (if any) consumed a given healing
        session's summary. This closes the back-reference loop opened by
        :meth:`_fetch_healing_context`.

        Outlooks do not currently carry a stable integer id in their result
        dict (see ``core/outlook_generator.py`` — the result has ``status``,
        ``narrative``, ``genre``, etc., but no ``id``). When ``outlook_info``
        has no integer ``id`` field we fall back to writing the current unix
        timestamp as a defensive marker so the column is at least non-null and
        the session is visibly "claimed". This marker is intentionally a
        best-effort signal rather than a true foreign key; a clean outlook id
        should be plumbed through once outlooks are persisted with stable ids
        (tracked as future work).

        Args:
            session_id: Row id of the healing session to update. If ``None``,
                this method is a no-op and returns ``False``.
            outlook_info: The dict returned by
                ``OutlookGenerator.generate_single_outlook`` /
                ``generate_epic_outlook``. If it carries an integer ``id`` it is
                used verbatim; otherwise a unix-timestamp marker is written.

        Returns:
            ``True`` if the row was updated, ``False`` otherwise (including
            when ``session_id`` is ``None`` or the DB write fails — failures
            are logged at ``debug`` level so they never break outlook
            generation).
        """
        if session_id is None:
            return False

        # Resolve the value to write. Prefer a real integer id from the
        # outlook result; fall back to a unix-timestamp marker.
        outlook_id: int
        if isinstance(outlook_info, dict) and isinstance(outlook_info.get("id"), int):
            outlook_id = outlook_info["id"]
        else:
            outlook_id = int(datetime.now().timestamp())

        try:
            import sqlite3

            from core.schema import get_db_path

            conn = sqlite3.connect(get_db_path())
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE healing_dialogue_sessions SET linked_outlook_id = ? WHERE id = ?",
                (outlook_id, session_id),
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.debug(f"Failed to stamp linked_outlook_id on session {session_id}: {e}")
            return False

    def _fetch_buddha_context(self) -> str | None:
        """Fetch the latest completed 88 Buddhas recitation session for outlook enrichment.

        Mirrors :meth:`_fetch_healing_context` — pulls the most recent
        completed recitation session (``ended_at IS NOT NULL``) from
        ``buddha_recitation_sessions`` and formats it as additional context
        for the outlook generator. Returns ``None`` when no completed
        sessions exist or the DB is unavailable (defensive).
        """
        try:
            import sqlite3

            from core.schema import get_db_path

            conn = sqlite3.connect(get_db_path())
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """SELECT intention, cycles_completed, total_recited, dedication_text
                   FROM buddha_recitation_sessions
                   WHERE ended_at IS NOT NULL
                   ORDER BY ended_at DESC LIMIT 1""",
            )
            row = cursor.fetchone()
            conn.close()
            if not row:
                return None

            intention = row["intention"] or ""
            cycles = row["cycles_completed"] or 0
            total = row["total_recited"] or 0
            dedication = row["dedication_text"] or ""

            parts = [f"Recent 88 Buddhas recitation — intention: {intention}"]
            parts.append(f"cycles completed: {cycles}")
            parts.append(f"total recited: {total}")
            if dedication:
                parts.append(f"dedication: {dedication}")
            return ", ".join(parts)
        except Exception as e:
            logger.debug(f"No buddha context available for outlook: {e}")
            return None

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
        natal_dt: datetime | None = None,
        natal_location: tuple[float, float] | None = None,
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

        healing_session_id, healing_context = self._fetch_healing_context()
        if healing_context:
            custom_context = f"{custom_context}\n\n{healing_context}" if custom_context else healing_context

        buddha_context = self._fetch_buddha_context()
        if buddha_context:
            custom_context = f"{custom_context}\n\n{buddha_context}" if custom_context else buddha_context

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
            natal_dt=natal_dt,
            natal_location=natal_location,
        )

        # Stamp the generated outlook back into the healing session row so the
        # back-reference is closed. Best-effort — see _stamp_linked_outlook.
        if healing_session_id is not None:
            self._stamp_linked_outlook(healing_session_id, result)

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

        healing_session_id, healing_context = self._fetch_healing_context()
        if healing_context:
            custom_context = f"{custom_context}\n\n{healing_context}" if custom_context else healing_context

        buddha_context = self._fetch_buddha_context()
        if buddha_context:
            custom_context = f"{custom_context}\n\n{buddha_context}" if custom_context else buddha_context

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

        # Stamp the generated outlook back into the healing session row so the
        # back-reference is closed. Best-effort — see _stamp_linked_outlook.
        if healing_session_id is not None:
            self._stamp_linked_outlook(healing_session_id, result)

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

                    # Create the context for the sequencer.
                    # NOTE: RitualState has fields ``intention``, ``genre``,
                    # and ``metadata`` — NOT ``lat``, ``lon``, or
                    # ``target_intention``. The previous constructor call
                    # passed non-existent kwargs, raising TypeError which was
                    # silently swallowed by the broad ``except Exception``
                    # at line 517, so the broadcast loop NEVER produced a
                    # narrative. Fixed: pass lat/lon via ``metadata`` dict
                    # and intention via the correct field name.
                    context = RitualContext(
                        genre=config.get("genre", "healing"),
                        intention=config.get("custom_context") or "",
                        metadata={
                            "lat": config.get("lat", 34.0522),
                            "lon": config.get("lon", -118.2437),
                        },
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
                                # Previously wrote divination_results into
                                # BOTH divination_context AND divination_raw
                                # columns — the raw data (with merged
                                # radionics rates + sigil coordinates) was
                                # lost. Fixed to use the correct field.
                                json.dumps(final_context.divination_raw or final_context.divination_results),
                                # Previously hardcoded to "" — the entity
                                # invocation text (buddha + yidam with
                                # qualities/description/purpose) was computed
                                # and shown to the LLM but never persisted.
                                final_context.entities_used or "",
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
