#!/usr/bin/env python3
"""
Enhanced Text-to-Speech Engine for Vajra.Stream
Supports both cloud APIs and local open-source TTS systems
"""

import os
import sys
import time
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any
import warnings

# Base imports
import numpy as np


class TTSProvider:
    """Base class for TTS providers"""

    def __init__(self, name: str):
        self.name = name
        self.available = False
        self.error_msg = None

    def check_availability(self) -> bool:
        """Check if this provider is available"""
        raise NotImplementedError

    def speak(self, text: str, **kwargs) -> bool:
        """Speak text (blocking)"""
        raise NotImplementedError

    def generate_audio_file(self, text: str, output_path: str, **kwargs) -> bool:
        """Generate audio file from text"""
        raise NotImplementedError


class ElevenLabsTTS(TTSProvider):
    """ElevenLabs API - Premium cloud TTS with very natural voices"""

    def __init__(self):
        super().__init__("ElevenLabs")
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.client = None
        self.available = self.check_availability()

    def check_availability(self) -> bool:
        if not self.api_key:
            self.error_msg = "ELEVENLABS_API_KEY not set"
            return False

        try:
            from elevenlabs import generate, set_api_key, voices
            set_api_key(self.api_key)
            self.generate_func = generate
            self.voices_func = voices
            return True
        except ImportError:
            self.error_msg = "elevenlabs package not installed (pip install elevenlabs)"
            return False
        except Exception as e:
            self.error_msg = f"ElevenLabs initialization error: {str(e)}"
            return False

    def generate_audio_file(self, text: str, output_path: str,
                           voice: str = "Bella", **kwargs) -> bool:
        """Generate audio file using ElevenLabs"""
        try:
            audio = self.generate_func(
                text=text,
                voice=voice,
                model="eleven_monolingual_v1"
            )

            with open(output_path, 'wb') as f:
                f.write(audio)

            return True
        except Exception as e:
            self.error_msg = f"ElevenLabs generation error: {str(e)}"
            return False

    def speak(self, text: str, **kwargs) -> bool:
        """Generate and play audio"""
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            if self.generate_audio_file(text, tmp_path, **kwargs):
                # Play using system audio
                self._play_audio_file(tmp_path)
                return True
            return False
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _play_audio_file(self, path: str):
        """Play audio file using available player"""
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
        except ImportError:
            # Fallback to system player
            os.system(f"afplay {path}" if sys.platform == "darwin" else f"aplay {path}")


class AzureTTS(TTSProvider):
    """Azure Cognitive Services TTS - Microsoft cloud TTS"""

    def __init__(self):
        super().__init__("Azure TTS")
        self.api_key = os.getenv("AZURE_SPEECH_KEY")
        self.region = os.getenv("AZURE_SPEECH_REGION", "eastus")
        self.speech_config = None
        self.available = self.check_availability()

    def check_availability(self) -> bool:
        if not self.api_key:
            self.error_msg = "AZURE_SPEECH_KEY not set"
            return False

        try:
            import azure.cognitiveservices.speech as speechsdk
            self.speech_config = speechsdk.SpeechConfig(
                subscription=self.api_key,
                region=self.region
            )
            self.speechsdk = speechsdk
            return True
        except ImportError:
            self.error_msg = "azure-cognitiveservices-speech not installed"
            return False
        except Exception as e:
            self.error_msg = f"Azure TTS initialization error: {str(e)}"
            return False

    def generate_audio_file(self, text: str, output_path: str,
                           voice: str = "en-US-JennyNeural", **kwargs) -> bool:
        """Generate audio file using Azure TTS"""
        try:
            self.speech_config.speech_synthesis_voice_name = voice

            audio_config = self.speechsdk.audio.AudioOutputConfig(
                filename=output_path
            )

            synthesizer = self.speechsdk.SpeechSynthesizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )

            result = synthesizer.speak_text_async(text).get()

            if result.reason == self.speechsdk.ResultReason.SynthesizingAudioCompleted:
                return True
            else:
                self.error_msg = f"Azure synthesis failed: {result.reason}"
                return False
        except Exception as e:
            self.error_msg = f"Azure generation error: {str(e)}"
            return False

    def speak(self, text: str, voice: str = "en-US-JennyNeural", **kwargs) -> bool:
        """Speak text using Azure TTS"""
        try:
            self.speech_config.speech_synthesis_voice_name = voice

            synthesizer = self.speechsdk.SpeechSynthesizer(
                speech_config=self.speech_config
            )

            result = synthesizer.speak_text_async(text).get()

            if result.reason == self.speechsdk.ResultReason.SynthesizingAudioCompleted:
                return True
            else:
                self.error_msg = f"Azure speech failed: {result.reason}"
                return False
        except Exception as e:
            self.error_msg = f"Azure speech error: {str(e)}"
            return False


