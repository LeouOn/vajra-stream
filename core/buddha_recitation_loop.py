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
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from core.eighty_eight_buddhas import get_eighty_eight_buddhas

logger = logging.getLogger(__name__)

# ─── Module constants ──────────────────────────────────────────────────────
# Sentinel "default" voice: callers that don't pass an explicit `voice` arrive
# with this value. The provider treats it as "no override — apply role mapping"
# while the legacy Edge path treats it as a real voice name.
_DEFAULT_EDGE_VOICE = "zh-CN-YunxiNeural"

# Fixed liturgy texts (not user-configurable).
_DEDICATION_TEXT = "愿以此功德 普及于一切 我等与众生 皆共成佛道"
_FULL_MALA_DEDICATION_SUFFIX = "。回向法界一切众生，同证无上正等正觉。"
_FINAL_DEDICATION_TEXT = (
    "功德圆满。愿以此念诵88佛之功德，回向法界一切众生，离苦得乐，早证菩提。"
)

# TTS rate presets (Edge percent-string format; ignored by Qwen).
_RATE_NAME = "-30%"
_RATE_DEDICATION = "-40%"
_RATE_FINAL = "-35%"

# Broadcast every Nth name to avoid flooding WS clients.
_WS_NAME_BROADCAST_EVERY = 3

