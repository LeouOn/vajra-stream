"""
Orchestrator Bridge
Singleton bridge to expose the UnifiedOrchestrator to the FastAPI application.
"""

import logging
import asyncio
from typing import Optional, Dict, Any
from scripts.unified_orchestrator import UnifiedOrchestrator
from backend.websocket.connection_manager_stable_v2 import stable_connection_manager_v2

logger = logging.getLogger(__name__)

class OrchestratorBridge:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OrchestratorBridge, cls).__new__(cls)
            cls._instance.orchestrator = None
            cls._instance.initialized = False
        return cls._instance
    
    def initialize(self):
        """Initialize the Unified Orchestrator"""
        if not self.initialized:
            logger.info("Initializing Orchestrator Bridge...")
            try:
                self.orchestrator = UnifiedOrchestrator()
                self._register_event_forwarding()
                self.initialized = True
                logger.info("Orchestrator Bridge initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Orchestrator Bridge: {e}")
                raise
    
    def _register_event_forwarding(self):
        """Register handlers to forward events to WebSocket"""
        if self.orchestrator and self.orchestrator.event_bus:
            # Subscribe to all events for forwarding
            # Note: In a production system, we might want to filter this
            from modules.interfaces import DomainEvent
            self.orchestrator.event_bus.subscribe(DomainEvent, self._forward_event_to_websocket)
            
    def _forward_event_to_websocket(self, event):
        """Forward domain events to WebSocket clients"""
        try:
            # Convert event to dict for JSON serialization
            event_data = {
                "type": "domain_event",
                "event_type": event.__class__.__name__,
                "timestamp": event.timestamp.isoformat(),
                "data": event.__dict__
            }
            
            # Use asyncio.create_task to run async broadcast from sync callback
            try:
                loop = asyncio.get_running_loop()
                # logger.info(f"Forwarding event to websocket: {event.__class__.__name__}")
                loop.create_task(stable_connection_manager_v2.broadcast(event_data))
            except RuntimeError:
                # If no running loop (e.g. during startup/shutdown), skip
                logger.warning("No running loop to forward event")
                pass
                
        except Exception as e:
            logger.error(f"Error forwarding event to WebSocket: {e}")

    def get_orchestrator(self) -> Optional[UnifiedOrchestrator]:
        """Get the underlying orchestrator instance"""
        return self.orchestrator

    async def create_session(self, intention: str, targets: list, modalities: list, duration: int) -> str:
        """Wrapper for creating a session"""
        if not self.orchestrator:
            raise RuntimeError("Orchestrator not initialized")
            
        # Run the synchronous create_session method
        return self.orchestrator.create_session(
            intention=intention,
            targets=targets,
            modalities=modalities,
            duration=duration
        )

# Global instance
orchestrator_bridge = OrchestratorBridge()