class GoogleCloudTTS(TTSProvider):
    """Google Cloud Text-to-Speech"""

    def __init__(self):
        super().__init__("Google Cloud TTS")
        self.credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        self.client = None
        self.available = self.check_availability()

    def check_availability(self) -> bool:
        if not self.credentials_path:
            self.error_msg = "GOOGLE_APPLICATION_CREDENTIALS not set"
            return False

        try:
            from google.cloud import texttospeech
            self.client = texttospeech.TextToSpeechClient()
            self.texttospeech = texttospeech
            return True
        except ImportError:
            self.error_msg = "google-cloud-texttospeech not installed"
            return False
        except Exception as e:
            self.error_msg = f"Google Cloud TTS initialization error: {str(e)}"
            return False

    def generate_audio_file(self, text: str, output_path: str,
                           voice_name: str = "en-US-Wavenet-D",
                           language_code: str = "en-US", **kwargs) -> bool:
        """Generate audio file using Google Cloud TTS"""
        try:
            synthesis_input = self.texttospeech.SynthesisInput(text=text)

            voice = self.texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name=voice_name
            )

            audio_config = self.texttospeech.AudioConfig(
                audio_encoding=self.texttospeech.AudioEncoding.MP3
            )

            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )

            with open(output_path, 'wb') as f:
                f.write(response.audio_content)

            return True
        except Exception as e:
            self.error_msg = f"Google Cloud generation error: {str(e)}"
            return False

    def speak(self, text: str, **kwargs) -> bool:
        """Generate and play audio"""
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            if self.generate_audio_file(text, tmp_path, **kwargs):
                self._play_audio_file(tmp_path)
                return True
            return False
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _play_audio_file(self, path: str):
        """Play audio file"""
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
        except ImportError:
            os.system(f"afplay {path}" if sys.platform == "darwin" else f"aplay {path}")


class OpenAITTS(TTSProvider):
    """OpenAI TTS - Latest TTS from OpenAI"""

    def __init__(self):
        super().__init__("OpenAI TTS")
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = None
        self.available = self.check_availability()

    def check_availability(self) -> bool:
        if not self.api_key:
            self.error_msg = "OPENAI_API_KEY not set"
            return False

        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
            return True
        except ImportError:
            self.error_msg = "openai package not installed (pip install openai)"
            return False
        except Exception as e:
            self.error_msg = f"OpenAI initialization error: {str(e)}"
            return False

    def generate_audio_file(self, text: str, output_path: str,
                           voice: str = "nova", model: str = "tts-1", **kwargs) -> bool:
        """Generate audio file using OpenAI TTS"""
        try:
            response = self.client.audio.speech.create(
                model=model,  # tts-1 or tts-1-hd
                voice=voice,  # alloy, echo, fable, onyx, nova, shimmer
                input=text
            )

            response.stream_to_file(output_path)
            return True
        except Exception as e:
            self.error_msg = f"OpenAI generation error: {str(e)}"
            return False

    def speak(self, text: str, **kwargs) -> bool:
        """Generate and play audio"""
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            if self.generate_audio_file(text, tmp_path, **kwargs):
                self._play_audio_file(tmp_path)
                return True
            return False
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _play_audio_file(self, path: str):
        """Play audio file"""
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
        except ImportError:
            os.system(f"afplay {path}" if sys.platform == "darwin" else f"aplay {path}")


class CoquiTTS(TTSProvider):
    """Coqui TTS - Local open-source TTS (continuation of Mozilla TTS)"""

    def __init__(self):
        super().__init__("Coqui TTS")
        self.tts = None
        self.available = self.check_availability()

    def check_availability(self) -> bool:
        try:
            from TTS.api import TTS as CoquiTTSAPI
            # Use a fast, high-quality model
            self.tts = CoquiTTSAPI("tts_models/en/ljspeech/tacotron2-DDC")
            return True
        except ImportError:
            self.error_msg = "TTS package not installed (pip install TTS)"
            return False
        except Exception as e:
            self.error_msg = f"Coqui TTS initialization error: {str(e)}"
            return False

    def generate_audio_file(self, text: str, output_path: str, **kwargs) -> bool:
        """Generate audio file using Coqui TTS"""
        try:
            self.tts.tts_to_file(text=text, file_path=output_path)
            return True
        except Exception as e:
            self.error_msg = f"Coqui generation error: {str(e)}"
            return False

    def speak(self, text: str, **kwargs) -> bool:
        """Generate and play audio"""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            if self.generate_audio_file(text, tmp_path, **kwargs):
                self._play_audio_file(tmp_path)
                return True
            return False
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _play_audio_file(self, path: str):
        """Play audio file"""
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
        except ImportError:
            os.system(f"afplay {path}" if sys.platform == "darwin" else f"aplay {path}")


