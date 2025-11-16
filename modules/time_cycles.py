"""
Time Cycles Module
Wraps time_cycle_broadcaster functionality
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.interfaces import EventBus


class TimeCyclesService:
    """Time cycle healing broadcaster service"""

    def __init__(self, event_bus: EventBus = None):
        self.event_bus = event_bus
        self._broadcaster = None

    @property
    def broadcaster(self):
        """Get time cycle broadcaster"""
        if self._broadcaster is None:
            try:
                from core.time_cycle_broadcaster import TimeCycleBroadcaster
                self._broadcaster = TimeCycleBroadcaster()
            except ImportError:
                self._broadcaster = None
        return self._broadcaster

    def broadcast_to_time_cycle(
        self,
        target_date: datetime,
        intention: str = "healing",
        duration_minutes: int = 30
    ) -> Dict[str, Any]:
        """Broadcast healing to a specific time cycle"""
        if self.broadcaster is None:
            return {'error': 'Time cycle broadcaster not available'}

        try:
            session = self.broadcaster.broadcast(
                target_date=target_date,
                intention=intention,
                duration_minutes=duration_minutes
            )
            return {
                'status': 'success',
                'target_date': target_date.isoformat(),
                'intention': intention,
                'duration_minutes': duration_minutes,
                'session_id': session.get('session_id', 'unknown')
            }
        except Exception as e:
            return {'error': str(e)}

    def heal_past_event(
        self,
        event_date: datetime,
        event_name: str,
        intention: str = "healing and liberation"
    ) -> Dict[str, Any]:
        """Send healing to a past event"""
        return self.broadcast_to_time_cycle(
            target_date=event_date,
            intention=f"Healing for {event_name}: {intention}",
            duration_minutes=108  # Sacred number
        )

    def heal_future_event(
        self,
        event_date: datetime,
        event_name: str,
        intention: str = "protection and blessing"
    ) -> Dict[str, Any]:
        """Send blessing/protection to a future event"""
        return self.broadcast_to_time_cycle(
            target_date=event_date,
            intention=f"Blessing for {event_name}: {intention}",
            duration_minutes=30
        )

    def continuous_healing_cycle(
        self,
        start_date: datetime,
        end_date: datetime,
        intention: str = "ongoing healing"
    ) -> Dict[str, Any]:
        """Establish continuous healing across a time period"""
        if self.broadcaster is None:
            return {'error': 'Time cycle broadcaster not available'}

        try:
            cycle = self.broadcaster.continuous_cycle(
                start_date=start_date,
                end_date=end_date,
                intention=intention
            )
            return {
                'status': 'success',
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'intention': intention,
                'cycle_id': cycle.get('cycle_id', 'unknown')
            }
        except Exception as e:
            return {'error': str(e)}

    def get_current_cycle_info(self) -> Dict[str, Any]:
        """Get information about current time cycles"""
        if self.broadcaster is None:
            return {'error': 'Time cycle broadcaster not available'}

        try:
            info = self.broadcaster.get_current_cycle_info()
            return {
                'status': 'success',
                'current_time': datetime.now().isoformat(),
                'cycle_info': info
            }
        except Exception as e:
            return {'error': str(e)}

    def get_status(self) -> Dict[str, Any]:
        """Get status of time cycle broadcaster"""
        return {
            'broadcaster': self.broadcaster is not None,
            'current_time': datetime.now().isoformat()
        }
