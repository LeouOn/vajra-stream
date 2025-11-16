#!/usr/bin/env python3
"""
Vajra.Stream - RADIONICS OPERATION
Powerful crystal grid broadcasting system for healing intentions
Combines: Astrology + Frequencies + Prayer Wheel + LLM + Audio + Visuals

USAGE:
    python scripts/radionics_operation.py --intention "healing for all beings" --duration 3600
    python scripts/radionics_operation.py --target "world peace" --continuous
    python scripts/radionics_operation.py --preset heart_healing
"""

import sys
import os
import time
import argparse
from datetime import datetime
import sqlite3

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.audio_generator import ScalarWaveGenerator
from core.astrology import AstrologicalCalculator, format_astrological_report
from core.prayer_wheel import PrayerWheel
from core.llm_integration import LLMIntegration, DharmaLLM
from core.tts_engine import TTSEngine
from core.rothko_generator import RothkoGenerator
from core.intelligent_composer import IntelligentComposer

try:
    from core.visual_renderer_simple import SimpleVisualRenderer
    HAS_VISUAL = True
except:
    HAS_VISUAL = False

# Enhanced radionics capabilities
try:
    from core.radionics_engine import (
        RadionicsAnalyzer,
        RateDatabase,
        RadionicsRate,
        GeneralVitalityMeter
    )
    HAS_RADIONICS_ENGINE = True
except:
    HAS_RADIONICS_ENGINE = False

# Astrocartography capabilities
try:
    from core.astrocartography import (
        AstrocartographyCalculator,
        HistoricalChartCalculator,
        CalendarConverter
    )
    HAS_ASTROCARTOGRAPHY = True
except:
    HAS_ASTROCARTOGRAPHY = False


