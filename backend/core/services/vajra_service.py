"""
Vajra.Stream Service Wrapper
Exposes existing Vajra.Stream functionality through web APIs
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime

import numpy as np

# Add parent directory to path to import existing modules
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../"))

# Try importing each module individually to make loading resilient
try:
    from backend.app.config import Settings
except ImportError:
    Settings = None

try:
    from core.astrology import AstrologicalCalculator
except ImportError:
    AstrologicalCalculator = None

try:
    from core.audio_generator import ScalarWaveGenerator
except ImportError:
    ScalarWaveGenerator = None

try:
    from core.enhanced_audio_generator import EnhancedAudioGenerator, PrayerBowlGenerator
except ImportError:
    EnhancedAudioGenerator, PrayerBowlGenerator = None, None

try:
    from core.llm_integration import LLMIntegration
except ImportError:
    LLMIntegration = None

try:
    from core.prayer_wheel import PrayerWheel
except ImportError:
    PrayerWheel = None

try:
    from core.rothko_generator import RothkoGenerator
except ImportError:
    RothkoGenerator = None

try:
    from core.tts_engine import TTSEngine
except ImportError:
    TTSEngine = None

try:
    from core.visual_renderer import VisualRenderer
except ImportError:
    VisualRenderer = None

try:
    from hardware.crystal_broadcaster import Level2CrystalBroadcaster, Level3CrystalBroadcaster
except ImportError:
    Level2CrystalBroadcaster, Level3CrystalBroadcaster = None, None

ENHANCED_MODE = AstrologicalCalculator is not None
print(f"Service running with Astrological Calculations: {AstrologicalCalculator is not None}")


from backend.app.api.v1.endpoints.sessions import AudioConfig, SessionConfig


class VajraStreamService:
    """Main service wrapper for Vajra.Stream functionality"""

    def __init__(self):
        print("Initializing Vajra.Stream Service...")

        # Initialize existing modules if available
        self.settings = Settings() if Settings else None
        self.audio_generator = EnhancedAudioGenerator() if EnhancedAudioGenerator else None
        self.prayer_bowl_generator = PrayerBowlGenerator() if PrayerBowlGenerator else None
        self.level2_broadcaster = Level2CrystalBroadcaster() if Level2CrystalBroadcaster else None
        self.level3_broadcaster = Level3CrystalBroadcaster() if Level3CrystalBroadcaster else None
        self.prayer_wheel = PrayerWheel() if PrayerWheel else None
        self.astrology = AstrologicalCalculator() if AstrologicalCalculator else None
        self.llm_integration = LLMIntegration() if LLMIntegration else None
        self.tts_engine = TTSEngine() if TTSEngine else None
        self.rothko_generator = RothkoGenerator() if RothkoGenerator else None
        self.visual_renderer = VisualRenderer() if VisualRenderer else None

        print("Service modules initialized successfully")

        # Session state
        self.active_sessions: dict[str, dict] = {}
        self.current_audio_data: np.ndarray | None = None
        self.audio_spectrum: list[float] = []
        self.session_history: list[dict] = []

        # Persistence
        self._history_path = os.path.join(os.path.expanduser("~"), ".vajra-stream", "session_history.json")
        self._load_history()

        # Event bus for session events
        self.event_bus = None

        # Background broadcast loop for live radionics + scalar data
        self._broadcast_task: asyncio.Task | None = None

        print("Vajra.Stream Service ready!")

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
                    envelope_type=config.envelope_type,
                )
            else:
                # Fallback: generate simple sine wave
                print(f"Generating basic sine wave at {config.frequency} Hz")
                sample_rate = 44100
                t = np.linspace(0, config.duration, int(sample_rate * config.duration), False)

                if config.prayer_bowl_mode:
                    # Add some harmonics for prayer bowl effect
                    audio_data = (
                        np.sin(config.frequency * 2 * np.pi * t) * config.volume
                        + np.sin(config.frequency * 2 * 2 * np.pi * t) * config.volume * 0.3
                        + np.sin(config.frequency * 3 * 2 * np.pi * t) * config.volume * 0.1
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

    async def generate_chakra_audio(self, chakra_name: str, duration: float = 30.0) -> np.ndarray:
        """Generate specialized chakra healing audio"""
        try:
            print(f"Generating chakra audio for: {chakra_name}")
            if hasattr(self, "audio_generator") and self.audio_generator:
                audio_data = self.audio_generator.generate_chakra_healing(chakra_name, duration)
                self.current_audio_data = audio_data
                self._update_audio_spectrum(audio_data)
                return audio_data
            else:
                # Fallback to base configuration if enhanced generator not found
                # Basic frequency mapping fallback
                freqs = {
                    "root": 396.0,
                    "sacral": 417.0,
                    "solar_plexus": 528.0,
                    "heart": 639.0,
                    "throat": 741.0,
                    "third_eye": 852.0,
                    "crown": 963.0,
                }
                config = AudioConfig(frequency=freqs.get(chakra_name.lower(), 528.0), duration=duration)
                return await self.generate_prayer_bowl_audio(config)
        except Exception as e:
            print(f"Error generating chakra audio: {e}")
            config = AudioConfig(duration=duration)
            return self._generate_fallback_audio(config)

    def _generate_fallback_audio(self, config: AudioConfig) -> np.ndarray:
        """Generate fallback audio in case of errors"""
        sample_rate = 44100
        t = np.linspace(0, config.duration, int(sample_rate * config.duration), False)
        return np.sin(config.frequency * 2 * np.pi * t) * config.volume

    async def broadcast_audio(self, audio_data: np.ndarray, hardware_level: int = 2) -> bool:
        """Broadcast audio using existing crystal broadcasters"""
        try:
            # Import sounddevice for direct audio playback
            import threading

            import sounddevice as sd

            if ENHANCED_MODE:
                if hardware_level == 2 and self.level2_broadcaster:
                    print("Broadcasting with Level 2 Crystal Broadcaster")

                    # Play audio directly through sounddevice
                    def play_audio():
                        try:
                            # Convert to stereo if needed
                            if audio_data.ndim == 1:
                                stereo_audio = np.column_stack([audio_data, audio_data])
                            else:
                                stereo_audio = audio_data

                            sd.play(stereo_audio, samplerate=44100)
                            sd.wait()
                        except Exception as e:
                            print(f"Error in audio playback: {e}")

                    # Play in background thread
                    playback_thread = threading.Thread(target=play_audio)
                    playback_thread.daemon = True
                    playback_thread.start()

                    success = True
                elif hardware_level == 3 and self.level3_broadcaster:
                    print("Broadcasting with Level 3 Crystal Broadcaster")

                    # Play audio directly through sounddevice
                    def play_audio():
                        try:
                            # Convert to stereo if needed
                            if audio_data.ndim == 1:
                                stereo_audio = np.column_stack([audio_data, audio_data])
                            else:
                                stereo_audio = audio_data

                            sd.play(stereo_audio, samplerate=44100)
                            sd.wait()
                        except Exception as e:
                            print(f"Error in audio playback: {e}")

                    # Play in background thread
                    playback_thread = threading.Thread(target=play_audio)
                    playback_thread.daemon = True
                    playback_thread.start()

                    success = True
                else:
                    print(f"Hardware level {hardware_level} not available, using direct audio playback")

                    # Direct audio playback fallback
                    def play_audio():
                        try:
                            # Convert to stereo if needed
                            if audio_data.ndim == 1:
                                stereo_audio = np.column_stack([audio_data, audio_data])
                            else:
                                stereo_audio = audio_data

                            sd.play(stereo_audio, samplerate=44100)
                            sd.wait()
                        except Exception as e:
                            print(f"Error in audio playback: {e}")

                    # Play in background thread
                    playback_thread = threading.Thread(target=play_audio)
                    playback_thread.daemon = True
                    playback_thread.start()

                    success = True
            else:
                # Direct audio playback in basic mode
                print("Playing audio directly through system speakers")

                def play_audio():
                    try:
                        # Convert to stereo if needed
                        if audio_data.ndim == 1:
                            stereo_audio = np.column_stack([audio_data, audio_data])
                        else:
                            stereo_audio = audio_data

                        sd.play(stereo_audio, samplerate=44100)
                        sd.wait()
                    except Exception as e:
                        print(f"Error in audio playback: {e}")

                # Play in background thread
                playback_thread = threading.Thread(target=play_audio)
                playback_thread.daemon = True
                playback_thread.start()

                success = True

            if success:
                print("Audio broadcast successful - playing through system speakers")
            else:
                print("Audio broadcast failed")

            return success

        except ImportError:
            print("sounddevice not available, simulating audio broadcast")
            await asyncio.sleep(0.1)  # Simulate processing time
            return True
        except Exception as e:
            print(f"Error broadcasting audio: {e}")
            return False

    async def create_session(
        self,
        name: str,
        intention: str,
        audio_frequency: float = 136.1,
        duration: int = 3600,
        astrology_enabled: bool = True,
        hardware_enabled: bool = True,
        visuals_enabled: bool = True,
    ) -> str:
        """Create a new blessing session"""
        session_id = f"session_{int(time.time() * 1000)}"

        audio_config = AudioConfig(frequency=audio_frequency)
        config = SessionConfig(
            name=name,
            intention=intention,
            audio_config=audio_config,
            duration=duration,
            astrology_enabled=astrology_enabled,
            hardware_enabled=hardware_enabled,
            visuals_enabled=visuals_enabled,
        )

        session_data = {
            "id": session_id,
            "config": config,
            "status": "created",
            "start_time": None,
            "end_time": None,
            "astrology_data": None,
            "audio_data": None,
            "visual_data": None,
        }

        self.active_sessions[session_id] = session_data

        if astrology_enabled:
            session_data["astrology_data"] = await self._get_astrology_data()

        from modules.interfaces import SessionCreated

        if self.event_bus:
            try:
                self.event_bus.publish(
                    SessionCreated(
                        session_id=session_id,
                        name=name,
                        intention=intention,
                        duration=duration,
                        audio_frequency=audio_frequency,
                    )
                )
            except Exception:
                pass

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

        from modules.interfaces import BroadcastStarted, SessionStarted

        if self.event_bus:
            try:
                self.event_bus.publish(SessionStarted(session_id=session_id, name=session["config"].name))
            except Exception:
                pass
            try:
                self.event_bus.publish(
                    BroadcastStarted(
                        session_id=session_id,
                        hardware_level=2 if session["config"].hardware_enabled else 0,
                        frequencies=[session["config"].audio_config.frequency],
                    )
                )
            except Exception:
                pass

        # Notify via WebSocket that broadcast started
        try:
            from backend.websocket.connection_manager_stable_v2 import stable_connection_manager_v2

            asyncio.create_task(
                stable_connection_manager_v2.broadcast(
                    {
                        "type": "CRYSTAL_BROADCAST_STARTED",
                        "session_id": session_id,
                        "timestamp": time.time(),
                    }
                )
            )
        except Exception:
            pass  # Non-critical

        # Start live radionics rate + scalar wave broadcast loop
        self._start_broadcast_loop()

        print(f"Session started successfully: {session_id}")
        return True

    def _start_broadcast_loop(self):
        """Start background loop that broadcasts live radionics rate and scalar wave status."""
        if self._broadcast_task and not self._broadcast_task.done():
            return  # Already running
        self._broadcast_task = asyncio.create_task(self._broadcast_loop())

    async def _broadcast_loop(self):
        """Periodically emit RADIONICS_RATE_BROADCAST and SCALAR_WAVE_ACTIVE to WebSocket clients, and publish RNGReadingEvent."""
        import random
        import uuid

        from backend.core.services.rng_attunement_service import get_rng_service
        from modules.interfaces import RNGReadingEvent

        idle_count = 0
        while True:
            await asyncio.sleep(3)
            running = [s for s in self.active_sessions.values() if s.get("status") == "running"]
            if not running:
                idle_count += 1
                if idle_count > 10:
                    self._broadcast_task = None
                    return
                continue
            idle_count = 0

            try:
                from backend.websocket.connection_manager_stable_v2 import stable_connection_manager_v2

                # Count running sessions
                running = [s for s in self.active_sessions.values() if s.get("status") == "running"]
                if not running:
                    continue

                # Emit SCALAR_WAVE_ACTIVE
                await stable_connection_manager_v2.broadcast(
                    {
                        "type": "SCALAR_WAVE_ACTIVE",
                        "data": {"active": True, "session_count": len(running)},
                        "timestamp": time.time(),
                    }
                )

                # Get latest RNG data to publish an event
                rng_service = get_rng_service()
                rng_sessions = rng_service.get_all_sessions()
                if rng_sessions:
                    session_id = rng_sessions[-1]
                    latest_reading = rng_service.get_reading(session_id)

                    if latest_reading and self.event_bus:
                        # Publish DomainEvent for the Autonomous Agent
                        event = RNGReadingEvent(
                            timestamp=datetime.now(),
                            event_id=str(uuid.uuid4()),
                            session_id=session_id,
                            coherence=latest_reading.coherence,
                            entropy=latest_reading.entropy,
                            floating_needle_score=latest_reading.floating_needle_score,
                        )
                        try:
                            self.event_bus.publish(event)

                            # Also broadcast to frontend WebSockets for the UI
                            await stable_connection_manager_v2.broadcast(
                                {
                                    "type": "RNG_READING",
                                    "data": {
                                        "coherence": latest_reading.coherence,
                                        "entropy": latest_reading.entropy,
                                        "floating_needle_score": latest_reading.floating_needle_score,
                                        "session_id": session_id,
                                        "tone_arm": latest_reading.tone_arm,
                                        "needle_position": latest_reading.needle_position,
                                        "needle_state": latest_reading.needle_state,
                                        "trend": latest_reading.trend,
                                        "quality": latest_reading.quality,
                                    },
                                    "timestamp": time.time(),
                                }
                            )
                        except Exception as e:
                            print(f"Error publishing RNGReadingEvent: {e}")

                # Emit Buddha Recitation status if running
                try:
                    from core.buddha_recitation_loop import get_recitation_loop

                    loop = get_recitation_loop()
                    status = loop.get_status()
                    if status.get("running"):
                        await stable_connection_manager_v2.broadcast(
                            {
                                "type": "BUDDHA_RECITATION_UPDATE",
                                "data": status,
                                "timestamp": time.time(),
                            }
                        )
                except Exception as e:
                    print(f"Error broadcasting Buddha Recitation: {e}")

                # Emit Saka Dawa Status
                try:
                    from core.auspicious_timing import check_saka_dawa

                    saka_dawa_status = check_saka_dawa()
                    await stable_connection_manager_v2.broadcast(
                        {
                            "type": "SAKA_DAWA_CHECK",
                            "data": saka_dawa_status,
                            "timestamp": time.time(),
                        }
                    )
                except Exception as e:
                    print(f"Error broadcasting Saka Dawa Check: {e}")

                # Emit RADIONICS_RATE_BROADCAST for each running session
                for session in running:
                    cfg = session.get("config")
                    freq = getattr(getattr(cfg, "audio_config", None), "frequency", 528.0)
                    rate = round((freq % 100) + random.uniform(-2, 2), 2)
                    await stable_connection_manager_v2.broadcast(
                        {
                            "type": "RADIONICS_RATE_BROADCAST",
                            "data": {
                                "rate": rate,
                                "session_id": session["id"],
                                "frequency": freq,
                            },
                            "timestamp": time.time(),
                        }
                    )

            except Exception as e:
                print(f"Error in broadcast loop: {e}")

    async def stop_session(self, session_id: str) -> bool:
        """Stop a blessing session"""
        if session_id not in self.active_sessions:
            print(f"Session not found: {session_id}")
            return False

        session = self.active_sessions[session_id]
        session["status"] = "stopped"
        session["end_time"] = time.time()

        from modules.interfaces import SessionStopped

        runtime = time.time() - session["start_time"] if session.get("start_time") else 0
        if self.event_bus:
            try:
                self.event_bus.publish(
                    SessionStopped(
                        session_id=session_id,
                        name=session["config"].name,
                        runtime_seconds=runtime,
                    )
                )
            except Exception:
                pass

        # Move to history
        self.session_history.append(session.copy())
        del self.active_sessions[session_id]
        self._save_history()

        print(f"Session stopped: {session_id}")
        return True

    def _load_history(self):
        """Load session history from JSON file, restoring data across restarts."""
        try:
            if os.path.exists(self._history_path):
                with open(self._history_path, encoding="utf-8") as f:
                    self.session_history = json.load(f)
                print(f"Loaded {len(self.session_history)} historical sessions from {self._history_path}")
        except Exception as e:
            print(f"Could not load session history: {e}")
            self.session_history = []

    def _save_history(self):
        """Persist session history to JSON file."""
        try:
            os.makedirs(os.path.dirname(self._history_path), exist_ok=True)
            # Serialize — strip non-JSON-serializable fields
            serializable = []
            for s in self.session_history[-500:]:  # Keep last 500 sessions
                clean = {}
                for k, v in s.items():
                    if k in ("audio_data", "visual_data", "astrology_data"):
                        clean[k] = "[binary data]" if v else None
                    elif isinstance(v, (str, int, float, bool, list, dict, type(None))):
                        clean[k] = v
                    else:
                        try:
                            json.dumps({k: v})
                            clean[k] = v
                        except (TypeError, ValueError):
                            clean[k] = str(v)[:200]
                serializable.append(clean)
            with open(self._history_path, "w", encoding="utf-8") as f:
                json.dump(serializable, f, indent=2, default=str)
        except Exception as e:
            print(f"Could not save session history: {e}")

    def delete_session(self, session_id: str) -> bool:
        """Delete a session (only if not running)"""
        if session_id not in self.active_sessions:
            print(f"Session not found: {session_id}")
            return False

        session = self.active_sessions[session_id]
        if session["status"] == "running":
            print(f"Cannot delete running session: {session_id}")
            return False

        del self.active_sessions[session_id]
        print(f"Session deleted: {session_id}")
        return True

    async def _get_astrology_data(self, dt: datetime = None, location: tuple[float, float] = None) -> dict:
        """Get astrological data for a given time and location"""
        try:
            if self.astrology:
                import pytz

                calc_time = dt if dt is not None else datetime.now(pytz.UTC)
                calc_loc = location if location is not None else (37.7749, -122.4194)

                print(f"Getting comprehensive astrology data for dt={calc_time}, loc={calc_loc}...")

                # Calculate new consolidated astrological data
                data = self.astrology.get_comprehensive_astrology(calc_time, calc_loc)

                # Maintain legacy format items at top level for backward compatibility
                data["moon_phase"] = self.astrology.get_moon_phase(calc_time)
                data["planetary_positions"] = data["western"]["positions"]

                # Serialize auspicious times datetime objects to strings
                ser_auspicious = {}
                auspicious = self.astrology.calculate_auspicious_times(calc_time, calc_loc)
                for k, v in auspicious.items():
                    if isinstance(v, datetime):
                        ser_auspicious[k] = v.isoformat()
                    elif isinstance(v, dict):
                        ser_auspicious[k] = v
                data["auspicious_times"] = ser_auspicious
                data["timestamp"] = time.time()

                return data
            else:
                # Fallback data
                return {
                    "moon_phase": {"phase_name": "waxing", "illumination": 50.0, "phase_angle": 90.0},
                    "planetary_positions": {"sun": {"formatted": "Aries 0.00°"}},
                    "auspicious_times": {"sunrise": "morning", "sunset": "evening"},
                    "timestamp": time.time(),
                }
        except Exception as e:
            print(f"Error getting astrology data: {e}")
            return {}

    async def _generate_visuals(self, audio_data: np.ndarray) -> dict:
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

                return {"sacred_geometry": visual_data, "rothko_art": rothko_data, "timestamp": time.time()}
            else:
                return {
                    "sacred_geometry": {"status": "basic_mode"},
                    "rothko_art": {"status": "basic_mode"},
                    "timestamp": time.time(),
                }
        except Exception as e:
            print(f"Error generating visuals: {e}")
            return {}

    def _update_audio_spectrum(self, audio_data: np.ndarray):
        """Update audio spectrum for real-time visualization"""
        try:
            # Simple FFT for spectrum analysis
            fft = np.fft.fft(audio_data)
            frequencies = np.abs(fft[: len(fft) // 2])

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

    def get_audio_spectrum(self) -> list[float]:
        """Get current audio spectrum for WebSocket streaming"""
        return self.audio_spectrum

    def get_session_status(self, session_id: str) -> dict | None:
        """Get status of a specific session"""
        return self.active_sessions.get(session_id)

    def get_all_sessions(self) -> dict:
        """Get all active sessions"""
        return self.active_sessions

    def get_session_history(self) -> list[dict]:
        """Get session history"""
        return self.session_history

    def get_system_status(self) -> dict:
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
                "visual_renderer": self.visual_renderer is not None,
            },
        }


# Global service instance
vajra_service = VajraStreamService()
