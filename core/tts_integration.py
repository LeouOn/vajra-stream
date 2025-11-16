#!/usr/bin/env python3
"""
TTS Integration - Text-to-Speech for Spiritual Practice

Gives voice to:
- Blessing narratives and liberation stories
- Mantras and sacred syllables
- Guided meditations
- Historical commemorations
- Radionics intentions
- Educational content

Supports multiple TTS engines with automatic fallback.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Union
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import re
import time

# Try importing TTS engines
try:
    import pyttsx3
    HAS_PYTTSX3 = True
except ImportError:
    HAS_PYTTSX3 = False

try:
    from gtts import gTTS
    HAS_GTTS = True
except ImportError:
    HAS_GTTS = False

try:
    import edge_tts
    HAS_EDGE_TTS = True
except ImportError:
    HAS_EDGE_TTS = False

try:
    from core.blessing_narratives import GeneratedStory
    HAS_NARRATIVES = True
except ImportError:
    HAS_NARRATIVES = False


# ============================================================================
# ENUMS AND DATA CLASSES
# ============================================================================

class TTSEngineType(Enum):
    """Available TTS engines"""
    PYTTSX3 = "pyttsx3"      # Offline, free
    GTTS = "gtts"            # Online, free
    EDGE_TTS = "edge_tts"    # Online, free, high quality
    AUTO = "auto"            # Auto-select best available


class VoiceGender(Enum):
    """Voice gender options"""
    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"


class SpeakingRate(Enum):
    """Speaking rate presets"""
    VERY_SLOW = "very_slow"  # 80-100 WPM (meditation)
    SLOW = "slow"            # 100-120 WPM (contemplative)
    NORMAL = "normal"        # 140-160 WPM (conversational)
    FAST = "fast"            # 180-200 WPM (energetic)


@dataclass
class Voice:
    """Voice information"""
    id: str
    name: str
    gender: VoiceGender
    language: str = "en"
    engine: str = ""
    quality: str = "standard"  # standard, neural, premium


@dataclass
class TTSConfig:
    """TTS generation configuration"""
    engine: TTSEngineType = TTSEngineType.AUTO
    voice_id: Optional[str] = None
    rate: SpeakingRate = SpeakingRate.NORMAL
    volume: float = 1.0  # 0.0 to 1.0
    pitch: Optional[int] = None  # Engine-dependent
    add_pauses: bool = True
    pause_duration: float = 1.0  # seconds


# ============================================================================
# TTS ENGINE BASE CLASS
# ============================================================================

class TTSEngine(ABC):
    """Base class for TTS engines"""

    @abstractmethod
    def synthesize(self, text: str, output_file: str, **kwargs) -> str:
        """
        Synthesize speech from text.

        Args:
            text: Text to synthesize
            output_file: Output audio file path
            **kwargs: Engine-specific parameters

        Returns:
            Path to generated audio file
        """
        pass

    @abstractmethod
    def get_voices(self) -> List[Voice]:
        """Get available voices"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if engine is available"""
        pass

    def preprocess_text(self, text: str) -> str:
        """Preprocess text (remove markdown, etc.)"""
        # Remove markdown headers
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)

        # Remove markdown emphasis
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*(.+?)\*', r'\1', text)      # Italic
        text = re.sub(r'_(.+?)_', r'\1', text)        # Italic

        # Remove custom pause markers for simple engines
        # (Keep for engines that support them)
        # text = re.sub(r'\[PAUSE:\d+\]', '', text)

        return text


# ============================================================================
# PYTTSX3 ENGINE (Offline)
# ============================================================================

