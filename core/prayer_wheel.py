"""
Vajra.Stream - Digital Prayer Wheel
Continuous generation and emanation of prayers, mantras, and aspirations
Combines ancient prayer wheel technology with modern LLM and audio systems
"""

import time
from datetime import datetime
from typing import Optional, List, Dict
import json
import os
from pathlib import Path


class PrayerWheel:
    """
    Digital prayer wheel - generates and broadcasts prayers continuously
    Like a traditional Tibetan prayer wheel, but powered by AI and frequency generation
    """

    def __init__(self, llm_integration=None, audio_generator=None, tts_engine=None):
        """
        Initialize prayer wheel

        Args:
            llm_integration: LLMIntegration instance for generating prayers
            audio_generator: ScalarWaveGenerator instance for frequencies
            tts_engine: TTSEngine instance for speaking prayers
        """
        self.llm = llm_integration
        self.audio = audio_generator
        self.tts = tts_engine

        # Load traditional prayers and mantras
        self.traditional_prayers = self._load_traditional_prayers()

        # Session tracking
        self.session_start = None
        self.prayers_generated = 0
        self.rotations = 0  # Like counting physical wheel spins

    def _load_traditional_prayers(self) -> Dict[str, List[str]]:
        """Load library of traditional prayers and mantras"""
        return {
            'mantras': [
                "Om Mani Padme Hum",  # Avalokiteshvara - compassion
                "Om Tare Tuttare Ture Soha",  # Green Tara - protection
                "Gate Gate Paragate Parasamgate Bodhi Svaha",  # Heart Sutra
                "Om Ah Hum Vajra Guru Padma Siddhi Hum",  # Guru Rinpoche
                "Tayata Om Bekanze Bekanze Maha Bekanze Radza Samudgate Soha",  # Medicine Buddha
                "Om Ah Ra Pa Tsa Na Dhih",  # Manjushri - wisdom
            ],
            'aspirations': [
                "May all beings be happy and free from suffering",
                "May all beings have happiness and the causes of happiness",
                "May all beings be free from suffering and the causes of suffering",
                "May all beings never be separated from the great happiness devoid of suffering",
                "May all beings dwell in equanimity, free from attachment and aversion",
            ],
            'dedications': [
                "By this merit may all obtain omniscience. May it defeat the enemy, wrongdoing.",
                "May all beings be freed from the stormy waves of birth, old age, sickness and death.",
                "For as long as space endures, and for as long as living beings remain, "
                "until then may I too abide to dispel the misery of the world.",
            ],
            'bodhisattva_vows': [
                "Sentient beings are numberless; I vow to liberate them all",
                "Delusions are inexhaustible; I vow to end them all",
                "Dharma gates are boundless; I vow to enter them all",
                "Buddha's way is unsurpassable; I vow to become it",
            ]
        }

    def generate_prayer(self, intention: str = "peace", use_llm: bool = True,
                       tradition: str = 'universal') -> str:
        """
        Generate a prayer based on intention

        Args:
            intention: What to pray for
            use_llm: Use LLM to generate new prayer (if available)
            tradition: Prayer tradition style
        """
        if use_llm and self.llm:
            # Generate fresh prayer using LLM
            from core.llm_integration import DharmaLLM
            dharma = DharmaLLM(self.llm)
            prayer = dharma.generate_prayer(intention, tradition)
        else:
            # Use traditional prayer
            prayer = self._select_traditional_prayer(intention)

        self.prayers_generated += 1
        return prayer

    def _select_traditional_prayer(self, intention: str) -> str:
        """Select appropriate traditional prayer based on intention"""
        intention_lower = intention.lower()

        # Map intentions to prayer types
        if 'wisdom' in intention_lower or 'insight' in intention_lower:
            # Manjushri mantra
            return "Om Ah Ra Pa Tsa Na Dhih"

        elif 'healing' in intention_lower or 'health' in intention_lower:
            # Medicine Buddha mantra
            return "Tayata Om Bekanze Bekanze Maha Bekanze Radza Samudgate Soha"

        elif 'protection' in intention_lower or 'safety' in intention_lower:
            # Green Tara
            return "Om Tare Tuttare Ture Soha"

        elif 'compassion' in intention_lower or 'love' in intention_lower:
            # Avalokiteshvara
            return "Om Mani Padme Hum"

        else:
            # Default to general aspiration
            import random
            return random.choice(self.traditional_prayers['aspirations'])

    def spin(self, prayer: str, duration: int = 60, with_audio: bool = True,
            with_voice: bool = False, frequencies: List[float] = None):
        """
        'Spin' the prayer wheel - broadcast prayer with audio and/or voice

        Args:
            prayer: Prayer text to broadcast
            duration: How long to spin (seconds)
            with_audio: Include frequency generation
            with_voice: Speak the prayer using TTS
            frequencies: Specific frequencies to use
        """
        print(f"\n{'='*60}")
        print(f"PRAYER WHEEL SPINNING")
        print(f"{'='*60}")
        print(f"Prayer: {prayer}")
        print(f"Duration: {duration} seconds")
        print(f"{'='*60}\n")

        # Speak prayer if TTS available
        if with_voice and self.tts:
            print("Speaking prayer...")
            self.tts.speak(prayer)

        # Generate carrier frequencies if audio available
        if with_audio and self.audio:
            print("Generating carrier frequencies...")

            if frequencies is None:
                # Default blessing frequencies
                frequencies = [7.83, 136.1, 528, 639]

            # Create frequency list for audio generator
            freq_list = [(f, 1.0) for f in frequencies]

            # Generate and play
            wave = self.audio.layer_frequencies(freq_list, duration=duration)
            self.audio.play(wave, blocking=False)

            # Wait for duration
            print(f"Broadcasting for {duration} seconds...\n")
            time.sleep(duration)

            # Stop audio
            self.audio.stop()

        self.rotations += 1
        print(f"\n✓ Rotation complete (Total rotations: {self.rotations})")

    def continuous_rotation(self, intention: str = "peace", interval: int = 60,
                          use_llm: bool = True, with_audio: bool = True,
                          with_voice: bool = False):
        """
        Continuously generate and broadcast prayers
        Like keeping a prayer wheel spinning perpetually

        Args:
            intention: Base intention for prayers
            interval: Seconds between prayer rotations
            use_llm: Generate new prayers with LLM
            with_audio: Include frequency broadcast
            with_voice: Speak prayers with TTS
        """
        self.session_start = datetime.now()

        print(f"\n{'='*60}")
        print(f"CONTINUOUS PRAYER WHEEL")
        print(f"{'='*60}")
        print(f"Intention: {intention}")
        print(f"Interval: {interval} seconds")
        print(f"Started: {self.session_start.strftime('%I:%M %p')}")
        print(f"\nPress Ctrl+C to stop")
        print(f"{'='*60}\n")

        try:
            while True:
                # Generate prayer
                prayer = self.generate_prayer(intention, use_llm=use_llm)

                # Spin wheel with this prayer
                self.spin(prayer, duration=interval, with_audio=with_audio,
                         with_voice=with_voice)

                # Brief pause between rotations
                time.sleep(2)

        except KeyboardInterrupt:
            self._end_session()

    def mantra_accumulation(self, mantra: str, count: int = 108,
                           with_audio: bool = True, with_voice: bool = True,
                           duration_per: int = 10):
        """
        Accumulate mantra recitations (like traditional practice)

        Args:
            mantra: Mantra to recite
            count: Number of recitations (108 is traditional mala count)
            with_audio: Include frequencies
            with_voice: Speak mantra
            duration_per: Seconds per recitation
        """
        print(f"\n{'='*60}")
        print(f"MANTRA ACCUMULATION")
        print(f"{'='*60}")
        print(f"Mantra: {mantra}")
        print(f"Count: {count}")
        print(f"Total time: {(count * duration_per) / 60:.1f} minutes")
        print(f"{'='*60}\n")

        self.session_start = datetime.now()

        try:
            for i in range(count):
                print(f"\nRecitation {i+1}/{count}")

                # Speak mantra
                if with_voice and self.tts:
                    self.tts.speak(mantra)

                # Generate carrier wave
                if with_audio and self.audio:
                    # Use OM frequency and Schumann resonance for mantras
                    wave = self.audio.layer_frequencies(
                        [(136.1, 0.5), (7.83, 0.5)],
                        duration=duration_per
                    )
                    self.audio.play(wave, blocking=True)
                else:
                    time.sleep(duration_per)

                self.rotations += 1

                # Progress indicator
                if (i + 1) % 27 == 0:  # Quarter mala
                    print(f"  ✓ {i+1} recitations complete")

        except KeyboardInterrupt:
            print(f"\n\nMantra accumulation paused at {i+1} recitations")

        self._end_session()

    def prayer_cycle(self, theme: str = 'four_immeasurables', with_audio: bool = True):
        """
        Complete a traditional prayer cycle

        Args:
            theme: 'four_immeasurables', 'bodhisattva_vows', 'dedications'
            with_audio: Include audio frequencies
        """
        cycles = {
            'four_immeasurables': [
                "May all beings have happiness and the causes of happiness",
                "May all beings be free from suffering and the causes of suffering",
                "May all beings never be separated from the great happiness devoid of suffering",
                "May all beings dwell in equanimity, free from attachment and aversion",
            ],
            'bodhisattva_vows': self.traditional_prayers['bodhisattva_vows'],
            'dedications': self.traditional_prayers['dedications']
        }

        prayers = cycles.get(theme, cycles['four_immeasurables'])

        print(f"\n{'='*60}")
        print(f"PRAYER CYCLE: {theme.upper()}")
        print(f"{'='*60}\n")

        for i, prayer in enumerate(prayers, 1):
            print(f"\n{i}. {prayer}\n")

            if with_audio and self.audio:
                # Different frequency for each prayer
                freq = 528 + (i * 111)  # Varying frequencies
                wave = self.audio.generate_solfeggio_tone(freq, duration=20)
                self.audio.play(wave, blocking=True)
            else:
                time.sleep(5)

            self.rotations += 1

        print(f"\n{'='*60}")
        print(f"Prayer cycle complete: {len(prayers)} prayers offered")
        print(f"{'='*60}\n")

    def _end_session(self):
        """End prayer wheel session and show statistics"""
        if self.session_start:
            duration = datetime.now() - self.session_start

            print(f"\n{'='*60}")
            print(f"PRAYER WHEEL SESSION COMPLETE")
            print(f"{'='*60}")
            print(f"Duration: {duration}")
            print(f"Rotations: {self.rotations}")
            print(f"Prayers generated: {self.prayers_generated}")
            print(f"\nDedication:")
            print(f"May all merit from this practice benefit all beings")
            print(f"throughout space and time.")
            print(f"{'='*60}\n")

    def save_session_log(self, filepath: str = './logs/prayer_wheel_sessions.jsonl'):
        """Save session statistics"""
        if not self.session_start:
            return

        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        session_data = {
            'start_time': self.session_start.isoformat(),
            'end_time': datetime.now().isoformat(),
            'rotations': self.rotations,
            'prayers_generated': self.prayers_generated
        }

        with open(filepath, 'a') as f:
            f.write(json.dumps(session_data) + '\n')


if __name__ == "__main__":
    print("Testing Prayer Wheel")
    print("=" * 60)

    # Create prayer wheel (without LLM for basic test)
    from core.audio_generator import ScalarWaveGenerator

    audio = ScalarWaveGenerator()
    wheel = PrayerWheel(audio_generator=audio)

    # Test single prayer generation
    print("\n1. Generating prayer for compassion...")
    prayer = wheel.generate_prayer("compassion", use_llm=False)
    print(f"   {prayer}")

    # Test prayer cycle
    print("\n2. Running Four Immeasurables cycle...")
    print("   (without audio for quick test)")
    wheel.prayer_cycle(theme='four_immeasurables', with_audio=False)

    # Test mantra selection
    print("\n3. Generating prayers for different intentions...")
    intentions = ['healing', 'wisdom', 'protection', 'peace']
    for intention in intentions:
        prayer = wheel.generate_prayer(intention, use_llm=False)
        print(f"   {intention.title()}: {prayer}")

    print("\n" + "=" * 60)
    print("✓ Prayer Wheel test complete")
    print("\nTo test with audio and voice:")
    print("  - Uncomment audio tests above")
    print("  - Add TTS engine")
    print("  - Add LLM integration for generating new prayers")
