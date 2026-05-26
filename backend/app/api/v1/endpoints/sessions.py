"""
Sessions API endpoints for Vajra.Stream
"""

import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


class AudioConfig(BaseModel):
    frequency: float = 136.1
    duration: float = 30.0
    volume: float = 0.8
    prayer_bowl_mode: bool = True
    harmonic_strength: float = 0.3
    modulation_depth: float = 0.05
    envelope_type: str = "prayer_bowl"


class SessionConfig(BaseModel):
    name: str
    intention: str
    duration: int = 3600
    audio_frequency: float = 136.1
    astrology_enabled: bool = True
    hardware_enabled: bool = True
    visuals_enabled: bool = True

    _audio_config: AudioConfig = None

    def __init__(self, **data):
        super().__init__(**data)
        self._audio_config = AudioConfig(
            frequency=self.audio_frequency,
            duration=30.0,
            volume=0.8,
            prayer_bowl_mode=True,
            harmonic_strength=0.3,
            modulation_depth=0.05,
            envelope_type="prayer_bowl",
        )

    @property
    def audio_config(self) -> AudioConfig:
        return self._audio_config


@router.post("/create")
async def create_session(config: SessionConfig, background_tasks: BackgroundTasks):
    """Create a new blessing session"""
    try:
        logger.info(f"🆕 Session creation request: {config.name}")

        from backend.core.services.vajra_service import vajra_service

        session_id = await vajra_service.create_session(
            name=config.name,
            intention=config.intention,
            audio_frequency=config.audio_frequency,
            duration=config.duration,
            astrology_enabled=config.astrology_enabled,
            hardware_enabled=config.hardware_enabled,
            visuals_enabled=config.visuals_enabled,
        )
        logger.info(f"✅ Session created: {session_id}")

        return {
            "status": "success",
            "session_id": session_id,
            "message": "Session created successfully",
            "config": {
                "name": config.name,
                "intention": config.intention,
                "duration": config.duration,
                "audio_frequency": config.audio_frequency,
                "astrology_enabled": config.astrology_enabled,
                "hardware_enabled": config.hardware_enabled,
                "visuals_enabled": config.visuals_enabled,
            },
        }

    except Exception as e:
        logger.error(f"❌ Session creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/start")
async def start_session(session_id: str, background_tasks: BackgroundTasks):
    """Start a blessing session"""
    try:
        logger.info(f"🚀 Session start request: {session_id}")

        from backend.core.services.vajra_service import vajra_service

        success = await vajra_service.start_session(session_id)

        if success:
            logger.info(f"✅ Session started: {session_id}")
            return {"status": "success", "message": "Session started successfully", "session_id": session_id}
        else:
            logger.error(f"❌ Failed to start session: {session_id}")
            raise HTTPException(status_code=404, detail="Session not found or failed to start")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Session start error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/stop")
async def stop_session(session_id: str, background_tasks: BackgroundTasks):
    """Stop a blessing session"""
    try:
        logger.info(f"🛑 Session stop request: {session_id}")

        from backend.core.services.vajra_service import vajra_service

        success = await vajra_service.stop_session(session_id)

        if success:
            logger.info(f"✅ Session stopped: {session_id}")
            return {"status": "success", "message": "Session stopped successfully", "session_id": session_id}
        else:
            logger.error(f"❌ Failed to stop session: {session_id}")
            raise HTTPException(status_code=404, detail="Session not found or failed to stop")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Session stop error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/status")
