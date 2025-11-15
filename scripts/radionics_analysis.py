#!/usr/bin/env python3
"""
Enhanced Radionics Analysis Script

Provides command-line interface for:
- Rate analysis and generation
- General Vitality measurement
- Signature-to-rate conversion
- Broadcasting with feedback
- Rate database management
- Finding balancing rates

Usage examples:
    # Analyze a subject
    python radionics_analysis.py analyze "John Doe"

    # Measure General Vitality
    python radionics_analysis.py gv "World Peace"

    # Generate signature rate
    python radionics_analysis.py signature "Healing Energy"

    # Broadcast with feedback
    python radionics_analysis.py broadcast "Recovery" --duration 300

    # Find balancing rates
    python radionics_analysis.py balance "Stress"

    # Search rate database
    python radionics_analysis.py search "heart"

    # List all rates in category
    python radionics_analysis.py list-category chakra
"""

import sys
import os
import argparse
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.radionics_engine import (
    RadionicsAnalyzer,
    RadionicsRate,
    RateDatabase,
    SignatureCalculator,
    GeneralVitalityMeter,
    RandomNumberGenerator
)


class RadionicsAnalysisCLI:
    """Command-line interface for radionics analysis."""

    def __init__(self):
        """Initialize CLI with rate databases."""
        self.analyzer = RadionicsAnalyzer()
        self.sig_calculator = SignatureCalculator()
        self.gv_meter = GeneralVitalityMeter()

        # Load all rate databases
        self.databases = {}
        rate_dir = Path(__file__).parent.parent / "knowledge" / "radionics_rates"

        if rate_dir.exists():
            for db_file in rate_dir.glob("*.json"):
                db_name = db_file.stem
                try:
                    db = RateDatabase(str(db_file))
                    self.databases[db_name] = db
                    print(f"✓ Loaded {len(db.rates)} rates from {db_name}")
                except Exception as e:
                    print(f"⚠ Failed to load {db_name}: {e}")

        # Merge all databases into analyzer's database
        for db in self.databases.values():
            for rate in db.rates:
                self.analyzer.rate_database.add_rate(rate)

        total_rates = len(self.analyzer.rate_database.rates)
        print(f"📚 Total rates available: {total_rates}\n")

    def cmd_analyze(self, args):
        """Perform full radionics analysis on subject."""
        print(f"\n{'='*70}")
        print(f"RADIONICS ANALYSIS")
        print(f"{'='*70}")

        context = {}
        if args.with_astrology:
            try:
                from core.astrology import AstrologicalCalculator
                astro = AstrologicalCalculator()

                # Get current astrological data
                dt = datetime.now()
                moon_phase = astro.get_moon_phase(dt)
                context['moon_phase'] = moon_phase
                context['hour'] = dt.hour

                print(f"🌙 Moon Phase: {moon_phase}")
            except ImportError:
                print("⚠ Astrological integration not available")

        result = self.analyzer.analyze_subject(
            args.subject,
            num_rates=args.num_rates,
            context=context
        )

        print(f"\n{'='*70}")
        print("ANALYSIS COMPLETE")
        print(f"{'='*70}")

        if args.save:
            self._save_result(result, "analysis", args.subject)

    def cmd_gv(self, args):
        """Measure General Vitality."""
        print(f"\n{'='*70}")
        print(f"GENERAL VITALITY MEASUREMENT")
        print(f"{'='*70}")
        print(f"Subject: {args.subject}\n")

        if args.multiple:
            stats = self.gv_meter.measure_multiple(
                count=args.count,
                subject=args.subject
            )

            print(f"📊 Statistics from {args.count} measurements:")
            print(f"   Mean:   {stats['mean']:.1f}")
            print(f"   Median: {stats['median']:.1f}")
            print(f"   Std:    {stats['std']:.1f}")
            print(f"   Min:    {stats['min']:.1f}")
            print(f"   Max:    {stats['max']:.1f}")
            print(f"\n   Interpretation: {self.gv_meter.interpret_gv(stats['mean'])}")

            if args.verbose:
                print(f"\n   Individual measurements:")
                for i, gv in enumerate(stats['measurements'], 1):
                    print(f"      {i:2d}. {gv:6.1f}")
        else:
            gv = self.gv_meter.measure(args.subject)
            print(f"📊 General Vitality: {gv:.1f}")
            print(f"   {self.gv_meter.interpret_gv(gv)}")

        print(f"\n{'='*70}")

    def cmd_signature(self, args):
        """Generate signature rate from text."""
        print(f"\n{'='*70}")
        print(f"SIGNATURE RATE GENERATION")
        print(f"{'='*70}")
        print(f"Subject: {args.subject}\n")

        algorithms = args.algorithm.split(',') if ',' in args.algorithm else [args.algorithm]

        for algo in algorithms:
            rate = self.sig_calculator.text_to_rate(
                args.subject,
                num_dials=args.dials,
                max_value=args.max_value,
                algorithm=algo.strip()
            )
            print(f"🔢 {algo.upper()}: {rate}")
            print(f"   Values: {rate.values}")
            print(f"   {rate.description}\n")

        print(f"{'='*70}")

    def cmd_broadcast(self, args):
        """Broadcast rate with GV feedback."""
        print(f"\n{'='*70}")
        print(f"RADIONICS BROADCASTING WITH FEEDBACK")
        print(f"{'='*70}")

        # Get or generate rate
        if args.rate:
            # Parse rate string like "45-72-88"
            values = [int(v) for v in args.rate.split('-')]
            rate = RadionicsRate(values, name=f"Rate for {args.subject}")
        else:
            # Generate signature rate
            rate = self.sig_calculator.text_to_rate(args.subject, num_dials=3)
            print(f"Generated signature rate: {rate}\n")

        result = self.analyzer.broadcast_with_feedback(
            subject=args.subject,
            rate=rate,
            duration_seconds=args.duration,
            check_interval=args.interval
        )

        print(f"\n{'='*70}")
        print("BROADCAST COMPLETE")
        print(f"{'='*70}")
        print(f"Trend: {result['gv_trend'].upper()}")
        print(f"Change: {result['gv_change']:+.1f}")
        print(f"{'='*70}")

        if args.save:
            self._save_result(result, "broadcast", args.subject)

    def cmd_balance(self, args):
        """Find balancing rates for subject."""
        print(f"\n{'='*70}")
        print(f"BALANCING RATE GENERATION")
        print(f"{'='*70}")
        print(f"Subject: {args.subject}\n")

        balancing_rates = self.analyzer.find_balancing_rates(
            args.subject,
            num_rates=args.num_rates
        )

        print(f"🔮 Top {len(balancing_rates)} Balancing Rates:\n")
        for i, rate in enumerate(balancing_rates, 1):
            print(f"{i}. {rate}")
            print(f"   Potency: {rate.potency:.3f}")
            print(f"   {rate.description}\n")

        print(f"{'='*70}")

    def cmd_search(self, args):
        """Search rate databases."""
        print(f"\n{'='*70}")
        print(f"RATE DATABASE SEARCH")
        print(f"{'='*70}")
        print(f"Query: {args.query}\n")

        results = self.analyzer.rate_database.find_by_name(args.query, exact=args.exact)

        if results:
            print(f"Found {len(results)} matching rates:\n")
            for rate in results:
                print(f"🔢 {rate}")
                if args.verbose:
                    print(f"   Category: {rate.category}")
                    print(f"   Description: {rate.description}")
                    print(f"   Potency: {rate.potency:.3f}")
                print()
        else:
            print("No rates found matching query.")

        print(f"{'='*70}")

    def cmd_list_category(self, args):
        """List all rates in a category."""
        print(f"\n{'='*70}")
        print(f"RATES IN CATEGORY: {args.category.upper()}")
        print(f"{'='*70}\n")

        rates = self.analyzer.rate_database.find_by_category(args.category)

        if rates:
            for rate in rates:
                print(f"🔢 {rate}")
                if args.verbose:
                    print(f"   {rate.description}")
                print()
            print(f"Total: {len(rates)} rates")
        else:
            print(f"No rates found in category '{args.category}'")
            print("\nAvailable categories:")
            for cat in self.analyzer.rate_database.get_categories():
                print(f"  - {cat}")

        print(f"\n{'='*70}")

    def cmd_list_categories(self, args):
        """List all available categories."""
        print(f"\n{'='*70}")
        print(f"AVAILABLE RATE CATEGORIES")
        print(f"{'='*70}\n")

        categories = self.analyzer.rate_database.get_categories()

        for cat in categories:
            rates = self.analyzer.rate_database.find_by_category(cat)
            print(f"📂 {cat:20s} ({len(rates)} rates)")

        print(f"\nTotal: {len(categories)} categories")
        print(f"{'='*70}")

    def _save_result(self, result, result_type, subject):
        """Save analysis result to file."""
        import json

        # Create results directory
        results_dir = Path(__file__).parent.parent / "results" / "radionics_analysis"
        results_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_subject = "".join(c for c in subject if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_subject = safe_subject.replace(' ', '_')[:30]
        filename = f"{result_type}_{safe_subject}_{timestamp}.json"

        filepath = results_dir / filename

        with open(filepath, 'w') as f:
            json.dump(result, f, indent=2)

        print(f"\n💾 Results saved to: {filepath}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Enhanced Radionics Analysis Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s analyze "John Doe"
  %(prog)s gv "World Peace" --multiple --count 20
  %(prog)s signature "Healing" --algorithm mixed
  %(prog)s broadcast "Recovery" --duration 300 --interval 60
  %(prog)s balance "Anxiety" --num-rates 5
  %(prog)s search "heart"
  %(prog)s list-category chakra
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Analyze command
    p_analyze = subparsers.add_parser('analyze', help='Full radionics analysis')
    p_analyze.add_argument('subject', help='Subject to analyze')
    p_analyze.add_argument('--num-rates', type=int, default=10,
                          help='Number of resonant rates to generate')
    p_analyze.add_argument('--with-astrology', action='store_true',
                          help='Include astrological timing')
    p_analyze.add_argument('--save', action='store_true',
                          help='Save results to file')

    # GV command
    p_gv = subparsers.add_parser('gv', help='Measure General Vitality')
    p_gv.add_argument('subject', help='Subject to measure')
    p_gv.add_argument('--multiple', action='store_true',
                     help='Take multiple measurements')
    p_gv.add_argument('--count', type=int, default=10,
                     help='Number of measurements (with --multiple)')
    p_gv.add_argument('--verbose', '-v', action='store_true',
                     help='Show individual measurements')

    # Signature command
    p_sig = subparsers.add_parser('signature', help='Generate signature rate')
    p_sig.add_argument('subject', help='Text to convert to rate')
    p_sig.add_argument('--algorithm', default='mixed',
                      choices=['hash', 'gematria', 'phonetic', 'mixed'],
                      help='Algorithm to use')
    p_sig.add_argument('--dials', type=int, default=3,
                      help='Number of rate values')
    p_sig.add_argument('--max-value', type=int, default=100,
                      help='Maximum value per dial')

    # Broadcast command
    p_broadcast = subparsers.add_parser('broadcast', help='Broadcast with feedback')
    p_broadcast.add_argument('subject', help='Subject to broadcast to')
    p_broadcast.add_argument('--rate', help='Rate to broadcast (e.g., "45-72-88")')
    p_broadcast.add_argument('--duration', type=int, default=300,
                            help='Duration in seconds')
    p_broadcast.add_argument('--interval', type=int, default=60,
                            help='GV check interval in seconds')
    p_broadcast.add_argument('--save', action='store_true',
                            help='Save results to file')

    # Balance command
    p_balance = subparsers.add_parser('balance', help='Find balancing rates')
    p_balance.add_argument('subject', help='Subject to balance')
    p_balance.add_argument('--num-rates', type=int, default=5,
                          help='Number of balancing rates')

    # Search command
    p_search = subparsers.add_parser('search', help='Search rate database')
    p_search.add_argument('query', help='Search term')
    p_search.add_argument('--exact', action='store_true',
                         help='Exact match only')
    p_search.add_argument('--verbose', '-v', action='store_true',
                         help='Show full details')

    # List category command
    p_list_cat = subparsers.add_parser('list-category', help='List rates in category')
    p_list_cat.add_argument('category', help='Category name')
    p_list_cat.add_argument('--verbose', '-v', action='store_true',
                           help='Show full details')

    # List categories command
    p_list_cats = subparsers.add_parser('list-categories', help='List all categories')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Initialize CLI
    cli = RadionicsAnalysisCLI()

    # Dispatch to command handler
    handler = getattr(cli, f'cmd_{args.command.replace("-", "_")}', None)
    if handler:
        handler(args)
    else:
        print(f"Unknown command: {args.command}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
