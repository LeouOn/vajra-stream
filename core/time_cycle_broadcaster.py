#!/usr/bin/env python3
"""
Time Cycle Broadcaster - Systematic Blessings Through Historical Periods

Sends healing, blessings, and compassionate energy to historical periods
of mass suffering, cycling day by day through difficult times.

Integrates:
- Radionics broadcasting to specific times/places
- Astrocartography for planetary positions
- Blessing dedications for populations
- Visualizations showing daily progress
- Multi-system coordinated healing work

This is profound compassionate action - may all beings benefit.
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import time

try:
    from core.compassionate_blessings import (
        BlessingDatabase,
        BlessingTarget,
        BlessingCategory,
        BlessingCoordinate,
        GeoCoordinate
    )
    HAS_BLESSINGS = True
except ImportError:
    HAS_BLESSINGS = False

try:
    from core.astrocartography import (
        AstrocartographyCalculator,
        HistoricalChartCalculator,
        CalendarConverter
    )
    HAS_ASTRO = True
except ImportError:
    HAS_ASTRO = False

try:
    from core.energetic_visualization import (
        RothkoVisualizer,
        SacredGeometryVisualizer,
        create_chakra_meditation
    )
    HAS_VIZ = True
except ImportError:
    HAS_VIZ = False


# ============================================================================
# TIME CYCLE BROADCASTER
# ============================================================================

class TimeCycleBroadcaster:
    """
    Broadcast healing energy through historical time periods.

    Systematically sends blessings to periods of mass suffering,
    day by day, with integrated visualizations and radionics.
    """

    def __init__(self, events_file: str = None):
        """
        Initialize time cycle broadcaster.

        Args:
            events_file: Path to historical events JSON file
        """
        if events_file is None:
            # Default location
            base_path = Path(__file__).parent.parent
            events_file = base_path / "knowledge" / "historical_suffering_events.json"

        self.events_file = events_file
        self.events = self._load_events()
        self.blessing_db = BlessingDatabase() if HAS_BLESSINGS else None
        self.astro_calc = AstrocartographyCalculator() if HAS_ASTRO else None
        self.chart_calc = HistoricalChartCalculator() if HAS_ASTRO else None

    def _load_events(self) -> Dict:
        """Load historical events from JSON"""
        try:
            with open(self.events_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: Events file not found: {self.events_file}")
            return {"historical_suffering_periods": []}

    def get_event_by_id(self, event_id: str) -> Optional[Dict]:
        """Get event by ID"""
        for event in self.events.get('historical_suffering_periods', []):
            if event['id'] == event_id:
                return event
        return None

    def list_events(self) -> List[Dict]:
        """List all available events"""
        return self.events.get('historical_suffering_periods', [])

    def parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime"""
        return datetime.strptime(date_str, "%Y-%m-%d")

    def generate_date_range(self, start_date: str, end_date: str,
                           step_days: int = 1) -> List[datetime]:
        """
        Generate list of dates in range.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            step_days: Days between each date

        Returns:
            List of datetime objects
        """
        start = self.parse_date(start_date)
        end = self.parse_date(end_date)

        dates = []
        current = start
        while current <= end:
            dates.append(current)
            current += timedelta(days=step_days)

        return dates

    def create_blessing_targets_for_event(self, event: Dict) -> List[str]:
        """
        Create blessing targets for an event.

        Args:
            event: Event dictionary

        Returns:
            List of target IDs created
        """
        if not HAS_BLESSINGS or not self.blessing_db:
            print("Warning: Blessing system not available")
            return []

        target_ids = []

        # Create target for the overall event
        main_target = BlessingTarget(
            identifier=f"historical_{event['id']}",
            name=f"{event['name']} - All Victims",
            category=BlessingCategory.DECEASED,
            description=event['description'],
            coordinates=None,  # Multiple locations
            intention=f"May all who suffered during {event['name']} find peace and liberation",
            priority=10  # High priority for mass suffering
        )

        try:
            self.blessing_db.add_target(main_target)
            target_ids.append(main_target.identifier)
        except:
            pass  # May already exist

        # Create targets for each primary location
        for location in event.get('primary_locations', []):
            loc_target = BlessingTarget(
                identifier=f"historical_{event['id']}_{location['name'].replace(' ', '_').lower()}",
                name=f"{event['name']} - {location['name']}",
                category=BlessingCategory.DECEASED,
                description=f"Victims at {location['name']} during {event['name']}",
                coordinates=BlessingCoordinate(
                    julian_day=datetime.now().toordinal() + 1721425.5,  # Convert to Julian day
                    location=GeoCoordinate(
                        latitude=location['lat'],
                        longitude=location['lon'],
                        location_name=location['name']
                    )
                ),
                intention=f"May all who suffered at {location['name']} find peace",
                priority=10
            )

            try:
                self.blessing_db.add_target(loc_target)
                target_ids.append(loc_target.identifier)
            except:
                pass  # May already exist

        return target_ids

    def broadcast_to_date(self, event: Dict, date: datetime,
                         duration_seconds: int = 60,
                         create_visualization: bool = True,
                         viz_output_dir: Optional[str] = None) -> Dict:
        """
        Broadcast healing to a specific date in an event.

        Args:
            event: Event dictionary
            date: Date to broadcast to
            duration_seconds: How long to broadcast
            create_visualization: Create daily visualization
            viz_output_dir: Directory for visualization output

        Returns:
            Results dictionary
        """
        results = {
            'event_id': event['id'],
            'event_name': event['name'],
            'date': date.strftime('%Y-%m-%d'),
            'timestamp': datetime.now().isoformat(),
            'actions': []
        }

        print(f"\n{'='*70}")
        print(f"Broadcasting Healing Energy")
        print(f"Event: {event['name']}")
        print(f"Date: {date.strftime('%B %d, %Y')}")
        print(f"{'='*70}\n")

        # 1. Calculate astrocartography for this date
        if HAS_ASTRO and self.chart_calc:
            print(f"📍 Calculating planetary positions for {date.strftime('%Y-%m-%d')}...")
            try:
                chart = self.chart_calc.calculate_chart(
                    year=date.year,
                    month=date.month,
                    day=date.day,
                    hour=12,
                    latitude=event['primary_locations'][0]['lat'],
                    longitude=event['primary_locations'][0]['lon'],
                    location_name=event['primary_locations'][0]['name']
                )
                results['actions'].append({
                    'type': 'astrocartography',
                    'status': 'success',
                    'data': f"Calculated planetary positions for {chart['location_name']}"
                })
                print(f"   ✓ Planetary positions calculated")
            except Exception as e:
                print(f"   ⚠ Could not calculate chart: {e}")
                results['actions'].append({
                    'type': 'astrocartography',
                    'status': 'failed',
                    'error': str(e)
                })

        # 2. Create/update blessing targets
        if HAS_BLESSINGS and self.blessing_db:
            print(f"\n🙏 Recording blessing dedication...")
            target_ids = self.create_blessing_targets_for_event(event)

            # Record session
            session_id = self.blessing_db.record_session(
                mantra_type="Om Mani Padme Hum",
                total_mantras=108,
                total_rotations=1,
                targets_blessed=len(target_ids),
                allocation_method="Equal distribution",
                notes=f"Time Cycle Healing for {event['name']} on {date.strftime('%Y-%m-%d')}. Duration: {duration_seconds}s"
            )

            # Dedicate to all targets
            for target_id in target_ids:
                self.blessing_db.record_dedication(
                    target_identifier=target_id,
                    session_id=session_id,
                    mantra_type="Om Mani Padme Hum",
                    mantras_count=108,
                    notes=f"Healing for {date.strftime('%B %d, %Y')}"
                )

            print(f"   ✓ Dedicated 108 mantras to {len(target_ids)} targets")
            results['actions'].append({
                'type': 'blessing_dedication',
                'status': 'success',
                'targets': len(target_ids),
                'mantras': 108
            })

        # 3. Create daily visualization
        if create_visualization and HAS_VIZ:
            print(f"\n🎨 Creating daily visualization...")
            try:
                viz_path = self._create_daily_visualization(
                    event=event,
                    date=date,
                    output_dir=viz_output_dir
                )
                print(f"   ✓ Visualization created: {viz_path}")
                results['actions'].append({
                    'type': 'visualization',
                    'status': 'success',
                    'path': viz_path
                })
            except Exception as e:
                print(f"   ⚠ Could not create visualization: {e}")
                results['actions'].append({
                    'type': 'visualization',
                    'status': 'failed',
                    'error': str(e)
                })

        # 4. Simulate radionics broadcast
        print(f"\n📡 Broadcasting healing energy...")
        print(f"   Duration: {duration_seconds} seconds")
        print(f"   Intention: {event['blessing_focus']}")

        # Simulate brief broadcast
        time.sleep(min(duration_seconds, 3))  # Don't actually wait full duration in testing

        print(f"   ✓ Broadcast complete")
        results['actions'].append({
            'type': 'radionics_broadcast',
            'status': 'simulated',
            'duration': duration_seconds,
            'intention': event['blessing_focus']
        })

        # 5. Display mantras
        print(f"\n🕉 Mantras for {event['name']}:")
        for mantra in event.get('mantras', []):
            print(f"   • {mantra}")

        print(f"\n{'='*70}")
        print(f"✨ Healing broadcast complete for {date.strftime('%B %d, %Y')}")
        print(f"{'='*70}\n")

        return results

    def _create_daily_visualization(self, event: Dict, date: datetime,
                                   output_dir: Optional[str] = None) -> str:
        """
        Create visualization for a specific day.

        Args:
            event: Event dictionary
            date: Date to visualize
            output_dir: Output directory

        Returns:
            Path to created visualization
        """
        if output_dir is None:
            output_dir = "/tmp/time_cycle_visualizations"

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Create filename
        filename = f"{event['id']}_{date.strftime('%Y%m%d')}.png"
        filepath = Path(output_dir) / filename

        # Create Rothko-style visualization based on theme
        viz = RothkoVisualizer(1920, 1080, background=(20, 20, 25))

        # Use visualization themes from event
        themes = event.get('visualization_themes', [])

        # Create a somber, healing color field
        # Dark bottom (suffering), transitioning to light top (healing/liberation)
        viz.create_field(
            color=(40, 20, 30),      # Deep dark purple (suffering)
            position=(0.0, 0.5),
            size=(1.0, 0.5),
            edge_blur=60,
            name="Darkness of suffering"
        )

        viz.create_field(
            color=(100, 80, 140),    # Lighter purple (transition)
            position=(0.0, 0.25),
            size=(1.0, 0.35),
            edge_blur=70,
            name="Healing begins"
        )

        viz.create_field(
            color=(180, 160, 200),   # Light violet (liberation)
            position=(0.0, 0.0),
            size=(1.0, 0.35),
            edge_blur=80,
            name="Light of liberation"
        )

        viz.render_all_fields()

        # Add date text
        try:
            from PIL import ImageFont
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
        except:
            font = None

        if font:
            # Add event name
            viz.draw.text(
                (50, 50),
                event['name'],
                fill=(200, 200, 200),
                font=font
            )

            # Add date
            date_text = date.strftime('%B %d, %Y')
            viz.draw.text(
                (50, 100),
                date_text,
                fill=(180, 180, 180),
                font=font
            )

            # Add intention at bottom
            try:
                small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
                intention_text = "May all who suffered find peace and liberation"
                viz.draw.text(
                    (50, 1020),
                    intention_text,
                    fill=(160, 160, 160),
                    font=small_font
                )
            except:
                pass

        viz.save(str(filepath))
        return str(filepath)

    def run_daily_cycle(self, event_id: str,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None,
                       step_days: int = 1,
                       duration_per_day: int = 60,
                       create_visualizations: bool = True,
                       viz_output_dir: Optional[str] = None,
                       max_days: Optional[int] = None) -> List[Dict]:
        """
        Run a full cycle through an event period.

        Args:
            event_id: ID of event to cycle through
            start_date: Override start date (YYYY-MM-DD)
            end_date: Override end date (YYYY-MM-DD)
            step_days: Days between broadcasts
            duration_per_day: Seconds per day broadcast
            create_visualizations: Create daily visualizations
            viz_output_dir: Directory for visualizations
            max_days: Maximum number of days to process

        Returns:
            List of results for each day
        """
        event = self.get_event_by_id(event_id)
        if not event:
            raise ValueError(f"Event not found: {event_id}")

        # Use event dates if not overridden
        start = start_date or event['start_date']
        end = end_date or event['end_date']

        # Generate date range
        dates = self.generate_date_range(start, end, step_days)

        # Limit if max_days specified
        if max_days and len(dates) > max_days:
            dates = dates[:max_days]
            print(f"\nℹ️  Limiting to first {max_days} days (of {len(self.generate_date_range(start, end, step_days))} total)\n")

        total_days = len(dates)

        print(f"\n{'='*70}")
        print(f"STARTING TIME CYCLE HEALING")
        print(f"{'='*70}")
        print(f"Event: {event['name']}")
        print(f"Period: {start} to {end}")
        print(f"Total days to process: {total_days}")
        print(f"Step: Every {step_days} day(s)")
        print(f"Duration per day: {duration_per_day} seconds")
        print(f"Estimated deaths: {event['estimated_deaths']:,}")
        print(f"Population affected: {event['population_affected']}")
        print(f"{'='*70}\n")

        results = []

        for i, date in enumerate(dates, 1):
            print(f"\n[Day {i}/{total_days}]")

            day_result = self.broadcast_to_date(
                event=event,
                date=date,
                duration_seconds=duration_per_day,
                create_visualization=create_visualizations,
                viz_output_dir=viz_output_dir
            )

            results.append(day_result)

            # Brief pause between days
            if i < total_days:
                time.sleep(0.5)

        # Summary
        print(f"\n{'='*70}")
        print(f"TIME CYCLE HEALING COMPLETE")
        print(f"{'='*70}")
        print(f"Event: {event['name']}")
        print(f"Days processed: {len(results)}")
        print(f"Total mantras dedicated: {len(results) * 108}")
        print(f"\nMay all {event['estimated_deaths']:,} souls find peace.")
        print(f"May healing reach across time to all who suffered.")
        print(f"May this work benefit all beings.")
        print(f"{'='*70}\n")

        return results

    def run_sample_cycle(self, event_id: str,
                        num_days: int = 7,
                        create_visualizations: bool = True) -> List[Dict]:
        """
        Run a sample cycle (first N days of event).

        Useful for testing and demonstration.

        Args:
            event_id: ID of event
            num_days: Number of days to process
            create_visualizations: Create visualizations

        Returns:
            List of results
        """
        event = self.get_event_by_id(event_id)
        if not event:
            raise ValueError(f"Event not found: {event_id}")

        return self.run_daily_cycle(
            event_id=event_id,
            max_days=num_days,
            duration_per_day=10,  # Shorter for testing
            create_visualizations=create_visualizations
        )


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def list_all_events():
    """List all available historical events"""
    broadcaster = TimeCycleBroadcaster()
    events = broadcaster.list_events()

    print(f"\n{'='*70}")
    print("AVAILABLE HISTORICAL EVENTS FOR HEALING WORK")
    print(f"{'='*70}\n")

    for event in events:
        print(f"ID: {event['id']}")
        print(f"Name: {event['name']}")
        print(f"Period: {event['start_date']} to {event['end_date']}")
        print(f"Deaths: {event['estimated_deaths']:,}")
        print(f"Description: {event['description']}")
        print(f"Suggestion: {event.get('daily_cycle_suggestion', 'N/A')}")
        print(f"{'-'*70}\n")


