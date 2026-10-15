#!/usr/bin/env python3
"""
Integrated Scalar-Radionics Broadcaster

Combines advanced scalar wave generation with radionics broadcasting
for maximum healing power. Integrates with all Vajra Stream systems.

Every call to ``broadcast_to_targets`` is recorded in the operations ledger
(``core/operations.py``, kind ``broadcast``) with its real start, measured
duration and outcome. That record replaces the retired MOPS throughput
figure: a broadcast is one operation that takes real time.

Features:
- Scalar wave generation (hybrid RNG / chaotic streams)
- Multi-target radionics broadcasting
- Energetic anatomy integration
- Real-time visualization
- Intention encoding
- Harmonic frequency selection
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

try:
    from core.advanced_scalar_waves import HybridScalarWaveGenerator

    HAS_SCALAR = True
except ImportError:
    HAS_SCALAR = False

try:
    from core.compassionate_blessings import BlessingDatabase

    HAS_BLESSINGS = True
except ImportError:
    HAS_BLESSINGS = False

try:
    from core.energetic_anatomy import EnergeticAnatomyDatabase

    HAS_ANATOMY = True
except ImportError:
    HAS_ANATOMY = False


class IntentionType(Enum):
    """Types of healing intentions"""

    HEALING = "healing"
    LIBERATION = "liberation"
    EMPOWERMENT = "empowerment"
    PROTECTION = "protection"
    RECONCILIATION = "reconciliation"
    PEACE = "peace"
    LOVE = "love"
    WISDOM = "wisdom"


@dataclass
class BroadcastConfiguration:
    """Configuration for scalar-radionics broadcast"""

    intention: IntentionType
    target_count: int
    duration_seconds: float
    scalar_intensity: float  # 0.0-1.0
    frequency_hz: float | None
    mantra: str
    use_meridians: bool = False
    use_chakras: bool = False
    breathing_pattern: bool = False


class IntegratedScalarRadionicsBroadcaster:
    """Combined scalar-wave + radionics broadcasting engine.

    Integrates :class:`~core.advanced_scalar_waves.HybridScalarWaveGenerator`
    for scalar wave generation with :class:`~core.compassionate_blessings.BlessingDatabase`
    for targeted blessing allocation, and optional :class:`~core.energetic_anatomy.EnergeticAnatomyDatabase`
    for meridian/chakra-aware broadcasts.

    All subsystems are optional — the broadcaster degrades gracefully when
    dependencies are missing (pure-Python fallback).

    Attributes:
        scalar_gen: :class:`HybridScalarWaveGenerator` or None.
        blessing_db: :class:`BlessingDatabase` or None.
        anatomy_db: :class:`EnergeticAnatomyDatabase` or None.
    """

    def __init__(self, crystal_service=None):
        # Initialize subsystems
        self.scalar_gen = HybridScalarWaveGenerator() if HAS_SCALAR else None
        self.blessing_db = BlessingDatabase() if HAS_BLESSINGS else None
        self.anatomy_db = EnergeticAnatomyDatabase() if HAS_ANATOMY else None
        # Optional crystal service for prayer bowl audio output.
        # When injected, broadcast_to_targets() will invoke the crystal
        # broadcaster in parallel with scalar wave generation.
        self.crystal_service = crystal_service

        # Solfeggio and planetary frequencies
        self.frequencies = {
            "liberation": 396,  # Liberating guilt and fear
            "change": 417,  # Undoing situations
            "healing_dna": 528,  # DNA repair, love
            "connection": 639,  # Connecting relationships
            "awakening": 741,  # Awakening intuition
            "spiritual": 852,  # Returning to spiritual order
            "unity": 963,  # Divine consciousness
            "earth": 136.10,  # OM, Earth day
            "sun": 126.22,  # Sun
            "moon": 210.42,  # Moon
            "mercury": 141.27,  # Mercury
            "venus": 221.23,  # Venus
            "mars": 144.72,  # Mars
            "jupiter": 183.58,  # Jupiter
            "saturn": 147.85,  # Saturn
        }

        # Statistics
        self.total_broadcasts = 0
        self.total_values_generated = 0
        self.total_targets_blessed = 0

    def encode_intention(self, intention: IntentionType) -> int:
        """Encode intention as numeric seed (gematria-inspired)"""
        intention_values = {
            IntentionType.HEALING: 432,  # 432 Hz harmony
            IntentionType.LIBERATION: 396,  # Liberation frequency
            IntentionType.EMPOWERMENT: 528,  # DNA/transformation
            IntentionType.PROTECTION: 741,  # Awakening/protection
            IntentionType.RECONCILIATION: 639,  # Connection
            IntentionType.PEACE: 852,  # Spiritual order
            IntentionType.LOVE: 528,  # Love frequency
            IntentionType.WISDOM: 963,  # Divine consciousness
        }
        return intention_values.get(intention, 528)

    def select_frequency(self, intention: IntentionType) -> float:
        """Select appropriate frequency for intention"""
        frequency_map = {
            IntentionType.HEALING: self.frequencies["healing_dna"],
            IntentionType.LIBERATION: self.frequencies["liberation"],
            IntentionType.EMPOWERMENT: self.frequencies["awakening"],
            IntentionType.PROTECTION: self.frequencies["awakening"],
            IntentionType.RECONCILIATION: self.frequencies["connection"],
            IntentionType.PEACE: self.frequencies["spiritual"],
            IntentionType.LOVE: self.frequencies["healing_dna"],
            IntentionType.WISDOM: self.frequencies["unity"],
        }
        return frequency_map.get(intention, self.frequencies["healing_dna"])

    def broadcast_to_targets(self, config: BroadcastConfiguration) -> dict:
        """
        Perform integrated scalar-radionics broadcast to targets.

        The broadcast is recorded in the operations ledger as one
        ``broadcast`` operation: started when the work begins, completed
        (or failed) when it ends, with the measured elapsed time. The
        ledger id is returned as ``results["operation_id"]`` (``None`` if
        the ledger was unavailable; a ledger fault never stops a broadcast).
        """
        frequency = config.frequency_hz or self.select_frequency(config.intention)
        op_id = _ledger_begin(config, frequency)
        try:
            results = self._run_broadcast(config)
        except Exception as exc:
            _ledger_end(op_id, error=str(exc))
            raise
        _ledger_end(
            op_id,
            result={
                "values_generated": results["values_generated"],
                "targets_blessed": results["targets_blessed"],
                "meridians_activated": results["meridians_activated"],
                "chakras_activated": results["chakras_activated"],
                "crystal_status": (results.get("crystal_output") or {}).get("status"),
            },
        )
        results["operation_id"] = op_id
        return results

    def _run_broadcast(self, config: BroadcastConfiguration) -> dict:
        """The broadcast itself; see :meth:`broadcast_to_targets`."""
        print("\n" + "=" * 70)
        print("INTEGRATED SCALAR-RADIONICS BROADCAST")
        print("=" * 70)
        print()

        results = {
            "start_time": datetime.now().isoformat(),
            "config": {
                "intention": config.intention.value,
                "targets": config.target_count,
                "duration": config.duration_seconds,
                "intensity": config.scalar_intensity,
                "frequency": config.frequency_hz or self.select_frequency(config.intention),
                "mantra": config.mantra,
            },
            "values_generated": 0,
            "targets_blessed": 0,
            "meridians_activated": 0,
            "chakras_activated": 0,
        }

        # Get targets from database
        if self.blessing_db:
            targets = self.blessing_db.get_all_targets()
            if targets:
                targets = targets[: config.target_count]
                results["targets_blessed"] = len(targets)
                print(f"📡 Broadcasting to {len(targets)} targets")
                for target in targets[:5]:  # Show first 5
                    print(f"   • {target.name}")
                if len(targets) > 5:
                    print(f"   ... and {len(targets) - 5} more")
            else:
                print("⚠️  No targets in database - creating universal target")
                targets = []
        else:
            targets = []
            print("📡 Broadcasting to universal field")

        print()
        print(f"🎯 Intention: {config.intention.value}")
        print(f"🔊 Frequency: {results['config']['frequency']:.2f} Hz")
        print(f"🕉️  Mantra: {config.mantra}")
        print(f"⚡ Intensity: {config.scalar_intensity:.0%}")
        print(f"⏱️  Duration: {config.duration_seconds:.0f} seconds")
        print()

        # Invoke crystal broadcaster for prayer bowl audio (if available).
        # This is the integration point that was previously missing —
        # the "Integrated" broadcaster never touched crystal hardware.
        crystal_result = None
        if self.crystal_service:
            carrier_freqs = [7.83, config.frequency_hz or self.select_frequency(config.intention)]
            try:
                crystal_result = self.crystal_service.broadcast_intention(
                    intention=f"Scalar-Radionics: {config.intention.value}",
                    frequencies=carrier_freqs,
                    duration=int(config.duration_seconds),
                    hardware_level=2,
                    prayer_bowl_mode=True,
                    amplitude=0.15 + 0.35 * config.scalar_intensity,
                )
                print(f"🔔 Crystal broadcast: {crystal_result.get('status', 'unknown')}")
            except Exception as e:
                crystal_result = {"status": "failed", "error": str(e)}
                print(f"⚠️  Crystal broadcast failed: {e}")
            print()

        # Activate meridians if requested
        if config.use_meridians and self.anatomy_db:
            meridians = self.anatomy_db.get_all_meridians()
            results["meridians_activated"] = len(meridians)
            print(f"🌿 Activating {len(meridians)} meridians:")
            for m in meridians:
                print(f"   • {m.name} ({m.element.value if m.element else 'N/A'})")
            print()

        # Activate chakras if requested
        if config.use_chakras and self.anatomy_db:
            chakras = self.anatomy_db.get_all_chakras()
            results["chakras_activated"] = len(chakras)
            print(f"🕉️  Activating {len(chakras)} chakras:")
            for ch in chakras:
                print(f"   • {ch.name} ({ch.frequency}Hz)")
            print()

        # Generate scalar wave field
        if self.scalar_gen:
            print("⚡ Generating scalar wave field...")
            print()

            self.encode_intention(config.intention)
            values_count = 0
            start_time = time.time()

            if config.breathing_pattern:
                # Sacred breathing pattern
                print("🌬️  Using sacred breathing pattern...")
                values_count = self._breathing_broadcast(config)
            else:
                # Continuous broadcast. Guard against zero/negative durations
                # (used by smoke tests) to avoid ZeroDivisionError in the
                # progress calculation below; one batch is enough to prove
                # the code path works.
                if config.duration_seconds <= 0:
                    stream = self.scalar_gen.generate_hybrid_stream(int(1000 * config.scalar_intensity))
                    values_count = len(stream)
                else:
                    while (time.time() - start_time) < config.duration_seconds:
                        # Generate based on intensity
                        batch_size = int(1000 * config.scalar_intensity)
                        stream = self.scalar_gen.generate_hybrid_stream(batch_size)

                        values_count += len(stream)

                        # Show progress every 5 seconds
                        elapsed = time.time() - start_time
                        if int(elapsed) % 5 == 0:
                            progress = elapsed / config.duration_seconds
                            temp = self.scalar_gen.thermal.state.temperature
                            print(
                                f"\r⏱️  {elapsed:.0f}s/{config.duration_seconds:.0f}s | "
                                f"📊 {values_count:,} values | "
                                f"🌡️  {temp:.1f}°C | "
                                f"{'█' * int(progress * 20)}{' ' * (20 - int(progress * 20))} {progress:.0%}",
                                end="",
                                flush=True,
                            )

            elapsed = time.time() - start_time
            results["values_generated"] = values_count

            print()
            print()
            print("✅ Scalar wave generation complete!")
            print(f"   Values generated: {values_count:,} in {elapsed:.1f}s")
            print()

        # Record session if we have blessing database
        if self.blessing_db and targets:
            print("📝 Recording blessing session...")
            session_id = self.blessing_db.record_session(
                mantra_type=config.mantra,
                total_mantras=108,
                total_rotations=1,
                targets_blessed=len(targets),
                allocation_method="Scalar-Radionics Broadcast",
                notes=f"Integrated broadcast with {config.intention.value} intention",
            )

            # Dedicate to each target
            for target in targets:
                self.blessing_db.record_dedication(
                    target_identifier=target.identifier,
                    session_id=session_id,
                    mantra_type=config.mantra,
                    mantras_count=108,
                    notes=f"Scalar-radionics broadcast ({config.intention.value})",
                )

            print(f"✅ Blessed {len(targets)} targets")
            print()

        # Update statistics
        self.total_broadcasts += 1
        self.total_values_generated += results["values_generated"]
        self.total_targets_blessed += results["targets_blessed"]

        # Final summary
        print("=" * 70)
        print("BROADCAST COMPLETE")
        print("=" * 70)
        print()
        print(f"Intention: {config.intention.value}")
        print(f"Values generated: {results['values_generated']:,}")
        print(f"Targets: {results['targets_blessed']}")
        if results["meridians_activated"]:
            print(f"Meridians: {results['meridians_activated']} activated")
        if results["chakras_activated"]:
            print(f"Chakras: {results['chakras_activated']} activated")
        print()
        print("May all beings benefit from this transmission!")
        print("Om Mani Padme Hum 🙏")
        print()

        results["end_time"] = datetime.now().isoformat()
        results["crystal_output"] = crystal_result
        return results

    def _breathing_broadcast(self, config: BroadcastConfiguration) -> int:
        """Broadcast using sacred breathing pattern; returns the number of values generated."""
        print("  Inhale phase (33s) - building field...")
        start = time.time()
        values = 0
        while (time.time() - start) < 33:
            progress = (time.time() - start) / 33.0
            batch = int(1000 * progress * config.scalar_intensity)
            stream = self.scalar_gen.generate_hybrid_stream(max(10, batch))
            values += len(stream)

        print(f"  ✓ Inhale complete ({values:,} values)")

        print("  Hold phase (27s) - maximum intensity...")
        start = time.time()
        while (time.time() - start) < 27:
            batch = int(1000 * config.scalar_intensity)
            stream = self.scalar_gen.generate_hybrid_stream(batch)
            values += len(stream)

        print(f"  ✓ Hold complete ({values:,} values)")

        print("  Exhale phase (33s) - releasing field...")
        start = time.time()
        while (time.time() - start) < 33:
            progress = 1.0 - ((time.time() - start) / 33.0)
            batch = int(1000 * progress * config.scalar_intensity)
            stream = self.scalar_gen.generate_hybrid_stream(max(10, batch))
            values += len(stream)

        print(f"  ✓ Exhale complete ({values:,} values)")

        print("  Rest phase (12s) - integration...")
        time.sleep(12)

        print("  ✓ Breathing cycle complete")
        return values

    def healing_protocol(self, target_name: str, duration_minutes: int = 10):
        """
        Run complete healing protocol for a target.
        """
        print("\n" + "=" * 70)
        print(f"HEALING PROTOCOL: {target_name}")
        print("=" * 70)
        print()

        # Configuration
        config = BroadcastConfiguration(
            intention=IntentionType.HEALING,
            target_count=1,
            duration_seconds=duration_minutes * 60,
            scalar_intensity=0.8,
            frequency_hz=528,  # DNA repair
            mantra="Om Mani Padme Hum",
            use_chakras=True,
            breathing_pattern=False,
        )

        results = self.broadcast_to_targets(config)
        return results

    def liberation_protocol(self, event_name: str, souls_count: int = 1000000):
        """
        Run liberation protocol for historical trauma.
        """
        print("\n" + "=" * 70)
        print(f"LIBERATION PROTOCOL: {event_name}")
        print(f"For {souls_count:,} souls")
        print("=" * 70)
        print()

        config = BroadcastConfiguration(
            intention=IntentionType.LIBERATION,
            target_count=10,
            duration_seconds=108,  # Sacred number
            scalar_intensity=1.0,
            frequency_hz=396,  # Liberation frequency
            mantra="Om Mani Padme Hum",
            use_meridians=True,
            use_chakras=True,
            breathing_pattern=True,
        )

        results = self.broadcast_to_targets(config)
        return results

    def empowerment_protocol(self, target_group: str):
        """
        Run empowerment protocol.
        """
        print("\n" + "=" * 70)
        print(f"EMPOWERMENT PROTOCOL: {target_group}")
        print("=" * 70)
        print()

        config = BroadcastConfiguration(
            intention=IntentionType.EMPOWERMENT,
            target_count=100,
            duration_seconds=216,  # 2 x 108
            scalar_intensity=0.9,
            frequency_hz=528,  # Transformation
            mantra="Gate Gate Paragate Parasamgate Bodhi Svaha",
            use_chakras=True,
            breathing_pattern=True,
        )

        results = self.broadcast_to_targets(config)
        return results

    def print_statistics(self):
        """Print broadcaster statistics"""
        print("\n" + "=" * 70)
        print("BROADCASTER STATISTICS")
        print("=" * 70)
        print()
        print(f"Total Broadcasts: {self.total_broadcasts}")
        print(f"Total Values Generated: {self.total_values_generated:,}")
        print(f"Total Targets Blessed: {self.total_targets_blessed}")
        print()


# ============================================================================
# OPERATIONS LEDGER
# ============================================================================


def _ledger_begin(config: BroadcastConfiguration, frequency_hz: float) -> str | None:
    """Create and start a ``broadcast`` ledger operation; ``None`` if the ledger is unavailable."""
    try:
        from core import operations

        op = operations.create_operation(
            "broadcast",
            f"Scalar-radionics broadcast: {config.intention.value}",
            params={
                "intention": config.intention.value,
                "target_count": config.target_count,
                "requested_duration_seconds": config.duration_seconds,
                "scalar_intensity": config.scalar_intensity,
                "frequency_hz": frequency_hz,
                "mantra": config.mantra,
                "breathing_pattern": config.breathing_pattern,
            },
        )
        operations.start_operation(op["id"])
        return op["id"]
    except Exception:
        logger.warning("operations ledger unavailable; broadcast not recorded", exc_info=True)
        return None


def _ledger_end(op_id: str | None, *, result: dict[str, Any] | None = None, error: str | None = None) -> None:
    """Complete (or fail, when ``error`` is given) a ledger operation started by :func:`_ledger_begin`."""
    if op_id is None:
        return
    try:
        from core import operations

        if error is not None:
            operations.fail_operation(op_id, error)
        else:
            operations.complete_operation(op_id, result=result)
    except Exception:
        logger.warning("could not close ledger operation %s", op_id, exc_info=True)


# ============================================================================
# CLI INTERFACE
# ============================================================================


def main():
    """Main CLI interface"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Integrated Scalar-Radionics Broadcaster",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Healing protocol (10 minutes)
  %(prog)s --healing "Person Name" --duration 10

  # Liberation protocol
  %(prog)s --liberation "Those who suffered in times of war" --souls 0

  # Empowerment protocol
  %(prog)s --empowerment "All Beings in Difficulty"

  # Custom broadcast
  %(prog)s --intention healing --targets 50 --duration 300 --intensity 0.9

