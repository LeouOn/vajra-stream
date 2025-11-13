#!/usr/bin/env python3
"""
Vajra.Stream - Main Orchestrator
Integrates all systems: astrology, LLM, prayer wheel, audio, visuals, TTS
Complete dharma technology platform
"""

import sys
import os
import argparse
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.audio_generator import ScalarWaveGenerator
from core.llm_integration import LLMIntegration, DharmaLLM
from core.prayer_wheel import PrayerWheel
from core.tts_engine import TTSEngine, GuidedMeditationSpeaker
from core.rothko_generator import RothkoGenerator
from core.astrology import AstrologicalCalculator, format_astrological_report


class VajraOrchestrator:
    """
    Main orchestrator - coordinates all Vajra.Stream systems
    """

    def __init__(self, enable_audio: bool = True, enable_llm: bool = True,
                 enable_tts: bool = True, enable_visuals: bool = True):
        """
        Initialize all systems

        Args:
            enable_audio: Enable audio/frequency generation
            enable_llm: Enable LLM integration
            enable_tts: Enable text-to-speech
            enable_visuals: Enable visual generation
        """
        print("\n" + "="*60)
        print("VAJRA.STREAM - INITIALIZING")
        print("="*60 + "\n")

        # Audio generator
        self.audio = None
        if enable_audio:
            try:
                self.audio = ScalarWaveGenerator()
                print("✓ Audio generator ready")
            except Exception as e:
                print(f"✗ Audio generator failed: {e}")

        # LLM integration
        self.llm = None
        self.dharma_llm = None
        if enable_llm:
            try:
                self.llm = LLMIntegration(model_type='auto')
                if self.llm.client or self.llm.local_model:
                    self.dharma_llm = DharmaLLM(self.llm)
                    print("✓ LLM integration ready")
                else:
                    print("ℹ LLM not configured (optional)")
            except Exception as e:
                print(f"ℹ LLM initialization skipped: {e}")

        # TTS engine
        self.tts = None
        if enable_tts:
            try:
                self.tts = TTSEngine(rate=150, volume=0.9)
                print("✓ TTS engine ready")
            except Exception as e:
                print(f"ℹ TTS not available: {e}")

        # Visual generator
        self.visuals = None
        if enable_visuals:
            try:
                self.visuals = RothkoGenerator()
                print("✓ Visual generator ready")
            except Exception as e:
                print(f"✗ Visual generator failed: {e}")

        # Astrology calculator
        self.astrology = AstrologicalCalculator()
        print("✓ Astrology calculator ready")

        # Prayer wheel
        self.prayer_wheel = PrayerWheel(
            llm_integration=self.llm,
            audio_generator=self.audio,
            tts_engine=self.tts
        )
        print("✓ Prayer wheel ready")

        print("\n" + "="*60)
        print("INITIALIZATION COMPLETE")
        print("="*60 + "\n")

    def show_current_energetics(self, location: tuple = None):
        """
        Display current astrological energetics

        Args:
            location: (latitude, longitude) tuple
        """
        now = datetime.now()
        data = self.astrology.get_current_energetics(now, location)

        print(format_astrological_report(data))

        # Recommend frequencies
        freqs = self.astrology.recommend_frequencies_for_time(now)
        print("\nRecommended Frequencies for Current Time:")
        for freq in freqs:
            print(f"  {freq} Hz")

        # Calendar events
        events = self.astrology.get_dharma_calendar_events(now)
        if events:
            print("\nDharma Calendar Events:")
            for event in events:
                print(f"  • {event}")

        print()

    def generate_and_broadcast_prayer(self, intention: str = "peace",
                                     duration: int = 60, use_llm: bool = True,
                                     with_audio: bool = True, with_voice: bool = True,
                                     with_visual: bool = True, astrological: bool = True):
        """
        Complete prayer generation and broadcast using all systems

        Args:
            intention: Prayer intention
            duration: Broadcast duration
            use_llm: Generate new prayer with LLM
            with_audio: Include frequency broadcast
            with_voice: Speak prayer with TTS
            with_visual: Generate Rothko meditation image
            astrological: Use astrologically-aligned frequencies
        """
        print(f"\n{'='*60}")
        print(f"VAJRA.STREAM - PRAYER GENERATION & BROADCAST")
        print(f"{'='*60}")
        print(f"Intention: {intention}")
        print(f"Time: {datetime.now().strftime('%I:%M %p on %B %d, %Y')}")
        print(f"{'='*60}\n")

        # Generate prayer
        prayer = self.prayer_wheel.generate_prayer(intention, use_llm=use_llm)

        print(f"Prayer Generated:")
        print(f"\n{prayer}\n")
        print(f"{'='*60}\n")

        # Determine frequencies
        frequencies = None
        if astrological and self.astrology:
            frequencies = self.astrology.recommend_frequencies_for_time()
            print("Using astrologically-aligned frequencies:")
            for freq in frequencies:
                print(f"  {freq} Hz")
            print()

        # Generate visual if requested
        if with_visual and self.visuals:
            print("Generating contemplation visual...")
            img = self.visuals.generate_for_mood(intention)

            # Save image
            output_dir = './generated/rothko'
            os.makedirs(output_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = f"{output_dir}/{intention}_{timestamp}.png"
            img.save(filepath)
            print(f"✓ Visual saved: {filepath}\n")

        # Broadcast prayer
        self.prayer_wheel.spin(
            prayer,
            duration=duration,
            with_audio=with_audio,
            with_voice=with_voice,
            frequencies=frequencies
        )

        print(f"\n{'='*60}")
        print(f"DEDICATION")
        print(f"{'='*60}")
        print("May all merit from this practice benefit all beings")
        print("throughout space and time.")
        print(f"{'='*60}\n")

    def run_guided_meditation(self, practice_type: str = "loving_kindness",
                            with_audio: bool = True, duration: int = 300):
        """
        Run a guided meditation session

        Args:
            practice_type: Type of meditation
            with_audio: Include background frequencies
            duration: Total duration in seconds
        """
        if not self.dharma_llm:
            print("LLM not available. Cannot generate meditation instructions.")
            return

        print(f"\n{'='*60}")
        print(f"GUIDED MEDITATION: {practice_type.upper()}")
        print(f"{'='*60}\n")

        # Generate meditation instructions
        print("Generating meditation instructions...\n")
        instructions = self.dharma_llm.generate_meditation_instruction(practice_type)

        # Create guided meditation speaker
        if self.tts:
            guide = GuidedMeditationSpeaker(self.tts)

            # Start background frequencies if requested
            if with_audio and self.audio:
                print("Starting background frequencies...")
                # Alpha/theta waves for meditation
                wave = self.audio.generate_binaural_beat(200, 8, duration=duration)
                self.audio.play(wave, blocking=False)

            # Guide the meditation
            guide.guide_full_meditation(practice_type, instructions)

            # Stop audio
            if self.audio:
                self.audio.stop()
        else:
            # No TTS - just print instructions
            print("Meditation Instructions:")
            print(instructions)
            print("\nNote: TTS not available. Instructions printed above.")

    def continuous_blessing_stream(self, intention: str = "peace",
                                  interval: int = 300, with_llm: bool = True):
        """
        Run continuous blessing stream (24/7 mode)

        Args:
            intention: Base intention
            interval: Seconds between prayer rotations
            with_llm: Generate new prayers each time
        """
        print(f"\n{'='*60}")
        print(f"CONTINUOUS BLESSING STREAM")
        print(f"{'='*60}")
        print(f"Intention: {intention}")
        print(f"Interval: {interval} seconds ({interval/60:.1f} minutes)")
        print(f"\nThis will run continuously until stopped with Ctrl+C")
        print(f"{'='*60}\n")

        self.prayer_wheel.continuous_rotation(
            intention=intention,
            interval=interval,
            use_llm=with_llm,
            with_audio=True,
            with_voice=False  # Don't speak continuously (too much)
        )

    def generate_dharma_content(self, content_type: str, topic: str):
        """
        Generate dharma content (teaching, prayer, contemplation, etc.)

        Args:
            content_type: 'teaching', 'prayer', 'contemplation', 'dedication'
            topic: Topic or intention
        """
        if not self.dharma_llm:
            print("LLM not available. Cannot generate content.")
            return

        print(f"\n{'='*60}")
        print(f"GENERATING {content_type.upper()}")
        print(f"{'='*60}")
        print(f"Topic: {topic}\n")

        if content_type == 'teaching':
            content = self.dharma_llm.generate_teaching(topic, length='medium')
        elif content_type == 'prayer':
            content = self.dharma_llm.generate_prayer(topic)
        elif content_type == 'contemplation':
            content = self.dharma_llm.generate_contemplation(topic)
        elif content_type == 'dedication':
            content = self.dharma_llm.generate_dedication()
        else:
            print(f"Unknown content type: {content_type}")
            return

        print(content)
        print(f"\n{'='*60}\n")

        # Optionally speak it
        if self.tts:
            speak = input("Speak this content? (y/n): ").lower()
            if speak == 'y':
                if content_type == 'teaching':
                    self.tts.speak_teaching(content)
                else:
                    self.tts.speak_prayer_slowly(content)

    def create_chakra_visualization_series(self):
        """Generate Rothko-style images for all chakras"""
        if not self.visuals:
            print("Visual generator not available")
            return

        print(f"\n{'='*60}")
        print("GENERATING CHAKRA VISUALIZATION SERIES")
        print(f"{'='*60}\n")

        paths = self.visuals.generate_chakra_series()

        print(f"\n✓ Generated {len(paths)} chakra visualizations")
        print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Vajra.Stream - Digital Dharma Technology Orchestrator'
    )

    # Mode selection
    parser.add_argument(
        'mode',
        choices=['prayer', 'meditation', 'teaching', 'continuous', 'astrology',
                'chakra-visuals', 'test'],
        help='Operation mode'
    )

    # Common arguments
    parser.add_argument('--intention', type=str, default='peace',
                       help='Intention or topic')
    parser.add_argument('--duration', type=int, default=300,
                       help='Duration in seconds')
    parser.add_argument('--no-audio', action='store_true',
                       help='Disable audio generation')
    parser.add_argument('--no-llm', action='store_true',
                       help='Disable LLM generation')
    parser.add_argument('--no-tts', action='store_true',
                       help='Disable text-to-speech')
    parser.add_argument('--no-visuals', action='store_true',
                       help='Disable visual generation')

    # Location for astrology
    parser.add_argument('--latitude', type=float, help='Latitude for astrology')
    parser.add_argument('--longitude', type=float, help='Longitude for astrology')

    args = parser.parse_args()

    # Initialize orchestrator
    orchestrator = VajraOrchestrator(
        enable_audio=not args.no_audio,
        enable_llm=not args.no_llm,
        enable_tts=not args.no_tts,
        enable_visuals=not args.no_visuals
    )

    # Get location if provided
    location = None
    if args.latitude and args.longitude:
        location = (args.latitude, args.longitude)

    # Execute mode
    if args.mode == 'prayer':
        orchestrator.generate_and_broadcast_prayer(
            intention=args.intention,
            duration=args.duration,
            use_llm=not args.no_llm,
            with_audio=not args.no_audio,
            with_voice=not args.no_tts,
            with_visual=not args.no_visuals,
            astrological=True
        )

    elif args.mode == 'meditation':
        orchestrator.run_guided_meditation(
            practice_type=args.intention,
            with_audio=not args.no_audio,
            duration=args.duration
        )

    elif args.mode == 'teaching':
        orchestrator.generate_dharma_content('teaching', args.intention)

    elif args.mode == 'continuous':
        orchestrator.continuous_blessing_stream(
            intention=args.intention,
            interval=args.duration,
            with_llm=not args.no_llm
        )

    elif args.mode == 'astrology':
        orchestrator.show_current_energetics(location)

    elif args.mode == 'chakra-visuals':
        orchestrator.create_chakra_visualization_series()

    elif args.mode == 'test':
        print("\nTesting all systems...")
        print("="*60)

        # Test astrology
        print("\n1. Astrology System:")
        orchestrator.show_current_energetics(location)

        # Test visual
        if not args.no_visuals:
            print("\n2. Visual Generation:")
            orchestrator.create_chakra_visualization_series()

        # Test prayer generation
        print("\n3. Prayer Generation:")
        orchestrator.generate_and_broadcast_prayer(
            intention="testing all systems",
            duration=10,
            use_llm=not args.no_llm,
            with_audio=not args.no_audio,
            with_voice=False,  # Skip voice in test
            with_visual=False  # Already tested
        )

        print("\n" + "="*60)
        print("✓ System test complete")
        print("="*60 + "\n")


if __name__ == "__main__":
    main()
