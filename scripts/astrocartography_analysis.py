#!/usr/bin/env python3
"""
Astrocartography Analysis CLI

Command-line tool for analyzing planetary influences across different
times and locations throughout history.

Features:
- Calculate astrocartography lines for any date
- Find parans (planetary crossings)
- Compare multiple locations
- Historical chart calculations (13,000 BC - 17,000 AD)
- Local space astrology
- Calendar conversion (Julian/Gregorian)

Usage examples:
    # Calculate lines for a date
    python astrocartography_analysis.py lines 2025 1 1

    # Find parans
    python astrocartography_analysis.py parans 2025 1 1

    # Historical chart
    python astrocartography_analysis.py chart -100 3 15 --lat 41.9 --lon 12.5 --location "Rome"

    # Find power places
    python astrocartography_analysis.py power-places 2025 6 21 --focus benefic

    # Compare locations
    python astrocartography_analysis.py compare 2025 1 1 \
        --location "New York,40.7,-74.0" \
        --location "London,51.5,-0.1" \
        --location "Tokyo,35.7,139.7"

    # Local space from birthplace
    python astrocartography_analysis.py local-space 1990 5 15 --lat 34.05 --lon -118.25

    # Convert calendar
    python astrocartography_analysis.py convert --year -43 --month 3 --day 15 --calendar julian
"""

import sys
import os
import argparse
from datetime import datetime
from pathlib import Path
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.astrocartography import (
    AstrocartographyCalculator,
    CalendarConverter,
    LocalSpaceCalculator,
    HistoricalChartCalculator,
    quick_astrocartography,
    find_power_places
)


