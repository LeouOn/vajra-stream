"""
Healing Session Engine — lifecycle management for healing/blessing sessions.

Orchestrates a complete healing session from setup through execution to
logging. Integrates the protocol selector, audio generators, prayer wheel,
TTS engine, and astrological calculator into a unified session flow.

A session consists of three phases:
1. **Opening / Grounding** — intention setting, breath awareness, chakra scan.
2. **Main Practice** — frequency broadcast, mantra recitation, guided practice.
3. **Closing / Integration** — dedication of merit, session logging.

Dependencies:
    Optional (all gracefully degraded): :class:`~core.protocol_selector.ProtocolSelector`,
    :class:`~core.audio_generator.ScalarWaveGenerator`,
    :class:`~core.prayer_wheel.PrayerWheel`,
    :class:`~core.tts_engine.TTSEngine`,
    :class:`~core.astrology.AstrologicalCalculator`.

Exports:
    HealingSession — main session orchestrator.
    SessionPhase, SessionLog — supporting data classes.
"""

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# --- Optional imports — all degrade gracefully ---

try:
    from core.protocol_selector import ProtocolSelector

    HAS_PROTOCOL = True
except ImportError:
    HAS_PROTOCOL = False

try:
    from core.audio_generator import ScalarWaveGenerator

    HAS_AUDIO = True
except ImportError:
    HAS_AUDIO = False

try:
    from core.prayer_wheel import PrayerWheel

    HAS_PRAYER = True
except ImportError:
    HAS_PRAYER = False

try:
    from core.tts_engine import TTSEngine

    HAS_TTS = True
except ImportError:
    HAS_TTS = False

try:
    from core.astrology import AstrologicalCalculator

    HAS_ASTRO = True
except ImportError:
    HAS_ASTRO = False


class SessionPhase(Enum):
    """Phases of a healing session."""

    PREPARATION = "preparation"
    OPENING = "opening"
    MAIN_PRACTICE = "main_practice"
    CLOSING = "closing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class SessionLog:
    """Record of a completed healing session.

    Attributes:
        session_id: Unique session identifier.
        intention: The intention set for the session.
        condition: Target condition (or None if general).
        duration_minutes: Planned duration in minutes.
        actual_duration_seconds: Actual elapsed seconds.
        phases_completed: Which phases were completed.
        protocol: The :class:`ConditionProtocol` used (or None).
        frequencies_used: List of frequencies broadcast.
        mantras_used: List of mantras recited.
        astrology_snapshot: Optional astrology data at session start.
        notes: Free-form session notes.
        started_at: ISO-8601 start timestamp.
        ended_at: ISO-8601 end timestamp.
    """

    session_id: str
    intention: str
    condition: str | None = None
    duration_minutes: int = 30
    actual_duration_seconds: float = 0.0
    phases_completed: list[str] = field(default_factory=list)
    protocol: dict | None = None
    frequencies_used: list[float] = field(default_factory=list)
    mantras_used: list[str] = field(default_factory=list)
    astrology_snapshot: dict | None = None
    notes: str = ""
    started_at: str = ""
    ended_at: str = ""

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "intention": self.intention,
            "condition": self.condition,
            "duration_minutes": self.duration_minutes,
            "actual_duration_seconds": self.actual_duration_seconds,
            "phases_completed": self.phases_completed,
            "protocol": self.protocol,
            "frequencies_used": self.frequencies_used,
            "mantras_used": self.mantras_used,
            "astrology_snapshot": self.astrology_snapshot,
            "notes": self.notes,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
        }