May all transmissions serve liberation!
Om Mani Padme Hum 🙏
        """,
    )

    parser.add_argument("--healing", type=str, metavar="NAME", help="Run healing protocol for named target")
    parser.add_argument("--liberation", type=str, metavar="EVENT", help="Run liberation protocol for historical event")
    parser.add_argument("--empowerment", type=str, metavar="GROUP", help="Run empowerment protocol for group")

    parser.add_argument("--intention", type=str, choices=[i.value for i in IntentionType], help="Broadcast intention")
    parser.add_argument("--targets", type=int, default=10, help="Number of targets (default: 10)")
    parser.add_argument("--duration", type=int, default=60, help="Duration in seconds (default: 60)")
    parser.add_argument("--intensity", type=float, default=0.8, help="Scalar intensity 0.0-1.0 (default: 0.8)")
    parser.add_argument("--frequency", type=float, help="Frequency in Hz (default: auto-select)")
    parser.add_argument(
        "--mantra", type=str, default="Om Mani Padme Hum", help="Mantra to broadcast (default: Om Mani Padme Hum)"
    )
    parser.add_argument("--meridians", action="store_true", help="Activate meridian system")
    parser.add_argument("--chakras", action="store_true", help="Activate chakra system")
    parser.add_argument("--breathing", action="store_true", help="Use sacred breathing pattern")
    parser.add_argument("--souls", type=int, help="Number of souls (for liberation protocol)")
    parser.add_argument("--stats", action="store_true", help="Show broadcaster statistics")

    args = parser.parse_args()

    broadcaster = IntegratedScalarRadionicsBroadcaster()

    if args.healing:
        broadcaster.healing_protocol(args.healing, duration_minutes=args.duration)

    elif args.liberation:
        souls = args.souls or 1000000
        broadcaster.liberation_protocol(args.liberation, souls_count=souls)

    elif args.empowerment:
        broadcaster.empowerment_protocol(args.empowerment)

    elif args.intention:
        # Custom broadcast
        intention = IntentionType(args.intention)
        config = BroadcastConfiguration(
            intention=intention,
            target_count=args.targets,
            duration_seconds=args.duration,
            scalar_intensity=args.intensity,
            frequency_hz=args.frequency,
            mantra=args.mantra,
            use_meridians=args.meridians,
            use_chakras=args.chakras,
            breathing_pattern=args.breathing,
        )
        broadcaster.broadcast_to_targets(config)

    else:
        parser.print_help()

    if args.stats:
        broadcaster.print_statistics()


if __name__ == "__main__":
    main()
