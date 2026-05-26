"""
Wave Manager
Lifecycle manager for scalar wave generation sessions.

Delegates to ScalarWaveService from the container, adding:
- Session lifecycle (create, start, stop, list)
- Method selection and benchmarking
- Thermal monitoring integration
- Event bus publishing for wave session events
"""

import uuid
from datetime import datetime
from typing import Any

from modules.interfaces import EventBus


class WaveSession:
    """Track a scalar wave generation session."""

    def __init__(self, method: str, count: int, intensity: float = 1.0):
        self.session_id = str(uuid.uuid4())
        self.method = method
        self.count = count
        self.intensity = intensity
        self.status = "created"
        self.created_at = datetime.now()
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None
        self.result: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "method": self.method,
            "count": self.count,
            "intensity": self.intensity,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "mops": self.result.get("mops") if self.result else None,
        }


class WaveManager:
    """
    Manages scalar wave generation sessions.

    Provides a clean lifecycle API over the ScalarWaveService.
    """

    def __init__(self, event_bus: EventBus | None = None):
        self.event_bus = event_bus
        self._scalar_service = None
        self._active_sessions: dict[str, WaveSession] = {}
        self._history: list[WaveSession] = []

    @property
    def scalar_service(self):
        if self._scalar_service is None:
            from modules.scalar_waves import ScalarWaveService

            self._scalar_service = ScalarWaveService(event_bus=self.event_bus)
        return self._scalar_service

    def create_session(self, method: str = "hybrid", count: int = 10000, intensity: float = 1.0) -> str:
        """Create a new wave generation session."""
        session = WaveSession(method=method, count=count, intensity=intensity)
        self._active_sessions[session.session_id] = session
        return session.session_id

    def start_session(self, session_id: str) -> dict[str, Any]:
        """Start generating waves for a session."""
        session = self._active_sessions.get(session_id)
        if not session:
            return {"error": f"Session {session_id} not found"}

        session.status = "running"
        session.started_at = datetime.now()

        try:
            result = self.scalar_service.generate(
                method=session.method,
                count=session.count,
                intensity=session.intensity,
            )
            session.result = result
            session.status = "completed"
            session.completed_at = datetime.now()
        except Exception as e:
            session.status = "error"
            session.result = {"error": str(e)}

        return {
            "session_id": session_id,
            "status": session.status,
            "result": session.result,
        }

    def stop_session(self, session_id: str) -> dict[str, Any]:
        """Stop and archive a wave session."""
        session = self._active_sessions.pop(session_id, None)
        if not session:
            return {"error": f"Session {session_id} not found"}

        session.status = "stopped"
        session.completed_at = datetime.now()
        self._history.append(session)
        return session.to_dict()

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get session status."""
        session = self._active_sessions.get(session_id)
        return session.to_dict() if session else None

    def list_active(self) -> list[dict[str, Any]]:
        """List all active wave sessions."""
        return [s.to_dict() for s in self._active_sessions.values()]

    def list_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """List historical wave sessions."""
        return [s.to_dict() for s in self._history[-limit:]]

    def benchmark(self, duration: float = 3.0) -> dict[str, Any]:
        """Benchmark all generation methods."""
        return self.scalar_service.benchmark(duration=duration)

    def get_thermal_status(self) -> dict[str, Any]:
        """Get thermal monitoring status."""
        return self.scalar_service.get_thermal_status()

    def get_status(self) -> dict[str, Any]:
        """Get overall wave manager status."""
        return {
            "active_sessions": len(self._active_sessions),
            "history_count": len(self._history),
            "thermal": self.get_thermal_status(),
        }
