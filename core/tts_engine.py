"""
Vajra.Stream - Text-to-Speech Engine
Speaks prayers, mantras, and teachings
Converts generated text to spoken audio for meditation and practice
"""

import pyttsx3
from typing import Optional, List
import time
import os


class TTSEngine:
    """
    Text-to-speech engine for dharma content
    Speaks prayers, mantras, teachings with appropriate pacing and tone
    """

    def __init__(self, rate: int = 150, volume: float = 0.9, voice_index: int = 0):
        """
        Initialize TTS engine

        Args:
            rate: Speech rate (words per minute, default 150 - slower for contemplation)
            volume: Volume level (0.0 to 1.0)
            voice_index: Which voice to use (0 = default, try different indices for different voices)
        """
        self.engine = pyttsx3.init()

        # Set properties
        self.engine.setProperty('rate', rate)
        self.engine.setProperty('volume', volume)

        # Try to set voice
        voices = self.engine.getProperty('voices')
        if voice_index < len(voices):
            self.engine.setProperty('voice', voices[voice_index].id)

        self.rate = rate
        self.volume = volume

    def speak(self, text: str, blocking: bool = True):
        """
        Speak text

        Args:
            text: Text to speak
            blocking: Wait for speech to finish
        """
        self.engine.say(text)

        if blocking:
            self.engine.runAndWait()

    def speak_with_pauses(self, text: str, pause_at: str = '.', pause_duration: float = 1.0):
        """
        Speak text with pauses at punctuation for contemplation

        Args:
            text: Text to speak
            pause_at: Character to pause at (default: period)
            pause_duration: How long to pause in seconds
        """
        # Split by pause character
        segments = text.split(pause_at)

        for i, segment in enumerate(segments):
            if segment.strip():
                self.speak(segment.strip(), blocking=True)

                # Pause between segments (except after last one)
                if i < len(segments) - 1:
                    time.sleep(pause_duration)

    def speak_mantra(self, mantra: str, repetitions: int = 1,
                    pause_between: float = 2.0, rate_override: Optional[int] = None):
        """
        Speak a mantra with appropriate pacing

        Args:
            mantra: Mantra text
            repetitions: How many times to repeat
            pause_between: Pause between repetitions
            rate_override: Override default rate for this mantra
        """
        # Slow down for mantras
        original_rate = self.rate

        if rate_override:
            self.engine.setProperty('rate', rate_override)
        else:
            # Default mantra rate is slower
            self.engine.setProperty('rate', int(self.rate * 0.7))

        try:
            for i in range(repetitions):
                print(f"  Reciting: {mantra}")
                self.speak(mantra, blocking=True)

                if i < repetitions - 1:
                    time.sleep(pause_between)

        finally:
            # Restore original rate
            self.engine.setProperty('rate', original_rate)

    def speak_prayer_slowly(self, prayer: str, pause_per_line: float = 3.0):
        """
        Speak a prayer very slowly with long pauses for contemplation

        Args:
            prayer: Prayer text (can be multi-line)
            pause_per_line: Seconds to pause after each line
        """
        # Very slow for prayers
        original_rate = self.rate
        self.engine.setProperty('rate', int(self.rate * 0.6))

        try:
            lines = prayer.split('\n')

            for line in lines:
                if line.strip():
                    self.speak(line.strip(), blocking=True)
                    time.sleep(pause_per_line)

        finally:
            self.engine.setProperty('rate', original_rate)

    def speak_teaching(self, teaching: str):
        """
        Speak a dharma teaching with natural pacing

        Args:
            teaching: Teaching text
        """
        # Natural reading pace for teachings
        self.speak_with_pauses(teaching, pause_at='.', pause_duration=0.8)

    def adjust_rate(self, rate: int):
        """Adjust speaking rate"""
        self.rate = rate
        self.engine.setProperty('rate', rate)

    def adjust_volume(self, volume: float):
        """Adjust volume (0.0 to 1.0)"""
        self.volume = volume
        self.engine.setProperty('volume', volume)

    def list_available_voices(self) -> List[dict]:
        """Get information about available voices"""
        voices = self.engine.getProperty('voices')

        voice_list = []
        for i, voice in enumerate(voices):
            voice_list.append({
                'index': i,
                'id': voice.id,
                'name': voice.name,
                'languages': voice.languages,
                'gender': getattr(voice, 'gender', 'unknown'),
                'age': getattr(voice, 'age', 'unknown')
            })

        return voice_list

    def set_voice_by_index(self, index: int):
        """Change voice by index"""
        voices = self.engine.getProperty('voices')
        if 0 <= index < len(voices):
            self.engine.setProperty('voice', voices[index].id)
            return True
        return False

    def save_to_file(self, text: str, filepath: str):
        """
        Save spoken text to audio file (if supported)

        Args:
            text: Text to convert
            filepath: Output file path (e.g., 'prayer.mp3')
        """
        # Note: pyttsx3 file saving support varies by platform
        # This is a basic implementation
        try:
            self.engine.save_to_file(text, filepath)
            self.engine.runAndWait()
            print(f"Saved audio to: {filepath}")
            return True
        except Exception as e:
            print(f"Could not save to file: {e}")
            return False


