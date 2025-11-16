#!/usr/bin/env python3
"""
Compassionate Blessing Manager CLI

Command-line tool for managing blessing targets and dedicating
mantras/prayers to marginalized and suffering beings.

Usage examples:
    # Add a blessing target
    python blessing_manager.py add \
        --name "Missing Person #12345" \
        --category missing_person \
        --lat 40.7 --lon -74.0 \
        --date "2020-06-15 14:30" \
        --description "Missing since June 2020" \
        --priority 8

    # List all targets
    python blessing_manager.py list

    # List by category
    python blessing_manager.py list --category shelter_animal

    # Dedicate mantras
    python blessing_manager.py dedicate \
        --mantras 10000 \
        --mantra-type om_mani_padme_hum \
        --allocation equitable

    # Broadcast blessings to all targets
    python blessing_manager.py broadcast \
        --duration 600 \
        --mantra-type om_mani_padme_hum

    # Show statistics
    python blessing_manager.py stats

    # Export for visualization
    python blessing_manager.py export --format json
"""

import sys
import os
import argparse
from datetime import datetime
from pathlib import Path
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.compassionate_blessings import (
    BlessingDatabase,
    BlessingTarget,
    BlessingCategory,
    MantraType,
    BlessingAllocator,
    GeoCoordinate,
    BlessingCoordinate,
    create_target
)