class Pyttsx3Engine(TTSEngine):
    """Offline TTS using pyttsx3"""

    def __init__(self):
        self.engine = None
        if HAS_PYTTSX3:
            try:
                self.engine = pyttsx3.init()
            except Exception as e:
                print(f"Warning: Could not initialize pyttsx3: {e}")
                self.engine = None

    def is_available(self) -> bool:
        """Check if pyttsx3 is available"""
        return HAS_PYTTSX3 and self.engine is not None

    def get_voices(self) -> List[Voice]:
        """Get available system voices"""
        if not self.is_available():
            return []

        voices = []
        try:
            system_voices = self.engine.getProperty('voices')
            for i, voice in enumerate(system_voices):
                # Try to detect gender from voice name
                name_lower = voice.name.lower()
                if 'female' in name_lower or 'woman' in name_lower:
                    gender = VoiceGender.FEMALE
                elif 'male' in name_lower or 'man' in name_lower:
                    gender = VoiceGender.MALE
                else:
                    gender = VoiceGender.NEUTRAL

                voices.append(Voice(
                    id=voice.id,
                    name=voice.name,
                    gender=gender,
                    language=voice.languages[0] if voice.languages else 'en',
                    engine='pyttsx3',
                    quality='standard'
                ))
        except Exception as e:
            print(f"Warning: Could not get voices: {e}")

        return voices

    def synthesize(self, text: str, output_file: str, **kwargs) -> str:
        """Synthesize speech using pyttsx3"""
        if not self.is_available():
            raise RuntimeError("pyttsx3 engine not available")

        # Clean text
        text = self.preprocess_text(text)

        # Set properties
        voice_id = kwargs.get('voice_id')
        if voice_id:
            self.engine.setProperty('voice', voice_id)

        # Rate (words per minute)
        rate = kwargs.get('rate', 150)
        if isinstance(rate, SpeakingRate):
            rate = {
                SpeakingRate.VERY_SLOW: 90,
                SpeakingRate.SLOW: 110,
                SpeakingRate.NORMAL: 150,
                SpeakingRate.FAST: 190
            }.get(rate, 150)
        self.engine.setProperty('rate', rate)

        # Volume (0.0 to 1.0)
        volume = kwargs.get('volume', 1.0)
        self.engine.setProperty('volume', volume)

        # Generate audio
        try:
            self.engine.save_to_file(text, output_file)
            self.engine.runAndWait()
            return output_file
        except Exception as e:
            raise RuntimeError(f"Failed to synthesize speech: {e}")


# ============================================================================
# GTTS ENGINE (Online, Free)
# ============================================================================

class GTTSEngine(TTSEngine):
    """Google TTS engine (online, free)"""

    def is_available(self) -> bool:
        """Check if gTTS is available"""
        return HAS_GTTS

    def get_voices(self) -> List[Voice]:
        """Get available voices (gTTS has limited options)"""
        if not HAS_GTTS:
            return []

        # gTTS doesn't have multiple voices, just languages
        # Return a basic set
        return [
            Voice(
                id='gtts_en',
                name='Google TTS English',
                gender=VoiceGender.FEMALE,
                language='en',
                engine='gtts',
                quality='standard'
            )
        ]

    def synthesize(self, text: str, output_file: str, **kwargs) -> str:
        """Synthesize speech using gTTS"""
        if not self.is_available():
            raise RuntimeError("gTTS not available")

        # Clean text
        text = self.preprocess_text(text)

        # Get language
        lang = kwargs.get('lang', 'en')

        # Slow mode for meditation/contemplative content
        slow = kwargs.get('slow', False)
        if 'rate' in kwargs:
            rate = kwargs['rate']
            if rate in [SpeakingRate.VERY_SLOW, SpeakingRate.SLOW]:
                slow = True

        try:
            tts = gTTS(text=text, lang=lang, slow=slow)
            tts.save(output_file)
            return output_file
        except Exception as e:
            raise RuntimeError(f"Failed to synthesize speech with gTTS: {e}")


# ============================================================================
# TTS NARRATOR (High-Level Interface)
# ============================================================================

