"""
Dependency Injection Container
Single place that wires all modules together
"""

import sys
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from infrastructure.event_bus import SimpleEventBus
from modules.scalar_waves import ScalarWaveService


class Container:
    """Dependency injection container - wires everything together"""

    _instance = None

    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        logger.info("🔧 Initializing Vajra Stream Container...")

        # Core infrastructure
        self.event_bus = SimpleEventBus()

        # Services (lazy loaded)
        self._scalar_waves = None
        self._radionics = None
        self._anatomy = None
        self._blessings = None
        self._astrology = None
        self._audio = None
        self._visualization = None
        self._time_cycles = None
        self._prayer_wheel = None
        self._composer = None
        self._healing = None
        self._llm = None

        # Setup event handlers
        self._setup_event_handlers()

        self._initialized = True
        logger.info("✅ Container initialized successfully")

    @property
    def scalar_waves(self) -> ScalarWaveService:
        """Get scalar wave service"""
        if self._scalar_waves is None:
            logger.info("Initializing Scalar Wave Service...")
            self._scalar_waves = ScalarWaveService(event_bus=self.event_bus)
        return self._scalar_waves

    @property
    def radionics(self):
        """Get radionics service"""
        if self._radionics is None:
            logger.info("Initializing Radionics Service...")
            from modules.radionics import RadionicsService
            self._radionics = RadionicsService(event_bus=self.event_bus)
        return self._radionics

    @property
    def anatomy(self):
        """Get anatomy service"""
        if self._anatomy is None:
            logger.info("Initializing Anatomy Service...")
            from modules.anatomy import AnatomyService
            self._anatomy = AnatomyService(event_bus=self.event_bus)
        return self._anatomy

    @property
    def blessings(self):
        """Get blessings service"""
        if self._blessings is None:
            logger.info("Initializing Blessings Service...")
            from modules.blessings import BlessingService
            self._blessings = BlessingService(event_bus=self.event_bus)
        return self._blessings

    @property
    def astrology(self):
        """Get astrology service"""
        if self._astrology is None:
            logger.info("Initializing Astrology Service...")
            try:
                from modules.astrology import AstrologyService
                self._astrology = AstrologyService(event_bus=self.event_bus)
            except ImportError:
                logger.warning("Astrology service not available")
                self._astrology = None
        return self._astrology

    @property
    def audio(self):
        """Get audio service"""
        if self._audio is None:
            logger.info("Initializing Audio Service...")
            from modules.audio import AudioService
            self._audio = AudioService(event_bus=self.event_bus)
        return self._audio

    @property
    def visualization(self):
        """Get visualization service"""
        if self._visualization is None:
            logger.info("Initializing Visualization Service...")
            from modules.visualization import VisualizationService
            self._visualization = VisualizationService(event_bus=self.event_bus)
        return self._visualization

    @property
    def time_cycles(self):
        """Get time cycles service"""
        if self._time_cycles is None:
            logger.info("Initializing Time Cycles Service...")
            from modules.time_cycles import TimeCyclesService
            self._time_cycles = TimeCyclesService(event_bus=self.event_bus)
        return self._time_cycles

    @property
    def prayer_wheel(self):
        """Get prayer wheel service"""
        if self._prayer_wheel is None:
            logger.info("Initializing Prayer Wheel Service...")
            from modules.prayer_wheel import PrayerWheelService
            self._prayer_wheel = PrayerWheelService(event_bus=self.event_bus)
        return self._prayer_wheel

    @property
    def composer(self):
        """Get composer service"""
        if self._composer is None:
            logger.info("Initializing Composer Service...")
            from modules.composer import ComposerService
            self._composer = ComposerService(event_bus=self.event_bus)
        return self._composer

    @property
    def healing(self):
        """Get healing service"""
        if self._healing is None:
            logger.info("Initializing Healing Service...")
            from modules.healing import HealingService
            self._healing = HealingService(event_bus=self.event_bus)
        return self._healing

    @property
    def llm(self):
        """Get LLM service"""
        if self._llm is None:
            logger.info("Initializing LLM Service...")
            from modules.llm import LLMService
            self._llm = LLMService(event_bus=self.event_bus)
        return self._llm

    def _setup_event_handlers(self):
        """Wire up event handlers between modules"""
        from modules.interfaces import HealingSessionStarted, ScalarWavesGenerated, BlessingGenerated

        # Example: Log all events
        def log_all_events(event):
            logger.info(f"📢 Event: {type(event).__name__}")

        # Subscribe to all event types
        for event_type in [HealingSessionStarted, ScalarWavesGenerated, BlessingGenerated]:
            self.event_bus.subscribe(event_type, log_all_events)

        # Example: When healing session starts, generate scalar waves automatically
        def auto_generate_scalar_waves(event: HealingSessionStarted):
            logger.info(f"🌊 Auto-generating scalar waves for {event.target_name}")
            # This would be called automatically when session starts
            # self.scalar_waves.generate("hybrid", 10000, 0.8)

        # Uncomment to enable auto-generation
        # self.event_bus.subscribe(HealingSessionStarted, auto_generate_scalar_waves)

    def reset(self):
        """Reset container (useful for testing)"""
        self._scalar_waves = None
        self._radionics = None
        self._anatomy = None
        self._blessings = None
        self._astrology = None
        self._audio = None
        self._visualization = None
        self._time_cycles = None
        self._prayer_wheel = None
        self._composer = None
        self._healing = None
        self._llm = None
        self.event_bus.clear()
        logger.info("Container reset")


# Global container instance
container = Container()
