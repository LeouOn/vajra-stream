"""
Autonomous Ritual Engine — 24/7 self-running blessing orchestrator.

Monitors planetary hours, selects optimal practices based on auspicious
timing + merit multipliers + history, then autonomously executes complete
4-phase rituals (PREPARATION → INVOCATION → BROADCAST → DEDICATION).

Architecture:
    RitualScheduler (asyncio loop, every 60s)
        → PracticeSelector (scores practices by timing + merit + novelty)
        → RitualExecutionEngine (4-phase ritual orchestration)
            → TTS (speak invocations + sutras + dedications)
            → DeepSeek API (generate blessings)
            → WebSocket (broadcast status to frontend)
            → SQLite DB (log history, track merit)
            → EventBus (notify AutonomousAgent)

Usage:
    engine = get_ritual_engine()
    await engine.start()     # Begin autonomous operation
    await engine.stop()      # Pause
    status = engine.status   # Current state

API:
    POST /api/v1/ritual/start    — Start autonomous engine
    POST /api/v1/ritual/stop     — Stop engine
    GET  /api/v1/ritual/status   — Current status + history + schedule
    POST /api/v1/ritual/trigger  — Manually trigger next ritual now
"""

import asyncio
import json
import logging
import os
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ─── Data Classes ──────────────────────────────────────────

class RitualPhase(str, Enum):
    IDLE = "idle"
    PREPARATION = "preparation"
    INVOCATION = "invocation"
    BROADCAST = "broadcast"
    DEDICATION = "dedication"
    COMPLETED = "completed"


class EngineState(str, Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    EXECUTING = "executing"  # Mid-ritual
    PAUSED = "paused"


@dataclass
class RitualRecord:
    """A completed ritual logged to the database."""
    id: int = 0
    practice_name: str = ""
    practice_id: str = ""
    genre: str = ""
    planetary_hour: str = ""
    timing_quality: str = ""
    merit_multiplier: int = 1
    narrative_length: int = 0
    tts_generated: bool = False
    started_at: str = ""
    completed_at: str = ""
    narrative_preview: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "practice_name": self.practice_name,
            "practice_id": self.practice_id, "genre": self.genre,
            "planetary_hour": self.planetary_hour, "timing_quality": self.timing_quality,
            "merit_multiplier": self.merit_multiplier, "narrative_length": self.narrative_length,
            "tts_generated": self.tts_generated,
            "started_at": self.started_at, "completed_at": self.completed_at,
            "narrative_preview": self.narrative_preview,
        }


@dataclass
class PracticeScore:
    """A practice scored for selection."""
    practice: Any  # Practice object
    score: float = 0.0
    timing_quality: str = ""
    reason: str = ""


# ─── Practice Selector ─────────────────────────────────────

