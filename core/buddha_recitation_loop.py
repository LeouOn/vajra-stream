"""
88 Buddhas Continuous Recitation Loop
Perpetual mala-cycle recitation of the 88 Buddha names with TTS,
dedication intervals, and progress tracking.

Usage:
    loop = BuddhaRecitationLoop()
    await loop.start(intention="world peace", mala_cycles=3)
    # Runs in background, reciting all 88 names per cycle
    # Dedication every 21 names, full dedication every 108

Speaker resolution:
    The loop uses the unified TTSProvider with role="buddhist_chant" by default.
    The speaker is auto-mapped per project via the TTSProvider's role registry
    (Uncle_Fu for Qwen, zh-CN-YunxiNeural for Edge). Callers can pass an
    explicit `voice` to override, or `project_id` to use per-project overrides.
"""

import asyncio
import logging
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.eighty_eight_buddhas import get_eighty_eight_buddhas
from modules.interfaces import EventBus, RecitationCompleted, RecitationStarted

logger = logging.getLogger(__name__)


@dataclass
class RecitationState:
    """Mutable state for the recitation loop."""

    running: bool = False
    intention: str = ""
    current_index: int = 0
    current_cycle: int = 0
    total_recited: int = 0
    mala_count: int = 0
    dedications: int = 0
    current_buddha: dict[str, Any] = field(default_factory=dict)
    started_at: str = ""
    last_recited_at: str = ""
    backend: str = ""
    speaker: str = ""
    role: str = "buddhist_chant"
    project_id: str | None = None
    stats: dict[str, Any] = field(default_factory=dict)
    # DB primary key of the row in ``buddha_recitation_sessions`` for this
    # invocation. ``None`` when the session has not been persisted yet (or
    # when persistence is unavailable, e.g. tests with no DB). All DB
    # operations are defensive — the in-memory loop still runs if this is None.
    session_db_id: int | None = None