class PiperTTS(TTSProvider):
    """Piper - Fast local TTS optimized for Raspberry Pi"""

    def __init__(self):
        super().__init__("Piper TTS")
        self.piper_path = None
        self.model_path = None
        self.available = self.check_availability()

    def check_availability(self) -> bool:
        # Check if piper binary is available
        import shutil
        self.piper_path = shutil.which("piper")

        if not self.piper_path:
            self.error_msg = "piper binary not found in PATH"
            return False

        # Look for models
        model_dirs = [
            Path.home() / ".local/share/piper/models",
            Path("/usr/share/piper/models"),
            Path("./models/piper")
        ]

        for model_dir in model_dirs:
            if model_dir.exists():
                # Look for any .onnx model
                models = list(model_dir.glob("**/*.onnx"))
                if models:
                    self.model_path = models[0]
                    return True

        self.error_msg = "No piper models found"
        return False

    def generate_audio_file(self, text: str, output_path: str, **kwargs) -> bool:
        """Generate audio file using Piper"""
        try:
            import subprocess

            # Piper reads from stdin and writes to stdout
            cmd = [
                self.piper_path,
                "--model", str(self.model_path),
                "--output_file", output_path
            ]

            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate(input=text)

            if process.returncode == 0:
                return True
            else:
                self.error_msg = f"Piper error: {stderr}"
                return False
        except Exception as e:
            self.error_msg = f"Piper generation error: {str(e)}"
            return False

    def speak(self, text: str, **kwargs) -> bool:
        """Generate and play audio"""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            if self.generate_audio_file(text, tmp_path, **kwargs):
                self._play_audio_file(tmp_path)
                return True
            return False
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _play_audio_file(self, path: str):
        """Play audio file"""
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
        except ImportError:
            os.system(f"afplay {path}" if sys.platform == "darwin" else f"aplay {path}")


class Pyttsx3TTS(TTSProvider):
    """Pyttsx3 - Basic offline TTS (fallback)"""

    def __init__(self):
        super().__init__("pyttsx3")
        self.engine = None
        self.available = self.check_availability()

    def check_availability(self) -> bool:
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            return True
        except ImportError:
            self.error_msg = "pyttsx3 not installed"
            return False
        except Exception as e:
            self.error_msg = f"pyttsx3 initialization error: {str(e)}"
            return False

    def speak(self, text: str, rate: int = 150, **kwargs) -> bool:
        """Speak text using pyttsx3"""
        try:
            self.engine.setProperty('rate', rate)
            self.engine.say(text)
            self.engine.runAndWait()
            return True
        except Exception as e:
            self.error_msg = f"pyttsx3 speech error: {str(e)}"
            return False

    def generate_audio_file(self, text: str, output_path: str,
                           rate: int = 150, **kwargs) -> bool:
        """Generate audio file using pyttsx3"""
        try:
            self.engine.setProperty('rate', rate)
            self.engine.save_to_file(text, output_path)
            self.engine.runAndWait()
            return True
        except Exception as e:
            self.error_msg = f"pyttsx3 generation error: {str(e)}"
            return False


