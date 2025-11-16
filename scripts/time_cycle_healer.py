#!/usr/bin/env python3
"""
Time Cycle Healer - CLI for Running Historical Healing Cycles

Easy-to-use command-line tool for sending blessings and healing
to historical periods of mass suffering.

Usage:
    python time_cycle_healer.py --list
    python time_cycle_healer.py --event holocaust --days 7
    python time_cycle_healer.py --event cambodian_genocide --full-cycle
    python time_cycle_healer.py --event rwandan_genocide --test
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.time_cycle_broadcaster import (
    TimeCycleBroadcaster,
    list_all_events,
    run_quick_test
)


class TimeCycleHealerCLI:
    """Command-line interface for time cycle healing"""

    def __init__(self):
        self.broadcaster = TimeCycleBroadcaster()

    def cmd_list(self, args):
        """List all available events"""
        list_all_events()

    def cmd_info(self, args):
        """Show detailed info about an event"""
        event = self.broadcaster.get_event_by_id(args.event)
        if not event:
            print(f"❌ Event not found: {args.event}")
            return

        print(f"\n{'='*70}")
        print(f"{event['name'].upper()}")
        print(f"{'='*70}\n")

        print(f"Period: {event['start_date']} to {event['end_date']}")
        print(f"Estimated Deaths: {event['estimated_deaths']:,}")
        print(f"Population Affected: {event['population_affected']}")
        print(f"\nDescription:")
        print(f"  {event['description']}")
        print(f"\nBlessing Focus:")
        print(f"  {event['blessing_focus']}")
        print(f"\nPrimary Locations:")
        for loc in event['primary_locations']:
            print(f"  • {loc['name']}, {loc['country']}")
            print(f"    Coordinates: {loc['lat']}, {loc['lon']}")

        if event.get('special_dates'):
            print(f"\nSpecial Dates:")
            for special in event['special_dates']:
                print(f"  • {special['date']}: {special['name']}")
                if 'deaths' in special:
                    print(f"    Deaths: {special['deaths']:,}")

        print(f"\nRecommended Mantras:")
        for mantra in event.get('mantras', []):
            print(f"  • {mantra}")

        print(f"\nVisualization Themes:")
        for theme in event.get('visualization_themes', []):
            print(f"  • {theme}")

        print(f"\nDaily Cycle Suggestion:")
        print(f"  {event.get('daily_cycle_suggestion', 'N/A')}")

        print(f"\n{'='*70}\n")

    def cmd_test(self, args):
        """Run a quick test cycle"""
        event_id = args.event
        num_days = args.days if args.days else 3

        print(f"\n🧪 Running test cycle for {event_id} ({num_days} days)\n")

        run_quick_test(event_id=event_id, num_days=num_days)

    def cmd_run(self, args):
        """Run a healing cycle"""
        event_id = args.event

        if args.full_cycle:
            # Run the entire period
            print(f"\n⚠️  WARNING: Running full cycle can take considerable time!")
            event = self.broadcaster.get_event_by_id(event_id)
            if event:
                dates = self.broadcaster.generate_date_range(
                    event['start_date'],
                    event['end_date']
                )
                print(f"This will process {len(dates)} days.")

                confirm = input("Continue? (yes/no): ")
                if confirm.lower() != 'yes':
                    print("Cancelled.")
                    return

                max_days = None
            else:
                print(f"❌ Event not found: {event_id}")
                return
        else:
            max_days = args.days if args.days else 7

        # Run the cycle
        results = self.broadcaster.run_daily_cycle(
            event_id=event_id,
            max_days=max_days,
            duration_per_day=args.duration,
            create_visualizations=not args.no_viz,
            viz_output_dir=args.viz_dir
        )

        print(f"\n✅ Cycle complete! Processed {len(results)} days.")

        if not args.no_viz:
            viz_dir = args.viz_dir or "/tmp/time_cycle_visualizations"
            print(f"\n🎨 Visualizations saved to: {viz_dir}")

    def run(self):
        """Main entry point"""
        parser = argparse.ArgumentParser(
            description="Time Cycle Healer - Send blessings to historical periods of suffering",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # List all available events
  %(prog)s --list

  # Get detailed info about an event
  %(prog)s --info --event holocaust

  # Run a quick 3-day test
  %(prog)s --test --event rwandan_genocide

  # Run a 7-day healing cycle
  %(prog)s --run --event cambodian_genocide --days 7

  # Run full cycle (WARNING: can be very long!)
  %(prog)s --run --event holocaust --full-cycle

  # Run without creating visualizations
  %(prog)s --run --event wwi --days 10 --no-viz

May all beings be free from suffering.
Om Mani Padme Hum 🙏
            """
        )

        # Commands
        parser.add_argument('--list', action='store_true',
                          help='List all available events')
        parser.add_argument('--info', action='store_true',
                          help='Show detailed info about an event')
        parser.add_argument('--test', action='store_true',
                          help='Run a quick test cycle (3 days)')
        parser.add_argument('--run', action='store_true',
                          help='Run a healing cycle')

        # Event selection
        parser.add_argument('--event', type=str,
                          help='Event ID (e.g., holocaust, rwandan_genocide)')

        # Cycle parameters
        parser.add_argument('--days', type=int,
                          help='Number of days to process (default: 7)')
        parser.add_argument('--full-cycle', action='store_true',
                          help='Run entire period (WARNING: can be very long!)')
        parser.add_argument('--duration', type=int, default=60,
                          help='Seconds per day broadcast (default: 60)')

        # Visualization
        parser.add_argument('--no-viz', action='store_true',
                          help='Skip creating visualizations')
        parser.add_argument('--viz-dir', type=str,
                          help='Directory for visualizations (default: /tmp/time_cycle_visualizations)')

        args = parser.parse_args()

        # Route to appropriate command
        if args.list:
            self.cmd_list(args)
        elif args.info:
            if not args.event:
                print("❌ --event required with --info")
                parser.print_help()
            else:
                self.cmd_info(args)
        elif args.test:
            if not args.event:
                print("❌ --event required with --test")
                parser.print_help()
            else:
                self.cmd_test(args)
        elif args.run:
            if not args.event:
                print("❌ --event required with --run")
                parser.print_help()
            else:
                self.cmd_run(args)
        else:
            parser.print_help()


if __name__ == "__main__":
    cli = TimeCycleHealerCLI()
    cli.run()