class BuddhaRecitationLoop:
    """
    Continuous 88-Buddha recitation loop.

    Cycles through all 88 names with configurable:
    - Interval between names (seconds)
    - Mala cycle size (default 108 names before full dedication)
    - Sub-dedication interval (every 21 names)
    - TTS voice selection
    - Callback hooks for UI updates
    """

    def __init__(self, tts_reciter=None, event_bus: EventBus | None = None):
        """
        Args:
            tts_reciter: Optional pre-built TTS engine. If None, the loop will
                use the unified TTSProvider (Qwen3-TTS or Edge) on start().
            event_bus: Optional event bus (implements ``publish(event)``). When
                supplied, :class:`RecitationStarted` / :class:`RecitationCompleted`
                domain events are published on start/stop. Persistence and the
                WebSocket broadcasts work regardless of this argument.
        """
        self._svc = get_eighty_eight_buddhas()
        self._tts = tts_reciter
        self.event_bus = event_bus
        self.state = RecitationState()
        self._on_name: list[callable] = []
        self._on_dedication: list[callable] = []
        self._on_cycle_complete: list[callable] = []
        self._buddhas: list[dict] = []
        self._voice_override: str | None = None
        self._provider = None

    def _load_buddhas(self):
        """Load the full 88-Buddha list for recitation."""
        seq = self._svc.get_confession_sequence()
        past = [
            {
                "name_chinese": b["name_chinese"],
                "name_pinyin": b["name_pinyin"],
                "name_sanskrit": b["name_sanskrit"],
                "category": "past",
            }
            for b in seq.get("fifty_three_past_buddhas", [])
        ]
        conf = [
            {
                "name_chinese": b["name_chinese"],
                "name_pinyin": b["name_pinyin"],
                "name_sanskrit": b["name_sanskrit"],
                "category": "confession",
            }
            for b in seq.get("thirty_five_confession_buddhas", [])
        ]
        self._buddhas = past + conf

    # ------------------------------------------------------------------
    # DB persistence helpers (defensive — never break the in-memory loop)
    # ------------------------------------------------------------------
    @staticmethod
    def _connect() -> sqlite3.Connection:
        """Open a short-lived SQLite connection.

        Same pattern as :class:`modules.healing_dialogue.HealingDialogueService`:
        ``check_same_thread=False`` is unnecessary here because every call
        opens its own connection and immediately commits, but ``Row`` factory
        gives consistent dict-style access for the read helpers.
        """
        from core.schema import get_db_path

        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row
        return conn

    def _persist_session_start(self, intention: str, started_at_iso: str) -> int | None:
        """INSERT a new row in ``buddha_recitation_sessions``.

        Returns the new row id, or ``None`` on failure (the in-memory loop
        continues regardless — persistence is additive).
        """
        try:
            with self._connect() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO buddha_recitation_sessions
                        (intention, started_at, cycles_completed, total_recited)
                    VALUES (?, ?, 0, 0)
                    """,
                    (intention, started_at_iso),
                )
                conn.commit()
                return cursor.lastrowid
        except Exception as exc:  # noqa: BLE001 — DB must not break the loop
            logger.warning("buddha_recitation: failed to persist session start: %s", exc)
            return None

    def _persist_session_progress(self) -> None:
        """UPDATE the current row with the latest counters.

        Called from the loop after each name recitation and after each full
        cycle. No-op when :attr:`RecitationState.session_db_id` is unset.
        """
        sid = self.state.session_db_id
        if sid is None:
            return
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    UPDATE buddha_recitation_sessions
                    SET cycles_completed = ?,
                        total_recited    = ?
                    WHERE id = ?
                    """,
                    (self.state.current_cycle, self.state.total_recited, sid),
                )
                conn.commit()
        except Exception as exc:  # noqa: BLE001 — DB must not break the loop
            logger.debug("buddha_recitation: progress persist failed: %s", exc)

    def _persist_session_end(
        self, ended_at_iso: str, summary: str, dedication_text: str | None
    ) -> None:
        """FINALIZE the current row with ``ended_at``, ``summary``, ``dedication_text``."""
        sid = self.state.session_db_id
        if sid is None:
            return
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    UPDATE buddha_recitation_sessions
                    SET ended_at        = ?,
                        cycles_completed = ?,
                        total_recited    = ?,
                        dedication_text  = ?,
                        summary          = ?
                    WHERE id = ?
                    """,
                    (
                        ended_at_iso,
                        self.state.current_cycle,
                        self.state.total_recited,
                        dedication_text,
                        summary,
                        sid,
                    ),
                )
                conn.commit()
        except Exception as exc:  # noqa: BLE001 — DB must not break the loop
            logger.warning("buddha_recitation: failed to persist session end: %s", exc)

    def _safe_publish(self, event: Any) -> None:
        """Publish ``event`` on the event bus if one is wired."""
        if self.event_bus is None:
            return
        try:
            self.event_bus.publish(event)
        except Exception as exc:  # noqa: BLE001 — event bus must not break the loop
            logger.warning("buddha_recitation: event publish failed: %s", exc)

    def on_name_recited(self, callback):
        """Register callback invoked after each Buddha name is recited."""
        self._on_name.append(callback)

    def on_dedication(self, callback):
        """Register callback invoked at dedication intervals."""
        self._on_dedication.append(callback)

    def on_cycle_complete(self, callback):
        """Register callback invoked when a full 88-name cycle completes."""
        self._on_cycle_complete.append(callback)

    async def start(
        self,
        intention: str = "愿一切众生离苦得乐",
        interval_seconds: float = 3.0,
        dedication_interval: int = 21,
        mala_cycles: int | None = None,
        voice: str = "zh-CN-YunxiNeural",
        role: str = "buddhist_chant",
        project_id: str | None = None,
    ) -> RecitationState:
        """
        Start the continuous recitation loop.

        Args:
            intention: Dedication intention
            interval_seconds: Seconds between each Buddha name
            dedication_interval: Recite dedication every N names (default 21)
            mala_cycles: Stop after N full 88-name cycles (None = infinite)
            voice: Explicit voice/speaker override (bypasses role mapping).
                   Default 'zh-CN-YunxiNeural' is only used for legacy Edge paths.
            role: Ritual role used for per-project auto-speaker mapping.
                  Defaults to 'buddhist_chant'. Ignored if `voice` is provided.
            project_id: Project id; the loop will use per-project speaker
                  overrides if set via `tts_provider.set_project_speaker(...)`.
        """
        if self.state.running:
            return self.state

        self._load_buddhas()
        if not self._buddhas:
            self.state.running = False
            return self.state

        self.state = RecitationState(
            running=True,
            intention=intention,
            started_at=datetime.now().isoformat(),
            role=role,
            project_id=project_id,
        )
        self._voice_override = voice

        # Persist the new session row. DB failures are non-fatal — the
        # in-memory loop continues to work with ``session_db_id = None``.
        self.state.session_db_id = self._persist_session_start(
            intention, self.state.started_at
        )

        # Broadcast WS event
        self._broadcast_ws(
            "BUDDHA_RECITATION_STARTED",
            {
                "intention": intention,
                "total_buddhas": len(self._buddhas),
            },
        )

        # Publish domain event (best-effort).
        if self.state.session_db_id is not None:
            self._safe_publish(
                RecitationStarted(
                    timestamp=datetime.now(timezone.utc),
                    event_id=str(uuid.uuid4()),
                    intention=intention,
                    session_id=self.state.session_db_id,
                )
            )

        # Initialize TTS if not explicitly disabled
        if self._tts is None:
            try:
                from core.tts_provider import get_tts_provider

                self._provider = get_tts_provider()
                # Apply project_id on the provider for per-project overrides
                if project_id is not None:
                    self._provider.config.project_id = project_id
                self.state.backend = self._provider.active_backend.value
                # Resolve the actual speaker the loop will use
                edge_v, qwen_s = self._provider._resolve_voice(voice if voice != "zh-CN-YunxiNeural" else None, role)
                if self._provider.active_backend.value == "qwen":
                    self.state.speaker = qwen_s or "Uncle_Fu"
                else:
                    self.state.speaker = edge_v or "zh-CN-YunxiNeural"
            except Exception as e:
                logger.warning("TTSProvider unavailable, falling back to legacy BuddhaTTSReciter: %s", e)
                self._provider = None
                try:
                    from core.buddha_tts import BuddhaTTSReciter

                    self._tts = BuddhaTTSReciter(voice=voice)
                except Exception:
                    self._tts = False  # Sentinel: TTS unavailable

        # Run the loop as a background task
        asyncio.create_task(self._run_loop(interval_seconds, dedication_interval, mala_cycles))
        return self.state

    def _broadcast_ws(self, event_type: str, data: dict):
        """Broadcast a recitation event to all WebSocket clients."""
        try:
            import asyncio

            from backend.websocket.connection_manager_stable_v2 import stable_connection_manager_v2

            payload = {"type": event_type, "data": data, "timestamp": __import__("time").time()}
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(stable_connection_manager_v2.broadcast(payload))
            except RuntimeError:
                pass
        except Exception:
            pass

    def stop(self) -> RecitationState:
        """Stop the recitation loop."""
        self.state.running = False

        # Finalize the DB row + emit the completed domain event. Best-effort:
        # a failure here does not affect the in-memory state.
        ended_at_iso = datetime.now().isoformat()
        dedication_text = (
            "愿以此功德 普及于一切 我等与众生 皆共成佛道"
        )
        summary = (
            f"Recited {self.state.total_recited} Buddha names across "
            f"{self.state.current_cycle} full cycle(s) with "
            f"{self.state.dedications} dedication(s). "
            f"Intention: {self.state.intention}"
        )
        self._persist_session_end(ended_at_iso, summary, dedication_text)

        if self.state.session_db_id is not None:
            self._safe_publish(
                RecitationCompleted(
                    timestamp=datetime.now(timezone.utc),
                    event_id=str(uuid.uuid4()),
                    session_id=self.state.session_db_id,
                    cycles_completed=self.state.current_cycle,
                    total_recited=self.state.total_recited,
                    dedication_text=dedication_text,
                )
            )

        self._broadcast_ws("BUDDHA_RECITATION_STOPPED", self.get_status())
        return self.state

    def get_status(self) -> dict[str, Any]:
        """Get current recitation status."""
        total = len(self._buddhas)
        return {
            "running": self.state.running,
            "intention": self.state.intention,
            "current_index": self.state.current_index,
            "current_cycle": self.state.current_cycle,
            "total_recited": self.state.total_recited,
            "mala_count": self.state.mala_count,
            "dedications": self.state.dedications,
            "total_buddhas": total,
            "current_buddha": self.state.current_buddha,
            "progress_pct": round((self.state.current_index / total * 100), 1) if total else 0,
            "started_at": self.state.started_at,
            "last_recited_at": self.state.last_recited_at,
            "backend": self.state.backend,
            "speaker": self.state.speaker,
            "role": self.state.role,
            "project_id": self.state.project_id,
        }

    async def _speak_text(self, text: str, rate: str | None = None) -> bool:
        """Internal: speak a single text via the active TTS backend."""
        # Preferred: unified TTSProvider (Qwen3-TTS or Edge)
        if self._provider is not None:
            try:
                rate_arg = rate
                # Edge TTS expects a percent string; Qwen ignores it
                edge_v, qwen_s = self._provider._resolve_voice(
                    self._voice_override if self._voice_override != "zh-CN-YunxiNeural" else None,
                    self.state.role,
                )
                path = await self._provider.speak(
                    text=text,
                    voice=self._voice_override if self._voice_override != "zh-CN-YunxiNeural" else None,
                    rate=rate_arg,
                    role=self.state.role,
                )
                if path:
                    return True
            except Exception as e:
                logger.debug("TTSProvider speak failed, trying legacy reciter: %s", e)
        # Fallback: legacy BuddhaTTSReciter (Edge only)
        if self._tts and self._tts is not False and getattr(self._tts, "available", False):
            try:
                await self._tts.speak(text, rate=rate or "-30%")
                return True
            except Exception:
                return False
        return False

    async def _run_loop(self, interval_seconds: float, dedication_interval: int, max_cycles: int | None):
        """Internal: main recitation loop."""
        total = len(self._buddhas)
        opening = "大慈大悲愍众生 大喜大舍济含识 南無"

        while self.state.running:
            for i, buddha in enumerate(self._buddhas):
                if not self.state.running:
                    break

                self.state.current_index = i
                self.state.current_buddha = buddha
                self.state.total_recited += 1
                self.state.mala_count += 1
                self.state.last_recited_at = datetime.now().isoformat()

                # Recite the name via TTS
                name = buddha.get("name_chinese", "")
                if name:
                    text = f"南無{name}" if not name.startswith("南無") else name
                    await self._speak_text(text, rate="-30%")

                # Fire name-recited callbacks
                for cb in self._on_name:
                    try:
                        cb(buddha, self.state)
                    except Exception:
                        pass

                # Broadcast to WebSocket (throttled: every 3rd name to avoid flooding)
                if self.state.total_recited % 3 == 0:
                    self._broadcast_ws("BUDDHA_NAME_RECITED", self.get_status())

                # Persist progress (every name; defensive — see helper).
                # SQLite local writes are sub-ms and the default interval is
                # 3s/name, so this is cheap and matches the spec.
                self._persist_session_progress()

                # Dedication interval
                if self.state.mala_count > 0 and self.state.mala_count % dedication_interval == 0:
                    self.state.dedications += 1
                    dedication_text = "愿以此功德 普及于一切 我等与众生 皆共成佛道"
                    await self._speak_text(dedication_text, rate="-40%")
                    for cb in self._on_dedication:
                        try:
                            cb(self.state.mala_count, self.state)
                        except Exception:
                            pass

                # Full mala (108) dedication
                if self.state.mala_count > 0 and self.state.mala_count % 108 == 0:
                    full_ded = f"{dedication_text}。回向法界一切众生，同证无上正等正觉。"
                    await self._speak_text(full_ded, rate="-40%")
                    self.state.mala_count = 0
                    for cb in self._on_cycle_complete:
                        try:
                            cb(self.state)
                        except Exception:
                            pass

                # Wait between names
                await asyncio.sleep(interval_seconds)

            # Cycle complete
            self.state.current_cycle += 1
            # Persist the bumped cycle counter immediately.
            self._persist_session_progress()
            for cb in self._on_cycle_complete:
                try:
                    cb(self.state)
                except Exception:
                    pass

            # Stop if max cycles reached
            if max_cycles and self.state.current_cycle >= max_cycles:
                break

        self.state.running = False

        # Final dedication
        final = "功德圆满。愿以此念诵88佛之功德，回向法界一切众生，离苦得乐，早证菩提。"
        await self._speak_text(final, rate="-35%")


# Global instance
_recitation_loop: BuddhaRecitationLoop | None = None


def get_recitation_loop() -> BuddhaRecitationLoop:
    global _recitation_loop
    if _recitation_loop is None:
        _recitation_loop = BuddhaRecitationLoop()
    return _recitation_loop


# ---------------------------------------------------------------------------
# Read-side helpers (for SessionHistory / DailyStreak frontend components)
# ---------------------------------------------------------------------------
# These are module-level functions rather than classmethods because they have
# no dependency on the running loop instance — they just read the
# ``buddha_recitation_sessions`` table. Endpoint code can call them directly.


def _open_recitation_db() -> sqlite3.Connection:
    """Open a short-lived read connection with Row factory."""
    from core.schema import get_db_path

    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def get_recent_sessions(limit: int = 20) -> list[dict[str, Any]]:
    """Return the most recent recitation sessions, newest first.

    Each row is shaped for the ``SessionHistory.jsx`` component:
    ``session_id``, ``intention``, ``started_at``, ``ended_at``,
    ``cycles_completed``, ``total_recited``, ``dedication_text``,
    ``summary``, ``linked_healing_session_id``. Returns an empty list when
    the table is missing or unreadable (defensive — frontend still renders).
    """
    limit = max(1, min(int(limit), 200))
    try:
        with _open_recitation_db() as conn:
            rows = conn.execute(
                """
                SELECT id, intention, started_at, ended_at,
                       cycles_completed, total_recited, dedication_text,
                       summary, linked_healing_session_id
                FROM buddha_recitation_sessions
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    except sqlite3.OperationalError as exc:
        # Table not created yet — fresh install before first init_db().
        logger.debug("buddha_recitation: get_recent_sessions: %s", exc)
        return []
    except Exception as exc:  # noqa: BLE001 — read helper must not raise
        logger.warning("buddha_recitation: get_recent_sessions failed: %s", exc)
        return []

    return [
        {
            "session_id": row["id"],
            "intention": row["intention"],
            "started_at": row["started_at"],
            "ended_at": row["ended_at"],
            "cycles_completed": row["cycles_completed"],
            "total_recited": row["total_recited"],
            "dedication_text": row["dedication_text"],
            "summary": row["summary"],
            "linked_healing_session_id": row["linked_healing_session_id"],
        }
        for row in rows
    ]