class RadionicsOperation:
    """
    Complete radionics broadcasting system
    Uses crystal grid as radionic antenna to broadcast healing intentions
    """

    def __init__(self, db_path='vajra_stream.db'):
        """Initialize all systems"""
        print("\n" + "="*70)
        print("🔮 VAJRA.STREAM RADIONICS OPERATION - INITIALIZING 🔮")
        print("="*70)

        # Core systems
        self.audio = ScalarWaveGenerator()
        self.composer = IntelligentComposer()
        self.astro = AstrologicalCalculator()

        # Optional systems (graceful degradation)
        self.llm = None
        self.dharma_llm = None
        self.tts = None
        self.visual_gen = None
        self.visual_renderer = None

        # Initialize optional systems
        try:
            llm = LLMIntegration(model_type='auto')
            if llm.client or llm.local_model:
                self.llm = llm
                self.dharma_llm = DharmaLLM(llm)
                print("✓ LLM system ready (will generate prayers)")
        except Exception as e:
            print(f"ℹ LLM not available: {e}")

        try:
            self.tts = TTSEngine()
            print("✓ TTS system ready (will speak intentions)")
        except:
            print("ℹ TTS not available (silent mode)")

        try:
            self.visual_gen = RothkoGenerator()
            print("✓ Visual generator ready (Rothko meditation images)")
        except:
            print("ℹ Visual generator not available")

        if HAS_VISUAL:
            try:
                self.visual_renderer = SimpleVisualRenderer()
                print("✓ Visual renderer ready (mandalas)")
            except:
                print("ℹ Visual renderer not available")

        # Prayer wheel
        self.prayer_wheel = PrayerWheel(
            llm_integration=self.llm,
            audio_generator=self.audio,
            tts_engine=self.tts
        )

        # Enhanced radionics capabilities
        self.radionics_analyzer = None
        self.gv_meter = None
        if HAS_RADIONICS_ENGINE:
            try:
                self.radionics_analyzer = RadionicsAnalyzer()
                self.gv_meter = GeneralVitalityMeter()

                # Load rate databases
                from pathlib import Path
                rate_dir = Path(__file__).parent.parent / "knowledge" / "radionics_rates"
                if rate_dir.exists():
                    for db_file in rate_dir.glob("*.json"):
                        db = RateDatabase(str(db_file))
                        for rate in db.rates:
                            self.radionics_analyzer.rate_database.add_rate(rate)

                total_rates = len(self.radionics_analyzer.rate_database.rates)
                print(f"✓ Radionics Analysis Engine ready ({total_rates} rates loaded)")
            except Exception as e:
                print(f"ℹ Radionics analysis not available: {e}")

        # Astrocartography capabilities
        self.astrocarto = None
        self.historical_chart = None
        if HAS_ASTROCARTOGRAPHY:
            try:
                self.astrocarto = AstrocartographyCalculator()
                self.historical_chart = HistoricalChartCalculator()
                print(f"✓ Astrocartography ready (13,000 BC - 17,000 AD range)")
            except Exception as e:
                print(f"ℹ Astrocartography not available: {e}")

        # Database
        self.db_path = db_path
        self.session_id = None

        print("="*70)
        print("✅ RADIONICS SYSTEM READY FOR OPERATION")
        print("="*70 + "\n")

    def broadcast_intention(self,
                          intention: str,
                          duration: int = 3600,
                          location: tuple = None,
                          with_astrology: bool = True,
                          with_prayer: bool = True,
                          with_audio: bool = True,
                          with_visuals: bool = True,
                          with_voice: bool = False,
                          continuous: bool = False,
                          with_analysis: bool = False,
                          with_gv_measurement: bool = False):
        """
        MAIN RADIONICS OPERATION
        Broadcast healing intention through crystal grid

        Args:
            intention: What to broadcast (e.g., "healing for all beings")
            duration: Broadcast duration in seconds (default 1 hour)
            location: (lat, lon) for astrological alignment
            with_astrology: Use astrologically-optimized frequencies
            with_prayer: Generate prayer text
            with_audio: Broadcast frequencies
            with_visuals: Generate meditation visuals
            with_voice: Speak the intention
            continuous: Run continuously (ignores duration)
            with_analysis: Perform radionics rate analysis
            with_gv_measurement: Measure General Vitality before/after
        """
        print("\n" + "🌟"*35)
        print("🔮 RADIONICS BROADCASTING OPERATION INITIATED 🔮")
        print("🌟"*35)
        print(f"\n📡 TARGET INTENTION: {intention}")
        print(f"⏰ DURATION: {'CONTINUOUS' if continuous else f'{duration} seconds ({duration/60:.1f} minutes)'}")
        print(f"🌍 LOCATION: {location if location else 'Not specified (universal broadcast)'}")
        print(f"\n{'='*70}\n")

        # Start database session
        self._start_session(intention, duration)

        # Step 1: Astrological Assessment
        if with_astrology:
            print("🔮 STEP 1: ASTROLOGICAL ALIGNMENT")
            print("-" * 70)
            energetics = self.astro.get_current_energetics(datetime.now(), location)
            print(format_astrological_report(energetics))

            # Get recommended frequencies
            frequencies = self.astro.recommend_frequencies_for_time()
            print(f"\n✨ Astrologically-aligned frequencies selected: {frequencies}\n")

            # Save astrological snapshot
            self._save_astrology_snapshot(energetics, frequencies)
        else:
            # Default frequency set
            frequencies = [7.83, 136.1, 528, 639, 741]
            print(f"Using default frequencies: {frequencies}\n")

        # Step 1.5: Radionics Analysis (if requested)
        baseline_gv = None
        analysis_result = None
        if (with_analysis or with_gv_measurement) and self.radionics_analyzer:
            step_num = 2 if with_astrology else 1
            print(f"🔬 STEP {step_num}: RADIONICS ANALYSIS")
            print("-" * 70)

            # Measure baseline General Vitality
            if with_gv_measurement and self.gv_meter:
                print("📊 Measuring baseline General Vitality...")
                gv_stats = self.gv_meter.measure_multiple(count=10, subject=intention)
                baseline_gv = gv_stats['mean']
                interpretation = self.gv_meter.interpret_gv(baseline_gv)
                print(f"   GV: {baseline_gv:.1f}")
                print(f"   Status: {interpretation}\n")

            # Perform rate analysis
            if with_analysis:
                print("🔮 Performing rate analysis...")
                context = {}
                if with_astrology:
                    context = {
                        'moon_phase': energetics.get('moon_phase', ''),
                        'hour': datetime.now().hour,
                        'intention_length': len(intention)
                    }

                analysis_result = self.radionics_analyzer.analyze_subject(
                    intention,
                    num_rates=5,
                    context=context
                )
                print("✓ Analysis complete\n")

        # Step 2: Prayer Generation
        prayer_text = None
        if with_prayer:
            print("🙏 STEP 2: PRAYER GENERATION")
            print("-" * 70)

            if self.dharma_llm:
                print("Generating prayer with LLM...\n")
                prayer_text = self.dharma_llm.generate_prayer(intention, tradition='universal')
                print(f"📜 PRAYER:\n{prayer_text}\n")

                # Save to database
                self._save_llm_generation('prayer', intention, prayer_text)
            else:
                # Use traditional prayer from prayer wheel
                prayer_text = self.prayer_wheel.generate_prayer(intention, use_llm=False)
                print(f"📜 TRADITIONAL PRAYER:\n{prayer_text}\n")

            # Speak it if TTS available and requested
            if with_voice and self.tts and prayer_text:
                print("🗣️ Speaking prayer...")
                self.tts.speak_prayer_slowly(prayer_text, pause_per_line=2.0)
                print()

        # Step 3: Visual Generation
        if with_visuals and self.visual_gen:
            print("🎨 STEP 3: VISUAL MEDITATION GENERATION")
            print("-" * 70)
            print("Generating Rothko-style meditation visual...")

            try:
                img = self.visual_gen.generate_for_mood(intention)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filepath = f"./generated/rothko/radionics_{timestamp}.png"
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                img.save(filepath)
                print(f"✓ Visual saved: {filepath}\n")

                self._save_visual(intention, filepath)
            except Exception as e:
                print(f"⚠ Visual generation failed: {e}\n")

        # Step 4: CRYSTAL GRID BROADCASTING
        print("💎 STEP 4: CRYSTAL GRID BROADCASTING")
        print("="*70)
        print("🔊 BROADCASTING THROUGH CRYSTAL GRID NOW...")
        print("\n📡 Radionic transmission active")
        print("🔮 Crystal grid amplifying intention")
        print("🌊 Scalar waves emanating")
        print("\n" + "="*70 + "\n")

        if with_audio:
            if continuous:
                self._broadcast_continuous(intention, frequencies, prayer_text)
            else:
                self._broadcast_timed(intention, frequencies, prayer_text, duration)
        else:
            print("(Audio disabled - holding intention silently)")
            try:
                if continuous:
                    while True:
                        time.sleep(60)
                else:
                    time.sleep(duration)
            except KeyboardInterrupt:
                pass

        # Final GV measurement (if requested)
        if with_gv_measurement and self.gv_meter and baseline_gv is not None:
            print("\n" + "="*70)
            print("📊 FINAL GENERAL VITALITY MEASUREMENT")
            print("="*70)

            final_gv_stats = self.gv_meter.measure_multiple(count=10, subject=intention)
            final_gv = final_gv_stats['mean']
            gv_change = final_gv - baseline_gv

            print(f"\nBaseline GV: {baseline_gv:.1f}")
            print(f"Final GV:    {final_gv:.1f}")
            print(f"Change:      {gv_change:+.1f}")

            if gv_change > 20:
                trend = "✓ IMPROVING - Vitality increased significantly"
            elif gv_change < -20:
                trend = "⚠ DECLINING - Consider additional support"
            else:
                trend = "→ STABLE - Maintaining current state"

            print(f"Trend:       {trend}")
            print(f"\nFinal Status: {self.gv_meter.interpret_gv(final_gv)}")
            print("="*70 + "\n")

        # End session
        self._end_session()

        print("\n" + "="*70)
        print("✅ RADIONICS OPERATION COMPLETE")
        print("="*70)
        print("\n🙏 DEDICATION:")
        print("May all merit from this radionics operation")
        print("benefit all beings throughout space and time.")
        print("May healing reach wherever it is needed.")
        print("\nGate gate pāragate pārasaṃgate bodhi svāhā 🙏")
        print("\n" + "="*70 + "\n")

    def broadcast_to_time_location(self,
                                   intention: str,
                                   year: int, month: int, day: int,
                                   hour: int = 12, minute: int = 0,
                                   latitude: float = None, longitude: float = None,
                                   location_name: str = "",
                                   duration: int = 3600,
                                   calendar_type: str = 'auto',
                                   with_astrocartography: bool = True,
                                   with_prayer: bool = True,
                                   with_audio: bool = True):
        """
        Broadcast intention to a specific time and place in history.

        Useful for:
        - Sending healing to ancestral locations
        - Broadcasting to significant historical events
        - Working with specific planetary alignments at past times
        - Location-based healing across time

        Args:
            intention: What to broadcast
            year, month, day, hour, minute: Target date/time (negative year for BCE)
            latitude, longitude: Target location coordinates
            location_name: Name of location
            duration: Broadcasting duration in seconds
            calendar_type: 'gregorian', 'julian', or 'auto'
            with_astrocartography: Calculate planetary lines for that time
            with_prayer: Generate prayer
            with_audio: Broadcast with audio
        """
        print("\n" + "🌟"*35)
        print("⏰ TIME & LOCATION RADIONICS BROADCAST ⏰")
        print("🌟"*35)

        # Format target date
        if year < 0:
            date_str = f"{abs(year)} BCE / {month:02d} / {day:02d} {hour:02d}:{minute:02d}"
        else:
            date_str = f"{year} CE / {month:02d} / {day:02d} {hour:02d}:{minute:02d}"

        print(f"\n📡 INTENTION: {intention}")
        print(f"⏰ TARGET TIME: {date_str} ({calendar_type} calendar)")

        if latitude is not None and longitude is not None:
            print(f"📍 TARGET LOCATION: {location_name if location_name else 'Unknown'}")
            print(f"   Coordinates: {latitude}°N, {longitude}°E")
        else:
            print(f"📍 TARGET LOCATION: Universal (no specific location)")

        print(f"⏱️  BROADCAST DURATION: {duration} seconds ({duration/60:.1f} minutes)")
        print(f"\n{'='*70}\n")

        # Start session
        self._start_session(f"{intention} @ {date_str}", duration)

        # Calculate historical chart if location provided
        if self.historical_chart and latitude is not None and longitude is not None:
            print("📜 HISTORICAL CHART CALCULATION")
            print("-" * 70)

            chart = self.historical_chart.calculate_chart(
                year, month, day, hour, minute, 0,
                latitude, longitude, location_name, calendar_type
            )

            print(f"Julian Day: {chart['julian_day']:.2f}")
            print(f"\nPlanetary Positions at {location_name}:")

            for planet in ['sun', 'moon', 'venus', 'jupiter']:
                if planet in chart['planets']:
                    p = chart['planets'][planet]
                    retro = " (R)" if p['retrograde'] else ""
                    print(f"  {planet.capitalize():10s}: {p['degree']:6.2f}° {p['sign']}{retro}")

            print(f"\nAscendant: {chart['houses']['angles']['ascendant']:.2f}°")
            print(f"Midheaven: {chart['houses']['angles']['mc']:.2f}°")
            print()

        # Calculate astrocartography if enabled
        frequencies = [7.83, 136.1, 528, 639, 741]  # Default

        if with_astrocartography and self.astrocarto:
            print("🗺️  ASTROCARTOGRAPHY ANALYSIS")
            print("-" * 70)

            lines = self.astrocarto.calculate_planetary_lines(
                year, month, day, hour, minute, 0,
                ['jupiter', 'venus', 'sun', 'moon'], calendar_type
            )

            print(f"Benefic planetary lines for {date_str}:\n")

            for planet in ['jupiter', 'venus']:
                if planet in lines['lines']:
                    p_lines = lines['lines'][planet]
                    print(f"{planet.upper()}:")
                    for angle in ['MC', 'ASC']:
                        if angle in p_lines:
                            lon = p_lines[angle]['longitude']
                            if lon > 180:
                                lon_str = f"{360-lon:.1f}°W"
                            elif lon < 0:
                                lon_str = f"{abs(lon):.1f}°W"
                            else:
                                lon_str = f"{lon:.1f}°E"
                            print(f"  {angle}: {lon_str}")
                    print()

        # Prayer generation
        prayer_text = None
        if with_prayer:
            print("🙏 PRAYER GENERATION")
            print("-" * 70)

            prayer_context = f"{intention} for {location_name if location_name else 'all beings'} at {date_str}"

            if self.dharma_llm:
                prayer_text = self.dharma_llm.generate_prayer(prayer_context, tradition='universal')
                print(f"📜 PRAYER:\n{prayer_text}\n")
                self._save_llm_generation('prayer', prayer_context, prayer_text)
            else:
                prayer_text = self.prayer_wheel.generate_prayer(prayer_context, use_llm=False)
                print(f"📜 TRADITIONAL PRAYER:\n{prayer_text}\n")

        # BROADCASTING
        print("💎 TIME-LOCATION BROADCASTING")
        print("="*70)
        print("🔊 BROADCASTING THROUGH CRYSTAL GRID NOW...")
        print(f"\n📡 Sending intention to: {date_str}")
        if location_name:
            print(f"📍 Location: {location_name}")
        print("🔮 Crystal grid amplifying intention across time")
        print("🌊 Scalar waves emanating to target coordinates")
        print("\n" + "="*70 + "\n")

        if with_audio:
            self._broadcast_timed(intention, frequencies, prayer_text, duration)
        else:
            print("(Audio disabled - holding intention silently)")
            try:
                time.sleep(duration)
            except KeyboardInterrupt:
                pass

        # End session
        self._end_session()

        print("\n" + "="*70)
        print("✅ TIME-LOCATION BROADCAST COMPLETE")
        print("="*70)
        print(f"\n🙏 Intention sent to {date_str}")
        if location_name:
            print(f"   Location: {location_name}")
        print("\nMay healing reach across time and space.")
        print("May all beings benefit from this transmission.")
        print("\n" + "="*70 + "\n")

    def _broadcast_timed(self, intention, frequencies, prayer_text, duration):
        """Broadcast for specified duration"""
        # Use intelligent composer for harmonic broadcasting
        print(f"Composing harmonic broadcast pattern...")

        # Create prayer bowl synthesis with our frequencies
        wave = self.composer.compose_harmonic_layers(
            frequencies=frequencies,
            duration=duration,
            pattern='evolving'  # Evolving harmonies
        )

        print(f"Playing {duration} second broadcast...")
        print(f"Frequencies: {frequencies}")
        print("\n💫 Broadcasting intention through crystal grid...")
        print("(Place written intention in center of crystal grid)")
        print("\nPress Ctrl+C to stop early\n")

        try:
            import sounddevice as sd
            sd.play(wave, samplerate=self.audio.sample_rate)
            sd.wait()
        except KeyboardInterrupt:
            import sounddevice as sd
            sd.stop()
            print("\n\n⏸️ Broadcast interrupted by user")

    def _broadcast_continuous(self, intention, frequencies, prayer_text):
        """Broadcast continuously until stopped"""
        print("♾️ CONTINUOUS BROADCASTING MODE")
        print("This will run until you press Ctrl+C")
        print("="*70 + "\n")

        rotation_count = 0

        try:
            while True:
                rotation_count += 1
                print(f"\n🔄 Rotation {rotation_count} - {datetime.now().strftime('%I:%M:%S %p')}")

                # 5-minute segments
                segment_duration = 300

                # Generate new prayer each rotation if LLM available
                if self.dharma_llm and rotation_count % 3 == 1:  # Every 3rd rotation
                    prayer_text = self.dharma_llm.generate_prayer(intention)
                    print(f"📜 New prayer:\n{prayer_text}\n")

                # Broadcast segment
                wave = self.composer.compose_harmonic_layers(
                    frequencies=frequencies,
                    duration=segment_duration,
                    pattern='evolving'
                )

                print(f"Broadcasting segment {rotation_count}...")
                import sounddevice as sd
                sd.play(wave, samplerate=self.audio.sample_rate)
                sd.wait()

                # Brief pause between rotations
                time.sleep(2)

        except KeyboardInterrupt:
            print(f"\n\n⏸️ Continuous broadcast stopped after {rotation_count} rotations")
            print(f"Total broadcast time: ~{rotation_count * 5} minutes")

    # Database methods
    def _start_session(self, intention, duration):
        """Start database session"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO sessions (session_type, start_time, intention, settings)
                VALUES (?, ?, ?, ?)
            ''', ('radionics_broadcast', datetime.now(), intention, f'duration={duration}'))

            self.session_id = cursor.lastrowid
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"⚠ Database logging failed: {e}")

    def _save_astrology_snapshot(self, energetics, frequencies):
        """Save astrological snapshot to database"""
        if not self.session_id:
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            moon_phase = energetics['moon_phase']['phase_name']
            moon_illum = energetics['moon_phase']['illumination']
            nakshatra = energetics['lunar_mansion']['name']

            cursor.execute('''
                INSERT INTO astrological_snapshots
                (timestamp, moon_phase, moon_illumination, lunar_mansion,
                 recommended_frequencies)
                VALUES (?, ?, ?, ?, ?)
            ''', (datetime.now(), moon_phase, moon_illum, nakshatra,
                  ','.join(map(str, frequencies))))

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"⚠ Astrology snapshot save failed: {e}")

    def _save_llm_generation(self, prompt_type, prompt, generated):
        """Save LLM generation to database"""
        if not self.session_id:
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO llm_generations
                (session_id, prompt_type, prompt_text, generated_text,
                 model_used, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (self.session_id, prompt_type, prompt, generated,
                  self.llm.model_name if self.llm else 'none', datetime.now()))

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"⚠ LLM generation save failed: {e}")

    def _save_visual(self, intention, filepath):
        """Save visual generation record"""
        if not self.session_id:
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO generated_visuals
                (session_id, intention, filepath, created_at)
                VALUES (?, ?, ?, ?)
            ''', (self.session_id, intention, filepath, datetime.now()))

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"⚠ Visual save failed: {e}")

    def _end_session(self):
        """End database session"""
        if not self.session_id:
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE sessions SET end_time = ? WHERE id = ?
            ''', (datetime.now(), self.session_id))

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"⚠ Session end failed: {e}")


# PRESET OPERATIONS
PRESETS = {
    'world_peace': {
        'intention': 'May peace prevail throughout the world. May all conflicts cease. May all beings live in harmony.',
        'duration': 7200,  # 2 hours
        'description': 'Global peace broadcast'
    },
    'heart_healing': {
        'intention': 'May the hearts of all beings be healed. May love flow freely. May compassion blossom.',
        'duration': 3600,  # 1 hour
        'description': 'Heart chakra healing for all'
    },
    'planetary_healing': {
        'intention': 'May the Earth be healed. May all ecosystems be restored. May humanity awaken to harmony with nature.',
        'duration': 10800,  # 3 hours
        'description': 'Environmental/planetary healing'
    },
    'protection': {
        'intention': 'May all beings be protected from harm. May safety and security be established. May fear dissolve.',
        'duration': 3600,
        'description': 'Protection for all beings'
    },
    'awakening': {
        'intention': 'May all beings awaken to their true nature. May wisdom dawn. May liberation be swift.',
        'duration': 5400,  # 90 minutes
        'description': 'Collective awakening'
    },
}


def main():
    parser = argparse.ArgumentParser(
        description='Vajra.Stream Radionics Operation - Crystal Grid Broadcasting'
    )

    parser.add_argument('--intention', type=str,
                       help='Intention to broadcast')
    parser.add_argument('--target', type=str,
                       help='Target for broadcast (synonym for --intention)')
    parser.add_argument('--duration', type=int, default=3600,
                       help='Duration in seconds (default 3600 = 1 hour)')
    parser.add_argument('--continuous', action='store_true',
                       help='Run continuously until stopped')
    parser.add_argument('--preset', choices=list(PRESETS.keys()),
                       help='Use preset operation')
    parser.add_argument('--latitude', type=float,
                       help='Latitude for astrological alignment')
    parser.add_argument('--longitude', type=float,
                       help='Longitude for astrological alignment')
    parser.add_argument('--no-astrology', action='store_true',
                       help='Disable astrological alignment')
    parser.add_argument('--no-prayer', action='store_true',
                       help='Disable prayer generation')
    parser.add_argument('--no-audio', action='store_true',
                       help='Disable audio (silent operation)')
    parser.add_argument('--no-visuals', action='store_true',
                       help='Disable visual generation')
    parser.add_argument('--with-voice', action='store_true',
                       help='Speak intentions aloud (requires TTS)')
    parser.add_argument('--with-analysis', action='store_true',
                       help='Perform radionics rate analysis before broadcasting')
    parser.add_argument('--with-gv', action='store_true',
                       help='Measure General Vitality before and after broadcasting')

    # Time/location broadcasting
    parser.add_argument('--to-time', action='store_true',
                       help='Broadcast to a specific time and place')
    parser.add_argument('--year', type=int,
                       help='Target year (negative for BCE, e.g., -100 for 100 BCE)')
    parser.add_argument('--month', type=int,
                       help='Target month (1-12)')
    parser.add_argument('--day', type=int,
                       help='Target day')
    parser.add_argument('--hour', type=int, default=12,
                       help='Target hour (0-23, default 12)')
    parser.add_argument('--minute', type=int, default=0,
                       help='Target minute (0-59, default 0)')
    parser.add_argument('--location-name', type=str,
                       help='Name of target location')
    parser.add_argument('--calendar', type=str, default='auto',
                       choices=['auto', 'gregorian', 'julian'],
                       help='Calendar system for historical dates')

    parser.add_argument('--list-presets', action='store_true',
                       help='List available presets and exit')

    args = parser.parse_args()

    # List presets
    if args.list_presets:
        print("\n" + "="*70)
        print("AVAILABLE RADIONICS PRESETS")
        print("="*70 + "\n")
        for name, config in PRESETS.items():
            print(f"🔮 {name}")
            print(f"   {config['description']}")
            print(f"   Duration: {config['duration']/60:.0f} minutes")
            print(f"   Intention: {config['intention'][:60]}...")
            print()
        return

    # Determine intention
    if args.preset:
        config = PRESETS[args.preset]
        intention = config['intention']
        duration = config['duration']
        print(f"\n🔮 Using preset: {args.preset}")
        print(f"   {config['description']}\n")
    elif args.intention or args.target:
        intention = args.intention or args.target
        duration = args.duration
    else:
        print("\n⚠️ Error: Must specify --intention, --target, or --preset")
        print("\nExamples:")
        print("  python scripts/radionics_operation.py --intention \"healing for all\"")
        print("  python scripts/radionics_operation.py --preset world_peace")
        print("  python scripts/radionics_operation.py --target \"peace\" --continuous")
        print("\nUse --list-presets to see available presets")
        return

    # Initialize
    ops = RadionicsOperation()

    # Check if broadcasting to specific time/location
    if args.to_time:
        # Validate required arguments
        if args.year is None or args.month is None or args.day is None:
            print("\n⚠️ Error: --to-time requires --year, --month, and --day")
            print("\nExample:")
            print("  python scripts/radionics_operation.py --to-time \\")
            print("    --intention \"healing for ancestors\" \\")
            print("    --year 1900 --month 1 --day 1 \\")
            print("    --latitude 40.7 --longitude -74.0 \\")
            print("    --location-name \"New York City\"")
            return

        # Time/location broadcast
        ops.broadcast_to_time_location(
            intention=intention,
            year=args.year,
            month=args.month,
            day=args.day,
            hour=args.hour,
            minute=args.minute,
            latitude=args.latitude,
            longitude=args.longitude,
            location_name=args.location_name or "",
            duration=duration,
            calendar_type=args.calendar,
            with_astrocartography=True,
            with_prayer=not args.no_prayer,
            with_audio=not args.no_audio
        )
    else:
        # Normal present-time broadcast
        location = None
        if args.latitude and args.longitude:
            location = (args.latitude, args.longitude)

        ops.broadcast_intention(
            intention=intention,
            duration=duration,
            location=location,
            with_astrology=not args.no_astrology,
            with_prayer=not args.no_prayer,
            with_audio=not args.no_audio,
            with_visuals=not args.no_visuals,
            with_voice=args.with_voice,
            continuous=args.continuous,
            with_analysis=args.with_analysis,
            with_gv_measurement=args.with_gv
        )


if __name__ == "__main__":
    main()
