"""
Orchestrator Bridge
Singleton bridge to expose the UnifiedOrchestrator to the FastAPI application.
"""

import asyncio
import logging
import os
import threading

from backend.websocket.connection_manager import stable_connection_manager_v2

# The JSON-safety helper is imported from its LEAF module, not from the
# connection manager: the manager is stubbed in sys.modules by some tests
# (so the bridge can be loaded in isolation) and that stub does not
# carry the helper.
from backend.websocket.json_safe import to_json_safe
from scripts.unified_orchestrator import UnifiedOrchestrator

logger = logging.getLogger(__name__)

# The crystal broadcast on session start is opt-in, default OFF: starting a
# session must not play an hour of sound on its own. Read at call time so it
# can be flipped without a restart.
#
# SCOPE: this flag governs ONLY the bridge's session-start callback below. It
# does NOT govern scripts/unified_orchestrator.py, which calls the crystal
# broadcaster directly when the caller asks for the crystal modality - that
# path is an explicit request and is left as it is.
_BRIDGE_CRYSTAL_ON_SESSION_START_ENV = "VAJRA_BRIDGE_CRYSTAL_ON_SESSION_START"


# The one shared JSON-safety helper lives in the connection manager, which is
# where the payloads are actually sent. The old private name is kept as an
# alias so existing importers (and the offline review probe) keep working.
_json_safe = to_json_safe


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
        """Handle session started event - trigger crystal broadcast as background task.

        The crystal broadcast is OPT-IN and OFF by default: it plays real
        sound through the speakers for up to an hour, so it must never happen
        just because a session started. Set
        VAJRA_BRIDGE_CRYSTAL_ON_SESSION_START=1 to enable it. The flag is read
        here, at call time, so it can be changed without a restart.
        """
        if os.environ.get(_BRIDGE_CRYSTAL_ON_SESSION_START_ENV) != "1":
            logger.info(
                "Crystal broadcast on session start is disabled; set %s=1 to enable it",
                _BRIDGE_CRYSTAL_ON_SESSION_START_ENV,
            )
            return
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
                self._crystal_thread = threading.Thread(target=run_broadcast, daemon=True)
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
            # Convert event to dict for JSON serialization. The values must be
            # JSON-safe: the event carries a raw datetime, and Starlette's
            # send_json serialises inside the per-client call, so an
            # unserialisable value used to raise in every client and the
            # connection manager disconnected EVERYONE.
            event_data = {
                "type": event.__class__.__name__,
                "timestamp": event.timestamp.isoformat(),
                "data": {k: to_json_safe(v) for k, v in event.__dict__.items() if not k.startswith("_")},
            }

            # The websockets belong to the SERVER's event loop. This handler
            # also runs on whatever loop published the event, and a publisher
            # on a WORKER thread (the tool registry offloads sync tools to
            # threads) runs on that thread's own private loop - sending from
            # there either fails with "attached to a different loop" or writes
            # to the transport unsafely, and the failure looked like a dead
            # client, so a healthy client was evicted.
            manager = stable_connection_manager_v2
            server_loop = manager.main_loop
            try:
                running_loop = asyncio.get_running_loop()
            except RuntimeError:
                running_loop = None
            if server_loop is not None and running_loop is not server_loop:
                # Another loop's thread: hand the message to the server loop
                # through the existing seam. If there is no loop to hand it to
                # (tests, CLI) the send is awaited here instead.
                if not manager.schedule_broadcast(event_data):
                    await manager.broadcast(event_data)
            else:
                # Already on the server's loop: send here, exactly as before.
                await manager.broadcast(event_data)

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