def get_streak() -> int:
    """Return the current consecutive-day recitation streak.

    Counts consecutive UTC days (ending today, or ending on the most recent
    session date if no session happened today) that contain at least one
    started session. Returns ``0`` when there are no sessions or the table
    is unavailable.

    The streak is forgiving: it walks back from the most recent session's
    day, so a streak doesn't break until a full day passes with no session.
    """
    try:
        with _open_recitation_db() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT DATE(started_at) AS day
                FROM buddha_recitation_sessions
                WHERE started_at IS NOT NULL
                ORDER BY day DESC
                """,
            ).fetchall()
    except sqlite3.OperationalError as exc:
        logger.debug("buddha_recitation: get_streak: %s", exc)
        return 0
    except Exception as exc:  # noqa: BLE001 — read helper must not raise
        logger.warning("buddha_recitation: get_streak failed: %s", exc)
        return 0

    if not rows:
        return 0

    # Parse distinct days into a set for O(1) membership checks.
    days: set[str] = {row["day"] for row in rows if row["day"]}

    # Anchor: the most recent session day. Walk back counting consecutive
    # days that have a session.
    most_recent = max(days)
    try:
        cursor_date = datetime.fromisoformat(most_recent).date()
    except (ValueError, TypeError):
        return 0

    streak = 0
    # Cap at 10_000 iterations as a hard safety net against pathological data.
    for _ in range(10_000):
        if cursor_date.isoformat() not in days:
            break
        streak += 1
        try:
            cursor_date = cursor_date.fromordinal(cursor_date.toordinal() - 1)
        except (ValueError, OverflowError):
            break
    return streak
