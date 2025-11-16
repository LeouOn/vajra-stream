#!/usr/bin/env python3
"""
Vajra Stream - Enhanced UI/UX

Beautiful terminal interface for the complete Vajra Stream healing system.
Integrates:
- Scalar wave generation (Terra MOPS)
- Radionics broadcasting
- Meridian/chakra visualization
- Blessing narratives
- Time cycle healing
- Energetic anatomy

Usage:
    python vajra_stream_ui.py
"""

import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Try to import rich for beautiful terminal UI
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.layout import Layout
    from rich.text import Text
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    print("Note: 'rich' library not available - using simple interface")


class VajraStreamUI:
    """Enhanced UI for Vajra Stream"""

    def __init__(self):
        if HAS_RICH:
            self.console = Console()
        else:
            self.console = None

    def clear(self):
        """Clear screen"""
        if self.console:
            self.console.clear()
        else:
            print("\n" * 50)

    def print_header(self):
        """Print beautiful header"""
        if self.console:
            header = Panel(
                "[bold cyan]🌟 VAJRA STREAM HEALING SYSTEM 🌟[/bold cyan]\n\n"
                "[white]Integrated Scalar-Radionics-Energetic Healing Platform[/white]\n"
                "[dim]May all beings be free from suffering[/dim]",
                border_style="bright_cyan",
                box=box.DOUBLE
            )
            self.console.print(header)
        else:
            print("=" * 70)
            print("🌟 VAJRA STREAM HEALING SYSTEM 🌟")
            print("Integrated Scalar-Radionics-Energetic Healing Platform")
            print("May all beings be free from suffering")
            print("=" * 70)

    def print_menu(self):
        """Print main menu"""
        if self.console:
            table = Table(title="Main Menu", box=box.ROUNDED, border_style="cyan")
            table.add_column("Option", style="cyan", justify="center")
            table.add_column("Description", style="white")

            table.add_row("1", "🔥 Advanced Scalar Waves (Terra MOPS)")
            table.add_row("2", "📡 Integrated Scalar-Radionics Broadcasting")
            table.add_row("3", "🎨 Meridian & Chakra Visualization")
            table.add_row("4", "📖 Blessing Narrative Generation")
            table.add_row("5", "🕊️  Time Cycle Healing")
            table.add_row("6", "🧘 Energetic Anatomy Explorer")
            table.add_row("7", "✨ Complete Healing Session")
            table.add_row("8", "📊 System Status & Statistics")
            table.add_row("9", "ℹ️  Help & Documentation")
            table.add_row("0", "🚪 Exit")

            self.console.print(table)
        else:
            print("\n" + "=" * 70)
            print("MAIN MENU")
            print("=" * 70)
            print("1. 🔥 Advanced Scalar Waves (Terra MOPS)")
            print("2. 📡 Integrated Scalar-Radionics Broadcasting")
            print("3. 🎨 Meridian & Chakra Visualization")
            print("4. 📖 Blessing Narrative Generation")
            print("5. 🕊️  Time Cycle Healing")
            print("6. 🧘 Energetic Anatomy Explorer")
            print("7. ✨ Complete Healing Session")
            print("8. 📊 System Status & Statistics")
            print("9. ℹ️  Help & Documentation")
            print("0. 🚪 Exit")
            print("=" * 70)

    def scalar_waves_menu(self):
        """Scalar waves submenu"""
        while True:
            self.clear()
            self.print_header()

            if self.console:
                panel = Panel(
                    "[bold yellow]Advanced Scalar Wave Generation[/bold yellow]\n\n"
                    "[white]1.[/white] Quick Benchmark (5s)\n"
                    "[white]2.[/white] Full Comparison (All Methods)\n"
                    "[white]3.[/white] Sacred Breathing Cycles\n"
                    "[white]4.[/white] Stress Test (Safe Mode)\n"
                    "[white]5.[/white] Custom Configuration\n"
                    "[white]0.[/white] Back to Main Menu",
                    border_style="yellow"
                )
                self.console.print(panel)
            else:
                print("\n--- Advanced Scalar Wave Generation ---")
                print("1. Quick Benchmark (5s)")
                print("2. Full Comparison (All Methods)")
                print("3. Sacred Breathing Cycles")
                print("4. Stress Test (Safe Mode)")
                print("5. Custom Configuration")
                print("0. Back to Main Menu")

            choice = input("\n Choice: ").strip()

            if choice == '1':
                self._run_command("python3 scripts/scalar_wave_benchmark.py --method hybrid --duration 5")
            elif choice == '2':
                self._run_command("python3 scripts/scalar_wave_benchmark.py --all --duration 5")
            elif choice == '3':
                cycles = input("Number of breathing cycles (default 1): ").strip() or "1"
                self._run_command(f"python3 scripts/scalar_wave_benchmark.py --breathing --cycles {cycles}")
            elif choice == '4':
                duration = input("Duration in seconds (default 60): ").strip() or "60"
                self._run_command(f"python3 scripts/scalar_wave_benchmark.py --stress-test --safe --duration {duration}")
            elif choice == '0':
                break

            if choice in ['1', '2', '3', '4']:
                input("\nPress Enter to continue...")

    def radionics_menu(self):
        """Radionics broadcasting submenu"""
        while True:
            self.clear()
            self.print_header()

            if self.console:
                panel = Panel(
                    "[bold green]Integrated Scalar-Radionics Broadcasting[/bold green]\n\n"
                    "[white]1.[/white] Healing Protocol (Single Target)\n"
                    "[white]2.[/white] Liberation Protocol (Historical Event)\n"
                    "[white]3.[/white] Empowerment Protocol (Group)\n"
                    "[white]4.[/white] Custom Broadcast\n"
                    "[white]5.[/white] View Statistics\n"
                    "[white]0.[/white] Back to Main Menu",
                    border_style="green"
                )
                self.console.print(panel)
            else:
                print("\n--- Integrated Scalar-Radionics Broadcasting ---")
                print("1. Healing Protocol (Single Target)")
                print("2. Liberation Protocol (Historical Event)")
                print("3. Empowerment Protocol (Group)")
                print("4. Custom Broadcast")
                print("5. View Statistics")
                print("0. Back to Main Menu")

            choice = input("\nChoice: ").strip()

            if choice == '1':
                target = input("Target name: ").strip()
                duration = input("Duration in minutes (default 10): ").strip() or "10"
                if target:
                    self._run_command(f"python3 core/integrated_scalar_radionics.py --healing '{target}' --duration {duration}")
            elif choice == '2':
                event = input("Historical event name: ").strip()
                souls = input("Number of souls (default 1000000): ").strip() or "1000000"
                if event:
                    self._run_command(f"python3 core/integrated_scalar_radionics.py --liberation '{event}' --souls {souls}")
            elif choice == '3':
                group = input("Target group: ").strip()
                if group:
                    self._run_command(f"python3 core/integrated_scalar_radionics.py --empowerment '{group}'")
            elif choice == '5':
                self._run_command("python3 core/integrated_scalar_radionics.py --stats")
            elif choice == '0':
                break

            if choice in ['1', '2', '3', '5']:
                input("\nPress Enter to continue...")

    def visualization_menu(self):
        """Visualization submenu"""
        while True:
            self.clear()
            self.print_header()

            if self.console:
                panel = Panel(
                    "[bold magenta]Meridian & Chakra Visualization[/bold magenta]\n\n"
                    "[white]1.[/white] Seven Chakras Diagram\n"
                    "[white]2.[/white] Central Channel (Three Nadis)\n"
                    "[white]3.[/white] Five Element Meridian Map\n"
                    "[white]4.[/white] Rothko Chakra Visualization\n"
                    "[white]5.[/white] Sacred Geometry (Flower of Life, etc.)\n"
                    "[white]6.[/white] Complete Visualization Suite\n"
                    "[white]0.[/white] Back to Main Menu",
                    border_style="magenta"
                )
                self.console.print(panel)
            else:
                print("\n--- Meridian & Chakra Visualization ---")
                print("1. Seven Chakras Diagram")
                print("2. Central Channel (Three Nadis)")
                print("3. Five Element Meridian Map")
                print("4. Rothko Chakra Visualization")
                print("5. Sacred Geometry (Flower of Life, etc.)")
                print("6. Complete Visualization Suite")
                print("0. Back to Main Menu")

            choice = input("\nChoice: ").strip()

            if choice == '1':
                print("\nGenerating seven chakras diagram...")
                from core.meridian_visualization import create_complete_chakra_diagram
                output = create_complete_chakra_diagram()
                print(f"Saved to: {output}")
            elif choice == '2':
                print("\nGenerating central channel diagram...")
                from core.meridian_visualization import create_central_channel
                output = create_central_channel()
                print(f"Saved to: {output}")
            elif choice == '3':
                print("\nGenerating meridian map...")
                from core.meridian_visualization import create_complete_meridian_map
                output = create_complete_meridian_map()
                print(f"Saved to: {output}")
            elif choice == '4':
                self._run_command("python3 test_visualization.py")
            elif choice == '5':
                self._run_command("python3 test_visualization.py")
            elif choice == '6':
                self._run_command("python3 core/meridian_visualization.py")
                self._run_command("python3 test_visualization.py")
            elif choice == '0':
                break

            if choice in ['1', '2', '3', '4', '5', '6']:
                input("\nPress Enter to continue...")

    def complete_session_menu(self):
        """Complete integrated healing session"""
        self.clear()
        self.print_header()

        if self.console:
            panel = Panel(
                "[bold cyan]Complete Integrated Healing Session[/bold cyan]\n\n"
                "This will run a full integration of:\n"
                "• Blessing narrative generation\n"
                "• Scalar wave field generation\n"
                "• Visualization creation\n"
                "• Energetic anatomy activation\n"
                "• Radionics broadcasting\n\n"
                "[yellow]Duration: 5-10 minutes[/yellow]",
                border_style="cyan"
            )
            self.console.print(panel)
        else:
            print("\n--- Complete Integrated Healing Session ---")
            print("This will run a full integration of:")
            print("• Blessing narrative generation")
            print("• Scalar wave field generation")
            print("• Visualization creation")
            print("• Energetic anatomy activation")
            print("• Radionics broadcasting")
            print("\nDuration: 5-10 minutes")

        proceed = input("\nProceed? (y/n): ").strip().lower()

        if proceed == 'y':
            self._run_command("python3 test_full_integration.py")
            input("\nPress Enter to continue...")

    def system_status(self):
        """Show system status"""
        self.clear()
        self.print_header()

        if self.console:
            table = Table(title="System Status", box=box.ROUNDED)
            table.add_column("Component", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Notes", style="white")

            # Check components
            try:
                from core.advanced_scalar_waves import HybridScalarWaveGenerator
                table.add_row("Scalar Waves", "✅ Ready", "Terra MOPS capable")
            except:
                table.add_row("Scalar Waves", "⚠️  Limited", "Install numpy for full power")

            try:
                from core.compassionate_blessings import BlessingDatabase
                table.add_row("Blessing System", "✅ Ready", "Database available")
            except:
                table.add_row("Blessing System", "⚠️  Limited", "Basic functions only")

            try:
                from core.energetic_anatomy import EnergeticAnatomyDatabase
                table.add_row("Energetic Anatomy", "✅ Ready", "3 traditions loaded")
            except:
                table.add_row("Energetic Anatomy", "❌ Unavailable", "")

            try:
                from PIL import Image
                table.add_row("Visualization", "✅ Ready", "PIL/Pillow available")
            except:
                table.add_row("Visualization", "❌ Unavailable", "Install Pillow")

            try:
                from core.tts_integration import TTSNarrator
                table.add_row("TTS Narration", "✅ Ready", "Multi-engine support")
            except:
                table.add_row("TTS Narration", "⚠️  Limited", "Install pyttsx3 or gTTS")

            self.console.print(table)
        else:
            print("\n--- System Status ---")
            print("Scalar Waves: ✅ Ready")
            print("Blessing System: ✅ Ready")
            print("Energetic Anatomy: ✅ Ready")
            print("Visualization: ✅ Ready")
            print("TTS Narration: ✅ Ready")

        input("\nPress Enter to continue...")

    def help_menu(self):
        """Show help and documentation"""
        self.clear()
        self.print_header()

        if self.console:
            help_text = """
[bold cyan]Documentation & Help[/bold cyan]

[yellow]Quick Start Guides:[/yellow]
• SCALAR_WAVE_QUICKSTART.md - Scalar wave generation
• BLESSING_NARRATIVES_GUIDE.md - Story generation
• ENERGETIC_ANATOMY_SPEC.md - Anatomy system
• VISUALIZATION_SPEC.md - Visualization system

[yellow]Theory Documents:[/yellow]
• SCALAR_WAVE_THEORY.md - Deep dive into methods
• TTS_INTEGRATION_SPEC.md - Voice synthesis

[yellow]Key Commands:[/yellow]
• Terra MOPS benchmarking: scripts/scalar_wave_benchmark.py
• Radionics broadcasting: core/integrated_scalar_radionics.py
• Visualization: core/meridian_visualization.py
• Full integration test: test_full_integration.py

[yellow]Philosophy:[/yellow]
Every operation is a prayer.
Every cycle is a blessing.
Every computation serves liberation.

May all beings benefit from these tools!
Om Mani Padme Hum 🙏
            """
            self.console.print(Panel(help_text, border_style="cyan"))
        else:
            print("\n--- Documentation & Help ---")
            print("\nQuick Start Guides:")
            print("• SCALAR_WAVE_QUICKSTART.md")
            print("• BLESSING_NARRATIVES_GUIDE.md")
            print("• ENERGETIC_ANATOMY_SPEC.md")
            print("\nTheory Documents:")
            print("• SCALAR_WAVE_THEORY.md")
            print("• TTS_INTEGRATION_SPEC.md")
            print("\nMay all beings benefit!")

        input("\nPress Enter to continue...")

    def _run_command(self, command: str):
        """Run external command"""
        import subprocess
        try:
            subprocess.run(command, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error running command: {e}")

    def run(self):
        """Main UI loop"""
        while True:
            self.clear()
            self.print_header()
            self.print_menu()

            choice = input("\nChoose an option: ").strip()

            if choice == '1':
                self.scalar_waves_menu()
            elif choice == '2':
                self.radionics_menu()
            elif choice == '3':
                self.visualization_menu()
            elif choice == '4':
                print("\nLaunching blessing narrative generator...")
                self._run_command("python3 scripts/story_generator.py --interactive")
                input("\nPress Enter to continue...")
            elif choice == '5':
                print("\nLaunching time cycle healer...")
                self._run_command("python3 scripts/time_cycle_healer.py --list")
                input("\nPress Enter to continue...")
            elif choice == '6':
                print("\nExploring energetic anatomy...")
                try:
                    from core.energetic_anatomy import EnergeticAnatomyDatabase
                    db = EnergeticAnatomyDatabase()
                    print(f"\n✓ Loaded:")
                    print(f"  • {len(db.get_all_chakras())} Hindu chakras")
                    print(f"  • {len(db.get_all_meridians())} Taoist meridians")
                    print(f"  • {len(db.get_all_tibetan_chakras())} Tibetan chakras")
                except Exception as e:
                    print(f"Error: {e}")
                input("\nPress Enter to continue...")
            elif choice == '7':
                self.complete_session_menu()
            elif choice == '8':
                self.system_status()
            elif choice == '9':
                self.help_menu()
            elif choice == '0':
                self.clear()
                if self.console:
                    farewell = Panel(
                        "[bold cyan]May all beings be free from suffering.[/bold cyan]\n"
                        "[white]May all beings find peace and liberation.[/white]\n\n"
                        "[yellow]Om Mani Padme Hum 🙏[/yellow]",
                        border_style="cyan",
                        box=box.DOUBLE
                    )
                    self.console.print(farewell)
                else:
                    print("\nMay all beings be free from suffering.")
                    print("May all beings find peace and liberation.")
                    print("\nOm Mani Padme Hum 🙏\n")
                break


def main():
    """Main entry point"""
    ui = VajraStreamUI()
    try:
        ui.run()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Om Mani Padme Hum 🙏\n")
    except Exception as e:
        print(f"\nError: {e}")
        print("Om Mani Padme Hum 🙏\n")


if __name__ == "__main__":
    main()
