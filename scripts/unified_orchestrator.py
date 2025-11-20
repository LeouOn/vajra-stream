"""
Unified Orchestrator
Central brain that initializes the Event Bus, loads configuration,
and manages the lifecycle of all services.
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
import time
from datetime import datetime
import uuid
# from dataclasses import dataclass

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from infrastructure.event_bus import EnhancedEventBus
try:
    import config.settings as settings
except ImportError:
    # Fallback if config package is not found directly
    import sys
    sys.path.append(str(Path(__file__).parent.parent / "config"))
    import settings
from modules.blessing_router import BlessingRouter, TargetSpecification, TargetType, DeliveryMethod
from modules.crystal import CrystalService
from modules.radionics_enhancer import RadionicsEnhancer
from modules.interfaces import DomainEvent
from modules.audio import AudioService
from modules.healing import HealingService
from modules.visualization import VisualizationService

class RadionicsRateAttuned(DomainEvent):
    """Event: Radionics rate has been attuned"""
    def __init__(self, intention: str, rate: float, padding_layers: int, timestamp=None, event_id=None):
        # Initialize parent dataclass fields
        if timestamp is None:
            timestamp = datetime.now()
        if event_id is None:
            event_id = str(uuid.uuid4())
            
        # Since DomainEvent is a dataclass in modules.interfaces, we can set attributes directly
        # or call __init__ if it was generated. Dataclasses generate __init__.
        super().__init__(timestamp, event_id)
        self.intention = intention
        self.rate = rate
        self.padding_layers = padding_layers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class UnifiedOrchestrator:
    """
    Central orchestrator for Vajra Stream platform.
    Manages services, event bus, and session lifecycle.
    """
    
    def __init__(self):
        self.event_bus = EnhancedEventBus(persistence_path="data/events.jsonl")
        self.settings = settings
        self.services = {}
        self.active_sessions = {}
        
        self._initialize_services()
        self._register_handlers()
        
        logger.info("Unified Orchestrator initialized")
        
    def _initialize_services(self):
        """Initialize all core services"""
        logger.info("Initializing services...")
        
        # Initialize services with event bus injection
        self.services['blessing_router'] = BlessingRouter(self.event_bus)
        self.services['crystal'] = CrystalService(self.event_bus)
        self.services['radionics_enhancer'] = RadionicsEnhancer()
        self.services['audio'] = AudioService(self.event_bus)
        self.services['healing'] = HealingService(self.event_bus)
        self.services['visualization'] = VisualizationService(self.event_bus)
        
        logger.info(f"Initialized {len(self.services)} services: {list(self.services.keys())}")
        
    def _register_handlers(self):
        """Register event handlers"""
        # Example: Log all events
        # self.event_bus.subscribe(DomainEvent, self._log_event)
        pass
        
    def create_session(
        self,
        intention: str,
        targets: List[Dict[str, Any]],
        modalities: List[str],
        duration: int
    ) -> str:
        """Create unified healing/blessing session"""
        session_id = str(uuid.uuid4())
        
        logger.info(f"Creating session {session_id}")
        logger.info(f"Intention: {intention}")
        
        # Radionics Enhancement: Attune rate and apply trend padding
        radionics = self.services['radionics_enhancer']
        attuned_rate = radionics.attune_rate(intention)
        logger.info(f"Radionics Rate Attuned: {attuned_rate}")
        
        # Apply trend padding to intention (conceptual enhancement)
        # In a full implementation, this padded signal would be what is broadcasted
        padded_intention_signals = radionics.apply_trend_padding(intention, padding_type='fibonacci')
        logger.info(f"Trend Padding Applied: {len(padded_intention_signals)} layers")

        # Publish Radionics Event
        self.event_bus.publish(RadionicsRateAttuned(
            intention=intention,
            rate=attuned_rate,
            padding_layers=len(padded_intention_signals)
        ))

        # Process targets
        for target_data in targets:
            target_spec = TargetSpecification(
                target_type=TargetType(target_data.get('type', 'individual')),
                identifier=target_data.get('identifier', ''),
                metadata=target_data.get('metadata', {})
            )
            
            # Route blessing
            self.services['blessing_router'].route_blessing(
                intention=intention,
                target_spec=target_spec,
                delivery_method=DeliveryMethod.DIRECT # Default for now
            )
            
        # Activate modalities
        if 'crystal' in modalities:
            logger.info("Activating Crystal Service")
            # In a real scenario, this would be async or threaded
            self.services['crystal'].broadcast_intention(
                intention=intention,
                duration=duration,
                hardware_level=2 # Default to passive
            )
            
        self.active_sessions[session_id] = {
            'start_time': datetime.now(),
            'intention': intention,
            'status': 'active'
        }
        
        return session_id

    def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down orchestrator...")
        # Cleanup resources
        
if __name__ == "__main__":
    orchestrator = UnifiedOrchestrator()
    
    # Example usage
    try:
        orchestrator.create_session(
            intention="Universal Peace",
            targets=[
                {'type': 'individual', 'identifier': 'All Beings'}
            ],
            modalities=['crystal'],
            duration=10 # Short duration for test
        )
    except KeyboardInterrupt:
        orchestrator.shutdown()