class EnhancedTTSEngine:
    """
    Enhanced TTS Engine with automatic provider selection

    Priority order:
    1. Cloud APIs (if configured): OpenAI → ElevenLabs → Azure → Google
    2. Local open-source: Coqui → Piper
    3. Fallback: pyttsx3
    """

    def __init__(self, prefer_local: bool = False):
        """
        Initialize TTS engine

        Args:
            prefer_local: If True, prefer local TTS over cloud APIs
        """
        self.prefer_local = prefer_local
        self.providers = {}
        self.active_provider = None

        # Initialize all providers
        self._initialize_providers()

        # Select best available provider
        self._select_provider()

    def _initialize_providers(self):
        """Initialize all TTS providers"""
        provider_classes = [
            # Cloud APIs
            OpenAITTS,
            ElevenLabsTTS,
            AzureTTS,
            GoogleCloudTTS,
            # Local open-source
            CoquiTTS,
            PiperTTS,
            # Fallback
            Pyttsx3TTS
        ]

        for provider_class in provider_classes:
            try:
                provider = provider_class()
                self.providers[provider.name] = provider
            except Exception as e:
                print(f"Failed to initialize {provider_class.__name__}: {e}")

    def _select_provider(self):
        """Select best available TTS provider"""
        if self.prefer_local:
            # Try local first
            priority = [
                "Coqui TTS",
                "Piper TTS",
                "OpenAI TTS",
                "ElevenLabs",
                "Azure TTS",
                "Google Cloud TTS",
                "pyttsx3"
            ]
        else:
            # Try cloud first
            priority = [
                "OpenAI TTS",
                "ElevenLabs",
                "Azure TTS",
                "Google Cloud TTS",
                "Coqui TTS",
                "Piper TTS",
                "pyttsx3"
            ]

        for provider_name in priority:
            if provider_name in self.providers:
                provider = self.providers[provider_name]
                if provider.available:
                    self.active_provider = provider
                    print(f"✓ Selected TTS provider: {provider_name}")
                    return

        raise RuntimeError("No TTS provider available!")

    def list_available_providers(self) -> List[Dict[str, Any]]:
        """List all available TTS providers"""
        result = []
        for name, provider in self.providers.items():
            result.append({
                "name": name,
                "available": provider.available,
                "error": provider.error_msg if not provider.available else None
            })
        return result

    def set_provider(self, provider_name: str) -> bool:
        """Manually set TTS provider"""
        if provider_name in self.providers:
            provider = self.providers[provider_name]
            if provider.available:
                self.active_provider = provider
                print(f"✓ Switched to TTS provider: {provider_name}")
                return True
            else:
                print(f"✗ Provider '{provider_name}' not available: {provider.error_msg}")
                return False
        else:
            print(f"✗ Unknown provider: {provider_name}")
            return False

    def speak(self, text: str, **kwargs) -> bool:
        """
        Speak text using active TTS provider

        Args:
            text: Text to speak
            **kwargs: Provider-specific parameters
        """
        if not self.active_provider:
            raise RuntimeError("No TTS provider available")

        return self.active_provider.speak(text, **kwargs)

    def speak_slowly(self, text: str, pause_duration: float = 1.0, **kwargs) -> bool:
        """Speak text with contemplative pacing"""
        sentences = text.replace('?', '.').replace('!', '.').split('.')
        sentences = [s.strip() for s in sentences if s.strip()]

        for sentence in sentences:
            if not self.speak(sentence, **kwargs):
                return False
            time.sleep(pause_duration)

        return True

    def speak_mantra(self, mantra: str, repetitions: int = 108,
                     pause_duration: float = 2.0, **kwargs) -> bool:
        """Speak a mantra with repetitions"""
        for i in range(repetitions):
            if not self.speak(mantra, **kwargs):
                return False

            # Pause between repetitions
            if i < repetitions - 1:
                time.sleep(pause_duration)

        return True

    def generate_audio_file(self, text: str, output_path: str, **kwargs) -> bool:
        """
        Generate audio file from text

        Args:
            text: Text to synthesize
            output_path: Path to save audio file
            **kwargs: Provider-specific parameters
        """
        if not self.active_provider:
            raise RuntimeError("No TTS provider available")

        return self.active_provider.generate_audio_file(text, output_path, **kwargs)

    def get_current_provider(self) -> str:
        """Get name of currently active provider"""
        return self.active_provider.name if self.active_provider else None


# Convenience functions
def speak(text: str, prefer_local: bool = False, **kwargs) -> bool:
    """Quick speak function"""
    engine = EnhancedTTSEngine(prefer_local=prefer_local)
    return engine.speak(text, **kwargs)


def speak_prayer(text: str, prefer_local: bool = False, **kwargs) -> bool:
    """Speak prayer with contemplative pacing"""
    engine = EnhancedTTSEngine(prefer_local=prefer_local)
    return engine.speak_slowly(text, pause_duration=1.5, **kwargs)


def speak_mantra(mantra: str, repetitions: int = 108,
                prefer_local: bool = False, **kwargs) -> bool:
    """Speak mantra with repetitions"""
    engine = EnhancedTTSEngine(prefer_local=prefer_local)
    return engine.speak_mantra(mantra, repetitions=repetitions, **kwargs)


if __name__ == "__main__":
    # Test the TTS engine
    print("Vajra.Stream Enhanced TTS Engine Test\n")
    print("=" * 60)

    # Initialize engine
    print("\nInitializing TTS engine...")
    engine = EnhancedTTSEngine(prefer_local=False)

    # List available providers
    print("\nAvailable TTS Providers:")
    print("-" * 60)
    for provider in engine.list_available_providers():
        status = "✓ Available" if provider['available'] else f"✗ {provider['error']}"
        print(f"{provider['name']:<20} {status}")

    print("\n" + "=" * 60)
    print(f"Active Provider: {engine.get_current_provider()}")
    print("=" * 60)

    # Test speech
    print("\nTesting speech...")
    test_text = "Om Mani Padme Hum. May all beings be happy and free from suffering."

    success = engine.speak(test_text)

    if success:
        print("✓ Speech test successful")
    else:
        print("✗ Speech test failed")

    print("\n" + "=" * 60)
    print("Test complete!")