# Full mala cycle length (beads), triggers full dedication + counter reset.
_FULL_MALA_SIZE = 108


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

    def __init__(self, tts_reciter: Any = None) -> None:
        """
        Args:
            tts_reciter: Optional pre-built TTS engine. Pass ``False`` to
                explicitly disable TTS (e.g. for tests). If ``None``, start()
                will try the unified TTSProvider (Qwen3-TTS or Edge) first,
                then fall back to a legacy BuddhaTTSReciter if it is down.
        """
        self._buddha_service = get_eighty_eight_buddhas()
        # ``_tts`` has three states:
        #   None  -> not initialized yet; start() will try TTSProvider first
        #   False -> TTS explicitly disabled or unavailable (sentinel)
        #   <obj> -> a legacy BuddhaTTSReciter usable as fallback
        self._tts: Any = tts_reciter
        self.state = RecitationState()
        self._on_name: list[Callable[..., Any]] = []
        self._on_dedication: list[Callable[..., Any]] = []
        self._on_cycle_complete: list[Callable[..., Any]] = []
        self._buddhas: list[dict[str, Any]] = []
        self._voice_override: str | None = None
        self._provider: Any = None
        # Stored so stop() can cancel it; prevents fire-and-forget task leaks.
        self._task: asyncio.Task[None] | None = None

    # ─── Setup / loading ─────────────────────────────────────────────────

    @staticmethod
    def _build_buddha_entry(buddha: dict[str, Any], category: str) -> dict[str, Any]:
        """Project a raw service Buddha dict down to the fields the loop needs."""
        return {
            "name_chinese": buddha["name_chinese"],
            "name_pinyin": buddha["name_pinyin"],
            "name_sanskrit": buddha["name_sanskrit"],
            "category": category,
        }

    def _load_buddhas(self) -> None:
        """Load the full 88-Buddha list (53 past + 35 confession) for recitation."""
        seq = self._buddha_service.get_confession_sequence()
        past = [
            self._build_buddha_entry(b, "past")
            for b in seq.get("fifty_three_past_buddhas", [])
        ]
        confession = [
            self._build_buddha_entry(b, "confession")
            for b in seq.get("thirty_five_confession_buddhas", [])
        ]
        self._buddhas = past + confession

    def on_name_recited(self, callback: Callable[..., Any]) -> None:
        """Register callback invoked after each Buddha name is recited."""
        self._on_name.append(callback)

    def on_dedication(self, callback: Callable[..., Any]) -> None:
        """Register callback invoked at dedication intervals."""
        self._on_dedication.append(callback)

    def on_cycle_complete(self, callback: Callable[..., Any]) -> None:
        """Register callback invoked when a full 88-name cycle completes."""
        self._on_cycle_complete.append(callback)

    # ─── Lifecycle ────────────────────────────────────────────────────────

    async def start(
        self,
        intention: str = "愿一切众生离苦得乐",
        interval_seconds: float = 3.0,
        dedication_interval: int = 21,
        mala_cycles: int | None = None,
        voice: str = _DEFAULT_EDGE_VOICE,
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
            # Nothing to recite — leave the state stopped and bail out.
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

        # Broadcast WS event
        self._broadcast_ws(
            "BUDDHA_RECITATION_STARTED",
            {
                "intention": intention,
                "total_buddhas": len(self._buddhas),
            },
        )

        # Initialize TTS unless a reciter was explicitly provided (incl. False).
        if self._tts is None:
            self._init_provider_tts(voice=voice, role=role, project_id=project_id)

        # Run the loop as a background task so start() returns immediately.
        self._task = asyncio.create_task(
            self._run_loop(interval_seconds, dedication_interval, mala_cycles)
        )
        return self.state

    def _init_provider_tts(
        self,
        voice: str,
        role: str,
        project_id: str | None,
    ) -> None:
        """Initialize the unified TTSProvider and resolve the active speaker.

        On failure, falls back to a legacy BuddhaTTSReciter. If that also
        fails, sets ``self._tts = False`` so ``_speak_text`` becomes a no-op.
        """
        try:
            from core.tts_provider import get_tts_provider

            provider = get_tts_provider()
            # Apply project_id on the provider for per-project overrides.
            if project_id is not None:
                provider.config.project_id = project_id
            self._provider = provider
            self.state.backend = provider.active_backend.value

            # Resolve the actual speaker the loop will report.
            edge_voice, qwen_speaker = provider._resolve_voice(
                self._effective_voice(voice), role
            )
            if provider.active_backend.value == "qwen":
                self.state.speaker = qwen_speaker or "Uncle_Fu"
            else:
                self.state.speaker = edge_voice or _DEFAULT_EDGE_VOICE
        except Exception as e:
            logger.warning(
                "TTSProvider unavailable, falling back to legacy BuddhaTTSReciter: %s",
                e,
            )
            self._provider = None
            try:
                from core.buddha_tts import BuddhaTTSReciter

                self._tts = BuddhaTTSReciter(voice=voice)
            except Exception:
                # Sentinel: TTS unavailable — _speak_text will be a no-op.
                self._tts = False

    async def stop(self) -> RecitationState:
        """Stop the recitation loop and cancel the background task."""
        self.state.running = False
        task = self._task
        self._task = None
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
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

    # ─── TTS helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _effective_voice(voice: str | None) -> str | None:
        """Map the sentinel default voice to ``None`` so the provider applies
        role-based auto-mapping instead of literally using 'zh-CN-YunxiNeural'.
        """
        if voice is None or voice == _DEFAULT_EDGE_VOICE:
            return None
        return voice

    async def _speak_text(self, text: str, rate: str | None = None) -> bool:
        """Speak a single text snippet via the active TTS backend.

        Returns True if speech was produced, False if TTS is unavailable or
        the backend failed. Never raises — recitation must continue even when
        TTS is broken.
        """
        # Preferred: unified TTSProvider (Qwen3-TTS or Edge).
        if self._provider is not None:
            try:
                path = await self._provider.speak(
                    text=text,
                    voice=self._effective_voice(self._voice_override),
                    rate=rate,
                    role=self.state.role,
                )
                if path:
                    return True
            except Exception as e:
                logger.debug("TTSProvider speak failed, trying legacy reciter: %s", e)

        # Fallback: legacy BuddhaTTSReciter (Edge only).
        reciter = self._tts
        if reciter and reciter is not False and getattr(reciter, "available", False):
            try:
                await reciter.speak(text, rate=rate or _RATE_NAME)
                return True
            except Exception as e:
                logger.debug("Legacy TTS reciter failed: %s", e)
        return False

    # ─── WebSocket broadcast ──────────────────────────────────────────────

    def _broadcast_ws(self, event_type: str, data: dict[str, Any]) -> None:
        """Broadcast a recitation event to all WebSocket clients.

        Best-effort: silently no-ops if no event loop is running, or if the
        connection manager cannot be imported (e.g. during tests). Never raises.
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
            # No event loop in this thread — nothing to broadcast to.
            return
        if not loop.is_running():
            return
        try:
            asyncio.ensure_future(stable_connection_manager_v2.broadcast(payload))
        except Exception as e:
            logger.debug("WS broadcast failed for %s: %s", event_type, e)

    # ─── Callback dispatch ────────────────────────────────────────────────

    @staticmethod
    def _fire_callbacks(
        callbacks: list[Callable[..., Any]],
        *args: Any,
    ) -> None:
        """Invoke each callback with ``*args``, swallowing per-callback errors
        so one failing subscriber cannot break the recitation loop."""
        for cb in callbacks:
            try:
                cb(*args)
            except Exception as e:
                logger.debug("Recitation callback %r raised: %s", cb, e)

    # ─── Main loop ────────────────────────────────────────────────────────

    @staticmethod
    def _format_buddha_name(name: str) -> str:
        """Prefix a Buddha name with 南無 unless it already has it."""
        if name.startswith("南無"):
            return name
        return f"南無{name}"

    async def _run_loop(
        self,
        interval_seconds: float,
        dedication_interval: int,
        max_cycles: int | None,
    ) -> None:
        """Internal: main recitation loop.

        Iterates over all 88 names repeatedly, inserting a sub-dedication every
        ``dedication_interval`` names and a full-mala dedication every 108.
        Exits when ``state.running`` becomes False or ``max_cycles`` is reached.
        """
        while self.state.running:
            for i, buddha in enumerate(self._buddhas):
                if not self.state.running:
                    break

                self.state.current_index = i
                self.state.current_buddha = buddha
                self.state.total_recited += 1
                self.state.mala_count += 1
                self.state.last_recited_at = datetime.now().isoformat()

                # Recite the name via TTS.
                name = buddha.get("name_chinese", "")
                if name:
                    await self._speak_text(
                        self._format_buddha_name(name), rate=_RATE_NAME
                    )

                self._fire_callbacks(self._on_name, buddha, self.state)

                # Broadcast to WebSocket (throttled to avoid flooding clients).
                if self.state.total_recited % _WS_NAME_BROADCAST_EVERY == 0:
                    self._broadcast_ws("BUDDHA_NAME_RECITED", self.get_status())

                # Sub-dedication interval.
                if self.state.mala_count > 0 and self.state.mala_count % dedication_interval == 0:
                    self.state.dedications += 1
                    await self._speak_text(_DEDICATION_TEXT, rate=_RATE_DEDICATION)
                    self._fire_callbacks(self._on_dedication, self.state.mala_count, self.state)

                # Full mala (108) dedication — resets the mala counter.
                if self.state.mala_count > 0 and self.state.mala_count % _FULL_MALA_SIZE == 0:
                    full_ded = _DEDICATION_TEXT + _FULL_MALA_DEDICATION_SUFFIX
                    await self._speak_text(full_ded, rate=_RATE_DEDICATION)
                    self.state.mala_count = 0
                    self._fire_callbacks(self._on_cycle_complete, self.state)

                # Wait between names.
                await asyncio.sleep(interval_seconds)

            # One full pass through all 88 names completed.
            self.state.current_cycle += 1
            self._fire_callbacks(self._on_cycle_complete, self.state)

            # Stop if max cycles reached.
            if max_cycles and self.state.current_cycle >= max_cycles:
                break

        self.state.running = False

        # Final dedication once the loop exits for any reason.
        await self._speak_text(_FINAL_DEDICATION_TEXT, rate=_RATE_FINAL)


# Global instance
_recitation_loop: BuddhaRecitationLoop | None = None


def get_recitation_loop() -> BuddhaRecitationLoop:
    """Return the process-wide singleton BuddhaRecitationLoop."""
    global _recitation_loop
    if _recitation_loop is None:
        _recitation_loop = BuddhaRecitationLoop()
    return _recitation_loop
