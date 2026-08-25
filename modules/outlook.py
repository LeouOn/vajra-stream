"""
Outlook Module
Thin adapter wrapping core/outlook_generator.py for the DI container.
Supports background broadcast loops.
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.core.services.rng_attunement_service import get_rng_service
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
