"""
WebSocket Connection Manager for Vajra.Stream
Handles real-time data streaming to frontend
"""

from fastapi import WebSocket
from typing import List
import json
import time
import asyncio
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.streaming_active = False
        logger.info("WebSocket Connection Manager initialized")
    
    async def connect(self, websocket: WebSocket):
        """Accept and store new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
        
        # Send initial connection status
        await self.send_personal_message({
            "type": "connection_status",
            "status": "connected",
            "message": "Successfully connected to Vajra.Stream"
        }, websocket)

    async def handle_message(self, websocket: WebSocket, message: str):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "START_SESSION":
                await self._handle_start_session(data)
            elif msg_type == "UPDATE_SETTINGS":
                await self._handle_update_settings(data)
            elif msg_type == "ping":
                await self.send_personal_message({"type": "pong"}, websocket)
            else:
                logger.warning(f"Unknown message type: {msg_type}")
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def _handle_start_session(self, data: dict):
        """Handle session start request"""
        try:
            from backend.core.orchestrator_bridge import orchestrator_bridge
            
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
                "intention": intention
            })
            
        except Exception as e:
            logger.error(f"Error starting session: {e}")
            await self.broadcast({
                "type": "ERROR",
                "message": f"Failed to start session: {str(e)}"
            })

    async def _handle_update_settings(self, data: dict):
        """Handle settings update"""
        # TODO: Implement settings update logic
        logger.info(f"Settings update requested: {data}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific WebSocket client"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return
        
        disconnected_clients = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected_clients.append(connection)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            self.disconnect(client)
    
    async def send_audio_spectrum(self, spectrum: List[float]):
        """Send audio spectrum data to all clients"""
        await self.broadcast({
            "type": "audio_spectrum",
            "data": spectrum,
            "timestamp": time.time()
        })
    
    async def send_session_update(self, session_data: dict):
        """Send session status update to all clients"""
        await self.broadcast({
            "type": "session_update",
            "data": session_data,
            "timestamp": time.time()
        })
    
    async def send_system_status(self, status: dict):
        """Send system status to all clients"""
        await self.broadcast({
            "type": "system_status",
            "data": status,
            "timestamp": time.time()
        })
    
    async def start_realtime_streaming(self):
        """Start streaming real-time data to all clients"""
        if self.streaming_active:
            logger.warning("Real-time streaming already active")
            return
        
        self.streaming_active = True
        logger.info("Starting real-time data streaming...")
        
        try:
            while self.streaming_active:
                try:
                    # Import here to avoid circular imports
                    from backend.core.services.vajra_service import vajra_service

                    # Get current data
                    spectrum = vajra_service.get_audio_spectrum()
                    sessions = vajra_service.get_all_sessions()
                    system_status = vajra_service.get_system_status()
                    
                    # Send real-time data
                    await self.broadcast({
                        "type": "realtime_data",
                        "timestamp": time.time(),
                        "audio_spectrum": spectrum,
                        "active_sessions": sessions,
                        "system_status": system_status
                    })
                    
                    # 10Hz update rate (100ms)
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Error in streaming loop: {e}")
                    await asyncio.sleep(1)  # Wait before retrying
                    
        except asyncio.CancelledError:
            logger.info("Real-time streaming cancelled")
        except Exception as e:
            logger.error(f"Fatal error in streaming: {e}")
        finally:
            self.streaming_active = False
            logger.info("Real-time streaming stopped")
    
    def stop_realtime_streaming(self):
        """Stop real-time streaming"""
        self.streaming_active = False
        logger.info("Stopping real-time data streaming...")
    
    async def send_heartbeat(self):
        """Send heartbeat to all clients"""
        await self.broadcast({
            "type": "heartbeat",
            "timestamp": time.time()
        })
    
    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)
    
    def is_streaming(self) -> bool:
        """Check if streaming is active"""
        return self.streaming_active

# Global connection manager
connection_manager = ConnectionManager()