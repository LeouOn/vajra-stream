#!/usr/bin/env python3
"""
Story Generator - Create Liberation Narratives

Generates blissful stories about:
- Arrivals in pure lands
- Liberation from hell realms and hungry ghost states
- Empowerment of the powerless
- Reconciliation and healing
- Alternate timelines and divine interventions

Usage Examples:
    # Generate a single pure land story
    python story_generator.py --generate --name "Unknown Soul" --type pure_land_arrival

    # Generate stories for all missing persons in the database
    python story_generator.py --batch --category missing_person --type pure_land_arrival --count 10

    # Generate hell liberation story with LLM
    python story_generator.py --generate --name "Suffering Being" --type hell_liberation --use-llm

    # Export a collection of stories
    python story_generator.py --batch --category hungry_ghost --output ./stories --count 20
"""

import sys
import argparse
from pathlib import Path
from typing import List, Optional
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.blessing_narratives import (
    StoryGenerator,
    NarrativeType,
    PureLandTradition,
    GeneratedStory,
    StoryExporter,
    PureLandDescriptions
)

try:
    from core.compassionate_blessings import BlessingDatabase, BlessingCategory
    HAS_BLESSINGS_DB = True
except ImportError:
    HAS_BLESSINGS_DB = False


class StoryGeneratorCLI:
    """Command-line interface for story generation"""

    def __init__(self):
        self.generator = None
        self.db = None if not HAS_BLESSINGS_DB else BlessingDatabase()

    def cmd_generate(self, args):
        """Generate a single story"""
        print("\n" + "="*70)
        print("GENERATING LIBERATION NARRATIVE")
        print("="*70 + "\n")

        # Initialize generator
        self.generator = StoryGenerator(
            use_llm=args.use_llm,
            llm_provider=args.llm_provider
        )

        # Get narrative type
        try:
            narrative_type = NarrativeType(args.type)
        except ValueError:
            print(f"❌ Invalid narrative type: {args.type}")
            print(f"Valid types: {[t.value for t in NarrativeType]}")
            return

        # Get pure land if applicable
        pure_land = PureLandTradition.UNIVERSAL_LIGHT
        if args.pure_land:
            try:
                pure_land = PureLandTradition(args.pure_land)
            except ValueError:
                print(f"❌ Invalid pure land: {args.pure_land}")
                print(f"Valid options: {[p.value for p in PureLandTradition]}")
                return

        # Generate story
        print(f"📖 Generating {narrative_type.value} story for: {args.name}")
        if args.use_llm:
            print(f"🤖 Using LLM: {args.llm_provider}")
        else:
            print("📝 Using templates")

        story = self.generator.generate_story(
            target_name=args.name,
            narrative_type=narrative_type,
            pure_land=pure_land,
            custom_context=args.context or ""
        )

        # Display story
        print("\n" + "="*70)
        print(story.story_text)
        print("="*70 + "\n")

        # Save if requested
        if args.output:
            output_path = Path(args.output)
            if output_path.suffix == '.json':
                StoryExporter.export_as_json(story, str(output_path))
                print(f"💾 Saved as JSON: {output_path}")
            else:
                StoryExporter.export_as_markdown(story, str(output_path))
                print(f"💾 Saved as Markdown: {output_path}")

    def cmd_batch(self, args):
        """Generate batch of stories from database"""
        if not HAS_BLESSINGS_DB:
            print("❌ Blessing database not available. Install dependencies first.")
            return

        print("\n" + "="*70)
        print("BATCH STORY GENERATION")
        print("="*70 + "\n")

        # Initialize generator
        self.generator = StoryGenerator(
            use_llm=args.use_llm,
            llm_provider=args.llm_provider
        )

        # Get narrative type
        try:
            narrative_type = NarrativeType(args.type)
        except ValueError:
            print(f"❌ Invalid narrative type: {args.type}")
            return

        # Get pure land if applicable
        pure_land = PureLandTradition.UNIVERSAL_LIGHT
        if args.pure_land:
            try:
                pure_land = PureLandTradition(args.pure_land)
            except ValueError:
                print(f"❌ Invalid pure land: {args.pure_land}")
                return

        # Get targets from database
        if args.category:
            try:
                category = BlessingCategory(args.category)
                targets = self.db.get_targets_by_category(category)
                print(f"📊 Found {len(targets)} targets in category: {category.value}")
            except ValueError:
                print(f"❌ Invalid category: {args.category}")
                return
        else:
            # Get all targets
            stats = self.db.get_statistics()
            targets = []
            for cat in BlessingCategory:
                targets.extend(self.db.get_targets_by_category(cat))
            print(f"📊 Found {len(targets)} total targets in database")

        if not targets:
            print("❌ No targets found")
            return

        # Limit count
        count = min(args.count, len(targets))
        targets = targets[:count]

        print(f"📖 Generating {count} stories...")
        print(f"Type: {narrative_type.value}")
        if narrative_type == NarrativeType.PURE_LAND_ARRIVAL:
            print(f"Pure Land: {pure_land.value}")
        print()

        # Generate stories
        stories = []
        for i, target in enumerate(targets, 1):
            print(f"  [{i}/{count}] {target.name}...")

            story = self.generator.generate_story(
                target=target,
                narrative_type=narrative_type,
                pure_land=pure_land
            )
            stories.append(story)

        print(f"\n✅ Generated {len(stories)} stories")

        # Export collection
        if args.output:
            output_dir = Path(args.output)
            print(f"\n💾 Exporting collection to: {output_dir}")
            StoryExporter.export_collection(stories, str(output_dir))
            print(f"✅ Exported {len(stories)} stories + index")
        else:
            # Display first story as example
            print("\n" + "="*70)
            print("EXAMPLE STORY (first of collection):")
            print("="*70 + "\n")
            print(stories[0].story_text)
            print("\n" + "="*70)
            print("\nUse --output <directory> to save all stories")

    def cmd_list_types(self, args):
        """List available narrative types and pure lands"""
        print("\n" + "="*70)
        print("AVAILABLE NARRATIVE TYPES")
        print("="*70 + "\n")

        for ntype in NarrativeType:
            print(f"  • {ntype.value}")

        print("\n" + "="*70)
        print("AVAILABLE PURE LAND TRADITIONS")
        print("="*70 + "\n")

        for pland in PureLandTradition:
            desc = PureLandDescriptions.get_description(pland)
            print(f"  • {pland.value}")
            print(f"    {desc['name']}")
            print()

    def cmd_describe_pure_land(self, args):
        """Show detailed description of a pure land"""
        try:
            pure_land = PureLandTradition(args.pure_land)
        except ValueError:
            print(f"❌ Invalid pure land: {args.pure_land}")
            return

        desc = PureLandDescriptions.get_description(pure_land)

        print("\n" + "="*70)
        print(desc['name'].upper())
        print("="*70 + "\n")

        print(desc['description'].strip())

        print("\n" + "-"*70)
        print("ACTIVITIES")
        print("-"*70 + "\n")

        for activity in desc['activities']:
            print(f"  • {activity}")

        print("\n" + "-"*70)
        print("SENSORY EXPERIENCE")
        print("-"*70 + "\n")

        for sense, experience in desc['sensory'].items():
            print(f"  {sense.upper()}: {experience}")

        print("\n" + "="*70 + "\n")

    def cmd_interactive(self, args):
        """Interactive story generation mode"""
        print("\n" + "="*70)
        print("INTERACTIVE STORY GENERATION")
        print("="*70 + "\n")

        # Name
        name = input("Enter being's name (or description): ").strip()
        if not name:
            name = "Unknown Being"

        # Narrative type
        print("\nNarrative Types:")
        types = list(NarrativeType)
        for i, ntype in enumerate(types, 1):
            print(f"  {i}. {ntype.value}")

        type_choice = input("\nSelect type (1-{0}): ".format(len(types))).strip()
        try:
            narrative_type = types[int(type_choice) - 1]
        except (ValueError, IndexError):
            print("Invalid choice. Using pure_land_arrival.")
            narrative_type = NarrativeType.PURE_LAND_ARRIVAL

        # Pure land if applicable
        pure_land = PureLandTradition.UNIVERSAL_LIGHT
        if narrative_type == NarrativeType.PURE_LAND_ARRIVAL:
            print("\nPure Land Traditions:")
            plands = list(PureLandTradition)
            for i, pl in enumerate(plands, 1):
                desc = PureLandDescriptions.get_description(pl)
                print(f"  {i}. {desc['name']}")

            pl_choice = input("\nSelect pure land (1-{0}): ".format(len(plands))).strip()
            try:
                pure_land = plands[int(pl_choice) - 1]
            except (ValueError, IndexError):
                print("Invalid choice. Using Universal Light.")
                pure_land = PureLandTradition.UNIVERSAL_LIGHT

        # LLM option
        use_llm_input = input("\nUse LLM for generation? (y/n, default: n): ").strip().lower()
        use_llm = use_llm_input == 'y'

        # Context
        print("\nOptional context (press Enter to skip):")
        context = input("> ").strip()

        # Generate
        print("\n📖 Generating story...\n")

        self.generator = StoryGenerator(use_llm=use_llm)

        story = self.generator.generate_story(
            target_name=name,
            narrative_type=narrative_type,
            pure_land=pure_land,
            custom_context=context
        )

        # Display
        print("\n" + "="*70)
        print(story.story_text)
        print("="*70 + "\n")

        # Save option
        save = input("Save this story? (y/n): ").strip().lower()
        if save == 'y':
            filename = input("Filename (default: story.md): ").strip()
            if not filename:
                filename = "story.md"

            StoryExporter.export_as_markdown(story, filename)
            print(f"💾 Saved to: {filename}")

    def run(self):
        """Main entry point"""
        parser = argparse.ArgumentParser(
            description="Generate Liberation Narratives",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Generate single story
  %(prog)s --generate --name "Lost Soul" --type pure_land_arrival --pure-land sukhavati

  # Batch generate for missing persons
  %(prog)s --batch --category missing_person --count 10 --output ./stories

  # Interactive mode
  %(prog)s --interactive

  # List available options
  %(prog)s --list-types

  # Describe a pure land
  %(prog)s --describe-pure-land sukhavati
            """
        )

        # Main commands
        parser.add_argument('--generate', action='store_true',
                          help='Generate a single story')
        parser.add_argument('--batch', action='store_true',
                          help='Generate batch of stories from database')
        parser.add_argument('--interactive', action='store_true',
                          help='Interactive story generation mode')
        parser.add_argument('--list-types', action='store_true',
                          help='List available narrative types and pure lands')
        parser.add_argument('--describe-pure-land',
                          help='Show detailed description of a pure land')

        # Story parameters
        parser.add_argument('--name', default='Unknown Being',
                          help='Name of being receiving blessing')
        parser.add_argument('--type', default='pure_land_arrival',
                          help='Type of narrative (default: pure_land_arrival)')
        parser.add_argument('--pure-land', default='universal_light',
                          help='Pure land tradition (default: universal_light)')
        parser.add_argument('--context', help='Additional context for story')

        # Batch parameters
        parser.add_argument('--category',
                          help='Blessing category for batch generation')
        parser.add_argument('--count', type=int, default=10,
                          help='Number of stories to generate (default: 10)')

        # Generation parameters
        parser.add_argument('--use-llm', action='store_true',
                          help='Use LLM for generation (vs templates)')
        parser.add_argument('--llm-provider', default='ollama',
                          help='LLM provider (default: ollama)')

        # Output
        parser.add_argument('--output',
                          help='Output file or directory')

        args = parser.parse_args()

        # Route to appropriate command
        if args.list_types:
            self.cmd_list_types(args)
        elif args.describe_pure_land:
            self.cmd_describe_pure_land(args)
        elif args.interactive:
            self.cmd_interactive(args)
        elif args.batch:
            self.cmd_batch(args)
        elif args.generate:
            self.cmd_generate(args)
        else:
            parser.print_help()


if __name__ == "__main__":
    cli = StoryGeneratorCLI()
    cli.run()