def run_quick_test(event_id: str = "rwandan_genocide", num_days: int = 3):
    """
    Quick test of time cycle system.

    Args:
        event_id: Which event to test
        num_days: How many days to test
    """
    print("\n🧪 RUNNING QUICK TEST OF TIME CYCLE SYSTEM\n")

    broadcaster = TimeCycleBroadcaster()
    results = broadcaster.run_sample_cycle(
        event_id=event_id,
        num_days=num_days,
        create_visualizations=True
    )

    print(f"\n✅ Test complete! Processed {len(results)} days.")
    print(f"Check /tmp/time_cycle_visualizations/ for daily images.")


# Example usage
if __name__ == "__main__":
    print("Time Cycle Broadcaster - Systematic Healing Through History\n")

    # List available events
    list_all_events()

    # Run a quick test
    print("\n" + "="*70)
    print("Running sample 3-day cycle for Rwandan Genocide...")
    print("="*70 + "\n")

    run_quick_test(event_id="rwandan_genocide", num_days=3)

    print("\n" + "="*70)
    print("✨ Time Cycle Broadcaster Ready")
    print("="*70)
    print("\nTo run full cycles:")
    print("  broadcaster = TimeCycleBroadcaster()")
    print("  broadcaster.run_daily_cycle('holocaust', max_days=7)")
    print("\nMay all beings be free from suffering.")
    print("May healing reach across time and space.")
    print("Om Mani Padme Hum 🙏")
