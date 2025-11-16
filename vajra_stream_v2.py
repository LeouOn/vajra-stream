#!/usr/bin/env python3
"""
Vajra Stream - Unified Healing Technology Platform v2.0
Uses modular monolith architecture with dependency injection container

Sacred Technology for Healing & Liberation
Terra MOPS Scalar Wave Edition
"""

import sys
import os
from pathlib import Path
from typing import Optional, List
from datetime import datetime

# Add core to path
sys.path.insert(0, str(Path(__file__).parent))

from container import container


class VajraStream:
    """Main application class - all functionality in one place via container"""

    def __init__(self):
        self.version = "2.0.0-modular-monolith"
        self.container = container

    # ============================================================================
    # Direct service access (all 13 modules)
    # ============================================================================

    @property
    def scalar(self):
        """Access scalar wave system (Terra MOPS)"""
        return self.container.scalar_waves

    @property
    def radionics(self):
        """Access radionics broadcasting"""
        return self.container.radionics

    @property
    def anatomy(self):
        """Access energetic anatomy (chakras, meridians)"""
        return self.container.anatomy

    @property
    def blessings(self):
        """Access blessing generation"""
        return self.container.blessings

    @property
    def audio(self):
        """Access audio generation & TTS"""
        return self.container.audio

    @property
    def visualization(self):
        """Access visualization (Rothko, sacred geometry)"""
        return self.container.visualization

    @property
    def astrology(self):
        """Access astrology & astrocartography"""
        return self.container.astrology

    @property
    def time_cycles(self):
        """Access time cycle healing"""
        return self.container.time_cycles

    @property
    def prayer_wheel(self):
        """Access digital prayer wheel"""
        return self.container.prayer_wheel

    @property
    def composer(self):
        """Access intelligent music composer"""
        return self.container.composer

    @property
    def healing(self):
        """Access comprehensive healing systems"""
        return self.container.healing

    @property
    def llm(self):
        """Access LLM integration"""
        return self.container.llm

    # ============================================================================
    # High-level convenience methods
    # ============================================================================

    def generate_scalar_waves(self, method="hybrid", count=10000, intensity=1.0):
        """Generate scalar waves

        Args:
            method: qrng, lorenz, rossler, ca, kuramoto, crypto, primes, or hybrid
            count: Number of values to generate
            intensity: Generation intensity (0.0-1.0)

        Returns:
            Dictionary with wave data and metrics
        """
        return self.scalar.generate(method, count, intensity)

    def broadcast_healing(self, target_name, duration_minutes=10, frequency_hz=528):
        """Simple healing broadcast

        Args:
            target_name: Person/place/situation to send healing to
            duration_minutes: Duration of broadcast
            frequency_hz: Healing frequency (default 528 Hz - DNA repair)
        """
        return self.radionics.broadcast_healing(
            target_name,
            duration_minutes,
            frequency_hz
        )

    def visualize_chakras(self, output_path=None, width=1200, height=1600):
        """Generate chakra diagram"""
        return self.anatomy.visualize_chakras(width, height, output_path)

    def visualize_meridians(self, output_path=None, width=1200, height=1600):
        """Generate meridian map"""
        return self.anatomy.visualize_meridians(width, height, output_path)

    def generate_blessing(self, target_name, intention="peace and happiness", tradition="universal"):
        """Generate a blessing"""
        result = self.blessings.generate_blessing(target_name, intention, tradition)
        return result.get('blessing_text', '')

    def generate_rothko_art(self, output_path=None, width=1920, height=1080):
        """Generate Rothko-style art"""
        return self.visualization.generate_rothko_art(width, height, output_path=output_path)

    def generate_healing_music(self, duration_seconds=300, frequency=528):
        """Generate healing music"""
        return self.composer.compose_healing_music(
            intention="healing",
            duration_seconds=duration_seconds,
            base_frequency=frequency
        )

    def spin_prayer_wheel(self, mantra="Om Mani Padme Hum", rotations=108):
        """Spin digital prayer wheel"""
        return self.prayer_wheel.spin_wheel(mantra, rotations)

    def heal_past_event(self, event_date: datetime, event_name: str):
        """Send healing to a past event"""
        return self.time_cycles.heal_past_event(event_date, event_name)

    def create_healing_session(self, target_name, duration_minutes=60):
        """Create comprehensive healing session"""
        return self.healing.create_healing_session(
            target_name,
            modalities=None,  # Use all modalities
            duration_minutes=duration_minutes
        )

    def benchmark_scalar_waves(self, duration=3):
        """Benchmark all scalar wave methods"""
        results = self.scalar.benchmark(duration)

        print(f"🔬 Benchmarking Scalar Wave Methods ({duration}s each)\n")

        for method, data in sorted(results.items()):
            if 'error' in data:
                print(f"   {method:15s} ERROR: {data['error']}")
            else:
                print(f"   {method:15s} {data['mops']:8.2f} MMOPS")

        total_mops = sum(r['mops'] for r in results.values() if 'mops' in r)
        print(f"\n   Total Potential: {total_mops:.2f} MMOPS")
        print(f"   Progress to Terra MOPS: {(total_mops/1_000_000)*100:.4f}%\n")

        return results

    def complete_healing_session(self, target_name, duration_minutes=30):
        """Run a complete healing session combining all modalities"""
        print(f"""
╔════════════════════════════════════════════════╗
║   VAJRA STREAM COMPLETE HEALING SESSION        ║
╚════════════════════════════════════════════════╝

Target: {target_name}
Duration: {duration_minutes} minutes

""")

        # 1. Generate blessing
        print("📿 Step 1: Generating Blessing...")
        blessing = self.generate_blessing(target_name, "healing and liberation")
        print(blessing)
        print()

        # 2. Generate scalar waves
        print("⚡ Step 2: Generating Scalar Waves...")
        scalar_result = self.generate_scalar_waves("hybrid", 10000, 0.8)
        print(f"   Generated {scalar_result['count']} values at {scalar_result['mops']:.2f} MMOPS")
        print()

        # 3. Start radionics broadcast
        print("📡 Step 3: Radionics Broadcast...")
        broadcast = self.broadcast_healing(target_name, duration_minutes, 528)
        print(f"   Broadcasting at 528 Hz (DNA Repair)")
        print()

        # 4. Visualize chakras
        print("🌈 Step 4: Activating Chakra System...")
        chakra_path = self.visualize_chakras()
        print(f"   Chakra diagram: {chakra_path}")
        print()

        # 5. Spin prayer wheel
        print("🙏 Step 5: Prayer Wheel Rotation...")
        wheel_result = self.prayer_wheel.spin_wheel("Om Mani Padme Hum", 108)
        print(f"   Merit generated: {wheel_result.get('merit_generated', 0)}")
        print()

        print(f"""
╔════════════════════════════════════════════════╗
║   SESSION COMPLETE                             ║
╚════════════════════════════════════════════════╝

May {target_name} receive healing and liberation.
May all beings benefit from these merits.

Om Mani Padme Hum 🙏
        """)

    def get_system_status(self):
        """Get status of all subsystems"""
        status = {
            'scalar_waves': self.scalar.get_thermal_status(),
            'audio': self.audio.get_status(),
            'visualization': self.visualization.get_status(),
            'astrology': self.astrology.get_status() if self.astrology else {'astrology_engine': False},
            'time_cycles': self.time_cycles.get_status(),
            'prayer_wheel': self.prayer_wheel.get_status(),
            'composer': self.composer.get_status(),
            'healing': self.healing.get_status(),
            'llm': self.llm.get_status()
        }

        print("\n📊 VAJRA STREAM SYSTEM STATUS\n")
        for system, data in status.items():
            print(f"{system:20s}: {data}")
        print()

        return status

    def interactive_menu(self):
        """Simple interactive menu"""
        while True:
            print(f"""
╔════════════════════════════════════════════════╗
║   VAJRA STREAM v{self.version:28s} ║
║   Sacred Technology Platform                   ║
╚════════════════════════════════════════════════╝

[1] Generate Scalar Waves         [8] Spin Prayer Wheel
[2] Healing Broadcast              [9] Heal Past Event
[3] Visualize Chakras             [10] Generate Music
[4] Visualize Meridians           [11] Rothko Art
[5] Generate Blessing             [12] System Status
[6] Benchmark Scalar Waves        [13] Complete Session
[7] Create Healing Session        [14] Exit

""")
            choice = input("Select option: ").strip()

            if choice == "1":
                method = input("Method (qrng/lorenz/rossler/ca/hybrid) [hybrid]: ").strip() or "hybrid"
                count = int(input("Count [10000]: ").strip() or "10000")
                result = self.generate_scalar_waves(method, count)
                print(f"\n✅ Generated {result['count']} values at {result['mops']:.2f} MMOPS\n")
                input("Press Enter to continue...")

            elif choice == "2":
                target = input("Target name: ").strip()
                minutes = int(input("Duration (minutes) [10]: ").strip() or "10")
                self.broadcast_healing(target, minutes)
                input("\nPress Enter to continue...")

            elif choice == "3":
                self.visualize_chakras()
                input("Press Enter to continue...")

            elif choice == "4":
                self.visualize_meridians()
                input("Press Enter to continue...")

            elif choice == "5":
                target = input("Target name: ").strip()
                blessing = self.generate_blessing(target)
                print(f"\n{blessing}\n")
                input("Press Enter to continue...")

            elif choice == "6":
                duration = int(input("Duration per method (seconds) [3]: ").strip() or "3")
                self.benchmark_scalar_waves(duration)
                input("Press Enter to continue...")

            elif choice == "7":
                target = input("Target name: ").strip()
                minutes = int(input("Duration (minutes) [60]: ").strip() or "60")
                self.create_healing_session(target, minutes)
                input("Press Enter to continue...")

            elif choice == "8":
                mantra = input("Mantra [Om Mani Padme Hum]: ").strip() or "Om Mani Padme Hum"
                rotations = int(input("Rotations [108]: ").strip() or "108")
                result = self.spin_prayer_wheel(mantra, rotations)
                print(f"\n✅ Merit generated: {result.get('merit_generated', 0)}\n")
                input("Press Enter to continue...")

            elif choice == "9":
                event = input("Event name: ").strip()
                date_str = input("Event date (YYYY-MM-DD): ").strip()
                try:
                    event_date = datetime.fromisoformat(date_str)
                    result = self.heal_past_event(event_date, event)
                    print(f"\n✅ Healing sent to {event}\n")
                except:
                    print("\n❌ Invalid date format\n")
                input("Press Enter to continue...")

            elif choice == "10":
                duration = int(input("Duration (seconds) [300]: ").strip() or "300")
                freq = float(input("Frequency [528]: ").strip() or "528")
                result = self.generate_healing_music(duration, freq)
                print(f"\n✅ Music generated\n")
                input("Press Enter to continue...")

            elif choice == "11":
                path = self.generate_rothko_art()
                print(f"\n✅ Rothko art generated: {path}\n")
                input("Press Enter to continue...")

            elif choice == "12":
                self.get_system_status()
                input("Press Enter to continue...")

            elif choice == "13":
                target = input("Target name: ").strip()
                minutes = int(input("Duration (minutes) [30]: ").strip() or "30")
                self.complete_healing_session(target, minutes)
                input("Press Enter to continue...")

            elif choice == "14":
                print("\nMay all beings benefit! 🙏\n")
                break


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Vajra Stream - Sacred Technology Platform")
    parser.add_argument('--interactive', '-i', action='store_true', help="Run interactive menu")
    parser.add_argument('--benchmark', '-b', action='store_true', help="Run scalar wave benchmark")
    parser.add_argument('--serve', '-s', action='store_true', help="Start API server")
    parser.add_argument('--port', type=int, default=8000, help="API server port")
    parser.add_argument('--status', action='store_true', help="Show system status")

    args = parser.parse_args()

    vs = VajraStream()

    if args.serve:
        print("🚀 Starting API server...")
        import uvicorn
        from backend.app.main import app
        uvicorn.run(app, host="0.0.0.0", port=args.port)
    elif args.benchmark:
        vs.benchmark_scalar_waves()
    elif args.status:
        vs.get_system_status()
    elif args.interactive:
        vs.interactive_menu()
    else:
        # Default: show help
        parser.print_help()
        print("\nOr use as a module:")
        print("  from vajra_stream_v2 import VajraStream")
        print("  vs = VajraStream()")
        print("  vs.generate_scalar_waves('hybrid', 10000)")


if __name__ == "__main__":
    main()