class TTSNarrator:
    """
    High-level interface for text-to-speech narration.

    Handles:
    - Engine selection and fallback
    - Voice selection
    - Story narration
    - Mantra generation
    - Guided meditation
    - Historical commemoration
    """

    def __init__(self, engine: Union[TTSEngineType, str] = TTSEngineType.AUTO,
                 voice: Optional[str] = None,
                 config: Optional[TTSConfig] = None):
        """
        Initialize TTS narrator.

        Args:
            engine: Engine type or 'auto' for best available
            voice: Voice ID or name
            config: TTS configuration
        """
        self.config = config or TTSConfig()

        # Parse engine if string
        if isinstance(engine, str):
            try:
                engine = TTSEngineType(engine)
            except ValueError:
                engine = TTSEngineType.AUTO

        # Initialize engine
        self.engine = self._init_engine(engine)
        self.voice = voice

    def _init_engine(self, engine_type: TTSEngineType) -> TTSEngine:
        """Initialize TTS engine with fallback"""

        # Try requested engine or auto-select
        if engine_type == TTSEngineType.AUTO:
            # Try engines in order of preference
            if HAS_PYTTSX3:
                print("Trying pyttsx3 (offline) engine...")
                engine = Pyttsx3Engine()
                if engine.is_available():
                    print("✓ Using pyttsx3 (offline) engine")
                    return engine
                else:
                    print("✗ pyttsx3 not usable (espeak may not be installed)")

            if HAS_GTTS:
                print("✓ Using gTTS (online) engine")
                return GTTSEngine()

            raise RuntimeError("No TTS engine available. Install pyttsx3 + espeak or gTTS.")

        elif engine_type == TTSEngineType.PYTTSX3:
            if not HAS_PYTTSX3:
                raise RuntimeError("pyttsx3 not available")
            return Pyttsx3Engine()

        elif engine_type == TTSEngineType.GTTS:
            if not HAS_GTTS:
                raise RuntimeError("gTTS not available")
            return GTTSEngine()

        elif engine_type == TTSEngineType.EDGE_TTS:
            if not HAS_EDGE_TTS:
                raise RuntimeError("edge-tts not available")
            # TODO: Implement EdgeTTSEngine
            raise NotImplementedError("edge-tts engine not yet implemented")

        else:
            raise ValueError(f"Unknown engine type: {engine_type}")

    def list_voices(self) -> List[Voice]:
        """List available voices"""
        return self.engine.get_voices()

    def generate_audio(self, text: str, output_file: str,
                      rate: Optional[SpeakingRate] = None,
                      volume: Optional[float] = None,
                      **kwargs) -> str:
        """
        Generate audio from text.

        Args:
            text: Text to synthesize
            output_file: Output file path
            rate: Speaking rate
            volume: Volume (0.0 to 1.0)
            **kwargs: Additional engine-specific parameters

        Returns:
            Path to generated file
        """
        # Use config or override
        actual_rate = rate or self.config.rate
        actual_volume = volume if volume is not None else self.config.volume

        # Prepare kwargs
        synth_kwargs = {
            'rate': actual_rate,
            'volume': actual_volume,
            'voice_id': self.voice,
            **kwargs
        }

        return self.engine.synthesize(text, output_file, **synth_kwargs)

    def narrate_story(self, story: 'GeneratedStory', output_file: str,
                     rate: SpeakingRate = SpeakingRate.SLOW,
                     add_intro: bool = True,
                     add_outro: bool = True) -> str:
        """
        Narrate a blessing story.

        Args:
            story: GeneratedStory object
            output_file: Output file path
            rate: Speaking rate (slow recommended)
            add_intro: Add brief intro
            add_outro: Add dedication at end

        Returns:
            Path to generated file
        """
        if not HAS_NARRATIVES:
            raise RuntimeError("Blessing narratives system not available")

        # Build narration text
        parts = []

        if add_intro:
            parts.append(f"A story of liberation for {story.target_name}.")
            parts.append("")  # Pause

        # Main story (remove excessive formatting)
        clean_text = story.story_text
        # Remove markdown formatting
        clean_text = re.sub(r'^#+\s+', '', clean_text, flags=re.MULTILINE)
        clean_text = re.sub(r'\*\*(.+?)\*\*', r'\1', clean_text)
        clean_text = re.sub(r'\*(.+?)\*', r'\1', clean_text)
        # Remove horizontal rules
        clean_text = re.sub(r'-{3,}', '', clean_text)

        parts.append(clean_text)

        if add_outro and story.dedication:
            parts.append("")  # Pause
            parts.append("Dedication:")
            parts.append(story.dedication)

        full_text = "\n\n".join(parts)

        return self.generate_audio(
            text=full_text,
            output_file=output_file,
            rate=rate
        )

    def generate_mantra_audio(self, mantra: str, repetitions: int,
                             output_file: str,
                             pause_between: float = 1.0) -> str:
        """
        Generate mantra repetition audio.

        Args:
            mantra: Mantra text (e.g., "Om Mani Padme Hum")
            repetitions: Number of times to repeat
            output_file: Output file path
            pause_between: Seconds between repetitions

        Returns:
            Path to generated file
        """
        # Build text with pauses
        parts = []
        for i in range(repetitions):
            parts.append(mantra)
            if i < repetitions - 1:  # Don't pause after last one
                # Add pause markers (will be interpreted as silence)
                parts.append("...")  # Simple pause

        # Join with spaces for natural flow
        full_text = " . ".join(parts)

        return self.generate_audio(
            text=full_text,
            output_file=output_file,
            rate=SpeakingRate.SLOW  # Mantras should be slow and clear
        )

    def guided_meditation(self, script: str, output_file: str,
                         background_description: Optional[str] = None) -> str:
        """
        Generate guided meditation audio.

        Args:
            script: Meditation script
            output_file: Output file path
            background_description: Description of background sounds

        Returns:
            Path to generated file
        """
        # Parse custom markers like [PAUSE:5]
        processed_script = script

        # Replace pause markers with actual pauses
        # For now, just remove them (engines don't all support SSML)
        processed_script = re.sub(r'\[PAUSE:\d+\]', '...', processed_script)
        processed_script = re.sub(r'\[BREATHE\]', '... breathe ...', processed_script)

        return self.generate_audio(
            text=processed_script,
            output_file=output_file,
            rate=SpeakingRate.VERY_SLOW  # Meditations very slow
        )

    def commemorate_event(self, event: Dict, date, output_file: str) -> str:
        """
        Generate historical commemoration.

        Args:
            event: Event dictionary
            date: datetime object
            output_file: Output file path

        Returns:
            Path to generated file
        """
        # Build commemoration text
        text_parts = []

        text_parts.append(f"Today we remember {event['name']}.")
        text_parts.append(f"On {date.strftime('%B %d, %Y')}.")

        if event.get('estimated_deaths'):
            deaths = event['estimated_deaths']
            text_parts.append(f"We honor the {deaths:,} souls who perished.")

        text_parts.append(event.get('blessing_focus', ''))

        text_parts.append("May they find peace.")
        text_parts.append("May healing reach all who suffered.")

        # Add mantras
        mantras = event.get('mantras', [])
        if mantras:
            text_parts.append("")
            for mantra in mantras[:2]:  # Use first two
                text_parts.append(mantra)

        full_text = " ... ".join(text_parts)

        return self.generate_audio(
            text=full_text,
            output_file=output_file,
            rate=SpeakingRate.SLOW
        )


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def quick_narrate(text: str, output_file: str = "narration.mp3",
                 engine: str = 'auto', slow: bool = False) -> str:
    """
    Quick function to narrate text.

    Args:
        text: Text to narrate
        output_file: Output file
        engine: Engine to use
        slow: Use slow rate

    Returns:
        Path to generated file
    """
    narrator = TTSNarrator(engine=engine)
    rate = SpeakingRate.SLOW if slow else SpeakingRate.NORMAL

    return narrator.generate_audio(
        text=text,
        output_file=output_file,
        rate=rate
    )