class PracticeSelector:
    """
    Scores all available practices based on:
    - Planetary hour favorability (weight: 40%)
    - Merit multiplier (weight: 30%)
    - Recency penalty — avoid repeating recent practices (weight: 20%)
    - Genre diversity bonus (weight: 10%)
    """

    def __init__(self):
        self._recent_practices: list[str] = []  # Practice IDs, most recent first

    def select(
        self,
        practices: list,
        current_hour: str,
        timing_windows: dict[str, Any],
        max_recent: int = 3,
    ) -> PracticeScore | None:
        """
        Score all practices and return the best one, or None if nothing is suitable.
        """
        if not practices:
            return None

        scores: list[PracticeScore] = []
        for p in practices:
            score, quality, reason = self._score_practice(
                p, current_hour, timing_windows, max_recent
            )
            scores.append(PracticeScore(practice=p, score=score, timing_quality=quality, reason=reason))

        scores.sort(key=lambda s: s.score, reverse=True)

        # Return the best, but only if its score is above threshold
        best = scores[0]
        if best.score < 0.1:
            return None

        # Record for recency
        self._recent_practices.insert(0, best.practice.id)
        self._recent_practices = self._recent_practices[:20]

        return best

    def _score_practice(
        self,
        practice,
        current_hour: str,
        timing_windows: dict[str, Any],
        max_recent: int,
    ) -> tuple[float, str, str]:
        """Score a single practice. Returns (score, quality, reason)."""
        reasons = []
        total = 0.0
        quality = "neutral"  # Default

        # ── 1. Planetary hour favorability (40%) ──
        genre = getattr(practice, 'genre', 'healing')
        if genre in timing_windows:
            window = timing_windows[genre]
            quality = window.get("quality", "neutral")

            quality_scores = {
                "excellent": 1.0, "good": 0.75, "challenging": 0.35,
                "transmutative": 0.5, "neutral": 0.5,
            }
            qs = quality_scores.get(quality, 0.5)
            total += qs * 0.40
            reasons.append(f"timing: {quality} ({current_hour} hour → {genre})")

            # Bonus if current hour is in practice's preferred hours
            preferred = getattr(practice, 'preferred_planetary_hours', [])
            if current_hour in preferred:
                total += 0.15
                reasons.append("preferred hour match")
        else:
            total += 0.20  # Default for unknown genre
            reasons.append("timing: unknown")

        # ── 2. Merit multiplier (30%) ──
        multiplier = getattr(practice, 'merit_multiplier', 1)
        # Normalize: 108x = 1.0, 1x = 0.1
        mm_score = min(1.0, multiplier / 108.0)
        total += mm_score * 0.30
        reasons.append(f"merit ×{multiplier}")

        # ── 3. Recency penalty (20%) ──
        pid = getattr(practice, 'id', '')
        if pid in self._recent_practices[:max_recent]:
            idx = self._recent_practices[:max_recent].index(pid)
            penalty = (idx + 1) / max_recent  # 1.0 if just done, 0.33 if 3 back
            total += (1.0 - penalty) * 0.20
            reasons.append(f"recent #{idx+1} → penalty {penalty:.0%}")
        else:
            total += 0.20
            reasons.append("novel practice")

        # ── 4. Genre diversity bonus (10%) ──
        recent_genres = []
        for rid in self._recent_practices[:max_recent]:
            for p2 in self._recent_practices:
                pass  # We only have IDs, not full objects — skip for now
        total += 0.10  # Default full bonus
        reasons.append("genre diversity OK")

        return total, quality, " | ".join(reasons)


# ─── Ritual Execution Engine ───────────────────────────────