class AstrocartographyCLI:
    """Command-line interface for astrocartography analysis."""

    def __init__(self):
        """Initialize CLI."""
        self.astrocarto = AstrocartographyCalculator()
        self.historical = HistoricalChartCalculator()
        self.local_space = LocalSpaceCalculator()

    def cmd_lines(self, args):
        """Calculate astrocartography lines."""
        print(f"\n{'='*80}")
        print(f"ASTROCARTOGRAPHY LINES")
        print(f"{'='*80}")

        date_str = f"{args.year}/{args.month:02d}/{args.day:02d} {args.hour:02d}:{args.minute:02d}"
        print(f"Date/Time: {date_str} UTC")
        print(f"Calendar: {args.calendar}")

        if args.planets:
            planets = args.planets.split(',')
            print(f"Planets: {', '.join(planets)}")
        else:
            planets = None
            print("Planets: All")

        print()

        # Calculate lines
        result = self.astrocarto.calculate_planetary_lines(
            args.year, args.month, args.day,
            args.hour, args.minute, 0,
            planets, args.calendar
        )

        print(f"Julian Day: {result['julian_day']:.2f}")
        print(f"\n{'='*80}")
        print("PLANETARY LINES")
        print(f"{'='*80}\n")

        for planet, lines in result['lines'].items():
            print(f"{planet.upper()}:")
            print(f"{'-'*80}")

            for angle, data in lines.items():
                lon = data['longitude']

                # Convert to degrees East/West
                if lon > 180:
                    lon_str = f"{360-lon:.2f}°W"
                elif lon < 0:
                    lon_str = f"{abs(lon):.2f}°W"
                else:
                    lon_str = f"{lon:.2f}°E"

                print(f"  {angle:3s}: {lon_str:12s} - {data['meaning']}")

            print()

        if args.save:
            self._save_result(result, "lines", f"{args.year}_{args.month}_{args.day}")

    def cmd_parans(self, args):
        """Calculate parans (planetary crossings)."""
        print(f"\n{'='*80}")
        print(f"PARANS - Planetary Crossings")
        print(f"{'='*80}")

        date_str = f"{args.year}/{args.month:02d}/{args.day:02d} {args.hour:02d}:{args.minute:02d}"
        print(f"Date/Time: {date_str} UTC")
        print(f"Calendar: {args.calendar}\n")

        parans = self.astrocarto.calculate_parans(
            args.year, args.month, args.day,
            args.hour, args.minute, args.calendar
        )

        if not parans:
            print("No parans found for this date.")
            return

        print(f"Found {len(parans)} planetary crossings:\n")
        print(f"{'='*80}")

        for i, paran in enumerate(parans, 1):
            lon = paran['longitude']

            if lon > 180:
                lon_str = f"{360-lon:.2f}°W"
            elif lon < 0:
                lon_str = f"{abs(lon):.2f}°W"
            else:
                lon_str = f"{lon:.2f}°E"

            print(f"\n{i}. {paran['description']}")
            print(f"   Longitude: {lon_str}")
            print(f"   Orb: {paran['orb']:.2f}°")
            print(f"   Influence Zone: ~70 miles north/south of crossing")
            print(f"   Energy: {paran['combined_meaning']}")

        print(f"\n{'='*80}")

        if args.save:
            self._save_result(parans, "parans", f"{args.year}_{args.month}_{args.day}")

    def cmd_chart(self, args):
        """Calculate historical chart for a location."""
        print(f"\n{'='*80}")
        print(f"HISTORICAL ASTROLOGICAL CHART")
        print(f"{'='*80}")

        date_str = f"{args.year}/{args.month:02d}/{args.day:02d} {args.hour:02d}:{args.minute:02d}"
        print(f"Date/Time: {date_str} UTC")
        print(f"Location: {args.location} ({args.lat}°N, {args.lon}°E)")
        print(f"Calendar: {args.calendar}\n")

        chart = self.historical.calculate_chart(
            args.year, args.month, args.day,
            args.hour, args.minute, 0,
            args.lat, args.lon,
            args.location, args.calendar
        )

        print(f"Julian Day: {chart['julian_day']:.2f}")
        print(f"\n{'='*80}")
        print("PLANETARY POSITIONS")
        print(f"{'='*80}\n")

        for planet, data in chart['planets'].items():
            retro = " (R)" if data['retrograde'] else ""
            print(f"{planet:12s}: {data['degree']:6.2f}° {data['sign']:12s}{retro}")

        print(f"\n{'='*80}")
        print("HOUSE CUSPS (Placidus)")
        print(f"{'='*80}\n")

        for i, cusp in enumerate(chart['houses']['cusps'][:12], 1):
            print(f"House {i:2d}: {cusp:7.2f}°")

        print(f"\n{'='*80}")
        print("ANGLES")
        print(f"{'='*80}\n")

        angles = chart['houses']['angles']
        print(f"Ascendant:  {angles['ascendant']:7.2f}°")
        print(f"Midheaven:  {angles['mc']:7.2f}°")
        print(f"ARMC:       {angles['armc']:7.2f}°")
        print(f"Vertex:     {angles['vertex']:7.2f}°")

        print(f"\n{'='*80}")

        if args.save:
            self._save_result(chart, "chart", f"{args.location}_{args.year}_{args.month}_{args.day}")

    def cmd_power_places(self, args):
        """Find optimal power places for a date."""
        print(f"\n{'='*80}")
        print(f"POWER PLACES - Optimal Locations")
        print(f"{'='*80}")

        date_str = f"{args.year}/{args.month:02d}/{args.day:02d} {args.hour:02d}:{args.minute:02d}"
        print(f"Date/Time: {date_str} UTC")
        print(f"Focus: {args.focus}\n")

        optimal = self.astrocarto.find_optimal_locations(
            args.year, args.month, args.day,
            args.hour, args.minute,
            calendar_type=args.calendar
        )

        if args.focus == 'benefic':
            optimal = [loc for loc in optimal if loc['planet'] in ['jupiter', 'venus']]
        elif args.focus == 'career':
            optimal = [loc for loc in optimal if loc['planet'] in ['sun', 'saturn', 'jupiter']]
        elif args.focus == 'relationship':
            optimal = [loc for loc in optimal if loc['planet'] in ['venus', 'moon']]

        print(f"Found {len(optimal)} optimal locations:\n")
        print(f"{'='*80}")

        for i, location in enumerate(optimal[:10], 1):  # Top 10
            lon = location['longitude']

            if lon > 180:
                lon_str = f"{360-lon:.2f}°W"
            elif lon < 0:
                lon_str = f"{abs(lon):.2f}°W"
            else:
                lon_str = f"{lon:.2f}°E"

            print(f"\n{i}. {location['planet'].upper()} on {location['angle']}")
            print(f"   Longitude: {lon_str}")
            print(f"   Strength: {location['strength']:.2f}")
            print(f"   {location['meaning']}")

        print(f"\n{'='*80}")

        if args.save:
            self._save_result(optimal, "power_places", f"{args.year}_{args.month}_{args.day}")

    def cmd_compare(self, args):
        """Compare multiple locations for same time."""
        print(f"\n{'='*80}")
        print(f"LOCATION COMPARISON")
        print(f"{'='*80}")

        date_str = f"{args.year}/{args.month:02d}/{args.day:02d} {args.hour:02d}:{args.minute:02d}"
        print(f"Date/Time: {date_str} UTC")
        print(f"Comparing {len(args.locations)} locations\n")

        # Parse location strings: "Name,lat,lon"
        locations = []
        for loc_str in args.locations:
            parts = loc_str.split(',')
            if len(parts) != 3:
                print(f"Error: Invalid location format: {loc_str}")
                print("Format should be: Name,latitude,longitude")
                continue

            locations.append({
                'name': parts[0],
                'latitude': float(parts[1]),
                'longitude': float(parts[2])
            })

        results = self.historical.compare_locations(
            args.year, args.month, args.day,
            args.hour, args.minute,
            locations, args.calendar
        )

        print(f"{'='*80}")

        for loc_name, chart in results['locations'].items():
            print(f"\n{loc_name}")
            print(f"{'-'*80}")

            # Show key planets and angles
            print(f"Sun:        {chart['planets']['sun']['degree']:6.2f}° {chart['planets']['sun']['sign']}")
            print(f"Moon:       {chart['planets']['moon']['degree']:6.2f}° {chart['planets']['moon']['sign']}")
            print(f"Ascendant:  {chart['houses']['angles']['ascendant']:7.2f}°")
            print(f"Midheaven:  {chart['houses']['angles']['mc']:7.2f}°")

        print(f"\n{'='*80}")

        if args.save:
            self._save_result(results, "comparison", f"{args.year}_{args.month}_{args.day}")

    def cmd_local_space(self, args):
        """Calculate local space directions from birthplace."""
        print(f"\n{'='*80}")
        print(f"LOCAL SPACE ASTROLOGY")
        print(f"{'='*80}")

        date_str = f"{args.year}/{args.month:02d}/{args.day:02d} {args.hour:02d}:{args.minute:02d}"
        print(f"Birth Date/Time: {date_str}")
        print(f"Birth Location: ({args.lat}°N, {args.lon}°E)\n")

        result = self.local_space.calculate_local_space(
            args.year, args.month, args.day,
            args.hour, args.minute,
            args.lat, args.lon,
            args.calendar
        )

        print(f"{'='*80}")
        print("PLANETARY DIRECTIONS FROM BIRTHPLACE")
        print(f"{'='*80}\n")

        for planet, data in result['directions'].items():
            print(f"{planet:12s}: {data['direction']:12s} ({data['azimuth']:6.1f}°)")
            if args.verbose:
                print(f"              {data['meaning']}")

        print(f"\n{'='*80}")
        print("Travel in these directions from your birthplace for planetary energies")
        print(f"{'='*80}")

        if args.save:
            self._save_result(result, "local_space", f"{args.year}_{args.month}_{args.day}")

    def cmd_convert(self, args):
        """Convert between Julian and Gregorian calendars."""
        print(f"\n{'='*80}")
        print(f"CALENDAR CONVERSION")
        print(f"{'='*80}")

        jd = CalendarConverter.date_to_julian_day(
            args.year, args.month, args.day,
            args.hour, args.minute, 0,
            args.calendar
        )

        print(f"Input Date: {args.year}/{args.month:02d}/{args.day:02d} {args.hour:02d}:{args.minute:02d}")
        print(f"Input Calendar: {args.calendar}")
        print(f"\nJulian Day Number: {jd:.6f}")

        # Convert to both calendars
        gregorian = CalendarConverter.julian_day_to_date(jd, 'gregorian')
        julian = CalendarConverter.julian_day_to_date(jd, 'julian')

        print(f"\n{'='*80}")
        print("CONVERSIONS")
        print(f"{'='*80}\n")

        print(f"Gregorian: {gregorian['year']}/{gregorian['month']:02d}/{gregorian['day']:02d} "
              f"{gregorian['hour']:02d}:{gregorian['minute']:02d}:{gregorian['second']:02d}")

        print(f"Julian:    {julian['year']}/{julian['month']:02d}/{julian['day']:02d} "
              f"{julian['hour']:02d}:{julian['minute']:02d}:{julian['second']:02d}")

        print(f"\n{'='*80}")

    def _save_result(self, result, result_type, identifier):
        """Save analysis result to file."""
        # Create results directory
        results_dir = Path(__file__).parent.parent / "results" / "astrocartography"
        results_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{result_type}_{identifier}_{timestamp}.json"
        filepath = results_dir / filename

        with open(filepath, 'w') as f:
            json.dump(result, f, indent=2, default=str)

        print(f"\n💾 Results saved to: {filepath}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Astrocartography & Historical Astrology Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Calculate planetary lines
  %(prog)s lines 2025 1 1 --hour 12

  # Find parans
  %(prog)s parans 2025 1 1

  # Historical chart for Rome, 100 CE
  %(prog)s chart 100 3 21 --lat 41.9 --lon 12.5 --location "Rome" --calendar julian

  # Find benefic power places
  %(prog)s power-places 2025 6 21 --focus benefic

  # Compare locations
  %(prog)s compare 2025 1 1 --location "NYC,40.7,-74.0" --location "LA,34.0,-118.2"

  # Local space from birthplace
  %(prog)s local-space 1990 5 15 --lat 34.05 --lon -118.25

  # Calendar conversion
  %(prog)s convert --year -43 --month 3 --day 15 --calendar julian
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Lines command
    p_lines = subparsers.add_parser('lines', help='Calculate astrocartography lines')
    p_lines.add_argument('year', type=int, help='Year (negative for BCE)')
    p_lines.add_argument('month', type=int, help='Month (1-12)')
    p_lines.add_argument('day', type=int, help='Day')
    p_lines.add_argument('--hour', type=int, default=12, help='Hour (0-23)')
    p_lines.add_argument('--minute', type=int, default=0, help='Minute (0-59)')
    p_lines.add_argument('--planets', help='Comma-separated planet list (e.g., "sun,moon,venus")')
    p_lines.add_argument('--calendar', default='auto', choices=['auto', 'gregorian', 'julian'],
                        help='Calendar system')
    p_lines.add_argument('--save', action='store_true', help='Save results to file')

    # Parans command
    p_parans = subparsers.add_parser('parans', help='Calculate parans (planetary crossings)')
    p_parans.add_argument('year', type=int, help='Year (negative for BCE)')
    p_parans.add_argument('month', type=int, help='Month (1-12)')
    p_parans.add_argument('day', type=int, help='Day')
    p_parans.add_argument('--hour', type=int, default=12, help='Hour (0-23)')
    p_parans.add_argument('--minute', type=int, default=0, help='Minute (0-59)')
    p_parans.add_argument('--calendar', default='auto', choices=['auto', 'gregorian', 'julian'],
                         help='Calendar system')
    p_parans.add_argument('--save', action='store_true', help='Save results to file')

    # Chart command
    p_chart = subparsers.add_parser('chart', help='Calculate historical chart')
    p_chart.add_argument('year', type=int, help='Year (negative for BCE)')
    p_chart.add_argument('month', type=int, help='Month (1-12)')
    p_chart.add_argument('day', type=int, help='Day')
    p_chart.add_argument('--hour', type=int, default=12, help='Hour (0-23)')
    p_chart.add_argument('--minute', type=int, default=0, help='Minute (0-59)')
    p_chart.add_argument('--lat', type=float, required=True, help='Latitude')
    p_chart.add_argument('--lon', type=float, required=True, help='Longitude')
    p_chart.add_argument('--location', default='Unknown', help='Location name')
    p_chart.add_argument('--calendar', default='auto', choices=['auto', 'gregorian', 'julian'],
                        help='Calendar system')
    p_chart.add_argument('--save', action='store_true', help='Save results to file')

    # Power places command
    p_power = subparsers.add_parser('power-places', help='Find optimal locations')
    p_power.add_argument('year', type=int, help='Year')
    p_power.add_argument('month', type=int, help='Month (1-12)')
    p_power.add_argument('day', type=int, help='Day')
    p_power.add_argument('--hour', type=int, default=12, help='Hour (0-23)')
    p_power.add_argument('--minute', type=int, default=0, help='Minute (0-59)')
    p_power.add_argument('--focus', default='all',
                        choices=['all', 'benefic', 'career', 'relationship'],
                        help='Focus area')
    p_power.add_argument('--calendar', default='auto', choices=['auto', 'gregorian', 'julian'],
                        help='Calendar system')
    p_power.add_argument('--save', action='store_true', help='Save results to file')

    # Compare command
    p_compare = subparsers.add_parser('compare', help='Compare multiple locations')
    p_compare.add_argument('year', type=int, help='Year')
    p_compare.add_argument('month', type=int, help='Month (1-12)')
    p_compare.add_argument('day', type=int, help='Day')
    p_compare.add_argument('--hour', type=int, default=12, help='Hour (0-23)')
    p_compare.add_argument('--minute', type=int, default=0, help='Minute (0-59)')
    p_compare.add_argument('--location', action='append', dest='locations', required=True,
                          help='Location in format "Name,latitude,longitude" (can be repeated)')
    p_compare.add_argument('--calendar', default='auto', choices=['auto', 'gregorian', 'julian'],
                          help='Calendar system')
    p_compare.add_argument('--save', action='store_true', help='Save results to file')

    # Local space command
    p_local = subparsers.add_parser('local-space', help='Calculate local space directions')
    p_local.add_argument('year', type=int, help='Birth year')
    p_local.add_argument('month', type=int, help='Birth month (1-12)')
    p_local.add_argument('day', type=int, help='Birth day')
    p_local.add_argument('--hour', type=int, default=12, help='Birth hour (0-23)')
    p_local.add_argument('--minute', type=int, default=0, help='Birth minute (0-59)')
    p_local.add_argument('--lat', type=float, required=True, help='Birth latitude')
    p_local.add_argument('--lon', type=float, required=True, help='Birth longitude')
    p_local.add_argument('--calendar', default='auto', choices=['auto', 'gregorian', 'julian'],
                        help='Calendar system')
    p_local.add_argument('--verbose', '-v', action='store_true', help='Show detailed meanings')
    p_local.add_argument('--save', action='store_true', help='Save results to file')

    # Convert command
    p_convert = subparsers.add_parser('convert', help='Convert between calendars')
    p_convert.add_argument('--year', type=int, required=True, help='Year (negative for BCE)')
    p_convert.add_argument('--month', type=int, required=True, help='Month (1-12)')
    p_convert.add_argument('--day', type=int, required=True, help='Day')
    p_convert.add_argument('--hour', type=int, default=12, help='Hour (0-23)')
    p_convert.add_argument('--minute', type=int, default=0, help='Minute (0-59)')
    p_convert.add_argument('--calendar', default='gregorian', choices=['gregorian', 'julian'],
                          help='Input calendar system')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Initialize CLI
    cli = AstrocartographyCLI()

    # Dispatch to command handler
    handler = getattr(cli, f'cmd_{args.command.replace("-", "_")}', None)
    if handler:
        try:
            handler(args)
        except Exception as e:
            print(f"\n❌ Error: {e}")
            if '--verbose' in sys.argv or '-v' in sys.argv:
                import traceback
                traceback.print_exc()
            return 1
    else:
        print(f"Unknown command: {args.command}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
