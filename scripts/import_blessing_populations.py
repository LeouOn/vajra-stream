#!/usr/bin/env python3
"""
Import Blessing Populations

Loads pre-defined blessing populations from JSON files into the database.

Usage:
    # Import all populations
    python import_blessing_populations.py --all

    # Import specific population
    python import_blessing_populations.py --file universal_compassion.json

    # Import with custom priority override
    python import_blessing_populations.py --file animals.json --priority 9
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.compassionate_blessings import (
    BlessingDatabase,
    BlessingTarget,
    BlessingCategory,
    create_target
)


def import_population_file(filepath: Path, db: BlessingDatabase, priority_override: int = None):
    """Import blessing targets from a JSON file."""
    print(f"\n📖 Loading: {filepath.name}")
    print("-" * 70)

    with open(filepath, 'r') as f:
        data = json.load(f)

    description = data.get('description', '')
    note = data.get('note', '')

    print(f"Description: {description}")
    if note:
        print(f"Note: {note}")

    targets = data.get('targets', [])
    print(f"Targets: {len(targets)}\n")

    imported = 0
    for target_data in targets:
        try:
            # Parse category
            category = BlessingCategory(target_data['category'])

            # Parse location if present
            location = None
            if 'latitude' in target_data and 'longitude' in target_data:
                location = (target_data['latitude'], target_data['longitude'])

            # Parse date if present
            date = None
            if 'relevant_date' in target_data:
                date = datetime.fromisoformat(target_data['relevant_date'])

            # Use priority override or target priority or default
            priority = priority_override or target_data.get('priority', 5)

            # Create target
            target = create_target(
                name=target_data['name'],
                category=category,
                location=location,
                date=date,
                description=target_data.get('description', ''),
                priority=priority
            )

            # Set intention if provided
            if 'intention' in target_data:
                target.intention = target_data['intention']

            # Set additional data
            if 'additional_data' in target_data:
                target.additional_data = target_data['additional_data']

            # Add to database
            db.add_target(target)
            imported += 1

            print(f"  ✓ {target.name}")

        except Exception as e:
            print(f"  ✗ Error importing {target_data.get('name', 'unknown')}: {e}")

    print(f"\n✅ Imported {imported}/{len(targets)} targets from {filepath.name}")
    return imported


def main():
    parser = argparse.ArgumentParser(
        description="Import Blessing Populations from JSON files"
    )

    parser.add_argument('--all', action='store_true',
                       help='Import all population files')
    parser.add_argument('--file', help='Import specific file')
    parser.add_argument('--priority', type=int,
                       help='Override priority for all imported targets')
    parser.add_argument('--clear', action='store_true',
                       help='Clear existing targets before importing (CAUTION!)')

    args = parser.parse_args()

    # Initialize database
    db = BlessingDatabase()

    # Clear if requested
    if args.clear:
        response = input("\n⚠️  WARNING: This will delete ALL existing blessing targets. Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Cancelled.")
            return 0

        # TODO: Implement database clearing
        print("✓ Database cleared")

    # Get populations directory
    pop_dir = Path(__file__).parent.parent / "knowledge" / "blessing_populations"

    if not pop_dir.exists():
        print(f"❌ Error: Populations directory not found: {pop_dir}")
        return 1

    print("\n" + "="*70)
    print("IMPORTING BLESSING POPULATIONS")
    print("="*70)

    total_imported = 0

    if args.all:
        # Import all JSON files
        json_files = sorted(pop_dir.glob("*.json"))

        if not json_files:
            print("No population files found.")
            return 0

        print(f"\nFound {len(json_files)} population files:\n")

        for filepath in json_files:
            imported = import_population_file(filepath, db, args.priority)
            total_imported += imported

    elif args.file:
        # Import specific file
        filepath = pop_dir / args.file
        if not filepath.exists():
            print(f"❌ Error: File not found: {filepath}")
            return 1

        total_imported = import_population_file(filepath, db, args.priority)

    else:
        # Show available files and prompt
        json_files = sorted(pop_dir.glob("*.json"))

        print("\nAvailable population files:")
        print("-" * 70)
        for i, filepath in enumerate(json_files, 1):
            print(f"{i}. {filepath.name}")

        print("\nUse --all to import all, or --file <filename> for specific file")
        return 0

    # Show final statistics
    print("\n" + "="*70)
    print("IMPORT COMPLETE")
    print("="*70)

    print(f"\nTotal targets imported: {total_imported}")

    stats = db.get_statistics()
    print(f"Total targets in database: {stats['total_targets']}")
    print("\nTargets by category:")
    for category, count in stats['by_category'].items():
        print(f"  {category:30s}: {count}")

    print("\n" + "="*70)
    print("DEDICATION PRAYER")
    print("="*70 + "\n")

    print(f"""By adding {total_imported} beings to this sacred database,
may we remember those who are forgotten,
honor those who are unknown,
and hold in our hearts those who suffer.

May this technology serve as a meditation object
reminding us of the vast scope of suffering in the world,
and inspiring us to compassionate action.

May all {stats['total_targets']} beings in this database
receive the light of awareness and compassion,
and may this work ripen as the cause for their liberation
and the liberation of all beings.

Gate gate pāragate pārasaṃgate bodhi svāhā
""")

    print("="*70 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
