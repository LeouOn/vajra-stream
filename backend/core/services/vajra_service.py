"""
Vajra.Stream Service Wrapper
Exposes existing Vajra.Stream functionality through web APIs
"""

import asyncio
import sys
import os
from typing import Dict, List, Optional
import numpy as np
from dataclasses import dataclass
import time

# Add parent directory to path to import existing modules
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

try:
    from core.audio_generator import ScalarWaveGenerator
    from core.enhanced_audio_generator import EnhancedAudioGenerator, PrayerBowlGenerator
    from hardware.crystal_broadcaster import Level2CrystalBroadcaster, Level3CrystalBroadcaster
    from core.prayer_wheel import PrayerWheel
    from core.astrology import AstrologicalCalculator
    from core.llm_integration import LLMIntegration
    from core.tts_engine import TTSEngine
    from core.rothko_generator import RothkoGenerator
    from core.visual_renderer import VisualRenderer
    from config.settings import Settings
    
    ENHANCED_MODE = True
    print("✅ Enhanced Vajra.Stream modules loaded successfully")
    
except ImportError as e:
    print(f"WARNING: Could not load enhanced modules: {e}")
    print("INFO: Running in basic mode with fallback functionality")
    ENHANCED_MODE = False

@dataclass
class AudioConfig:
    """Audio configuration for prayer bowl generation"""
    frequency: float = 136.1  # OM frequency
    duration: float = 30.0
    volume: float = 0.8
    prayer_bowl_mode: bool = True
    harmonic_strength: float = 0.3
    modulation_depth: float = 0.05
    envelope_type: str = "prayer_bowl"

@dataclass
class SessionConfig:
    """Session configuration"""
    name: str
    intention: str
    audio_config: AudioConfig
    duration: int = 3600  # 1 hour
    astrology_enabled: bool = True
    hardware_enabled: bool = True
    visuals_enabled: bool = True