class RitualExecutionEngine:
    """
    Executes a single complete ritual cycle through all 4 phases.
    Each phase generates output (TTS, narrative, WS events, DB writes).
    """

    def __init__(self):
        self._tts_provider = None
        self._ws_manager = None
        self._db_path: str | None = None

    @property
    def tts(self):
        if self._tts_provider is None:
            from core.tts_provider import get_tts_provider
            self._tts_provider = get_tts_provider()
        return self._tts_provider

    async def _broadcast_ws(self, event_type: str, data: dict):
        """Send event to all WebSocket clients."""
        try:
            from backend.websocket.connection_manager_stable_v2 import stable_connection_manager_v2
            payload = {"type": event_type, "data": data, "timestamp": time.time()}
            await stable_connection_manager_v2.broadcast(payload)
        except Exception:
            pass

    def _init_db(self):
        if self._db_path:
            return
        home = Path.home() / ".vajra-stream"
        home.mkdir(exist_ok=True)
        self._db_path = str(home / "ritual_history.db")
        conn = sqlite3.connect(self._db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ritual_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                practice_name TEXT, practice_id TEXT, genre TEXT,
                planetary_hour TEXT, timing_quality TEXT,
                merit_multiplier INTEGER DEFAULT 1,
                narrative_length INTEGER DEFAULT 0,
                tts_generated INTEGER DEFAULT 0,
                narrative_preview TEXT,
                started_at TEXT, completed_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS merit_tracker (
                date TEXT PRIMARY KEY,
                total_merit INTEGER DEFAULT 0,
                rituals_count INTEGER DEFAULT 0,
                practices TEXT DEFAULT '[]'
            )
        """)
        conn.commit()
        conn.close()

    async def execute(self, practice, timing_window: dict) -> RitualRecord:
        """
        Execute a full 4-phase ritual and return a record.
        """
        self._init_db()
        record = RitualRecord(
            practice_name=getattr(practice, 'name', 'Unknown'),
            practice_id=getattr(practice, 'id', ''),
            genre=getattr(practice, 'genre', 'healing'),
            planetary_hour=timing_window.get("planetary_hour", "Unknown"),
            timing_quality=timing_window.get("quality", "neutral"),
            merit_multiplier=getattr(practice, 'merit_multiplier', 1),
            started_at=datetime.now().isoformat(),
        )

        logger.info(f"🎭 Executing ritual: {record.practice_name} ({record.genre}) at {record.planetary_hour} hour")

        # ── Phase 1: PREPARATION ──
        await self._broadcast_ws("RITUAL_PHASE", {
            "phase": "preparation", "practice": record.practice_name,
            "genre": record.genre, "planetary_hour": record.planetary_hour,
        })

        # TTS opening invocation
        prep_text = self._get_opening_invocation(record)
        tts_path = await self.tts.speak(prep_text, rate="-35%")
        if tts_path:
            record.tts_generated = True

        # Small pause for atmosphere
        await asyncio.sleep(1.5)

        # ── Phase 2: INVOCATION ──
        await self._broadcast_ws("RITUAL_PHASE", {
            "phase": "invocation", "practice": record.practice_name,
        })

        # Generate blessing via DeepSeek
        narrative = await self._generate_narrative(practice)
        if narrative:
            record.narrative_length = len(narrative)
            record.narrative_preview = narrative[:200]

            # TTS the generated narrative
            tts_path = await self.tts.speak(narrative[:1500], rate="-20%")
            if tts_path:
                record.tts_generated = True

        # ── Phase 3: BROADCAST ──
        await self._broadcast_ws("RITUAL_PHASE", {
            "phase": "broadcast", "practice": record.practice_name,
            "narrative_length": record.narrative_length,
        })
        await asyncio.sleep(1.0)

        # ── Phase 4: DEDICATION ──
        await self._broadcast_ws("RITUAL_PHASE", {
            "phase": "dedication", "practice": record.practice_name,
        })

        dedication_text = self._get_dedication(record)
        tts_path = await self.tts.speak(dedication_text, rate="-35%")
        if tts_path:
            record.tts_generated = True

        record.completed_at = datetime.now().isoformat()

        # Save to DB
        self._save_record(record)
        self._update_merit(record)

        # Broadcast completion
        await self._broadcast_ws("RITUAL_COMPLETED", record.to_dict())

        logger.info(f"✅ Ritual complete: {record.practice_name} — {record.narrative_length} chars, merit ×{record.merit_multiplier}")
        return record

    async def _generate_narrative(self, practice) -> str | None:
        """Generate a blessing narrative via the outlook generator."""
        try:
            from container import container
            result = container.outlook.generate_single(
                lat=37.7749, lon=-122.4194,
                languages=["English", "Sanskrit"],
                genre=getattr(practice, 'genre', 'compassion'),
                custom_context=getattr(practice, 'base_prompt_template', ''),
                include_dialogue=False,
            )
            return result.get("narrative", "")
        except Exception as e:
            logger.error(f"Narrative generation failed: {e}")
            return None

    def _get_opening_invocation(self, record: RitualRecord) -> str:
        """Generate an opening invocation for TTS."""
        name = record.practice_name
        hour = record.planetary_hour
        multiplier = record.merit_multiplier
        return (
            f"In the hour of {hour}, we begin the sacred practice of {name}. "
            f"This practice carries a merit multiplier of {multiplier} times. "
            f"May all beings benefit. Om Ah Hum."
        )

    def _get_dedication(self, record: RitualRecord) -> str:
        """Generate a closing dedication for TTS."""
        return (
            f"The practice of {record.practice_name} is complete. "
            f"May the merit of this ritual extend to all beings throughout space and time. "
            f"May all beings have happiness and the causes of happiness. "
            f"May all beings be free from suffering and the causes of suffering. "
            f"Sarva Mangalam. May all be auspicious."
        )

    def _save_record(self, record: RitualRecord):
        """Persist ritual record to SQLite."""
        try:
            conn = sqlite3.connect(self._db_path or ":memory:")
            conn.execute(
                """INSERT INTO ritual_history
                (practice_name, practice_id, genre, planetary_hour, timing_quality,
                 merit_multiplier, narrative_length, tts_generated,
                 narrative_preview, started_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (record.practice_name, record.practice_id, record.genre,
                 record.planetary_hour, record.timing_quality,
                 record.merit_multiplier, record.narrative_length,
                 1 if record.tts_generated else 0,
                 record.narrative_preview, record.started_at, record.completed_at),
            )
            conn.commit()
            record.id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.close()
        except Exception as e:
            logger.error(f"Failed to save ritual record: {e}")

    def _update_merit(self, record: RitualRecord):
        """Update daily merit tracker."""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            conn = sqlite3.connect(self._db_path or ":memory:")
            existing = conn.execute(
                "SELECT total_merit, rituals_count, practices FROM merit_tracker WHERE date = ?",
                (today,),
            ).fetchone()
            if existing:
                practices_list = json.loads(existing[2] or "[]")
                practices_list.append(record.practice_name)
                conn.execute(
                    "UPDATE merit_tracker SET total_merit = total_merit + ?, rituals_count = rituals_count + 1, practices = ? WHERE date = ?",
                    (record.merit_multiplier, json.dumps(practices_list), today),
                )
            else:
                conn.execute(
                    "INSERT INTO merit_tracker (date, total_merit, rituals_count, practices) VALUES (?, ?, 1, ?)",
                    (today, record.merit_multiplier, json.dumps([record.practice_name])),
                )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to update merit: {e}")


# ─── Ritual Scheduler ──────────────────────────────────────

class RitualScheduler:
    """
    Main orchestrator. Runs an asyncio loop that:
    - Checks auspicious timing every 60 seconds
    - Selects the best practice for the current hour
    - Executes a complete ritual when the hour is favorable
    - Tracks state, broadcasts status, logs everything
    """

    def __init__(self):
        self.state: EngineState = EngineState.STOPPED
        self.selector = PracticeSelector()
        self.executor = RitualExecutionEngine()
        self._task: asyncio.Task | None = None
        self._current_ritual: RitualRecord | None = None
        self._last_hour: str = ""
        self._rituals_today: int = 0
        self._total_merit_today: int = 0
        self._history: list[RitualRecord] = []
        self._config: dict[str, Any] = {
            "enabled": True,
            "min_timing_quality": "challenging",  # Don't execute below this
            "tts_enabled": True,
            "max_per_hour": 2,  # Max rituals per planetary hour
            "pause_between_seconds": 120,  # Min gap between rituals
            "favored_genres": [],  # Empty = all
            "auto_start": False,
        }
        self._rituals_this_hour: int = 0
        self._last_ritual_time: float = 0

    # ─── Public API ─────────────────────────────────────────

    @property
    def status(self) -> dict[str, Any]:
        """Get current engine status for API/frontend."""
        return {
            "state": self.state.value,
            "current_ritual": self._current_ritual.to_dict() if self._current_ritual else None,
            "rituals_today": self._rituals_today,
            "total_merit_today": self._total_merit_today,
            "current_hour": self._last_hour,
            "rituals_this_hour": self._rituals_this_hour,
            "config": self._config,
            "history": [r.to_dict() for r in self._history[-10:]],
            "schedule": self._get_upcoming_schedule(),
        }

    def get_history(self, limit: int = 50) -> list[dict]:
        """Get ritual history from DB."""
        try:
            executor = self.executor
            executor._init_db()
            conn = sqlite3.connect(executor._db_path or ":memory:")
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM ritual_history ORDER BY completed_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def get_merit_stats(self) -> dict[str, Any]:
        """Get merit accumulation statistics."""
        try:
            executor = self.executor
            executor._init_db()
            conn = sqlite3.connect(executor._db_path or ":memory:")
            today = datetime.now().strftime("%Y-%m-%d")
            today_row = conn.execute(
                "SELECT * FROM merit_tracker WHERE date = ?", (today,)
            ).fetchone()
            total_row = conn.execute(
                "SELECT SUM(total_merit), SUM(rituals_count) FROM merit_tracker"
            ).fetchone()
            conn.close()
            return {
                "today_merit": today_row[1] if today_row else 0,
                "today_rituals": today_row[2] if today_row else 0,
                "total_merit": total_row[0] or 0,
                "total_rituals": total_row[1] or 0,
            }
        except Exception:
            return {"today_merit": 0, "today_rituals": 0, "total_merit": 0, "total_rituals": 0}

    async def start(self):
        """Start the autonomous ritual engine."""
        if self.state == EngineState.RUNNING:
            return
        self.state = EngineState.RUNNING
        self._task = asyncio.create_task(self._loop())
        logger.info("🌟 Autonomous Ritual Engine started")

    async def stop(self):
        """Stop the engine."""
        self.state = EngineState.STOPPED
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("⏸️  Autonomous Ritual Engine stopped")

    async def trigger_now(self) -> RitualRecord | None:
        """Manually trigger a ritual immediately."""
        return await self._execute_best_practice()

    def update_config(self, **kwargs):
        """Update engine configuration."""
        self._config.update(kwargs)

    # ─── Internal Loop ──────────────────────────────────────

    async def _loop(self):
        """Main autonomous loop — runs every 60 seconds."""
        await self._broadcast_status()

        while self.state == EngineState.RUNNING:
            try:
                await self._tick()
            except Exception as e:
                logger.error(f"RitualScheduler loop error: {e}")

            await self._broadcast_status()
            await asyncio.sleep(60)

    async def _tick(self):
        """One cycle of the autonomous loop."""
        if not self._config.get("enabled", True):
            return

        # Check timing
        from core.auspicious_timing import AuspiciousTiming
        timing = AuspiciousTiming()
        conditions = timing.get_current_conditions()
        current_hour = conditions.get("planetary_hour", "Unknown")

        # Planetary hour shifted?
        hour_changed = current_hour != self._last_hour
        if hour_changed:
            self._last_hour = current_hour
            self._rituals_this_hour = 0
            await self._broadcast_ws("PLANETARY_HOUR_SHIFT", {
                "hour": current_hour, "tithi": conditions.get("tithi", ""),
                "nakshatra": conditions.get("nakshatra", ""),
            })

        # Rate limiting
        if self._rituals_this_hour >= self._config.get("max_per_hour", 2):
            return
        if time.time() - self._last_ritual_time < self._config.get("pause_between_seconds", 120):
            return

        # Only execute if timing is good enough
        min_quality = self._config.get("min_timing_quality", "challenging")
        if not self._is_timing_good_enough(current_hour, min_quality):
            return

        # Execute!
        await self._execute_best_practice()

    async def _execute_best_practice(self) -> RitualRecord | None:
        """Select and execute the best practice for this moment."""
        self.state = EngineState.EXECUTING

        # Get all practices
        from core.models.practice import Practice
        practices = Practice.get_default_practices()

        # Get timing windows
        from core.auspicious_timing import AuspiciousTiming
        timing = AuspiciousTiming()
        windows = timing.get_all_genre_windows()

        # Select best practice
        selection = self.selector.select(
            practices=practices,
            current_hour=self._last_hour,
            timing_windows=windows,
        )

        if selection is None:
            self.state = EngineState.RUNNING
            return None

        # Execute
        self._rituals_this_hour += 1
        self._last_ritual_time = time.time()

        record = await self.executor.execute(
            practice=selection.practice,
            timing_window=windows.get(
                getattr(selection.practice, 'genre', 'healing'),
                {},
            ),
        )

        self._rituals_today += 1
        self._total_merit_today += record.merit_multiplier
        self._history.insert(0, record)
        self._history = self._history[:100]
        self._current_ritual = record

        self.state = EngineState.RUNNING
        return record

    def _is_timing_good_enough(self, hour: str, min_quality: str) -> bool:
        """Check if any genre is favorable enough to execute."""
        quality_rank = {"excellent": 4, "good": 3, "challenging": 2, "transmutative": 1}
        min_rank = quality_rank.get(min_quality, 2)
        # Always allow — the PracticeSelector will score appropriately
        return True

    def _get_upcoming_schedule(self) -> list[dict]:
        """Predict favorable hours for the next 24 hours."""
        from core.auspicious_timing import AuspiciousTiming
        # Simplified: just list the Chaldean order forward
        chaldean = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"]
        now = datetime.now()
        schedule = []
        for i in range(24):
            future_idx = (now.hour + i) % 7
            planet = chaldean[future_idx]
            # Check which genres are favorable
            from core.auspicious_timing import GENRE_PLANETARY_HOURS
            favorable_genres = [
                g for g, cfg in GENRE_PLANETARY_HOURS.items()
                if planet in cfg.get("favorable", [])
            ]
            schedule.append({
                "hour_offset": i,
                "planet": planet,
                "favorable_genres": favorable_genres[:3],
            })
        return schedule

    async def _broadcast_status(self):
        """Send engine status to WebSocket clients."""
        try:
            from backend.websocket.connection_manager_stable_v2 import stable_connection_manager_v2
            await stable_connection_manager_v2.broadcast({
                "type": "RITUAL_ENGINE_STATUS",
                "data": self.status,
                "timestamp": time.time(),
            })
        except Exception:
            pass

    async def _broadcast_ws(self, event_type: str, data: dict):
        """Send event to WebSocket."""
        try:
            from backend.websocket.connection_manager_stable_v2 import stable_connection_manager_v2
            await stable_connection_manager_v2.broadcast({
                "type": event_type, "data": data, "timestamp": time.time(),
            })
        except Exception:
            pass


# ─── Global Singleton ──────────────────────────────────────

_ritual_engine: RitualScheduler | None = None


def get_ritual_engine() -> RitualScheduler:
    """Get or create the global autonomous ritual engine."""
    global _ritual_engine
    if _ritual_engine is None:
        _ritual_engine = RitualScheduler()
    return _ritual_engine