class BlessingManagerCLI:
    """Command-line interface for blessing management."""

    def __init__(self):
        """Initialize CLI."""
        self.db = BlessingDatabase()

    def cmd_add(self, args):
        """Add a new blessing target."""
        print(f"\n{'='*70}")
        print(f"ADDING BLESSING TARGET")
        print(f"{'='*70}\n")

        # Parse date if provided
        date = None
        if args.date:
            try:
                date = datetime.fromisoformat(args.date)
            except ValueError:
                print(f"⚠️  Invalid date format: {args.date}")
                print("Use ISO format: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS")
                return

        # Parse location
        location = None
        if args.lat is not None and args.lon is not None:
            location = (args.lat, args.lon)

        # Create target
        category = BlessingCategory(args.category)

        target = create_target(
            name=args.name,
            category=category,
            location=location,
            date=date,
            description=args.description or "",
            priority=args.priority
        )

        # Add to database
        self.db.add_target(target)

        print(f"✅ Added blessing target:")
        print(f"   Name: {target.name}")
        print(f"   Category: {target.category.value}")
        print(f"   Identifier: {target.identifier}")
        if location:
            print(f"   Location: {location[0]:.4f}°N, {location[1]:.4f}°E")
        if date:
            print(f"   Date: {date}")
        print(f"   Priority: {target.priority}")
        print(f"\n{'='*70}\n")

    def cmd_list(self, args):
        """List blessing targets."""
        print(f"\n{'='*70}")
        print(f"BLESSING TARGETS")
        print(f"{'='*70}\n")

        # Get targets
        if args.category:
            category = BlessingCategory(args.category)
            targets = self.db.get_targets_by_category(category)
            print(f"Category: {category.value}")
        else:
            targets = self.db.get_all_targets()
            print("All categories")

        print(f"Total: {len(targets)} targets\n")

        if not targets:
            print("No targets found.")
            return

        # Display
        for i, target in enumerate(targets, 1):
            print(f"{i}. {target.name or 'Unknown'}")
            print(f"   ID: {target.identifier}")
            print(f"   Category: {target.category.value}")

            if target.description:
                print(f"   Description: {target.description}")

            if target.coordinates and target.coordinates.location:
                loc = target.coordinates.location
                print(f"   Location: {loc.latitude:.4f}°N, {loc.longitude:.4f}°E")
                if loc.location_name:
                    print(f"   Place: {loc.location_name}")

            if target.relevant_date:
                print(f"   Date: {target.relevant_date}")

            print(f"   Mantras dedicated: {target.mantras_dedicated}")
            print(f"   Prayer wheel rotations: {target.prayer_wheel_rotations}")
            print(f"   Priority: {target.priority}")

            if args.verbose:
                print(f"   Intention: {target.intention}")
                print(f"   Sessions: {len(target.dedication_sessions)}")
                if target.dedication_sessions:
                    last_session = target.dedication_sessions[-1]
                    print(f"   Last dedication: {last_session}")

            print()

        print(f"{'='*70}\n")

    def cmd_dedicate(self, args):
        """Dedicate mantras to blessing targets."""
        print(f"\n{'='*70}")
        print(f"MANTRA DEDICATION")
        print(f"{'='*70}\n")

        # Get targets
        if args.category:
            category = BlessingCategory(args.category)
            targets = self.db.get_targets_by_category(category)
            print(f"Dedicating to category: {category.value}")
        elif args.identifier:
            target = self.db.get_target(args.identifier)
            targets = [target] if target else []
            print(f"Dedicating to target: {args.identifier}")
        else:
            targets = self.db.get_all_targets()
            print("Dedicating to all targets")

        if not targets:
            print("⚠️  No targets found.")
            return

        print(f"Total targets: {len(targets)}")
        print(f"Total mantras: {args.mantras}")
        print(f"Mantra type: {args.mantra_type}")
        print(f"Allocation method: {args.allocation}\n")

        # Allocate mantras
        if args.allocation == "equitable":
            allocation = BlessingAllocator.allocate_equitable(args.mantras, targets)
        elif args.allocation == "urgent":
            allocation = BlessingAllocator.allocate_urgent(args.mantras, targets)
        elif args.allocation == "weighted":
            allocation = BlessingAllocator.allocate_weighted(args.mantras, targets)
        else:
            allocation = BlessingAllocator.allocate_equitable(args.mantras, targets)

        # Record session
        session_id = self.db.record_session(
            mantra_type=args.mantra_type,
            total_mantras=args.mantras,
            total_rotations=args.rotations,
            targets_blessed=len(allocation),
            allocation_method=args.allocation,
            notes=args.notes or ""
        )

        print(f"Session ID: {session_id}\n")
        print("Allocation:")
        print("-" * 70)

        # Record dedications
        for target_id, count in allocation.items():
            target = self.db.get_target(target_id)
            if not target:
                continue

            self.db.record_dedication(
                target_identifier=target_id,
                session_id=session_id,
                mantra_type=args.mantra_type,
                mantras_count=count,
                dedicator=args.dedicator or "Practitioner",
                notes=""
            )

            print(f"{target.name or target.identifier}: {count} mantras")

        print()
        print("✅ Dedication complete!")
        print(f"\n{'='*70}")
        print("DEDICATION PRAYER")
        print(f"{'='*70}\n")

        print(self._generate_dedication_prayer(
            targets=targets,
            mantras=args.mantras,
            mantra_type=args.mantra_type
        ))

        print(f"\n{'='*70}\n")

    def cmd_stats(self, args):
        """Show blessing statistics."""
        print(f"\n{'='*70}")
        print(f"BLESSING STATISTICS")
        print(f"{'='*70}\n")

        stats = self.db.get_statistics()

        print(f"Total blessing targets: {stats['total_targets']}")
        print(f"Total mantras dedicated: {stats['total_mantras_dedicated']:,}")
        print(f"Total prayer wheel rotations: {stats['total_prayer_wheel_rotations']:,}")
        print(f"Total dedication sessions: {stats['total_sessions']}\n")

        print("Targets by category:")
        print("-" * 70)
        for category, count in stats['by_category'].items():
            print(f"  {category:30s}: {count:6d}")

        print(f"\n{'='*70}\n")

    def cmd_broadcast(self, args):
        """Broadcast blessings to all targets using radionics."""
        print(f"\n{'='*70}")
        print(f"COMPASSIONATE RADIONICS BROADCASTING")
        print(f"{'='*70}\n")

        # Get targets
        if args.category:
            category = BlessingCategory(args.category)
            targets = self.db.get_targets_by_category(category)
        else:
            targets = self.db.get_all_targets()

        if not targets:
            print("⚠️  No targets found.")
            return

        print(f"Broadcasting to {len(targets)} beings")
        print(f"Duration: {args.duration} seconds ({args.duration/60:.1f} minutes)")
        print(f"Mantra type: {args.mantra_type}\n")

        # Import radionics operation
        try:
            from scripts.radionics_operation import RadionicsOperation
        except ImportError:
            print("⚠️  Radionics system not available")
            return

        # Initialize radionics
        ops = RadionicsOperation()

        # Create combined intention
        intention = self._generate_broadcast_intention(targets, args.mantra_type)

        print("Broadcasting intention:")
        print("-" * 70)
        print(intention)
        print("-" * 70 + "\n")

        # Broadcast
        ops.broadcast_intention(
            intention=intention,
            duration=args.duration,
            with_astrology=True,
            with_prayer=True,
            with_audio=not args.no_audio,
            with_visuals=not args.no_visuals
        )

        # Record as blessing session
        session_id = self.db.record_session(
            mantra_type=args.mantra_type,
            total_mantras=0,  # Counted by broadcast duration
            total_rotations=0,
            targets_blessed=len(targets),
            allocation_method="broadcast",
            notes=f"Radionics broadcast, {args.duration}s"
        )

        print(f"\n✅ Broadcasting complete (Session ID: {session_id})")
        print(f"{'='*70}\n")

    def cmd_export(self, args):
        """Export blessing data."""
        print(f"\n{'='*70}")
        print(f"EXPORTING BLESSING DATA")
        print(f"{'='*70}\n")

        targets = self.db.get_all_targets()

        if args.format == "json":
            data = {
                'targets': [t.to_dict() for t in targets],
                'exported_at': datetime.now().isoformat(),
                'statistics': self.db.get_statistics()
            }

            output_file = args.output or "blessing_export.json"
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)

            print(f"✅ Exported {len(targets)} targets to {output_file}")

        elif args.format == "csv":
            import csv

            output_file = args.output or "blessing_export.csv"
            with open(output_file, 'w', newline='') as f:
                writer = csv.writer(f)

                # Header
                writer.writerow([
                    'Identifier', 'Name', 'Category', 'Description',
                    'Latitude', 'Longitude', 'Date', 'Mantras',
                    'Rotations', 'Priority'
                ])

                # Data
                for target in targets:
                    lat = target.coordinates.location.latitude if target.coordinates and target.coordinates.location else ''
                    lon = target.coordinates.location.longitude if target.coordinates and target.coordinates.location else ''
                    date = target.relevant_date.isoformat() if target.relevant_date else ''

                    writer.writerow([
                        target.identifier,
                        target.name or '',
                        target.category.value,
                        target.description,
                        lat,
                        lon,
                        date,
                        target.mantras_dedicated,
                        target.prayer_wheel_rotations,
                        target.priority
                    ])

            print(f"✅ Exported {len(targets)} targets to {output_file}")

        print(f"\n{'='*70}\n")

    def _generate_dedication_prayer(self, targets: list, mantras: int, mantra_type: str) -> str:
        """Generate dedication prayer text."""
        # Count categories
        categories = {}
        for target in targets:
            cat = target.category.value
            categories[cat] = categories.get(cat, 0) + 1

        # Mantra name
        mantra_names = {
            'om_mani_padme_hum': 'OM MANI PADME HUM (Chenrezig)',
            'bekandze': 'Medicine Buddha mantra',
            'om_tare_tuttare': 'OM TARE TUTTARE TURE SOHA (Green Tara)',
            'vajrasattva_100': 'Vajrasattva 100-syllable mantra',
            'om_ami_dewa_hri': 'OM AMI DEWA HRI (Amitabha)'
        }

        mantra_display = mantra_names.get(mantra_type, mantra_type)

        prayer = f"""By the merit of reciting {mantras:,} {mantra_display},
and through the power of compassion and wisdom,

May the {len(targets)} beings represented in this sacred database—
"""

        # List categories
        for cat, count in categories.items():
            prayer += f"  {count} {cat.replace('_', ' ')},\n"

        prayer += f"""
whose names are known to the Buddhas even if unknown to the world—
receive these blessings.

May those missing be found,
May those unidentified be recognized,
May those suffering find relief,
May those forgotten be remembered,
May those in transition find peaceful liberation.

May this work ripen as the cause for their ultimate enlightenment
and the enlightenment of all beings.

Gate gate pāragate pārasaṃgate bodhi svāhā
"""

        return prayer

    def _generate_broadcast_intention(self, targets: list, mantra_type: str) -> str:
        """Generate intention for radionics broadcasting."""
        categories = set(t.category.value for t in targets)
        cat_list = ", ".join(c.replace('_', ' ') for c in categories)

        return f"""Compassionate healing and liberation for {len(targets)} beings:
{cat_list}.

Through the power of {mantra_type.replace('_', ' ')},
may healing reach all who suffer,
may all who are lost be found,
may all who are forgotten be remembered,
may all beings be free from suffering and the causes of suffering.

Om Mani Padme Hum"""


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Compassionate Blessing Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add a missing person
  %(prog)s add --name "Case #12345" --category missing_person \\
    --lat 40.7 --lon -74.0 --date "2020-06-15" --priority 8

  # Add a shelter animal
  %(prog)s add --name "Max - Dog #A789" --category shelter_animal \\
    --lat 34.05 --lon -118.24 --date "2024-12-01" --priority 6

  # List all targets
  %(prog)s list

  # Dedicate 10,000 mantras
  %(prog)s dedicate --mantras 10000 --mantra-type om_mani_padme_hum

  # Broadcast to all
  %(prog)s broadcast --duration 600

  # Show statistics
  %(prog)s stats

  # Export data
  %(prog)s export --format json --output blessings.json
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Add command
    p_add = subparsers.add_parser('add', help='Add a blessing target')
    p_add.add_argument('--name', required=True, help='Name (or identifier)')
    p_add.add_argument('--category', required=True,
                      choices=[c.value for c in BlessingCategory],
                      help='Category of being')
    p_add.add_argument('--lat', type=float, help='Latitude')
    p_add.add_argument('--lon', type=float, help='Longitude')
    p_add.add_argument('--date', help='Date (ISO format: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)')
    p_add.add_argument('--description', help='Description')
    p_add.add_argument('--priority', type=int, default=5,
                      help='Priority (1-10, 10 highest, default 5)')

    # List command
    p_list = subparsers.add_parser('list', help='List blessing targets')
    p_list.add_argument('--category', choices=[c.value for c in BlessingCategory],
                       help='Filter by category')
    p_list.add_argument('--verbose', '-v', action='store_true',
                       help='Show detailed information')

    # Dedicate command
    p_dedicate = subparsers.add_parser('dedicate', help='Dedicate mantras')
    p_dedicate.add_argument('--mantras', type=int, required=True,
                           help='Number of mantras to dedicate')
    p_dedicate.add_argument('--mantra-type', default='om_mani_padme_hum',
                           choices=[m.value for m in MantraType],
                           help='Type of mantra')
    p_dedicate.add_argument('--rotations', type=int, default=0,
                           help='Prayer wheel rotations')
    p_dedicate.add_argument('--allocation', default='equitable',
                           choices=['equitable', 'urgent', 'weighted'],
                           help='Allocation method')
    p_dedicate.add_argument('--category', choices=[c.value for c in BlessingCategory],
                           help='Dedicate only to specific category')
    p_dedicate.add_argument('--identifier', help='Dedicate to specific target')
    p_dedicate.add_argument('--dedicator', default='Practitioner',
                           help='Name of person dedicating')
    p_dedicate.add_argument('--notes', help='Session notes')

    # Stats command
    p_stats = subparsers.add_parser('stats', help='Show statistics')

    # Broadcast command
    p_broadcast = subparsers.add_parser('broadcast', help='Broadcast blessings')
    p_broadcast.add_argument('--duration', type=int, default=600,
                            help='Duration in seconds (default 600 = 10 min)')
    p_broadcast.add_argument('--mantra-type', default='om_mani_padme_hum',
                            help='Mantra type for intention')
    p_broadcast.add_argument('--category', choices=[c.value for c in BlessingCategory],
                            help='Broadcast only to specific category')
    p_broadcast.add_argument('--no-audio', action='store_true',
                            help='Silent mode')
    p_broadcast.add_argument('--no-visuals', action='store_true',
                            help='No visual generation')

    # Export command
    p_export = subparsers.add_parser('export', help='Export blessing data')
    p_export.add_argument('--format', choices=['json', 'csv'], default='json',
                         help='Export format')
    p_export.add_argument('--output', '-o', help='Output file path')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Initialize CLI
    cli = BlessingManagerCLI()

    # Dispatch to command handler
    handler = getattr(cli, f'cmd_{args.command}', None)
    if handler:
        try:
            handler(args)
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return 1
    else:
        print(f"Unknown command: {args.command}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
