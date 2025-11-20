"""
Vajra.Stream Audio Service
Wraps existing audio generation functionality for API access
"""
import asyncio
import sys
import os
from typing import List, Optional, Dict, Any
import numpy as np
from datetime import datetime
import threading
import time

# Add project root to path for importing core modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    print("Warning: sounddevice not available. Audio playback will be simulated.")
    SOUNDDEVICE_AVAILABLE = False

try:
    from core.enhanced_audio_generator import EnhancedAudioGenerator
    from core.audio_generator import ScalarWaveGenerator
except ImportError as e:
    print(f"Warning: Could not import core audio modules: {e}")
    # Fallback for development without core modules
    EnhancedAudioGenerator = None
    ScalarWaveGenerator = None

class AudioService:
    """Service for managing audio generation and playback"""
    
    def __init__(self):
        self.generator = None
        self.current_session = None
        self.is_playing = False
        self.active_frequencies = []
        self.current_spectrum = []
        
        # Initialize audio generator if available
        if EnhancedAudioGenerator:
            try:
                self.generator = EnhancedAudioGenerator()
                print("Enhanced Audio Generator initialized successfully")
            except Exception as e:
                print(f"Error initializing Enhanced Audio Generator: {e}")
        
    async def generate_audio(self, config: dict) -> Dict[str, Any]:
        """Generate audio based on configuration"""
        if not self.generator:
            return {"error": "Audio generator not available"}
            
        try:
            audio_type = config.get("type", "prayer_bowl")
            frequency = config.get("frequency", 432)
            duration = config.get("duration", 300)
            intention = config.get("intention", "peace")
            pure_sine = config.get("pure_sine", False)
            
            if audio_type == "prayer_bowl":
                audio_data = self.generator.generate_prayer_bowl_tone(
                    frequency=frequency,
                    duration=duration,
                    pure_sine=pure_sine
                )
            elif audio_type == "solfeggio":
                audio_data = self.generator.generate_solfeggio_tone(frequency, duration)
            elif audio_type == "binaural":
                base_freq = config.get("base_frequency", 432)
                beat_freq = config.get("beat_frequency", 7.83)
                audio_data = self.generator.generate_binaural_beat(base_freq, beat_freq, duration)
            elif audio_type == "schumann":
                audio_data = self.generator.generate_schumann_resonance(duration)
            else:
                return {"error": f"Unknown audio type: {audio_type}"}
            
            # Store active frequencies
            self.active_frequencies = [frequency] if isinstance(frequency, (int, float)) else config.get("frequencies", [frequency])
            
            return {
                "status": "success",
                "audio_data": audio_data.tolist() if hasattr(audio_data, 'tolist') else audio_data,
                "sample_rate": 44100,
                "duration": duration,
                "frequency": frequency
            }
            
        except Exception as e:
            return {"error": f"Audio generation failed: {str(e)}"}
        
    async def play_audio(self, audio_data: List[float]) -> Dict[str, Any]:
        """Play audio data through system speakers"""
        try:
            if not SOUNDDEVICE_AVAILABLE:
                print(f"Simulating audio playback with {len(audio_data)} samples (sounddevice not available)")
                self.is_playing = True
                return {"status": "simulated", "message": "Audio playback simulated (sounddevice not available)"}
            
            self.is_playing = True
            
            # Convert list to numpy array if needed
            if isinstance(audio_data, list):
                audio_data = np.array(audio_data)
            
            # Ensure audio is in the right format (float32)
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            
            # For stereo, ensure we have 2D array
            if audio_data.ndim == 1:
                # Convert mono to stereo
                stereo_audio = np.column_stack([audio_data, audio_data])
            else:
                stereo_audio = audio_data
            
            print(f"Playing audio with {len(audio_data)} samples through system speakers")
            
            # Play audio in a separate thread to avoid blocking the async function
            def play_in_thread():
                try:
                    sd.play(stereo_audio, samplerate=44100)
                    sd.wait()  # Wait until playback is finished
                except Exception as e:
                    print(f"Error in audio playback thread: {e}")
                finally:
                    self.is_playing = False
            
            # Start playback in background thread
            playback_thread = threading.Thread(target=play_in_thread)
            playback_thread.daemon = True
            playback_thread.start()
            
            return {"status": "playing", "message": "Audio playback started through system speakers"}
            
        except Exception as e:
            self.is_playing = False
            return {"error": f"Audio playback failed: {str(e)}"}
        
    async def stop_audio(self) -> Dict[str, Any]:
        """Stop current audio playback"""
        try:
            self.is_playing = False
            if SOUNDDEVICE_AVAILABLE:
                sd.stop()  # Stop sounddevice playback
            print("Audio playback stopped")
            return {"status": "stopped", "message": "Audio playback stopped"}
        except Exception as e:
            return {"error": f"Audio stop failed: {str(e)}"}
        
    def get_spectrum(self) -> Dict[str, Any]:
        """Get current frequency spectrum (simulated)"""
        if self.is_playing and self.active_frequencies:
            # Generate simulated spectrum based on active frequencies
            spectrum = []
            for freq in self.active_frequencies:
                # Create a simple spectrum peak for each frequency
                amplitude = 0.8 * np.exp(-((freq - 440) / 100) ** 2)  # Gaussian-like distribution
                spectrum.append(amplitude)
            
            self.current_spectrum = spectrum
            return {"frequencies": self.active_frequencies, "amplitudes": spectrum}
        else:
            return {"frequencies": [], "amplitudes": []}
        
    def get_active_frequencies(self) -> List[float]:
        """Get currently active frequencies"""
        return self.active_frequencies
        
    def get_status(self) -> Dict[str, Any]:
        """Get current audio service status"""
        return {
            "is_playing": self.is_playing,
            "current_session": self.current_session,
            "active_frequencies": self.active_frequencies,
            "generator_available": self.generator is not None,
            "timestamp": datetime.now().isoformat()
        }

# Global audio service instance
audio_service = AudioService()