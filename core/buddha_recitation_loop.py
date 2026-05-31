"""
88 Buddhas Continuous Recitation Loop
Perpetual mala-cycle recitation of the 88 Buddha names with TTS,
dedication intervals, and progress tracking.

Usage:
    loop = BuddhaRecitationLoop()
    await loop.start(intention="world peace", mala_cycles=3)
    # Runs in background, reciting all 88 names per cycle
    # Dedication every 21 names, full dedication every 108
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from core.eighty_eight_buddhas import get_eighty_eight_buddhas


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

    def __init__(self, tts_reciter=None):
        self._svc = get_eighty_eight_buddhas()
        self._tts = tts_reciter
        self.state = RecitationState()
        self._on_name: list[callable] = []
        self._on_dedication: list[callable] = []
        self._on_cycle_complete: list[callable] = []
        self._buddhas: list[dict] = []

    def _load_buddhas(self):
        """Load the full 88-Buddha list for recitation."""
        seq = self._svc.get_confession_sequence()
        past = [{"name_chinese": b["name_chinese"], "name_pinyin": b["name_pinyin"], "name_sanskrit": b["name_sanskrit"], "category": "past"} for b in seq.get("fifty_three_past_buddhas", [])]
        conf = [{"name_chinese": b["name_chinese"], "name_pinyin": b["name_pinyin"], "name_sanskrit": b["name_sanskrit"], "category": "confession"} for b in seq.get("thirty_five_confession_buddhas", [])]
        self._buddhas = past + conf

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
    ) -> RecitationState:
        """
        Start the continuous recitation loop.

        Args:
            intention: Dedication intention
            interval_seconds: Seconds between each Buddha name
            dedication_interval: Recite dedication every N names (default 21)
            mala_cycles: Stop after N full 88-name cycles (None = infinite)
            voice: Edge TTS voice for recitation
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
        )

        # Broadcast WS event
        self._broadcast_ws("BUDDHA_RECITATION_STARTED", {
            "intention": intention, "total_buddhas": len(self._buddhas),
        })

        # Initialize TTS if not explicitly disabled
        if self._tts is None:
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
            payload = {"type": event_type, "data": data, "timestamp": __import__('time').time()}
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
        }

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
                if name and self._tts and self._tts is not False and getattr(self._tts, 'available', False):
                    try:
                        text = f"南無{name}" if not name.startswith("南無") else name
                        await self._tts.speak(text, rate="-30%")
                    except Exception:
                        pass

                # Fire name-recited callbacks
                for cb in self._on_name:
                    try:
                        cb(buddha, self.state)
                    except Exception:
                        pass

                # Broadcast to WebSocket (throttled: every 3rd name to avoid flooding)
                if self.state.total_recited % 3 == 0:
                    self._broadcast_ws("BUDDHA_NAME_RECITED", self.get_status())

                # Dedication interval
                if self.state.mala_count > 0 and self.state.mala_count % dedication_interval == 0:
                    self.state.dedications += 1
                    dedication_text = "愿以此功德 普及于一切 我等与众生 皆共成佛道"
                    if self._tts and self._tts is not False and getattr(self._tts, 'available', False):
                        try:
                            await self._tts.speak(dedication_text, rate="-40%")
                        except Exception:
                            pass
                    for cb in self._on_dedication:
                        try:
                            cb(self.state.mala_count, self.state)
                        except Exception:
                            pass

                # Full mala (108) dedication
                if self.state.mala_count > 0 and self.state.mala_count % 108 == 0:
                    if self._tts and self._tts.available:
                        try:
                            full_ded = f"{dedication_text}。回向法界一切众生，同证无上正等正觉。"
                            await self._tts.speak(full_ded, rate="-40%")
                        except Exception:
                            pass
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
        if self._tts and self._tts.available:
            try:
                final = "功德圆满。愿以此念诵88佛之功德，回向法界一切众生，离苦得乐，早证菩提。"
                await self._tts.speak(final, rate="-35%")
            except Exception:
                pass


# Global instance
_recitation_loop: BuddhaRecitationLoop | None = None


def get_recitation_loop() -> BuddhaRecitationLoop:
    global _recitation_loop
    if _recitation_loop is None:
        _recitation_loop = BuddhaRecitationLoop()
    return _recitation_loop
