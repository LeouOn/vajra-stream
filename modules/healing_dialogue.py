"""Healing Dialogue service — session lifecycle, DB persistence, event emission.

Thin DI-container adapter that wraps :class:`~core.llm.healing.AsyncHealingDialogue`
and provides the public surface used by the REST endpoints in
``backend/app/api/v1/endpoints/healing_dialogue.py``. Mirrors the
:class:`~modules.outlook.OutlookService` pattern:

* constructed lazily (the underlying :class:`ProviderRegistry` is only built
  on first use via :func:`~core.llm.bootstrap.build_default_registry`, so
  importing this module never triggers network or provider construction),
* optional ``event_bus`` — when present, :class:`HealingSessionStarted` and
  :class:`HealingSessionCompleted` domain events are published,
* stateless DB access — each method opens a short-lived ``sqlite3`` connection
  via :func:`~core.schema.get_db_path`, matching the pattern in
  ``backend/app/api/v1/endpoints/astrology.py``.

Session state is fully serialized into the ``healing_dialogue_sessions``
table (see :mod:`core.schema`) — the in-memory :class:`DialogueState` is
rebuilt from the DB on every call to :meth:`HealingDialogueService.process_message`,
so the service survives restarts and any number of concurrent workers.

See ``docs/specs/2026-06-17-healing-dialogue-design.md`` sections 4-5 for
the integration map and data model.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from core.healing_dialogue.phases import DialoguePhase, DialogueState
from core.llm.healing import AsyncHealingDialogue
from core.llm.registry import ProviderRegistry
from modules.interfaces import (
    EventBus,
    HealingSessionCompleted,
    HealingSessionStarted,
)

logger = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


class HealingDialogueService:
    """Session lifecycle, DB persistence, and event emission for healing dialogues.

    Public methods (all async except the helpers):

    * :meth:`create_session` — open a new session, persist initial state, emit
      ``HealingSessionStarted``.
    * :meth:`process_message` — append a user turn, call the LLM, append the
      assistant turn, update insights / phase, persist, and (on phase advance
      into SEEING) lazily pull astrology context. On advance into COMPLETED,
      triggers :meth:`summarize_session`.
    * :meth:`get_session` — load a single session's full state.
    * :meth:`list_sessions` — list recent session summaries.
    * :meth:`summarize_session` — ask the LLM to summarize the transcript,
      persist summary + key insights, emit ``HealingSessionCompleted``.
    * :meth:`advance_phase` — manually advance the phase (user override).
    """

    def __init__(self, event_bus: EventBus | None = None) -> None:
        self.event_bus = event_bus
        self._dialogue: AsyncHealingDialogue | None = None
        self._registry: ProviderRegistry | None = None

    # ------------------------------------------------------------------
    # Lazy collaborators
    # ------------------------------------------------------------------
    @property
    def registry(self) -> ProviderRegistry:
        """Lazily build a :class:`ProviderRegistry` for the dialogue to use.

        Built via :func:`core.llm.bootstrap.build_default_registry` so this
        service works identically inside and outside the FastAPI lifespan.
        The registry is cached for the lifetime of this service instance.
        """
        if self._registry is None:
            # Deferred import keeps module-import side effects minimal.
            from core.llm.bootstrap import build_default_registry

            self._registry = build_default_registry()
        return self._registry

    @property
    def dialogue(self) -> AsyncHealingDialogue:
        """Lazily build the :class:`AsyncHealingDialogue` from the registry."""
        if self._dialogue is None:
            self._dialogue = AsyncHealingDialogue(self.registry)
        return self._dialogue

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _connect() -> sqlite3.Connection:
        """Open a short-lived SQLite connection with Row factory.

        Uses the centralized :func:`core.schema.get_db_path` so this service
        and the REST endpoints share the same DB file as the rest of the app.
        """
        from core.schema import get_db_path

        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row
        return conn

    def _load_state_from_db(self, session_id: int) -> DialogueState:
        """Reconstruct a :class:`DialogueState` from the DB row.

        The full state (including ``message_history``, ``accumulated_insights``,
        ``astrology_context``, ``somatic_findings``, ``recommended_practice``,
        ``dedication_text``) is packed into ``transcript_json`` and the
        auxiliary columns. Raises ``KeyError`` if the row is missing.
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM healing_dialogue_sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"healing_dialogue_session id={session_id} not found")

        transcript = json.loads(row["transcript_json"] or "{}")
        # The transcript payload IS the DialogueState.to_dict() output, with
        # session_id remapped to the DB id. Rebuild accordingly.
        payload = dict(transcript)
        payload["session_id"] = str(row["id"])

        # Overlay the authoritative column values where present.
        if row["recommended_practice"]:
            try:
                payload["recommended_practice"] = json.loads(row["recommended_practice"])
            except (json.JSONDecodeError, TypeError):
                pass
        if row["dedication_text"]:
            payload["dedication_text"] = row["dedication_text"]
        # chart_id is authoritative from the column.
        payload["chart_id"] = row["chart_id"]
        # Phase from the column falls back to the transcript.
        payload.setdefault("current_phase", "arrival")

        return DialogueState.from_dict(payload)

    def _save_state_to_db(self, session_id: int, state: DialogueState) -> None:
        """Persist a :class:`DialogueState` back to its DB row.

        The full :meth:`DialogueState.to_dict` payload is written to
        ``transcript_json`` (so the round-trip is lossless). The
        ``current_phase``, ``recommended_practice``, ``dedication_text`` and
        ``ended_at`` columns are mirrored for direct SQL queries.
        """
        payload = state.to_dict()
        # Drop the session_id from the payload — it's the DB id and lives in
        # its own column. Keeping it in the JSON would create a confusing
        # second source of truth.
        payload.pop("session_id", None)

        phases_completed = self._phases_visited(state)
        recommended = (
            json.dumps(state.recommended_practice)
            if state.recommended_practice is not None
            else None
        )
        ended_at = state.completed_at.isoformat() if state.completed_at else None

        with self._connect() as conn:
            conn.execute(
                """
                UPDATE healing_dialogue_sessions
                SET transcript_json     = ?,
                    recommended_practice = ?,
                    dedication_text      = ?,
                    phases_completed     = ?,
                    ended_at             = ?
                WHERE id = ?
                """,
                (
                    json.dumps(payload, default=str),
                    recommended,
                    state.dedication_text,
                    json.dumps(phases_completed),
                    ended_at,
                    session_id,
                ),
            )
            conn.commit()

    @staticmethod
    def _phases_visited(state: DialogueState) -> list[str]:
        """Return the list of phase values the session has touched.

        We always include the current phase, plus the obvious predecessors
        (an arc that reached MEETING has by definition visited ARRIVAL and
        SEEING). This is a static derivation off the enum order — it doesn't
        try to reconstruct history from the message log.
        """
        order = [
            DialoguePhase.ARRIVAL,
            DialoguePhase.SEEING,
            DialoguePhase.MEETING,
            DialoguePhase.RELEASE,
            DialoguePhase.DEDICATION,
            DialoguePhase.COMPLETED,
        ]
        try:
            idx = order.index(state.current_phase)
        except ValueError:  # pragma: no cover - defensive
            return [state.current_phase.value]
        return [p.value for p in order[: idx + 1]]

    # ------------------------------------------------------------------
    # Astrology context pull
    # ------------------------------------------------------------------
    def _pull_astrology_context(self, chart_id: int) -> dict | None:
        """Pull cached chart + transit data for the Seeing phase.

        Loads the saved natal chart's ``cached_chart_data`` (already a JSON
        blob containing western/vedic/houses), then attaches a snapshot of
        the current transit-to-natal aspects via the
        :class:`~core.astrology.AstrologicalCalculator` when coordinates are
        available. Returns ``None`` if the chart is missing or pulling fails
        — the dialogue continues without astrology context rather than
        crashing.
        """
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT name, birth_time_iso, latitude, longitude, timezone, cached_chart_data "
                    "FROM saved_natal_charts WHERE id = ?",
                    (chart_id,),
                ).fetchone()
            if row is None:
                logger.info(
                    "healing dialogue: chart_id=%s not found; skipping astrology context",
                    chart_id,
                )
                return None

            data: dict[str, Any] = {
                "chart_id": chart_id,
                "name": row["name"],
                "birth_time_iso": row["birth_time_iso"],
            }

            cached = row["cached_chart_data"]
            if cached:
                try:
                    data["natal"] = json.loads(cached)
                except (json.JSONDecodeError, TypeError):
                    data["natal_raw"] = cached

            # Attempt a transit snapshot when we have coordinates. Wrapped
            # defensively — a calc failure must not break the dialogue.
            lat = row["latitude"]
            lon = row["longitude"]
            tz = row["timezone"]
            if lat is not None and lon is not None:
                try:
                    from dateutil import parser as _dt_parser

                    from core.astrology import AstrologicalCalculator

                    birth_dt = _dt_parser.parse(row["birth_time_iso"])
                    if birth_dt.tzinfo is None and tz:
                        import pytz

                        birth_dt = pytz.timezone(tz).localize(birth_dt)
                    transit_dt = datetime.now(timezone.utc)
                    calc = AstrologicalCalculator()
                    data["transits"] = calc.get_transits_to_natal(
                        birth_dt, (lat, lon), transit_dt
                    )
                except Exception as exc:  # noqa: BLE001 — best-effort enrichment
                    logger.debug(
                        "healing dialogue: transit calc failed for chart_id=%s: %s",
                        chart_id,
                        exc,
                    )
            return data
        except Exception as exc:  # noqa: BLE001 — must not break the dialogue
            logger.warning(
                "healing dialogue: failed to pull astrology context for chart_id=%s: %s",
                chart_id,
                exc,
            )
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def create_session(
        self,
        chart_id: int | None = None,
        session_type: str = "dialogue",
    ) -> dict:
        """Create a new healing dialogue session.

        Initializes a :class:`DialogueState` at ``ARRIVAL``, persists it to
        the DB, and emits :class:`HealingSessionStarted` on the event bus
        (if wired). Returns ``{"session_id", "phase", "started_at", "chart_id"}``.
        """
        now = datetime.now(timezone.utc)
        # Temporary session_id — the authoritative id is the DB autoincrement.
        state = DialogueState(
            session_id="pending",
            chart_id=chart_id,
            current_phase=DialoguePhase.ARRIVAL,
            phase_started_at=now,
            started_at=now,
        )

        payload = state.to_dict()
        payload.pop("session_id", None)

        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO healing_dialogue_sessions
                (chart_id, session_type, started_at, transcript_json,
                 phases_completed, recommended_practice, dedication_text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chart_id,
                    session_type,
                    state.started_at.isoformat(),
                    json.dumps(payload, default=str),
                    json.dumps([DialoguePhase.ARRIVAL.value]),
                    None,
                    None,
                ),
            )
            session_id = cursor.lastrowid
            conn.commit()

        # Emit domain event.
        if self.event_bus is not None:
            try:
                self.event_bus.publish(
                    HealingSessionStarted(
                        timestamp=now,
                        event_id=str(uuid.uuid4()),
                        target_name=f"healing_dialogue#{session_id}",
                        intention=session_type,
                        duration_minutes=0,
                    )
                )
            except Exception as exc:  # noqa: BLE001 — event bus must not break flow
                logger.warning("HealingSessionStarted emit failed: %s", exc)

        logger.info(
            "healing dialogue: created session id=%s chart_id=%s type=%s",
            session_id,
            chart_id,
            session_type,
        )
        return {
            "session_id": session_id,
            "phase": state.current_phase.value,
            "started_at": state.started_at.isoformat(),
            "chart_id": chart_id,
            "session_type": session_type,
        }

    async def process_message(self, session_id: int, user_message: str) -> dict:
        """Process a user message and advance the dialogue one turn.

        Flow:

        1. Load :class:`DialogueState` from DB.
        2. Append the user message to ``message_history``.
        3. Call :meth:`AsyncHealingDialogue.respond` with the full history,
           current phase, accumulated insights, and any gathered
           astrology/somatic context.
        4. Append the assistant response to ``message_history``.
        5. Merge extracted insights into ``accumulated_insights``.
        6. If a phase hint is returned, advance the phase. When advancing
           into SEEING for the first time, pull astrology context. When
           advancing into COMPLETED, trigger :meth:`summarize_session`.
        7. Persist the updated state.
        8. Return ``{content, phase, phase_hint, insights}``.
        """
        state = self._load_state_from_db(session_id)
        state.append_message("user", user_message)

        result = await self.dialogue.respond(
            messages=state.message_history,
            phase=state.current_phase,
            insights=state.accumulated_insights or None,
            astrology_context=state.astrology_context,
            somatic_findings=state.somatic_findings,
        )

        content = result.get("content", "")
        phase_hint = result.get("phase_hint")
        insights_update = result.get("insights_update") or {}

        state.append_message("assistant", content)
        self._merge_insights(state, insights_update)

        # Phase transition handling.
        next_phase_value = self._resolve_phase_hint(state, phase_hint)
        if next_phase_value is not None:
            self._apply_phase_advance(state, next_phase_value)

        # Pull astrology context on first entry to SEEING.
        if (
            state.current_phase is DialoguePhase.SEEING
            and state.astrology_context is None
            and state.chart_id is not None
        ):
            state.astrology_context = self._pull_astrology_context(state.chart_id)

        # Persist state.
        self._save_state_to_db(session_id, state)

        # On completion, summarize + emit HealingSessionCompleted.
        if state.current_phase is DialoguePhase.COMPLETED:
            try:
                await self.summarize_session(session_id)
            except Exception as exc:  # noqa: BLE001 — summary is best-effort
                logger.warning(
                    "healing dialogue: summarize_session failed for id=%s: %s",
                    session_id,
                    exc,
                )

        return {
            "session_id": session_id,
            "content": content,
            "phase": state.current_phase.value,
            "phase_hint": phase_hint,
            "insights": state.accumulated_insights,
        }

    async def get_session(self, session_id: int) -> dict:
        """Load a session's full state.

        Returns a dict with ``session_id``, ``phase``, ``started_at``,
        ``completed_at``, ``chart_id``, ``message_history``,
        ``accumulated_insights``, ``astrology_context``, ``somatic_findings``,
        ``recommended_practice``, ``dedication_text``, and the DB columns
        ``summary`` and ``key_insights`` (populated after completion).
        """
        state = self._load_state_from_db(session_id)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT summary, key_insights_json, linked_outlook_id, ended_at "
                "FROM healing_dialogue_sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
        summary = None
        key_insights: dict | None = None
        linked_outlook_id = None
        ended_at = None
        if row is not None:
            summary = row["summary"]
            ended_at = row["ended_at"]
            linked_outlook_id = row["linked_outlook_id"]
            if row["key_insights_json"]:
                try:
                    key_insights = json.loads(row["key_insights_json"])
                except (json.JSONDecodeError, TypeError):
                    key_insights = None

        return {
            "session_id": session_id,
            "phase": state.current_phase.value,
            "chart_id": state.chart_id,
            "started_at": state.started_at.isoformat() if state.started_at else None,
            "completed_at": (
                state.completed_at.isoformat() if state.completed_at else ended_at
            ),
            "message_history": state.message_history,
            "accumulated_insights": state.accumulated_insights,
            "astrology_context": state.astrology_context,
            "somatic_findings": state.somatic_findings,
            "recommended_practice": state.recommended_practice,
            "dedication_text": state.dedication_text,
            "summary": summary,
            "key_insights": key_insights,
            "linked_outlook_id": linked_outlook_id,
        }

    async def list_sessions(self, limit: int = 20) -> list[dict]:
        """List recent sessions, newest first.

        Returns a list of summary dicts (no transcript body) suitable for
        driving a session-picker UI.
        """
        limit = max(1, min(int(limit), 200))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, chart_id, session_type, started_at, ended_at,
                       summary, phases_completed, linked_outlook_id
                FROM healing_dialogue_sessions
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        out: list[dict] = []
        for row in rows:
            phases: list[str] = []
            if row["phases_completed"]:
                try:
                    phases = json.loads(row["phases_completed"])
                except (json.JSONDecodeError, TypeError):
                    phases = []
            out.append(
                {
                    "session_id": row["id"],
                    "chart_id": row["chart_id"],
                    "session_type": row["session_type"],
                    "started_at": row["started_at"],
                    "ended_at": row["ended_at"],
                    "summary": row["summary"],
                    "phases_completed": phases,
                    "linked_outlook_id": row["linked_outlook_id"],
                }
            )
        return out

    async def summarize_session(self, session_id: int) -> str:
        """Generate an LLM summary of the session.

        Loads the full transcript, asks the LLM to distill it into a short
        summary plus structured ``key_insights`` (themes, emotions,
        breakthroughs), persists both to the DB, and emits
        :class:`HealingSessionCompleted`. Returns the summary text.
        """
        state = self._load_state_from_db(session_id)
        transcript_lines = self._format_transcript(state.message_history)
        if not transcript_lines.strip():
            summary_text = "Session transcript was empty; no summary generated."
            key_insights: dict[str, Any] = {}
        else:
            summary_text, key_insights = await self._generate_summary(
                transcript_lines, state
            )

        # Merge any LLM-extracted insights back into accumulated_insights.
        if key_insights:
            self._merge_insights(state, key_insights)

        self._persist_summary(session_id, state, summary_text, key_insights)

        # Emit domain event.
        if self.event_bus is not None:
            try:
                self.event_bus.publish(
                    HealingSessionCompleted(
                        timestamp=datetime.now(timezone.utc),
                        event_id=str(uuid.uuid4()),
                        session_id=str(session_id),
                        summary=summary_text,
                        key_insights=key_insights or {},
                    )
                )
            except Exception as exc:  # noqa: BLE001 — event bus must not break flow
                logger.warning("HealingSessionCompleted emit failed: %s", exc)

        logger.info(
            "healing dialogue: summarized session id=%s (%d chars)",
            session_id,
            len(summary_text),
        )
        return summary_text

    async def advance_phase(self, session_id: int) -> dict:
        """Manually advance the phase (user force-advance).

        Loads state, advances one phase via :meth:`DialogueState.advance_phase`,
        pulls astrology context on entry to SEEING, persists, and returns
        the new phase summary. On advance into COMPLETED, triggers
        :meth:`summarize_session`.
        """
        state = self._load_state_from_db(session_id)
        if state.is_terminal():
            return {
                "session_id": session_id,
                "phase": state.current_phase.value,
                "advanced": False,
                "message": "Session is already in the terminal COMPLETED phase.",
            }

        state.advance_phase()

        if (
            state.current_phase is DialoguePhase.SEEING
            and state.astrology_context is None
            and state.chart_id is not None
        ):
            state.astrology_context = self._pull_astrology_context(state.chart_id)

        self._save_state_to_db(session_id, state)

        if state.current_phase is DialoguePhase.COMPLETED:
            try:
                await self.summarize_session(session_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "healing dialogue: summarize_session after manual advance failed: %s",
                    exc,
                )

        return {
            "session_id": session_id,
            "phase": state.current_phase.value,
            "advanced": True,
        }

    # ------------------------------------------------------------------
    # Internal helpers — phase transition logic
    # ------------------------------------------------------------------
    @staticmethod
    def _resolve_phase_hint(
        state: DialogueState, phase_hint: str | None
    ) -> str | None:
        """Validate a phase hint against the current state.

        Returns the next-phase value when ``phase_hint`` is a valid forward
        step from the current phase (i.e. the hinted phase is the next one
        in the arc, or further ahead). Returns ``None`` when the hint is
        missing, references the current/previous phase, or is invalid.
        """
        if not phase_hint:
            return None
        try:
            hinted = DialoguePhase(phase_hint)
        except ValueError:
            return None

        order = [
            DialoguePhase.ARRIVAL,
            DialoguePhase.SEEING,
            DialoguePhase.MEETING,
            DialoguePhase.RELEASE,
            DialoguePhase.DEDICATION,
            DialoguePhase.COMPLETED,
        ]
        try:
            current_idx = order.index(state.current_phase)
            hinted_idx = order.index(hinted)
        except ValueError:  # pragma: no cover - defensive
            return None
        # Only accept forward transitions.
        if hinted_idx <= current_idx:
            return None
        # Step one phase at a time — the LLM's hint may be several steps
        # ahead, but we want each phase to actually land.
        return order[current_idx + 1].value

    @staticmethod
    def _apply_phase_advance(state: DialogueState, next_phase_value: str) -> None:
        """Advance ``state`` to ``next_phase_value`` (validated by caller).

        Stamps ``phase_started_at`` and (on COMPLETED) ``completed_at``.
        """
        try:
            target = DialoguePhase(next_phase_value)
        except ValueError:  # pragma: no cover - defensive
            return
        # Walk forward one step at a time until we reach the target.
        # This intentionally only moves one phase per turn even if the
        # caller passed a multi-step hint — see _resolve_phase_hint.
        while state.current_phase is not target and not state.is_terminal():
            state.advance_phase()

    @staticmethod
    def _merge_insights(state: DialogueState, update: dict) -> None:
        """Merge an ``insights_update`` dict into ``accumulated_insights``.

        Lists under the same key are unioned (preserving order, deduped).
        Dict values are merged recursively. Scalars overwrite.
        """
        if not update:
            return
        if not state.accumulated_insights:
            state.accumulated_insights = {}
        insights = state.accumulated_insights
        for key, value in update.items():
            if isinstance(value, list):
                existing = insights.get(key)
                if isinstance(existing, list):
                    merged = list(existing)
                    for item in value:
                        if item not in merged:
                            merged.append(item)
                    insights[key] = merged
                else:
                    insights[key] = list(value)
            elif isinstance(value, dict) and isinstance(insights.get(key), dict):
                merged_dict = dict(insights[key])
                merged_dict.update(value)
                insights[key] = merged_dict
            else:
                insights[key] = value

    # ------------------------------------------------------------------
    # Internal helpers — summary generation
    # ------------------------------------------------------------------
    @staticmethod
    def _format_transcript(history: list[dict]) -> str:
        """Render the message history as a readable transcript for the LLM."""
        if not history:
            return ""
        lines: list[str] = []
        for msg in history:
            role = str(msg.get("role", "user")).upper()
            content = str(msg.get("content", "")).strip()
            if not content:
                continue
            lines.append(f"{role}:\n{content}")
        return "\n\n".join(lines)

    async def _generate_summary(
        self, transcript: str, state: DialogueState
    ) -> tuple[str, dict]:
        """Ask the LLM to summarize the transcript.

        Falls back to a deterministic short summary when no provider is
        available (so a session with no LLM connectivity still completes
        cleanly). Returns ``(summary_text, key_insights_dict)``.
        """
        summary_prompt = (
            "Summarize this healing dialogue session. Identify the core themes, "
            "the emotions that arose, the body locations mentioned, the chart "
            "findings (if any), the practice offered (if any), and any "
            "breakthroughs or dedications. Respond as JSON with the shape:\n"
            '{"summary": "<2-3 sentence distillation>", '
            '"key_insights": {"themes": [...], "emotions": [...], '
            '"body_locations": [...], "chart_findings": [...], '
            '"breakthroughs": [...]}}\n\n'
            f"TRANSCRIPT:\n{transcript}"
        )
        try:
            provider = await self.registry.pick_best()
            if provider is None:
                return self._fallback_summary(transcript, state)
            from core.llm.models import ChatMessage, ChatRequest

            request = ChatRequest(
                messages=[
                    ChatMessage(
                        role="user",
                        content=summary_prompt,
                    )
                ],
                system_prompt=(
                    "You distill healing dialogue sessions for the outlook "
                    "feedback loop. Be precise and compassionate."
                ),
                max_tokens=500,
                temperature=0.4,
            )
            response = await provider.generate(request)
            return self._parse_summary_payload(response.content or "")
        except Exception as exc:  # noqa: BLE001 — summary is best-effort
            logger.warning(
                "healing dialogue: LLM summary generation failed (%s); using fallback",
                exc,
            )
            return self._fallback_summary(transcript, state)

    @staticmethod
    def _parse_summary_payload(content: str) -> tuple[str, dict]:
        """Parse the LLM's summary response into ``(summary, key_insights)``.

        Accepts a JSON object matching the prompt shape. Falls back to using
        the raw content as the summary text when parsing fails.
        """
        # Try to extract a JSON block (the LLM may wrap it in prose).
        candidates: list[str] = []
        text = content.strip()
        # Direct JSON parse first.
        candidates.append(text)
        # First {...} block.
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidates.append(text[start : end + 1])

        for candidate in candidates:
            try:
                payload = json.loads(candidate)
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(payload, dict):
                summary = str(payload.get("summary") or "").strip()
                key_insights_raw = payload.get("key_insights")
                key_insights = (
                    key_insights_raw if isinstance(key_insights_raw, dict) else {}
                )
                if summary:
                    return summary, key_insights
        # Fall through: use raw content as summary, no structured insights.
        return content.strip()[:500], {}

    @staticmethod
    def _fallback_summary(transcript: str, state: DialogueState) -> tuple[str, dict]:
        """Deterministic short summary used when the LLM is unavailable."""
        # Take the last user message as a rough anchor for the session topic.
        last_user = ""
        for msg in reversed(state.message_history):
            if msg.get("role") == "user":
                last_user = str(msg.get("content", ""))[:200]
                break
        summary = (
            f"Healing dialogue session reached the {state.current_phase.value} phase. "
            f"Final user turn: \"{last_user}\""
        )
        key_insights = dict(state.accumulated_insights or {})
        return summary, key_insights

    def _persist_summary(
        self,
        session_id: int,
        state: DialogueState,
        summary_text: str,
        key_insights: dict,
    ) -> None:
        """Persist the summary, insights, and (if terminal) ended_at to the DB."""
        ended_at = state.completed_at.isoformat() if state.completed_at else _utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE healing_dialogue_sessions
                SET summary            = ?,
                    key_insights_json  = ?,
                    ended_at           = ?
                WHERE id = ?
                """,
                (
                    summary_text,
                    json.dumps(key_insights, default=str),
                    ended_at,
                    session_id,
                ),
            )
            conn.commit()


__all__ = ["HealingDialogueService"]
