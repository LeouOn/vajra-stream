#!/usr/bin/env python3
"""
TTS Narrator - CLI for Text-to-Speech Integration

Generate spoken narrations for blessing stories, mantras, meditations,
and historical commemoration.

Usage:
    python tts_narrator.py --story path/to/story.txt --output blessing.mp3
    python tts_narrator.py --mantra "Om Mani Padme Hum" --count 108
    python tts_narrator.py --meditate --chakra sahasrara --duration 10
    python tts_narrator.py --commemorate --event holocaust --date 1945-01-27
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.tts_integration import (
    TTSNarrator,
    quick_narrate
)
from core.blessing_narratives import StoryGenerator, NarrativeType, PureLandTradition
from core.time_cycle_broadcaster import TimeCycleBroadcaster


class TTSNarratorCLI:
    """Command-line interface for TTS narration"""

    def __init__(self):
        self.narrator = TTSNarrator()

    def cmd_story(self, args):
        """Narrate a blessing story"""
        if args.story_file:
            # Read story from file
            story_path = Path(args.story_file)
            if not story_path.exists():
                print(f"❌ Story file not found: {args.story_file}")
                return

            with open(story_path, 'r') as f:
                text = f.read()

            # Simple story object
            class SimpleStory:
                def __init__(self, text):
                    self.title = "Blessing Story"
                    self.narrative_text = text

            story = SimpleStory(text)

        elif args.generate:
            # Generate a new story
            generator = StoryGenerator()

            # Parse narrative type
            try:
                narrative_type = NarrativeType(args.type or "pure_land_arrival")
            except ValueError:
                print(f"❌ Invalid narrative type: {args.type}")
                print(f"Available types: {[t.value for t in NarrativeType]}")
                return

            # Parse pure land
            try:
                pure_land = PureLandTradition(args.pure_land or "universal_light")
            except ValueError:
                print(f"❌ Invalid pure land: {args.pure_land}")
                print(f"Available pure lands: {[p.value for p in PureLandTradition]}")
                return

            print(f"\n📖 Generating {narrative_type.value} story...")
            print(f"   Pure Land: {pure_land.value}")
            print(f"   Target: {args.name or 'Unknown Soul'}")

            story = generator.generate_story(
                target_name=args.name or "Unknown Soul",
                narrative_type=narrative_type,
                pure_land=pure_land,
                custom_context=args.context or ""
            )

            print(f"✅ Story generated: {story.title}")

        else:
            print("❌ Either --story-file or --generate required")
            return

        # Generate audio
        output_file = args.output or "/tmp/blessing_story.mp3"

        print(f"\n🎙️  Narrating story...")
        print(f"   Engine: {self.narrator.engine.__class__.__name__}")
        print(f"   Output: {output_file}")

        result = self.narrator.narrate_story(story, output_file)

        print(f"\n✅ Audio generated: {result}")
        print(f"   Duration: Story narration complete")

    def cmd_mantra(self, args):
        """Generate mantra repetition audio"""
        mantra = args.mantra
        count = args.count or 108
        output_file = args.output or f"/tmp/mantra_{count}.mp3"

        print(f"\n🕉️  Generating mantra repetition audio...")
        print(f"   Mantra: {mantra}")
        print(f"   Count: {count}")
        print(f"   Output: {output_file}")

        result = self.narrator.generate_mantra_audio(
            mantra=mantra,
            repetitions=count,
            output_file=output_file,
            pause_seconds=args.pause or 2.0
        )

        print(f"\n✅ Audio generated: {result}")
        print(f"   Total repetitions: {count}")

    def cmd_meditate(self, args):
        """Generate guided meditation audio"""
        if args.chakra:
            # Chakra meditation script
            chakra_info = {
                'muladhara': ('Root', 'Earth', 'grounding and stability'),
                'svadhisthana': ('Sacral', 'Water', 'creativity and pleasure'),
                'manipura': ('Solar Plexus', 'Fire', 'power and transformation'),
                'anahata': ('Heart', 'Air', 'love and compassion'),
                'vishuddha': ('Throat', 'Sound', 'truth and expression'),
                'ajna': ('Third Eye', 'Light', 'intuition and wisdom'),
                'sahasrara': ('Crown', 'Consciousness', 'unity and enlightenment')
            }

            if args.chakra not in chakra_info:
                print(f"❌ Unknown chakra: {args.chakra}")
                print(f"Available: {list(chakra_info.keys())}")
                return

            name, element, quality = chakra_info[args.chakra]

            script = f"""
            Welcome to this {name} chakra meditation.

            Find a comfortable seated position. Close your eyes and take three deep breaths.

            Bring your attention to the {name} chakra, associated with the element of {element}.

            This energy center governs {quality}.

            As you breathe, visualize healing light filling this chakra.

            With each breath, the light grows brighter and more vibrant.

            Any blockages or tensions dissolve in this healing light.

            Feel the energy flowing freely through this center.

            {name} chakra awakened. {name} chakra balanced. {name} chakra radiant.

            Continue breathing into this space for {args.duration or 5} more minutes.

            When you're ready, slowly open your eyes.

            May this practice bring you peace and healing.
            """

        elif args.script:
            # Load custom script
            script_path = Path(args.script)
            if not script_path.exists():
                print(f"❌ Script file not found: {args.script}")
                return

            with open(script_path, 'r') as f:
                script = f.read()

        else:
            # Default meditation
            script = """
            Welcome to this meditation.

            Find a comfortable position and close your eyes.

            Take three deep breaths. Breathe in peace. Breathe out tension.

            Bring your awareness to the present moment.

            Let thoughts come and go like clouds in the sky.

            Rest in spacious awareness.

            May all beings be happy. May all beings be free from suffering.

            Om Mani Padme Hum.

            When you're ready, slowly open your eyes.
            """

        output_file = args.output or "/tmp/meditation.mp3"

        print(f"\n🧘 Generating guided meditation...")
        print(f"   Output: {output_file}")

        result = self.narrator.guided_meditation(
            script=script,
            output_file=output_file
        )

        print(f"\n✅ Audio generated: {result}")

    def cmd_commemorate(self, args):
        """Generate historical commemoration narration"""
        if not args.event:
            print("❌ --event required")
            return

        broadcaster = TimeCycleBroadcaster()
        event = broadcaster.get_event_by_id(args.event)

        if not event:
            print(f"❌ Event not found: {args.event}")
            return

        # Parse date
        if args.date:
            try:
                date = datetime.strptime(args.date, "%Y-%m-%d")
            except ValueError:
                print(f"❌ Invalid date format: {args.date} (use YYYY-MM-DD)")
                return
        else:
            # Use start date
            date = datetime.strptime(event['start_date'], "%Y-%m-%d")

        output_file = args.output or f"/tmp/commemorate_{args.event}_{date.strftime('%Y%m%d')}.mp3"

        print(f"\n🕊️  Generating commemoration narration...")
        print(f"   Event: {event['name']}")
        print(f"   Date: {date.strftime('%B %d, %Y')}")
        print(f"   Output: {output_file}")

        result = self.narrator.commemorate_event(
            event=event,
            date=date,
            output_file=output_file
        )

        print(f"\n✅ Audio generated: {result}")

    def cmd_quick(self, args):
        """Quick text-to-speech generation"""
        if args.text:
            text = args.text
        elif args.file:
            text_path = Path(args.file)
            if not text_path.exists():
                print(f"❌ File not found: {args.file}")
                return
            with open(text_path, 'r') as f:
                text = f.read()
        else:
            print("❌ Either --text or --file required")
            return

        output_file = args.output or "/tmp/tts_output.mp3"

        print(f"\n🎙️  Generating audio...")
        print(f"   Text length: {len(text)} characters")
        print(f"   Output: {output_file}")

        result = quick_narrate(text, output_file)

        print(f"\n✅ Audio generated: {result}")

    def run(self):
        """Main entry point"""
        parser = argparse.ArgumentParser(
            description="TTS Narrator - Generate spoken blessings and meditations",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Narrate a story from file
  %(prog)s --story path/to/story.txt --output blessing.mp3

  # Generate and narrate a new story
  %(prog)s --generate --type hell_liberation --name "Lost Soul" --output liberation.mp3

  # Generate mantra repetition
  %(prog)s --mantra "Om Mani Padme Hum" --count 108 --output mantra108.mp3

  # Generate chakra meditation
  %(prog)s --meditate --chakra sahasrara --duration 10 --output crown_meditation.mp3

  # Commemorate historical event
  %(prog)s --commemorate --event holocaust --date 1945-01-27 --output liberation_auschwitz.mp3

  # Quick TTS
  %(prog)s --quick --text "May all beings be free from suffering" --output blessing.mp3

May these voices carry blessings to all beings! 🙏
            """
        )

        # Command modes
        mode_group = parser.add_mutually_exclusive_group(required=True)
        mode_group.add_argument('--story', dest='story_file',
                              help='Narrate story from file')
        mode_group.add_argument('--generate', action='store_true',
                              help='Generate and narrate new story')
        mode_group.add_argument('--mantra', type=str,
                              help='Generate mantra repetition')
        mode_group.add_argument('--meditate', action='store_true',
                              help='Generate guided meditation')
        mode_group.add_argument('--commemorate', action='store_true',
                              help='Generate historical commemoration')
        mode_group.add_argument('--quick', action='store_true',
                              help='Quick TTS from text or file')

        # Story generation options
        parser.add_argument('--type', type=str,
                          help='Story narrative type (for --generate)')
        parser.add_argument('--pure-land', type=str,
                          help='Pure land tradition (for --generate)')
        parser.add_argument('--name', type=str,
                          help='Target being name (for --generate)')
        parser.add_argument('--context', type=str,
                          help='Additional context (for --generate)')

        # Mantra options
        parser.add_argument('--count', type=int,
                          help='Mantra repetition count (default: 108)')
        parser.add_argument('--pause', type=float,
                          help='Pause between mantras in seconds (default: 2.0)')

        # Meditation options
        parser.add_argument('--chakra', type=str,
                          help='Chakra for meditation')
        parser.add_argument('--script', type=str,
                          help='Custom meditation script file')
        parser.add_argument('--duration', type=int,
                          help='Meditation duration in minutes')

        # Commemoration options
        parser.add_argument('--event', type=str,
                          help='Historical event ID')
        parser.add_argument('--date', type=str,
                          help='Date (YYYY-MM-DD)')

        # Quick TTS options
        parser.add_argument('--text', type=str,
                          help='Text to speak (for --quick)')
        parser.add_argument('--file', type=str,
                          help='Text file to speak (for --quick)')

        # Common options
        parser.add_argument('--output', '-o', type=str,
                          help='Output audio file path')
        parser.add_argument('--engine', type=str,
                          help='TTS engine to use (pyttsx3, gtts, edge)')
        parser.add_argument('--voice', type=str,
                          help='Voice to use (engine-specific)')

        args = parser.parse_args()

        # Route to appropriate command
        try:
            if args.story_file or args.generate:
                self.cmd_story(args)
            elif args.mantra:
                self.cmd_mantra(args)
            elif args.meditate:
                self.cmd_meditate(args)
            elif args.commemorate:
                self.cmd_commemorate(args)
            elif args.quick:
                self.cmd_quick(args)

        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return 1

        return 0


if __name__ == "__main__":
    cli = TTSNarratorCLI()
    sys.exit(cli.run())
