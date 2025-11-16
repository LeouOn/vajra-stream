"""
Audio & TTS Module
Wraps all audio generation and text-to-speech functionality
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.interfaces import EventBus


class AudioService:
    """Unified audio and TTS service"""

    def __init__(self, event_bus: EventBus = None):
        self.event_bus = event_bus
        self._audio_gen = None
        self._enhanced_audio = None
        self._tts = None
        self._enhanced_tts = None

    @property
    def audio_generator(self):
        """Get basic audio generator"""
        if self._audio_gen is None:
            try:
                from core.audio_generator import AudioGenerator
                self._audio_gen = AudioGenerator()
            except ImportError:
                self._audio_gen = None
        return self._audio_gen

    @property
    def enhanced_audio(self):
        """Get enhanced audio generator"""
        if self._enhanced_audio is None:
            try:
                from core.enhanced_audio_generator import EnhancedAudioGenerator
                self._enhanced_audio = EnhancedAudioGenerator()
            except ImportError:
                self._enhanced_audio = None
        return self._enhanced_audio

    @property
    def tts(self):
        """Get basic TTS engine"""
        if self._tts is None:
            try:
                from core.tts_engine import TTSEngine
                self._tts = TTSEngine()
            except ImportError:
                self._tts = None
        return self._tts

    @property
    def enhanced_tts(self):
        """Get enhanced TTS"""
        if self._enhanced_tts is None:
            try:
                from core.enhanced_tts import EnhancedTTS
                self._enhanced_tts = EnhancedTTS()
            except ImportError:
                self._enhanced_tts = None
        return self._enhanced_tts

    def generate_tone(
        self,
        frequency: float = 432.0,
        duration: float = 10.0,
        volume: float = 0.5
    ) -> Dict[str, Any]:
        """Generate a pure tone at specified frequency"""
        if self.audio_generator is None:
            return {'error': 'Audio generator not available'}

        try:
            audio_data = self.audio_generator.generate_tone(
                frequency=frequency,
                duration=duration,
                volume=volume
            )
            return {
                'status': 'success',
                'frequency': frequency,
                'duration': duration,
                'audio_data': audio_data
            }
        except Exception as e:
            return {'error': str(e)}

    def generate_binaural_beats(
        self,
        base_frequency: float = 432.0,
        beat_frequency: float = 7.83,
        duration: float = 60.0
    ) -> Dict[str, Any]:
        """Generate binaural beats"""
        if self.audio_generator is None:
            return {'error': 'Audio generator not available'}

        try:
            audio_data = self.audio_generator.generate_binaural(
                base_freq=base_frequency,
                beat_freq=beat_frequency,
                duration=duration
            )
            return {
                'status': 'success',
                'base_frequency': base_frequency,
                'beat_frequency': beat_frequency,
                'audio_data': audio_data
            }
        except Exception as e:
            return {'error': str(e)}

    def synthesize_speech(
        self,
        text: str,
        voice: Optional[str] = None,
        rate: float = 1.0,
        pitch: float = 1.0
    ) -> Dict[str, Any]:
        """Convert text to speech"""
        tts_engine = self.enhanced_tts or self.tts

        if tts_engine is None:
            return {'error': 'TTS not available'}

        try:
            audio_data = tts_engine.synthesize(
                text=text,
                voice=voice,
                rate=rate,
                pitch=pitch
            )
            return {
                'status': 'success',
                'text': text,
                'audio_data': audio_data
            }
        except Exception as e:
            return {'error': str(e)}

    def generate_mantra_audio(
        self,
        mantra: str = "Om Mani Padme Hum",
        repetitions: int = 108,
        frequency: float = 528.0
    ) -> Dict[str, Any]:
        """Generate mantra audio with background frequency"""
        result = {
            'status': 'success',
            'mantra': mantra,
            'repetitions': repetitions,
            'frequency': frequency
        }

        # Generate background tone
        tone_result = self.generate_tone(frequency, repetitions * 5, 0.3)
        if 'audio_data' in tone_result:
            result['background_tone'] = tone_result['audio_data']

        # Generate speech
        full_text = " ... ".join([mantra] * repetitions)
        speech_result = self.synthesize_speech(full_text, rate=0.8)
        if 'audio_data' in speech_result:
            result['speech'] = speech_result['audio_data']

        return result

    def get_available_voices(self) -> List[str]:
        """Get list of available TTS voices"""
        tts_engine = self.enhanced_tts or self.tts

        if tts_engine is None:
            return []

        try:
            return tts_engine.get_voices()
        except:
            return ['default']

    def get_status(self) -> Dict[str, Any]:
        """Get status of all audio subsystems"""
        return {
            'audio_generator': self.audio_generator is not None,
            'enhanced_audio': self.enhanced_audio is not None,
            'tts': self.tts is not None,
            'enhanced_tts': self.enhanced_tts is not None,
            'available_voices': self.get_available_voices()
        }
