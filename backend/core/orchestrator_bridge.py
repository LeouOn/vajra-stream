"""
Orchestrator Bridge
Singleton bridge to expose the UnifiedOrchestrator to the FastAPI application.
"""

import logging
import threading

from backend.websocket.connection_manager import stable_connection_manager_v2
from scripts.unified_orchestrator import UnifiedOrchestrator

logger = logging.getLogger(__name__)


class OrchestratorBridge:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.orchestrator = None
            cls._instance.initialized = False
            cls._instance._crystal_thread: threading.Thread | None = None
            cls._instance._shutdown_event = threading.Event()
        return cls._instance

    def initialize(self):
        """Initialize the Unified Orchestrator"""
        if not self.initialized:
            logger.info("Initializing Orchestrator Bridge...")
            try:
                # Inject the container's shared event bus so that production
                # events (published via container.event_bus) reach the
                # orchestrator's subscribers (e.g. AutonomousAgent, event
                # forwarding). Without this, UnifiedOrchestrator would spin
                # up its own private bus that nothing else publishes to.
                from container import container

                self.orchestrator = UnifiedOrchestrator(event_bus=container.event_bus)
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
            from modules.interfaces import DomainEvent, SessionStarted

            self.orchestrator.event_bus.subscribe(DomainEvent, self._forward_event_to_websocket)
            self.orchestrator.event_bus.subscribe(SessionStarted, self._on_session_started)

    def _on_session_started(self, event):
        """Handle session started event - trigger crystal broadcast as background task"""
        try:
            crystal = self.orchestrator.services.get("crystal")
            if crystal and event.session_id:

                def run_broadcast():
                    try:
                        crystal.broadcast_intention(
                            intention=event.name,
                            duration=3600,
                            hardware_level=2,
                            stop_event=self._shutdown_event,
                        )
                    except TypeError:
                        # Crystal signature predates stop_event support.
                        # Fall back to the uninterruptible call; the thread
                        # is still tracked and joined (best-effort) on
                        # shutdown because it is a daemon.
                        try:
                            crystal.broadcast_intention(
                                intention=event.name,
                                duration=3600,
                                hardware_level=2,
                            )
                        except Exception as e:
                            logger.error(f"Crystal broadcast error: {e}")
                    except Exception as e:
                        logger.error(f"Crystal broadcast error: {e}")

                # Reset the shutdown event in case the bridge is reused
                # across multiple sessions within a single process.
                self._shutdown_event.clear()
                self._crystal_thread = threading.Thread(
                    target=run_broadcast, daemon=True
                )
                self._crystal_thread.start()
        except Exception as e:
            logger.error(f"Error handling SessionStarted: {e}")

    def shutdown(self):
        """Signal the crystal broadcast thread to stop and join it.

        Sets the internal shutdown event so any cooperative broadcast
        loop can exit, then joins the tracked daemon thread with a
        bounded timeout. Idempotent — safe to call multiple times.
        """
        self._shutdown_event.set()
        thread = self._crystal_thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=5.0)
            if thread.is_alive():
                logger.warning(
                    "OrchestratorBridge crystal thread did not exit "
                    "within 5s on shutdown (daemon will not block process exit)"
                )

    async def _forward_event_to_websocket(self, event):
        """Forward domain events to WebSocket clients"""
        try:
            # Convert event to dict for JSON serialization
            event_data = {
                "type": event.__class__.__name__,
                "timestamp": event.timestamp.isoformat(),
                "data": {k: v for k, v in event.__dict__.items() if not k.startswith("_")},
            }

            # We can directly await now because EventBus handles coroutines!
            await stable_connection_manager_v2.broadcast(event_data)

        except Exception as e:
            logger.error(f"Error forwarding event to WebSocket: {e}")

    def get_orchestrator(self) -> UnifiedOrchestrator | None:
        """Get the underlying orchestrator instance"""
        return self.orchestrator

    async def create_session(self, intention: str, targets: list, modalities: list, duration: int) -> str:
        """Wrapper for creating a session"""
        if not self.orchestrator:
            raise RuntimeError("Orchestrator not initialized")

        # Run the synchronous create_session method
        return self.orchestrator.create_session(
            intention=intention, targets=targets, modalities=modalities, duration=duration
        )


# Global instance
orchestrator_bridge = OrchestratorBridge()