async def get_session_status(session_id: str):
    """Get status of a specific session"""
    try:
        from backend.core.services.vajra_service import vajra_service

        session = vajra_service.get_session_status(session_id)

        if session:
            # Calculate session duration if running
            duration_info = {}
            if session.get("status") == "running" and session.get("start_time"):
                current_time = asyncio.get_event_loop().time()
                elapsed = current_time - session["start_time"]
                remaining = session["config"].duration - elapsed

                duration_info = {
                    "elapsed_seconds": elapsed,
                    "remaining_seconds": remaining,
                    "progress_percentage": (elapsed / session["config"].duration) * 100,
                }

            return {
                "status": "success",
                "session": {
                    "id": session["id"],
                    "name": session["config"].name,
                    "intention": session["config"].intention,
                    "status": session["status"],
                    "start_time": session["start_time"],
                    "end_time": session["end_time"],
                    "audio_frequency": session["config"].audio_config.frequency,
                    "duration": session["config"].duration,
                    "astrology_enabled": session["config"].astrology_enabled,
                    "hardware_enabled": session["config"].hardware_enabled,
                    "visuals_enabled": session["config"].visuals_enabled,
                    **duration_info,
                },
            }
        else:
            raise HTTPException(status_code=404, detail="Session not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Session status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def get_all_sessions():
    """Get all active sessions"""
    try:
        from backend.core.services.vajra_service import vajra_service

        sessions = vajra_service.get_all_sessions()

        # Format sessions for response
        formatted_sessions = {}
        for session_id, session in sessions.items():
            formatted_sessions[session_id] = {
                "id": session["id"],
                "name": session["config"].name,
                "intention": session["config"].intention,
                "status": session["status"],
                "start_time": session["start_time"],
                "audio_frequency": session["config"].audio_config.frequency,
                "duration": session["config"].duration,
                "astrology_enabled": session["config"].astrology_enabled,
                "hardware_enabled": session["config"].hardware_enabled,
                "visuals_enabled": session["config"].visuals_enabled,
            }

        return {"status": "success", "sessions": formatted_sessions, "count": len(formatted_sessions)}
    except Exception as e:
        logger.error(f"❌ Sessions retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_session_history():
    """Get session history"""
    try:
        from backend.core.services.vajra_service import vajra_service

        history = vajra_service.get_session_history()

        # Format history for response
        formatted_history = []
        for session in history:
            formatted_history.append(
                {
                    "id": session["id"],
                    "name": session["config"].name,
                    "intention": session["config"].intention,
                    "status": session["status"],
                    "start_time": session["start_time"],
                    "end_time": session["end_time"],
                    "audio_frequency": session["config"].audio_config.frequency,
                    "duration": session["config"].duration,
                    "total_runtime": session["end_time"] - session["start_time"]
                    if session["end_time"] and session["start_time"]
                    else 0,
                }
            )

        return {"status": "success", "history": formatted_history, "count": len(formatted_history)}
    except Exception as e:
        logger.error(f"❌ Session history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_session_statistics():
    """Get session statistics"""
    try:
        from backend.core.services.vajra_service import vajra_service

        active_sessions = vajra_service.get_all_sessions()
        history = vajra_service.get_session_history()

        # Calculate statistics
        total_sessions = len(active_sessions) + len(history)
        running_sessions = len([s for s in active_sessions.values() if s["status"] == "running"])

        # Calculate total duration
        total_duration = sum(s["config"].duration for s in active_sessions.values())
        total_duration += sum(s.get("total_runtime", 0) for s in history)

        # Calculate average frequency
        all_frequencies = [s["config"].audio_config.frequency for s in active_sessions.values()] + [
            s.get("audio_frequency", 136.1) for s in history
        ]
        avg_frequency = sum(all_frequencies) / len(all_frequencies) if all_frequencies else 136.1

        return {
            "status": "success",
            "statistics": {
                "total_sessions": total_sessions,
                "active_sessions": len(active_sessions),
                "running_sessions": running_sessions,
                "completed_sessions": len(history),
                "total_duration_hours": total_duration / 3600,
                "average_frequency": avg_frequency,
                "most_common_frequency": max(set(all_frequencies), key=all_frequencies.count)
                if all_frequencies
                else 136.1,
            },
        }
    except Exception as e:
        logger.error(f"❌ Session statistics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """Delete a session (only if not running)"""
    try:
        from backend.core.services.vajra_service import vajra_service

        session = vajra_service.get_session_status(session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        if session["status"] == "running":
            raise HTTPException(status_code=400, detail="Cannot delete running session. Please stop it first.")

        if vajra_service.delete_session(session_id):
            logger.info(f"🗑️ Session deleted: {session_id}")
            return {"status": "success", "message": "Session deleted successfully", "session_id": session_id}
        else:
            raise HTTPException(status_code=404, detail="Failed to delete session")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Session deletion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