class HealingSession:
    """Orchestrate a complete healing session from start to finish.

    Integrates protocol selection, audio generation, prayer wheel spinning,
    TTS narration, and astrological context into a phased session flow.

    All integrations are optional — the session degrades gracefully when
    dependencies are unavailable, operating in a log-only / silent mode.

    Usage:
        >>> session = HealingSession()
        >>> log = session.run(intention="healing", condition="anxiety", duration_minutes=15)
        >>> print(f"Completed: {log.phases_completed}")

    Attributes:
        selector: :class:`ProtocolSelector` or None.
        audio_gen: :class:`ScalarWaveGenerator` or None.
        prayer_wheel: :class:`PrayerWheel` or None.
        tts: :class:`TTSEngine` or None.
        astro: :class:`AstrologicalCalculator` or None.
        log_dir: Directory for session log files.
    """

    def __init__(self, log_dir: str = "./session_logs"):
        """Initialise the session engine with available integrations.

        Args:
            log_dir: Directory to write session log JSON files.
        """
        self.selector = ProtocolSelector() if HAS_PROTOCOL else None
        self.audio_gen = ScalarWaveGenerator() if HAS_AUDIO else None
        self.prayer_wheel = PrayerWheel(audio_generator=self.audio_gen) if HAS_PRAYER else None
        self.tts = TTSEngine() if HAS_TTS else None
        self.astro = AstrologicalCalculator() if HAS_ASTRO else None
        self.log_dir = log_dir

    def run(
        self,
        intention: str = "healing and peace",
        condition: str | None = None,
        duration_minutes: int = 30,
        with_audio: bool = True,
        with_voice: bool = False,
        notes: str = "",
    ) -> SessionLog:
        """Run a complete healing session.

        Args:
            intention: The healing intention (e.g. "May all beings be at peace").
            condition: Optional condition to target (e.g. ``"anxiety"``).
                If provided, a protocol is selected automatically.
            duration_minutes: Planned session duration in minutes.
            with_audio: Whether to generate and play audio frequencies.
            with_voice: Whether to use TTS for spoken guidance.
            notes: Free-form session notes.

        Returns:
            :class:`SessionLog` with full session details.
        """
        import uuid

        session_id = str(uuid.uuid4())[:8]
        started_at = datetime.now()

        log = SessionLog(
            session_id=session_id,
            intention=intention,
            condition=condition,
            duration_minutes=duration_minutes,
            started_at=started_at.isoformat(),
            notes=notes,
        )

        # --- Astrology snapshot ---
        if self.astro:
            try:
                log.astrology_snapshot = self.astro.get_current_energetics()
            except Exception:
                pass

        # --- Protocol selection ---
        if condition and self.selector:
            try:
                protocol = self.selector.select_protocol(condition)
                log.protocol = {
                    "condition": protocol.condition,
                    "chakras": protocol.chakras,
                    "meridians": protocol.meridians,
                    "frequencies": protocol.frequencies,
                    "mantras": protocol.mantras,
                    "colours": protocol.colours,
                    "practices": protocol.practices,
                    "timing": protocol.timing,
                }
                log.frequencies_used = protocol.frequencies
                log.mantras_used = protocol.mantras
            except Exception:
                pass

        # Fallback frequencies if no protocol or no selector
        if not log.frequencies_used:
            log.frequencies_used = [7.83, 136.1, 528.0]

        print(f"\n{'=' * 60}")
        print(f"HEALING SESSION: {session_id}")
        print(f"{'=' * 60}")
        print(f"Intention: {intention}")
        if condition:
            print(f"Condition: {condition}")
        print(f"Duration: {duration_minutes} min")
        print(f"Frequencies: {log.frequencies_used}")
        if log.mantras_used:
            print(f"Mantras: {log.mantras_used}")
        print(f"{'=' * 60}\n")

        # --- Phase 1: Opening / Grounding (20% of duration) ---
        opening_sec = int(duration_minutes * 60 * 0.2)
        self._run_opening(intention, opening_sec, with_audio, with_voice)
        log.phases_completed.append("opening")

        # --- Phase 2: Main Practice (60% of duration) ---
        main_sec = int(duration_minutes * 60 * 0.6)
        self._run_main_practice(intention, log.frequencies_used, log.mantras_used, main_sec, with_audio, with_voice)
        log.phases_completed.append("main_practice")

        # --- Phase 3: Closing / Integration (20% of duration) ---
        closing_sec = int(duration_minutes * 60 * 0.2)
        self._run_closing(closing_sec, with_audio)
        log.phases_completed.append("closing")

        # --- Finalise ---
        ended_at = datetime.now()
        log.ended_at = ended_at.isoformat()
        log.actual_duration_seconds = (ended_at - started_at).total_seconds()

        print(f"\n{'=' * 60}")
        print("SESSION COMPLETE")
        print(f"{'=' * 60}")
        print(f"Duration: {log.actual_duration_seconds:.0f}s")
        print(f"Phases: {', '.join(log.phases_completed)}")
        print("\nDedication: May all beings benefit from this healing session.")
        print(f"{'=' * 60}\n")

        # Persist log
        self._save_log(log)

        return log

    def _run_opening(
        self,
        intention: str,
        duration_sec: int,
        with_audio: bool,
        with_voice: bool,
    ):
        """Run the opening/grounding phase."""
        print(f"[Opening Phase] {duration_sec}s — grounding and intention setting...")

        # Gentle Schumann resonance for grounding
        if with_audio and self.audio_gen:
            try:
                wave = self.audio_gen.generate_schumann_resonance(duration=duration_sec)
                self.audio_gen.play(wave, blocking=False)
            except Exception:
                pass

        # Speak intention if TTS available
        if with_voice and self.tts:
            try:
                self.tts.speak(f"Setting intention: {intention}")
            except Exception:
                pass

        time.sleep(duration_sec)

        if with_audio and self.audio_gen:
            try:
                self.audio_gen.stop()
            except Exception:
                pass

    def _run_main_practice(
        self,
        intention: str,
        frequencies: list[float],
        mantras: list[str],
        duration_sec: int,
        with_audio: bool,
        with_voice: bool,
    ):
        """Run the main practice phase with frequencies and mantras."""
        print(f"[Main Practice] {duration_sec}s — broadcasting...")

        # Build frequency list for layering
        if with_audio and self.audio_gen and frequencies:
            try:
                freq_list = [(f, 0.7) for f in frequencies]
                wave = self.audio_gen.layer_frequencies(freq_list, duration=duration_sec)
                self.audio_gen.play(wave, blocking=False)
            except Exception:
                pass

        # Recite mantras if available
        if with_voice and self.tts and mantras:
            try:
                for mantra in mantras:
                    self.tts.speak(mantra)
                    time.sleep(2)
            except Exception:
                pass

        # Spin prayer wheel if available
        if self.prayer_wheel and mantras:
            try:
                for mantra in mantras[:3]:  # Cap at 3 mantras
                    prayer = self.prayer_wheel.generate_prayer(intention, use_llm=False)
                    print(f"  Prayer wheel: {prayer[:60]}...")
            except Exception:
                pass

        time.sleep(duration_sec)

        if with_audio and self.audio_gen:
            try:
                self.audio_gen.stop()
            except Exception:
                pass

    def _run_closing(self, duration_sec: int, with_audio: bool):
        """Run the closing/integration phase."""
        print(f"[Closing Phase] {duration_sec}s — integration and dedication...")

        # Soft OM frequency for integration
        if with_audio and self.audio_gen:
            try:
                wave = self.audio_gen.generate_om_frequency(duration=duration_sec)
                self.audio_gen.play(wave, blocking=False)
            except Exception:
                pass

        time.sleep(duration_sec)

        if with_audio and self.audio_gen:
            try:
                self.audio_gen.stop()
            except Exception:
                pass

    def _save_log(self, log: SessionLog):
        """Persist session log to JSON file.

        Args:
            log: The :class:`SessionLog` to persist.
        """
        try:
            os.makedirs(self.log_dir, exist_ok=True)
            filename = os.path.join(
                self.log_dir,
                f"healing_session_{log.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            )
            with open(filename, "w") as f:
                json.dump(log.to_dict(), f, indent=2)
        except Exception:
            pass  # Logging is best-effort

    def get_available_integrations(self) -> dict[str, bool]:
        """Report which integrations are currently available.

        Returns:
            Dict mapping integration names to boolean availability.
        """
        return {
            "protocol_selector": self.selector is not None,
            "audio_generator": self.audio_gen is not None,
            "prayer_wheel": self.prayer_wheel is not None,
            "tts_engine": self.tts is not None,
            "astrology": self.astro is not None,
        }


if __name__ == "__main__":
    print("Testing Healing Session Engine")
    print("=" * 60)

    session = HealingSession()
    print("\nAvailable integrations:")
    for name, available in session.get_available_integrations().items():
        status = "✓" if available else "✗"
        print(f"  {status} {name}")

    # Run a quick dry-run session (no audio for CI/headless environments)
    print("\nRunning quick session (no audio, no voice)...")
    log = session.run(
        intention="May all beings be at peace",
        condition="anxiety",
        duration_minutes=1,  # Short for testing
        with_audio=False,
        with_voice=False,
        notes="Dry-run test session.",
    )

    print(f"\nLog saved: session_id={log.session_id}")
    print(f"Phases: {log.phases_completed}")
    if log.protocol:
        print(f"Protocol chakras: {log.protocol.get('chakras')}")
        print(f"Protocol frequencies: {log.protocol.get('frequencies')}")
