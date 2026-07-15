"""
Multi-Practice Recitation Engine
=================================

General-purpose recitation engine that supports ANY practice defined as a JSON
file under ``knowledge/practices/``. Runs alongside (and intentionally does NOT
replace) the legacy ``BuddhaRecitationLoop`` in ``core/buddha_recitation_loop.py``.

Supported out of the box (Wave 1 practice definitions):
    * Green Tārā           (green_tara)
    * Cundi / Zhunti       (zhunti)
    * Medicine Buddha      (medicine_buddha)
    * Vajrasattva          (vajrasattva)
    * Amitābha             (amitabha)
    * Avalokiteśvara       (avalokiteshvara)
    * Heart Sūtra          (heart_sutra)       — bonus, ships in Wave 1

Features
--------
* Loads every ``knowledge/practices/*.json`` at first use (lazy, cached).
* Resolves the actual mantra text from ``knowledge/mantras.json`` via the
  ``mantra_id`` reference in each practice definition.
* Starts / stops any practice by id — multiple practices may run concurrently
  (each gets its own asyncio task).
* Mala counting (108 beads per round) with auto-reset on full mala.
* Throttled WebSocket broadcasts (reusing the pattern from
  ``buddha_recitation_loop.py``) using the existing
  ``stable_connection_manager_v2``.
* Per-practice and global session history (in-memory, process-scoped).

WebSocket message types emitted:
    PRACTICE_STARTED    { practice_id, practice_name, intention, target_count }
    PRACTICE_RECITED    { practice_id, count, mala_count, current_repetition, ... }
    PRACTICE_COMPLETED  { practice_id, total_count, duration_seconds }
    PRACTICE_STOPPED    { practice_id, total_count, reason }

Usage
-----
    engine = get_practice_engine()
    await engine.start("green_tara", intention="swift liberation for all beings")
    status = engine.status("green_tara")
    await engine.stop("green_tara", reason="user")
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from core.tts_provider import get_tts_provider

logger = logging.getLogger(__name__)

# ─── Module constants ──────────────────────────────────────────────────────

# A standard Tibetan mala round. Practices that specify a larger target
# (e.g. 1000 or 10000) are simply multiple mala rounds.
_MALA_SIZE = 108

# Broadcast every Nth recitation to avoid flooding WS clients (matches the
# throttling pattern used by BuddhaRecitationLoop).
_WS_RECITE_BROADCAST_EVERY = 3

# Default seconds between recitations.
_DEFAULT_INTERVAL_SECONDS = 2.0

# Project root (the parent of ``core/``).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_PRACTICES_DIR = _PROJECT_ROOT / "knowledge" / "practices"
_MANTRAS_PATH = _PROJECT_ROOT / "knowledge" / "mantras.json"


# ─── Data classes ──────────────────────────────────────────────────────────


@dataclass
class PracticeDefinition:
    """In-memory projection of a ``knowledge/practices/*.json`` file."""

    practice_id: str
    name: str
    primary_purpose: str = ""
    tradition: str = ""
    category: str = ""
    mantras: list[dict[str, Any]] = field(default_factory=list)
    visualizations: list[str] = field(default_factory=list)
    benefits: list[str] = field(default_factory=list)
    dedication: str = ""
    frequency_hz: float | None = None
    color: str | None = None
    color_name: str | None = None
    element: str = ""
    chakra: str = ""
    target_count: int = _MALA_SIZE
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> PracticeDefinition:
        """Build a ``PracticeDefinition`` from a raw JSON dict.

        Tolerates the heterogeneous schemas produced by Wave 1 — every
        practice file uses a slightly different shape, so all optional
        fields are guarded with ``.get()``.
        """
        mantras_raw = data.get("mantras") or []
        if not isinstance(mantras_raw, list):
            mantras_raw = []

        target = _MALA_SIZE
        # ``target_count`` appears in zhunti_practice.json directly; other
        # practices encode it as the recommended_count of the first mantra.
        if isinstance(data.get("target_count"), int):
            target = int(data["target_count"])
        elif mantras_raw and isinstance(mantras_raw[0], dict):
            rec = mantras_raw[0].get("recommended_count")
            if isinstance(rec, int):
                target = int(rec)

        return cls(
            practice_id=str(data.get("practice_id", "")),
            name=str(data.get("name", data.get("deity", ""))),
            primary_purpose=str(data.get("primary_purpose", data.get("description", ""))),
            tradition=str(data.get("tradition", "")),
            category=str(data.get("category", "")),
            mantras=[m for m in mantras_raw if isinstance(m, dict)],
            visualizations=list(data.get("visualizations", []) or []),
            benefits=list(data.get("benefits", []) or []),
            dedication=str(data.get("dedication", "")),
            frequency_hz=data.get("frequency_hz") if isinstance(data.get("frequency_hz"), (int, float)) else None,
            color=data.get("color") if isinstance(data.get("color"), str) else None,
            color_name=data.get("color_name") if isinstance(data.get("color_name"), str) else None,
            element=str(data.get("element", "")),
            chakra=str(data.get("chakra", "")),
            target_count=target,
            raw=data,
        )

    def to_public_dict(self) -> dict[str, Any]:
        """Public-facing projection suitable for ``GET /practices/list``."""
        return {
            "practice_id": self.practice_id,
            "name": self.name,
            "primary_purpose": self.primary_purpose,
            "tradition": self.tradition,
            "category": self.category,
            "benefits": self.benefits,
            "dedication": self.dedication,
            "frequency_hz": self.frequency_hz,
            "color": self.color,
            "color_name": self.color_name,
            "element": self.element,
            "chakra": self.chakra,
            "target_count": self.target_count,
            "visualizations": self.visualizations,
            "mantra_count": len(self.mantras),
        }


@dataclass
class PracticeSession:
    """Mutable state for a single running practice session."""

    practice_id: str
    practice_name: str
    intention: str = ""
    target_count: int = _MALA_SIZE
    total_recited: int = 0
    mala_count: int = 0  # 0..108, resets on full mala
    mala_rounds: int = 0  # number of completed 108-bead rounds
    current_repetition: str = ""
    started_at: str = ""
    started_ts: float = 0.0
    last_recited_at: str = ""
    running: bool = False

    def to_status_dict(self) -> dict[str, Any]:
        elapsed = max(0.0, time.time() - self.started_ts) if self.started_ts else 0.0
        return {
            "practice_id": self.practice_id,
            "practice_name": self.practice_name,
            "intention": self.intention,
            "target_count": self.target_count,
            "total_recited": self.total_recited,
            "mala_count": self.mala_count,
            "mala_rounds": self.mala_rounds,
            "current_repetition": self.current_repetition,
            "running": self.running,
            "started_at": self.started_at,
            "last_recited_at": self.last_recited_at,
            "elapsed_seconds": round(elapsed, 1),
            "progress_pct": round((self.total_recited / self.target_count) * 100, 1) if self.target_count else 0.0,
        }


@dataclass
class PracticeHistoryEntry:
    """One finished practice session in the history log."""

    practice_id: str
    practice_name: str
    intention: str
    total_recited: int
    mala_rounds: int
    started_at: str
    ended_at: str
    duration_seconds: float
    reason: str  # "completed" | "stopped" | "error"

    def to_dict(self) -> dict[str, Any]:
        return {
            "practice_id": self.practice_id,
            "practice_name": self.practice_name,
            "intention": self.intention,
            "total_recited": self.total_recited,
            "mala_rounds": self.mala_rounds,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_seconds": self.duration_seconds,
            "reason": self.reason,
        }


# ─── Engine ────────────────────────────────────────────────────────────────


class PracticeEngine:
    """Generic, multi-practice recitation engine.

    A single process-wide instance is exposed via ``get_practice_engine()``.
    Definitions are loaded lazily on first access and cached for the life of
    the process.
    """

    def __init__(self) -> None:
        self._definitions: dict[str, PracticeDefinition] = {}
        self._mantras: dict[str, dict[str, Any]] = {}
        self._sessions: dict[str, PracticeSession] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._history: list[PracticeHistoryEntry] = []
        self._on_recite: list[Callable[[PracticeSession], None]] = []
        self._on_complete: list[Callable[[PracticeHistoryEntry], None]] = []
        self._definitions_loaded = False

    # ─── Loading ─────────────────────────────────────────────────────────

    def _ensure_loaded(self) -> None:
        """Load practice definitions and mantras once (idempotent)."""
        if self._definitions_loaded:
            return
        self._definitions_loaded = True
        self._load_mantras()
        self._load_practice_definitions()

    def _load_mantras(self) -> None:
        """Flatten ``knowledge/mantras.json`` into a lookup of mantra_id → entry.

        The file is grouped by category (``buddhist``, ``vajrayana_foundational``,
        etc.) — for our purposes we want a single flat namespace keyed by the
        inner mantra id.
        """
        if not _MANTRAS_PATH.exists():
            logger.warning("mantras.json missing at %s", _MANTRAS_PATH)
            return
        try:
            with open(_MANTRAS_PATH, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error("Failed to load mantras.json: %s", e)
            return

        flat: dict[str, dict[str, Any]] = {}
        if isinstance(data, dict):
            for _category, entries in data.items():
                if not isinstance(entries, dict):
                    continue
                for mantra_id, entry in entries.items():
                    if isinstance(entry, dict):
                        flat[mantra_id] = entry
        self._mantras = flat

    def _load_practice_definitions(self) -> None:
        """Load every ``knowledge/practices/*.json`` file."""
        if not _PRACTICES_DIR.exists():
            logger.warning("practices directory missing at %s", _PRACTICES_DIR)
            return

        for path in sorted(_PRACTICES_DIR.glob("*.json")):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                logger.error("Failed to load practice %s: %s", path, e)
                continue
            if not isinstance(data, dict):
                continue
            defn = PracticeDefinition.from_json(data)
            if not defn.practice_id:
                logger.warning("Skipping practice without id: %s", path)
                continue
            self._definitions[defn.practice_id] = defn
            logger.info("Loaded practice: %s (%s)", defn.practice_id, defn.name)

    # ─── Public introspection ───────────────────────────────────────────

    def list_practices(self) -> list[dict[str, Any]]:
        """Return all loaded practice definitions (public projection)."""
        self._ensure_loaded()
        return [d.to_public_dict() for d in self._definitions.values()]

    def get_definition(self, practice_id: str) -> PracticeDefinition | None:
        self._ensure_loaded()
        return self._definitions.get(practice_id)

    def resolve_mantra_text(self, defn: PracticeDefinition) -> str:
        """Resolve the primary recitation text for a practice.

        Strategy:
            1. If the practice lists mantras, take the first one's ``mantra_id``
               and look it up in ``mantras.json``.
            2. Fallback to the zhunti-style fields (``mantra_sanskrit`` /
               ``mantra_short``) present directly on the practice JSON.
            3. Final fallback: the practice ``name``.
        """
        if defn.mantras:
            first = defn.mantras[0]
            mantra_id = str(first.get("mantra_id", ""))
            entry = self._mantras.get(mantra_id) if mantra_id else None
            if entry:
                # Prefer spoken-language fields in priority order.
                for key in ("sanskrit", "name", "chinese", "pinyin"):
                    val = entry.get(key)
                    if isinstance(val, str) and val.strip():
                        return val
        # Zhunti-style inline fields.
        for key in ("mantra_sanskrit", "mantra_complete_sanskrit", "mantra_short"):
            val = defn.raw.get(key)
            if isinstance(val, str) and val.strip():
                return val
        return defn.name

    # ─── Callbacks ──────────────────────────────────────────────────────

    def on_recite(self, cb: Callable[[PracticeSession], None]) -> None:
        self._on_recite.append(cb)

    def on_complete(self, cb: Callable[[PracticeHistoryEntry], None]) -> None:
        self._on_complete.append(cb)

    @staticmethod
    def _fire_callbacks(
        callbacks: list[Callable[..., Any]],
        *args: Any,
    ) -> None:
        for cb in callbacks:
            try:
                cb(*args)
            except Exception as e:
                logger.debug("Practice callback %r raised: %s", cb, e)

    # ─── Lifecycle ──────────────────────────────────────────────────────

    async def start(
        self,
        practice_id: str,
        intention: str = "",
        interval_seconds: float = _DEFAULT_INTERVAL_SECONDS,
        target_count: int | None = None,
        enable_tts: bool = True,
    ) -> PracticeSession:
        """Start (or re-join) a practice session.

        If a session for ``practice_id`` is already running, returns it
        unchanged — calling ``start`` twice is a no-op rather than an error.

        Args:
            enable_tts: When True (default), speak each recitation via the
                unified TTS provider using the ``buddhist_chant`` role. If
                the interval is shorter than 2s, TTS fires only every Nth
                recitation to avoid blocking the loop (TTS takes ~1-2s per
                utterance). Failures are logged but never break the loop.
        """
        self._ensure_loaded()
        defn = self._definitions.get(practice_id)
        if defn is None:
            raise KeyError(f"Unknown practice: {practice_id!r}")

        existing = self._sessions.get(practice_id)
        if existing is not None and existing.running:
            return existing

        target = int(target_count) if target_count else defn.target_count
        session = PracticeSession(
            practice_id=practice_id,
            practice_name=defn.name,
            intention=intention or defn.primary_purpose,
            target_count=max(1, target),
            started_at=datetime.now().isoformat(),
            started_ts=time.time(),
            running=True,
        )
        self._sessions[practice_id] = session

        self._broadcast_ws(
            "PRACTICE_STARTED",
            {
                "practice_id": practice_id,
                "practice_name": defn.name,
                "intention": session.intention,
                "target_count": session.target_count,
            },
        )

        mantra_text = self.resolve_mantra_text(defn)
        self._tasks[practice_id] = asyncio.create_task(
            self._run_loop(
                practice_id,
                mantra_text,
                interval_seconds,
                enable_tts=enable_tts,
            )
        )
        return session

    async def stop(self, practice_id: str, reason: str = "user") -> PracticeSession | None:
        """Stop a running practice. Returns the (now-stopped) session or None."""
        session = self._sessions.get(practice_id)
        task = self._tasks.pop(practice_id, None)
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.debug("Practice task %s ended with error: %s", practice_id, e)

        if session is None:
            return None

        was_running = session.running
        session.running = False
        if was_running:
            self._record_history(session, reason=reason)
            self._broadcast_ws(
                "PRACTICE_STOPPED",
                {
                    "practice_id": practice_id,
                    "practice_name": session.practice_name,
                    "total_count": session.total_recited,
                    "mala_rounds": session.mala_rounds,
                    "reason": reason,
                },
            )
        return session

    async def stop_all(self, reason: str = "shutdown") -> None:
        """Stop every running practice (used on application shutdown)."""
        ids = [pid for pid, s in self._sessions.items() if s.running]
        for pid in ids:
            await self.stop(pid, reason=reason)

    def status(self, practice_id: str) -> dict[str, Any] | None:
        """Return current status dict for ``practice_id`` or None."""
        session = self._sessions.get(practice_id)
        return session.to_status_dict() if session else None

    def all_status(self) -> list[dict[str, Any]]:
        """Return status dicts for all known sessions (running or finished)."""
        return [s.to_status_dict() for s in self._sessions.values()]

    def history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return recent history entries (newest first)."""
        if limit <= 0:
            return []
        return [h.to_dict() for h in self._history[-limit:][::-1]]

    # ─── Main loop ──────────────────────────────────────────────────────

    async def _run_loop(
        self,
        practice_id: str,
        mantra_text: str,
        interval_seconds: float,
        enable_tts: bool = True,
    ) -> None:
        """Internal: per-practice asyncio recitation loop."""
        session = self._sessions.get(practice_id)
        if session is None:
            return

        # Resolve TTS provider lazily; unavailable TTS must not break the loop.
        tts_provider = None
        tts_speak_every_n = 1
        if enable_tts and mantra_text:
            try:
                tts_provider = get_tts_provider()
            except Exception as e:
                logger.warning("TTS provider unavailable for practice %s: %s", practice_id, e)
                tts_provider = None
            # Sub-2s intervals would be blocked by TTS (~1-2s per utterance);
            # speak only every Nth recitation to keep the loop responsive.
            if tts_provider is not None and interval_seconds < 2.0:
                tts_speak_every_n = max(1, int(2.0 / max(0.05, interval_seconds)))

        try:
            while session.running:
                if session.total_recited >= session.target_count:
                    break

                session.total_recited += 1
                session.mala_count += 1
                session.current_repetition = mantra_text
                session.last_recited_at = datetime.now().isoformat()

                # Mala round completion.
                if session.mala_count >= _MALA_SIZE:
                    session.mala_count = 0
                    session.mala_rounds += 1

                self._fire_callbacks(self._on_recite, session)

                # Throttled broadcast.
                if session.total_recited % _WS_RECITE_BROADCAST_EVERY == 0:
                    self._broadcast_ws(
                        "PRACTICE_RECITED",
                        session.to_status_dict(),
                    )

                # Speak the mantra via TTS; best-effort — failures must not break the loop.
                if tts_provider is not None and mantra_text and session.total_recited % tts_speak_every_n == 0:
                    try:
                        await tts_provider.speak(
                            text=mantra_text,
                            role="buddhist_chant",
                        )
                    except Exception as e:
                        logger.warning(
                            "TTS speak failed for practice %s: %s",
                            practice_id,
                            e,
                        )

                # Sleep cooperatively; if the task is cancelled we exit.
                await asyncio.sleep(max(0.05, interval_seconds))

            # Loop finished naturally → target reached.
            if session.total_recited >= session.target_count:
                session.running = False
                entry = self._record_history(session, reason="completed")
                self._broadcast_ws(
                    "PRACTICE_COMPLETED",
                    {
                        "practice_id": practice_id,
                        "practice_name": session.practice_name,
                        "total_count": session.total_recited,
                        "mala_rounds": session.mala_rounds,
                        "duration_seconds": entry.duration_seconds,
                        "intention": session.intention,
                    },
                )
                self._fire_callbacks(self._on_complete, entry)
        except asyncio.CancelledError:
            # Cooperative cancel — status already recorded by stop().
            raise
        except Exception as e:
            logger.exception("Practice %s crashed: %s", practice_id, e)
            session.running = False
            self._record_history(session, reason="error")
            self._broadcast_ws(
                "PRACTICE_STOPPED",
                {
                    "practice_id": practice_id,
                    "practice_name": session.practice_name,
                    "total_count": session.total_recited,
                    "mala_rounds": session.mala_rounds,
                    "reason": "error",
                },
            )

    # ─── History + WS ───────────────────────────────────────────────────

    def _record_history(
        self,
        session: PracticeSession,
        reason: str,
    ) -> PracticeHistoryEntry:
        ended_at = datetime.now().isoformat()
        duration = max(0.0, time.time() - session.started_ts) if session.started_ts else 0.0
        entry = PracticeHistoryEntry(
            practice_id=session.practice_id,
            practice_name=session.practice_name,
            intention=session.intention,
            total_recited=session.total_recited,
            mala_rounds=session.mala_rounds,
            started_at=session.started_at,
            ended_at=ended_at,
            duration_seconds=round(duration, 2),
            reason=reason,
        )
        self._history.append(entry)
        # Cap in-memory history to avoid unbounded growth.
        if len(self._history) > 500:
            self._history = self._history[-500:]
        return entry

    def _broadcast_ws(self, event_type: str, data: dict[str, Any]) -> None:
        """Broadcast a practice event to all WebSocket clients.

        Best-effort: silently no-ops if no event loop is running, or if the
        connection manager cannot be imported (e.g. during tests). Never raises.
        Mirrors the broadcast pattern in ``buddha_recitation_loop.py``.
        """
        try:
            from backend.websocket.connection_manager import (
                stable_connection_manager_v2,
            )
        except Exception as e:
            logger.debug("WS connection manager unavailable: %s", e)
            return

        payload = {
            "type": event_type,
            "data": data,
            "timestamp": time.time(),
        }
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            return
        if not loop.is_running():
            return
        try:
            asyncio.ensure_future(stable_connection_manager_v2.broadcast(payload))
        except Exception as e:
            logger.debug("WS broadcast failed for %s: %s", event_type, e)


# ─── Singleton accessor ────────────────────────────────────────────────────

_practice_engine: PracticeEngine | None = None


def get_practice_engine() -> PracticeEngine:
    """Return the process-wide singleton PracticeEngine."""
    global _practice_engine
    if _practice_engine is None:
        _practice_engine = PracticeEngine()
    return _practice_engine