class VajraStreamService:
    """Main service wrapper for Vajra.Stream functionality"""
    
    def __init__(self):
        print("Initializing Vajra.Stream Service...")
        
        if ENHANCED_MODE:
            try:
                # Initialize existing modules
                self.settings = Settings()
                self.audio_generator = EnhancedAudioGenerator()
                self.prayer_bowl_generator = PrayerBowlGenerator()
                self.level2_broadcaster = Level2CrystalBroadcaster()
                self.level3_broadcaster = Level3CrystalBroadcaster()
                self.prayer_wheel = PrayerWheel()
                self.astrology = AstrologicalCalculator()
                self.llm_integration = LLMIntegration()
                self.tts_engine = TTSEngine()
                self.rothko_generator = RothkoGenerator()
                self.visual_renderer = VisualRenderer()
                
                print("All enhanced modules initialized successfully")
            except Exception as e:
                print(f"Error initializing enhanced modules: {e}")
                print("Falling back to basic functionality")
                self._initialize_basic_mode()
        else:
            self._initialize_basic_mode()
        
        # Session state
        self.active_sessions: Dict[str, Dict] = {}
        self.current_audio_data: Optional[np.ndarray] = None
        self.audio_spectrum: List[float] = []
        self.session_history: List[Dict] = []
        
        print("Vajra.Stream Service ready!")
    
    def _initialize_basic_mode(self):
        """Initialize basic mode functionality"""
        self.audio_generator = None
        self.prayer_bowl_generator = None
        self.level2_broadcaster = None
        self.level3_broadcaster = None
        self.prayer_wheel = None
        self.astrology = None
        self.llm_integration = None
        self.tts_engine = None
        self.rothko_generator = None
        self.visual_renderer = None
    
    async def generate_prayer_bowl_audio(self, config: AudioConfig) -> np.ndarray:
        """Generate prayer bowl audio using existing enhanced generator"""
        try:
            if ENHANCED_MODE and self.prayer_bowl_generator:
                print(f"Generating prayer bowl audio at {config.frequency} Hz")
                audio_data = await self.prayer_bowl_generator.generate_prayer_bowl_tone(
                    frequency=config.frequency,
                    duration=config.duration,
                    volume=config.volume,
                    harmonic_strength=config.harmonic_strength,
                    modulation_depth=config.modulation_depth,
                    envelope_type=config.envelope_type
                )
            else:
                # Fallback: generate simple sine wave
                print(f"Generating basic sine wave at {config.frequency} Hz")
                sample_rate = 44100
                t = np.linspace(0, config.duration, int(sample_rate * config.duration), False)
                
                if config.prayer_bowl_mode:
                    # Add some harmonics for prayer bowl effect
                    audio_data = (
                        np.sin(config.frequency * 2 * np.pi * t) * config.volume +
                        np.sin(config.frequency * 2 * 2 * np.pi * t) * config.volume * 0.3 +
                        np.sin(config.frequency * 3 * 2 * np.pi * t) * config.volume * 0.1
                    )
                else:
                    audio_data = np.sin(config.frequency * 2 * np.pi * t) * config.volume
                
                # Apply simple envelope
                envelope = np.exp(-t * 0.1)  # Simple decay
                audio_data *= envelope
            
            self.current_audio_data = audio_data
            self._update_audio_spectrum(audio_data)
            
            print(f"Audio generated successfully: {len(audio_data)} samples")
            return audio_data
            
        except Exception as e:
            print(f"Error generating prayer bowl audio: {e}")
            # Return fallback audio
            return self._generate_fallback_audio(config)
    
    def _generate_fallback_audio(self, config: AudioConfig) -> np.ndarray:
        """Generate fallback audio in case of errors"""
        sample_rate = 44100
        t = np.linspace(0, config.duration, int(sample_rate * config.duration), False)
        return np.sin(config.frequency * 2 * np.pi * t) * config.volume
    
    async def broadcast_audio(self, audio_data: np.ndarray, hardware_level: int = 2) -> bool:
        """Broadcast audio using existing crystal broadcasters"""
        try:
            if ENHANCED_MODE:
                if hardware_level == 2 and self.level2_broadcaster:
                    print("Broadcasting with Level 2 Crystal Broadcaster")
                    success = await self.level2_broadcaster.generate_5_channel_blessing(audio_data)
                elif hardware_level == 3 and self.level3_broadcaster:
                    print("Broadcasting with Level 3 Crystal Broadcaster")
                    success = await self.level3_broadcaster.generate_528hz_blessing(audio_data)
                else:
                    print(f"Hardware level {hardware_level} not available")
                    success = False
            else:
                # Simulate broadcasting
                print(f"Simulating audio broadcast at level {hardware_level}")
                await asyncio.sleep(0.1)  # Simulate processing time
                success = True
            
            if success:
                print("Audio broadcast successful")
            else:
                print("Audio broadcast failed")
            
            return success
            
        except Exception as e:
            print(f"Error broadcasting audio: {e}")
            return False
    
    async def create_session(self, config: SessionConfig) -> str:
        """Create a new blessing session"""
        session_id = f"session_{int(time.time() * 1000)}"
        
        session_data = {
            "id": session_id,
            "config": config,
            "status": "created",
            "start_time": None,
            "end_time": None,
            "astrology_data": None,
            "audio_data": None,
            "visual_data": None
        }
        
        self.active_sessions[session_id] = session_data
        
        # Generate astrology data if enabled
        if config.astrology_enabled:
            session_data["astrology_data"] = await self._get_astrology_data()
        
        print(f"Session created: {session_id} - {config.name}")
        return session_id
    
    async def start_session(self, session_id: str) -> bool:
        """Start a blessing session"""
        if session_id not in self.active_sessions:
            print(f"Session not found: {session_id}")
            return False
        
        session = self.active_sessions[session_id]
        session["status"] = "running"
        session["start_time"] = time.time()
        
        print(f"Starting session: {session_id}")
        
        # Generate and play audio
        audio_data = await self.generate_prayer_bowl_audio(session["config"].audio_config)
        session["audio_data"] = audio_data
        
        # Broadcast if hardware enabled
        if session["config"].hardware_enabled:
            await self.broadcast_audio(audio_data)
        
        # Generate visuals if enabled
        if session["config"].visuals_enabled:
            session["visual_data"] = await self._generate_visuals(audio_data)
        
        print(f"Session started successfully: {session_id}")
        return True
    
    async def stop_session(self, session_id: str) -> bool:
        """Stop a blessing session"""
        if session_id not in self.active_sessions:
            print(f"Session not found: {session_id}")
            return False
        
        session = self.active_sessions[session_id]
        session["status"] = "stopped"
        session["end_time"] = time.time()
        
        # Move to history
        self.session_history.append(session.copy())
        del self.active_sessions[session_id]
        
        print(f"Session stopped: {session_id}")
        return True
    
    async def _get_astrology_data(self) -> Dict:
        """Get current astrological data"""
        try:
            if ENHANCED_MODE and self.astrology:
                print("Getting astrology data...")
                moon_phase = self.astrology.get_moon_phase()
                planetary_positions = self.astrology.get_planetary_positions()
                auspicious_times = self.astrology.get_auspicious_times()
                
                return {
                    "moon_phase": moon_phase,
                    "planetary_positions": planetary_positions,
                    "auspicious_times": auspicious_times,
                    "timestamp": time.time()
                }
            else:
                # Fallback data
                return {
                    "moon_phase": "waxing",
                    "planetary_positions": {"sun": "aries", "moon": "taurus"},
                    "auspicious_times": ["morning", "evening"],
                    "timestamp": time.time()
                }
        except Exception as e:
            print(f"Error getting astrology data: {e}")
            return {}
    
    async def _generate_visuals(self, audio_data: np.ndarray) -> Dict:
        """Generate visual data based on audio"""
        try:
            if ENHANCED_MODE and self.visual_renderer:
                print("Generating visuals...")
                visual_data = await self.visual_renderer.generate_sacred_geometry(audio_data)
                
                # Generate Rothko-style art
                if self.rothko_generator:
                    rothko_data = await self.rothko_generator.generate_contemplation_art(audio_data)
                else:
                    rothko_data = {}
                
                return {
                    "sacred_geometry": visual_data,
                    "rothko_art": rothko_data,
                    "timestamp": time.time()
                }
            else:
                return {
                    "sacred_geometry": {"status": "basic_mode"},
                    "rothko_art": {"status": "basic_mode"},
                    "timestamp": time.time()
                }
        except Exception as e:
            print(f"Error generating visuals: {e}")
            return {}
    
    def _update_audio_spectrum(self, audio_data: np.ndarray):
        """Update audio spectrum for real-time visualization"""
        try:
            # Simple FFT for spectrum analysis
            fft = np.fft.fft(audio_data)
            frequencies = np.abs(fft[:len(fft)//2])
            
            # Normalize and update (take first 100 frequency bins)
            if len(frequencies) > 0:
                max_freq = np.max(frequencies)
                if max_freq > 0:
                    self.audio_spectrum = (frequencies[:100] / max_freq).tolist()
                else:
                    self.audio_spectrum = [0.0] * 100
            else:
                self.audio_spectrum = [0.0] * 100
            
        except Exception as e:
            print(f"Error updating audio spectrum: {e}")
            self.audio_spectrum = [0.0] * 100
    
    def get_audio_spectrum(self) -> List[float]:
        """Get current audio spectrum for WebSocket streaming"""
        return self.audio_spectrum
    
    def get_session_status(self, session_id: str) -> Optional[Dict]:
        """Get status of a specific session"""
        return self.active_sessions.get(session_id)
    
    def get_all_sessions(self) -> Dict:
        """Get all active sessions"""
        return self.active_sessions
    
    def get_session_history(self) -> List[Dict]:
        """Get session history"""
        return self.session_history
    
    def get_system_status(self) -> Dict:
        """Get overall system status"""
        return {
            "enhanced_mode": ENHANCED_MODE,
            "active_sessions": len(self.active_sessions),
            "current_audio": self.current_audio_data is not None,
            "spectrum_available": len(self.audio_spectrum) > 0,
            "modules_loaded": {
                "audio_generator": self.audio_generator is not None,
                "prayer_bowl_generator": self.prayer_bowl_generator is not None,
                "crystal_broadcaster": self.level2_broadcaster is not None,
                "astrology": self.astrology is not None,
                "visual_renderer": self.visual_renderer is not None
            }
        }

# Global service instance
vajra_service = VajraStreamService()