def narrate_mantra(mantra: str = "Om Mani Padme Hum",
                  repetitions: int = 108,
                  output_file: str = "mantra.mp3") -> str:
    """
    Quick function to generate mantra audio.

    Args:
        mantra: Mantra text
        repetitions: Number of repetitions
        output_file: Output file

    Returns:
        Path to generated file
    """
    narrator = TTSNarrator()
    return narrator.generate_mantra_audio(
        mantra=mantra,
        repetitions=repetitions,
        output_file=output_file
    )


# Example usage
if __name__ == "__main__":
    print("TTS Integration System - Voice for Spiritual Practice\n")

    # Check available engines
    print("=== Available TTS Engines ===")
    print(f"pyttsx3 (offline): {'✓' if HAS_PYTTSX3 else '✗'}")
    print(f"gTTS (online): {'✓' if HAS_GTTS else '✗'}")
    print(f"edge-tts (online): {'✓' if HAS_EDGE_TTS else '✗'}")
    print()

    # Initialize narrator
    try:
        narrator = TTSNarrator()
        print(f"✓ TTS Narrator initialized with {narrator.engine.__class__.__name__}")
        print()

        # List available voices
        voices = narrator.list_voices()
        print(f"=== Available Voices ({len(voices)}) ===")
        for voice in voices[:3]:  # Show first 3
            print(f"  • {voice.name} ({voice.gender.value}, {voice.language})")
        print()

        # Example 1: Simple narration
        print("=== Example 1: Simple Narration ===")
        blessing_text = "May all beings be free from suffering. May all beings find peace and liberation."

        output = narrator.generate_audio(
            text=blessing_text,
            output_file="/tmp/blessing.mp3",
            rate=SpeakingRate.SLOW
        )
        print(f"✓ Generated: {output}")
        print()

        # Example 2: Mantra repetition
        print("=== Example 2: Mantra Repetition ===")
        output = narrator.generate_mantra_audio(
            mantra="Om Mani Padme Hum",
            repetitions=21,  # Shorter for demo
            output_file="/tmp/mantra_21.mp3"
        )
        print(f"✓ Generated: {output}")
        print()

        # Example 3: Quick function
        print("=== Example 3: Quick Narrate ===")
        output = quick_narrate(
            "This is a test of the quick narration function.",
            output_file="/tmp/quick_test.mp3"
        )
        print(f"✓ Generated: {output}")
        print()

        print("✨ TTS System Ready!")
        print("\nUsage:")
        print("  narrator = TTSNarrator()")
        print("  narrator.generate_audio('Your text here', 'output.mp3')")
        print("\nMay these voices carry blessings to all beings! 🙏")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nTo use TTS, install at least one engine:")
        print("  pip install pyttsx3  # Offline")
        print("  pip install gTTS     # Online, free")
