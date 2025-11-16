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
        self.event_bus.clear()
        logger.info("Container reset")


# Global container instance
container = Container()
