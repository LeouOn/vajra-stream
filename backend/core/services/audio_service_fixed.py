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

# Add project root to path for importing core modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

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
        """Play audio data (simulation)"""
        try:
            self.is_playing = True
            # In a real implementation, this would send audio to sounddevice
            # For now, we'll simulate playback
            print(f"Playing audio with {len(audio_data)} samples")
            return {"status": "playing", "message": "Audio playback started"}
        except Exception as e:
            return {"error": f"Audio playback failed: {str(e)}"}
        
    async def stop_audio(self) -> Dict[str, Any]:
        """Stop current audio playback"""
        try:
            self.is_playing = False
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