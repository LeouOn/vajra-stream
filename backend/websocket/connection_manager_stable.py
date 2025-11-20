"""
Stable WebSocket Connection Manager for Vajra.Stream
Handles real-time data streaming to frontend with robust error handling
"""

from fastapi import WebSocket
from typing import List, Dict, Any
import json
import time
import asyncio
import logging
import traceback
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StableConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}  # Use dict with connection IDs
        self.connection_metadata: Dict[str, Dict] = {}  # Store metadata for each connection
        self.streaming_active = False
        self.heartbeat_interval = 30  # Send heartbeat every 30 seconds
        self.connection_timeout = 60  # Consider connection dead after 60 seconds
        self._connection_id_counter = 0
        logger.info("Stable WebSocket Connection Manager initialized")
    
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
            "message_count": 0
        }
        
        logger.info(f"WebSocket {connection_id} connected. Total connections: {len(self.active_connections)}")
        
        # Send initial connection status
        await self.send_personal_message({
            "type": "connection_status",
            "status": "connected",
            "connection_id": connection_id,
            "message": "Successfully connected to Vajra.Stream",
            "timestamp": time.time()
        }, connection_id)
        
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
                await self.send_personal_message({
                    "type": "pong", 
                    "timestamp": time.time()
                }, connection_id)
            else:
                logger.warning(f"Unknown message type from {connection_id}: {msg_type}")
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received from {connection_id}")
            await self.send_personal_message({
                "type": "error",
                "message": "Invalid JSON format"
            }, connection_id)
        except Exception as e:
            logger.error(f"Error handling message from {connection_id}: {e}")
            logger.error(traceback.format_exc())
            await self.send_personal_message({
                "type": "error",
                "message": "Internal server error"
            }, connection_id)

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
                await self.send_personal_message({
                    "type": "ERROR",
                    "message": "Session service not available - running in basic mode"
                }, connection_id)
                return
            
            payload = data.get("payload", {})
            intention = payload.get("intention", "General Blessing")
            targets = payload.get("targets", [])
            modalities = payload.get("modalities", [])
            duration = payload.get("duration", 600)
            
            session_id = await orchestrator_bridge.create_session(
                intention=intention,
                targets=targets,
                modalities=modalities,
                duration=duration
            )
            
            await self.broadcast({
                "type": "SESSION_STARTED",
                "session_id": session_id,
                "intention": intention,
                "timestamp": time.time()
            })
            
        except Exception as e:
            logger.error(f"Error starting session: {e}")
            logger.error(traceback.format_exc())
            await self.send_personal_message({
                "type": "ERROR",
                "message": f"Failed to start session: {str(e)}"
            }, connection_id)

    async def _handle_update_settings(self, connection_id: str, data: dict):
        """Handle settings update"""
        logger.info(f"Settings update requested from {connection_id}: {data}")
        await self.send_personal_message({
            "type": "settings_updated",
            "message": "Settings received"
        }, connection_id)
    
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
            
        try:
            websocket = self.active_connections[connection_id]
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"Error sending personal message to {connection_id}: {e}")
            # Remove dead connection
            self.disconnect(connection_id)
            return False
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
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
        
        # Create snapshot to avoid dictionary changed size during iteration
        metadata_snapshot = dict(self.connection_metadata)
        
        for connection_id, metadata in metadata_snapshot.items():
            # Check for timeout
            time_since_last_heartbeat = current_time - metadata["last_heartbeat"]
            if time_since_last_heartbeat > self.connection_timeout:
                logger.warning(f"Connection {connection_id} timed out after {time_since_last_heartbeat:.1f}s (threshold: {self.connection_timeout}s)")
                timeout_clients.append(connection_id)
            else:
                # Log heartbeat status for debugging
                logger.debug(f"Connection {connection_id}: last heartbeat {time_since_last_heartbeat:.1f}s ago")
        
        # Remove timed out clients
        for connection_id in timeout_clients:
            self.disconnect(connection_id)
        
        # Send heartbeat to remaining clients
        if self.active_connections:
            logger.info(f"Sending heartbeat to {len(self.active_connections)} active connections")
            await self.broadcast({
                "type": "heartbeat",
                "timestamp": current_time,
                "active_connections": len(self.active_connections)
            })
    
    async def send_safe_realtime_data(self):
        """Send real-time data with safe imports and error handling"""
        try:
            # Safe imports with fallbacks
            vajra_service_available = False
            try:
                from backend.core.services.vajra_service import vajra_service
                vajra_service_available = True
            except ImportError as e:
                logger.debug(f"Vajra service not available: {e}")
            
            # Get current data safely
            spectrum = []
            sessions = {}
            system_status = {"status": "basic_mode", "services": {}}
            
            if vajra_service_available:
                try:
                    spectrum = vajra_service.get_audio_spectrum() or []
                    sessions = vajra_service.get_all_sessions() or {}
                    service_status = vajra_service.get_system_status() or {"status": "unknown"}
                    # Merge service status with our system_status
                    if isinstance(service_status, dict):
                        system_status.update(service_status)
                    # Ensure services key exists
                    if "services" not in system_status:
                        system_status["services"] = {}
                    system_status["services"]["vajra_service"] = "available"
                except Exception as e:
                    logger.error(f"Error getting data from vajra_service: {e}")
                    logger.error(traceback.format_exc())
                    # Ensure services key exists
                    if "services" not in system_status:
                        system_status["services"] = {}
                    system_status["services"]["vajra_service"] = "error"
            else:
                # Ensure services key exists
                if "services" not in system_status:
                    system_status["services"] = {}
                system_status["services"]["vajra_service"] = "unavailable"
            
            # Send real-time data
            await self.broadcast({
                "type": "realtime_data",
                "timestamp": time.time(),
                "audio_spectrum": spectrum,
                "active_sessions": sessions,
                "system_status": system_status
            })
            
        except Exception as e:
            logger.error(f"Error in send_safe_realtime_data: {e}")
            logger.error(traceback.format_exc())
    
    async def start_realtime_streaming(self):
        """Start streaming real-time data to all clients with robust error handling"""
        if self.streaming_active:
            logger.warning("Real-time streaming already active")
            return
        
        self.streaming_active = True
        logger.info("Starting stable real-time data streaming...")
        
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
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            "active_connections": len(self.active_connections),
            "streaming_active": self.streaming_active,
            "connections": {
                conn_id: {
                    "connected_at": metadata["connected_at"],
                    "last_heartbeat": metadata["last_heartbeat"],
                    "message_count": metadata["message_count"],
                    "age_seconds": time.time() - metadata["connected_at"]
                }
                for conn_id, metadata in self.connection_metadata.items()
            }
        }

# Global stable connection manager
stable_connection_manager = StableConnectionManager()