class GuidedMeditationSpeaker:
    """
    Specialized class for speaking guided meditations
    """

    def __init__(self, tts_engine: TTSEngine):
        self.tts = tts_engine

    def speak_meditation_intro(self, practice_name: str):
        """Speak meditation introduction"""
        intro = f"""Welcome to {practice_name} meditation.

        Find a comfortable position. Allow your body to settle.

        Take a few deep breaths. Let your awareness come into this present moment.

        When you are ready, we will begin."""

        self.tts.speak_with_pauses(intro, pause_at='.', pause_duration=2.0)

    def speak_meditation_body(self, instructions: str):
        """Speak main meditation instructions"""
        self.tts.speak_with_pauses(instructions, pause_at='.', pause_duration=2.5)

    def speak_meditation_closing(self):
        """Speak meditation closing"""
        closing = """Now, gently bringing your awareness back.

        Take a deep breath.

        Slowly opening your eyes when you are ready.

        May all beings benefit from this practice."""

        self.tts.speak_with_pauses(closing, pause_at='.', pause_duration=3.0)

    def guide_full_meditation(self, practice_name: str, instructions: str):
        """
        Guide a complete meditation session

        Args:
            practice_name: Name of the meditation
            instructions: Main practice instructions
        """
        print(f"\n{'='*60}")
        print(f"GUIDED MEDITATION: {practice_name.upper()}")
        print(f"{'='*60}\n")

        # Intro
        self.speak_meditation_intro(practice_name)

        # Wait a bit
        time.sleep(3)

        # Main practice
        self.speak_meditation_body(instructions)

        # Wait
        time.sleep(5)

        # Closing
        self.speak_meditation_closing()

        print(f"\n{'='*60}")
        print(f"Meditation complete")
        print(f"{'='*60}\n")


def create_contemplation_audio(tts: TTSEngine, text: str, output_dir: str = './generated/audio'):
    """
    Create audio file for contemplation practice

    Args:
        tts: TTS engine instance
        text: Text to convert to audio
        output_dir: Directory to save audio files
    """
    os.makedirs(output_dir, exist_ok=True)

    # Create filename from first few words
    words = text.split()[:5]
    filename = '_'.join(words) + '.mp3'
    filepath = os.path.join(output_dir, filename)

    tts.save_to_file(text, filepath)
    return filepath


if __name__ == "__main__":
    print("Testing TTS Engine")
    print("=" * 60)

    # Initialize TTS
    try:
        tts = TTSEngine(rate=150, volume=0.9)
        print("✓ TTS engine initialized")

        # List available voices
        print("\nAvailable voices:")
        voices = tts.list_available_voices()
        for voice in voices[:3]:  # Show first 3
            print(f"  {voice['index']}: {voice['name']}")

        # Test speaking a simple prayer
        print("\n1. Testing simple prayer...")
        prayer = "May all beings be happy and free from suffering"
        tts.speak(prayer)

        # Test mantra
        print("\n2. Testing mantra (Om Mani Padme Hum)...")
        tts.speak_mantra("Om Mani Padme Hum", repetitions=3, pause_between=1.5)

        # Test teaching
        print("\n3. Testing dharma teaching...")
        teaching = "Compassion is the wish for others to be free from suffering. " \
                  "It arises naturally when we see the struggles of other beings. " \
                  "We can cultivate compassion through meditation and daily practice."
        tts.speak_teaching(teaching)

        # Test guided meditation
        print("\n4. Testing guided meditation...")
        guide = GuidedMeditationSpeaker(tts)

        meditation_instructions = """Bring your attention to your breath.
        Notice the natural rhythm of breathing in and breathing out.
        There is nothing to change, simply observe.
        When the mind wanders, gently bring it back to the breath."""

        guide.guide_full_meditation("Breath Awareness", meditation_instructions)

        print("\n" + "=" * 60)
        print("✓ TTS engine test complete")

    except Exception as e:
        print(f"Error initializing TTS: {e}")
        print("Note: TTS may not work in headless environments")
