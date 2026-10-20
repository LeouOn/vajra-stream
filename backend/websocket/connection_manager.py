"""
Stable WebSocket Connection Manager for Vajra.Stream v2
Handles real-time data streaming to frontend with robust error handling

Consolidated per deferred Task 4: the former
``connection_manager_stable_v2`` module and this bare
``connection_manager`` module have been unified into this single canonical
file. The class (``StableConnectionManagerV2``) and the module-level
singleton instance (``stable_connection_manager_v2``) keep their names so
existing call sites are unaffected — only the import path changed from
``backend.websocket.connection_manager_stable_v2`` to
``backend.websocket.connection_manager``.
"""

import asyncio
import json
import logging
import time
import traceback
from typing import Any

from fastapi import WebSocket

from backend.websocket.json_safe import to_json_safe
from backend.websocket.message_provenance import annotate

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# One "unserialisable message" error line per message type per 60 s.
_UNSERIALISABLE_LOG_INTERVAL_SECONDS = 60.0


def _now() -> float:
    """Clock seam, so the log throttle can be tested with a fake clock."""
    return time.time()


class StableConnectionManagerV2:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}  # Use dict with connection IDs
        self.connection_metadata: dict[str, dict] = {}  # Store metadata for each connection
        self.streaming_active = False
        self.heartbeat_interval = 30  # Send heartbeat every 30 seconds
        self.connection_timeout = 60  # Consider connection dead after 60 seconds
        self._connection_id_counter = 0
        self.main_loop: asyncio.AbstractEventLoop | None = None
        # Strong refs to broadcast tasks created by schedule_broadcast (the loop keeps only weak ones).
        self._pending_sends: set[asyncio.Task] = set()
        # Throttle for the "unserialisable message" log: one line per message
        # type per 60 s, with a count of the ones suppressed in between, so a
        # persistent producer bug cannot write ten lines a second.
        self._unserialisable_log: dict[str, tuple[float, int]] = {}
        logger.info("Stable WebSocket Connection Manager V2 initialized")

    def set_main_loop(self, loop: asyncio.AbstractEventLoop | None) -> None:
        """Record the server's main event loop.

        Lets worker-thread publishers (e.g. radionics broadcasts) schedule
        WebSocket sends via run_coroutine_threadsafe even though they run
        off the event loop.
        """
        self.main_loop = loop

    def schedule_broadcast(self, message: dict) -> bool:
        """Schedule :meth:`broadcast` from any thread, without waiting for it.

        On the main loop's own thread this creates a task; from a worker thread
        (e.g. a tool run via ``asyncio.to_thread``) it hands the send to the
        recorded main loop with ``run_coroutine_threadsafe``. Returns False when
        there is no running loop to send on (tests, CLI scripts).
        """
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        loop = self.main_loop
        if running is not None and (loop is None or running is loop):
            task = running.create_task(self.broadcast(message))
            self._pending_sends.add(task)
            task.add_done_callback(self._pending_sends.discard)
            return True
        if loop is None or loop.is_closed() or not loop.is_running():
            return False
        asyncio.run_coroutine_threadsafe(self.broadcast(message), loop)
        return True

    def _generate_connection_id(self) -> str:
        """Generate unique connection ID"""
        self._connection_id_counter += 1
        return f"conn_{int(time.time())}_{self._connection_id_counter}"

    async def connect(self, websocket: WebSocket) -> str:
        """Accept and store new WebSocket connection"""
        await websocket.accept()
        connection_id = self._generate_connection_id()

        self.active_connections[connection_id] = websocket
        self.connection_metadata[connection_id] = {
            "connected_at": time.time(),
            "last_heartbeat": time.time(),
            "message_count": 0,
        }

        logger.info(f"WebSocket {connection_id} connected. Total connections: {len(self.active_connections)}")

        # Send initial connection status
        await self.send_personal_message(
            {
                "type": "connection_status",
                "status": "connected",
                "connection_id": connection_id,
                "message": "Successfully connected to Vajra.Stream",
                "timestamp": time.time(),
            },
            connection_id,
        )

        return connection_id

    async def handle_message(self, connection_id: str, message: str):
        """Handle incoming WebSocket messages"""
        if connection_id not in self.active_connections:
            logger.warning(f"Received message from unknown connection: {connection_id}")
            return

        try:
            data = json.loads(message)
            msg_type = data.get("type")

            # Update last activity
            if connection_id in self.connection_metadata:
                self.connection_metadata[connection_id]["last_heartbeat"] = time.time()
                self.connection_metadata[connection_id]["message_count"] += 1

            if msg_type == "START_SESSION":
                await self._handle_start_session(connection_id, data)
            elif msg_type == "UPDATE_SETTINGS":
                await self._handle_update_settings(connection_id, data)
            elif msg_type == "ping":
                await self.send_personal_message({"type": "pong", "timestamp": time.time()}, connection_id)
            else:
                logger.warning(f"Unknown message type from {connection_id}: {msg_type}")

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received from {connection_id}")
            await self.send_personal_message({"type": "error", "message": "Invalid JSON format"}, connection_id)
        except Exception as e:
            logger.error(f"Error handling message from {connection_id}: {e}")
            logger.error(traceback.format_exc())
            await self.send_personal_message({"type": "error", "message": "Internal server error"}, connection_id)

    async def _handle_start_session(self, connection_id: str, data: dict):
        """Handle session start request with safe imports"""
        try:
            # Safe import with fallback
            try:
                from backend.core.orchestrator_bridge import orchestrator_bridge

                orchestrator_available = True
            except ImportError as e:
                logger.warning(f"Orchestrator bridge not available: {e}")
                orchestrator_available = False

            if not orchestrator_available:
                await self.send_personal_message(
                    {"type": "ERROR", "message": "Session service not available - running in basic mode"}, connection_id
                )
                return

            payload = data.get("payload", {})
            intention = payload.get("intention", "General Blessing")
            targets = payload.get("targets", [])
            modalities = payload.get("modalities", [])
            duration = payload.get("duration", 600)

            session_id = await orchestrator_bridge.create_session(
                intention=intention, targets=targets, modalities=modalities, duration=duration
            )

            await self.broadcast(
                {"type": "SESSION_STARTED", "session_id": session_id, "intention": intention, "timestamp": time.time()}
            )

        except Exception as e:
            logger.error(f"Error starting session: {e}")
            logger.error(traceback.format_exc())
            await self.send_personal_message(
                {"type": "ERROR", "message": f"Failed to start session: {str(e)}"}, connection_id
            )

    async def _handle_update_settings(self, connection_id: str, data: dict):
        """Handle settings update"""
        logger.info(f"Settings update requested from {connection_id}: {data}")
        await self.send_personal_message({"type": "settings_updated", "message": "Settings received"}, connection_id)

    def disconnect(self, connection_id: str):
        """Remove WebSocket connection"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        if connection_id in self.connection_metadata:
            del self.connection_metadata[connection_id]
        logger.info(f"WebSocket {connection_id} disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: dict, connection_id: str):
        """Send message to specific WebSocket client"""
        if connection_id not in self.active_connections:
            logger.warning(f"Attempted to send message to unknown connection: {connection_id}")
            return False

        # An unserialisable payload is the caller's fault: the client is
        # healthy and must NOT be evicted for it. A genuine send failure below
        # still disconnects, as before.
        if not self._is_serialisable(message):
            return False

        try:
            websocket = self.active_connections[connection_id]
            await websocket.send_json(annotate(message))
            return True
        except Exception as e:
            logger.error(f"Error sending personal message to {connection_id}: {e}")
            # Remove dead connection
            self.disconnect(connection_id)
            return False

    def _log_unserialisable(self, message: Any, exc: Exception) -> None:
        """Log an unserialisable message, at most one line per type per 60 s."""
        mtype = message.get("type") if isinstance(message, dict) else type(message).__name__
        now = _now()
        last, suppressed = self._unserialisable_log.get(str(mtype), (0.0, 0))
        if now - last < _UNSERIALISABLE_LOG_INTERVAL_SECONDS:
            self._unserialisable_log[str(mtype)] = (last, suppressed + 1)
            return
        note = f" ({suppressed} similar suppressed)" if suppressed else ""
        logger.error(
            "Refusing to send unserialisable message of type %r: %s%s",
            mtype,
            exc,
            note,
        )
        self._unserialisable_log[str(mtype)] = (now, 0)

    def _is_serialisable(self, message: Any) -> bool:
        """True if the message can be serialised; logs (throttled) if not.

        A message that cannot be serialised is the CALLER's fault, not each
        client's, so it is rejected once, before any client is touched.
        """
        try:
            json.dumps(message, separators=(",", ":"), allow_nan=False)
            return True
        except (TypeError, ValueError) as e:
            self._log_unserialisable(message, e)
            return False

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return

        # Every message leaves with its provenance labels (message_provenance.py).
        message = annotate(message)
        # Validate the message ONCE, before any client is touched. A message
        # that cannot be serialised is the CALLER's fault, not each client's:
        # Starlette's send_json serialises inside the per-client call, so an
        # unserialisable value used to raise in every client and disconnect
        # EVERYONE. One error, no disconnects.
        if not self._is_serialisable(message):
            return
        # Create a snapshot of connections to avoid dictionary changed size during iteration
        connections_snapshot = dict(self.active_connections)
        disconnected_clients = []

        for connection_id, websocket in connections_snapshot.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client {connection_id}: {e}")
                disconnected_clients.append(connection_id)

        # Remove disconnected clients
        for connection_id in disconnected_clients:
            self.disconnect(connection_id)

    async def send_heartbeat_to_all(self):
        """Send heartbeat to all clients and check for timeouts"""
        current_time = time.time()
        timeout_clients = []

        for connection_id, metadata in self.connection_metadata.items():
            # Check for timeout
            if current_time - metadata["last_heartbeat"] > self.connection_timeout:
                logger.warning(f"Connection {connection_id} timed out")
                timeout_clients.append(connection_id)

        # Remove timed out clients
        for connection_id in timeout_clients:
            self.disconnect(connection_id)

        # Send heartbeat to remaining clients
        await self.broadcast(
            {"type": "heartbeat", "timestamp": current_time, "active_connections": len(self.active_connections)}
        )

    async def send_safe_realtime_data(self):
        """Send real-time data with safe imports and error handling"""
        try:
            # Create a simple, safe status object
            system_status = {
                "status": "basic_mode",
                "timestamp": time.time(),
                "services": {"connection_manager": "stable_v2", "streaming": self.streaming_active},
            }

            # Try to get vajra service data safely
            spectrum = []
            sessions = {}

            try:
                from backend.core.services.vajra_service import vajra_service

                try:
                    spectrum = vajra_service.get_audio_spectrum() or []
                    sessions = vajra_service.get_all_sessions() or {}
                    service_status = vajra_service.get_system_status()

                    # Safely update system status with service info
                    if isinstance(service_status, dict):
                        # Only add safe keys from service_status
                        safe_keys = ["status", "mode", "active_sessions"]
                        for key in safe_keys:
                            if key in service_status:
                                system_status[key] = service_status[key]

                    system_status["services"]["vajra_service"] = "available"
                    logger.debug("Vajra service data retrieved successfully")

                except Exception as e:
                    logger.error(f"Error getting data from vajra_service: {e}")
                    system_status["services"]["vajra_service"] = "error"

            except ImportError as e:
                logger.debug(f"Vajra service not available: {e}")
                system_status["services"]["vajra_service"] = "unavailable"

            # Send real-time data. The sessions carry a SessionConfig object,
            # which is not JSON-serialisable: that used to make the strict
            # pre-check reject the WHOLE frame, so with any session alive
            # every realtime frame was dropped. Convert at the boundary.
            await self.broadcast(
                {
                    "type": "realtime_data",
                    "timestamp": time.time(),
                    "audio_spectrum": spectrum,
                    "active_sessions": to_json_safe(sessions),
                    "system_status": to_json_safe(system_status),
                }
            )

            # Check for running sessions and send session_update messages
            for session_id, session in sessions.items():
                if session.get("status") == "running":
                    await self.broadcast(
                        {
                            "type": "session_update",
                            "data": {
                                "id": session_id,
                                "status": "running",
                                "name": getattr(session.get("config", {}), "name", str(session.get("config", {}))),
                            },
                        }
                    )

        except Exception as e:
            logger.error(f"Error in send_safe_realtime_data: {e}")
            logger.error(traceback.format_exc())

            # Send error status to clients
            try:
                await self.broadcast(
                    {
                        "type": "system_error",
                        "timestamp": time.time(),
                        "error": str(e),
                        "message": "Real-time data generation encountered an error",
                    }
                )
            except Exception as broadcast_error:
                logger.error(f"Failed to broadcast error message: {broadcast_error}")

    async def start_realtime_streaming(self):
        """Start streaming real-time data to all clients with robust error handling"""
        if self.streaming_active:
            logger.warning("Real-time streaming already active")
            return

        self.streaming_active = True
        logger.info("Starting stable real-time data streaming v2...")

        # Start heartbeat task
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        try:
            while self.streaming_active:
                try:
                    await self.send_safe_realtime_data()
                    # 10Hz update rate (100ms)
                    await asyncio.sleep(0.1)

                except Exception as e:
                    logger.error(f"Error in streaming loop: {e}")
                    logger.error(traceback.format_exc())
                    # Wait before retrying
                    await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info("Real-time streaming cancelled")
        except Exception as e:
            logger.error(f"Fatal error in streaming: {e}")
            logger.error(traceback.format_exc())
        finally:
            # Cancel heartbeat task
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

            self.streaming_active = False
            logger.info("Real-time streaming stopped")

    async def _heartbeat_loop(self):
        """Background task to send heartbeats and check for timeouts"""
        try:
            while self.streaming_active:
                await asyncio.sleep(self.heartbeat_interval)
                await self.send_heartbeat_to_all()
        except asyncio.CancelledError:
            logger.info("Heartbeat loop cancelled")
        except Exception as e:
            logger.error(f"Error in heartbeat loop: {e}")

    def stop_realtime_streaming(self):
        """Stop real-time streaming"""
        self.streaming_active = False
        logger.info("Stopping real-time data streaming...")

    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)

    def is_streaming(self) -> bool:
        """Check if streaming is active"""
        return self.streaming_active

    def get_connection_stats(self) -> dict[str, Any]:
        """Get connection statistics"""
        return {
            "active_connections": len(self.active_connections),
            "streaming_active": self.streaming_active,
            "connections": {
                conn_id: {
                    "connected_at": metadata["connected_at"],
                    "last_heartbeat": metadata["last_heartbeat"],
                    "message_count": metadata["message_count"],
                    "age_seconds": time.time() - metadata["connected_at"],
                }
                for conn_id, metadata in self.connection_metadata.items()
            },
        }


# Global stable connection manager v2
stable_connection_manager_v2 = StableConnectionManagerV2()
