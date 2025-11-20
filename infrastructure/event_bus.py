"""
Enhanced In-Process Event Bus
Supports robust event-driven communication with persistence and filtering
"""

from typing import Dict, List, Callable, Any, Optional, Union
from collections import defaultdict
import logging
import json
import os
import uuid
from datetime import datetime
from dataclasses import asdict
from pathlib import Path

logger = logging.getLogger(__name__)


class DomainEvent:
    """Base class for all domain events"""
    def __init__(self, timestamp: Optional[datetime] = None, event_id: Optional[str] = None):
        self.timestamp = timestamp or datetime.now()
        self.event_id = event_id or str(uuid.uuid4())


class EventFilter:
    """Base class for event filters"""
    def __init__(self, filter_func: Callable[[Any], bool]):
        self.filter_func = filter_func
    
    def should_process(self, event: Any) -> bool:
        """Check if event should be processed"""
        try:
            return self.filter_func(event)
        except Exception as e:
            logger.error(f"Error in event filter: {e}")
            return False


class EventMiddleware:
    """Base class for event middleware"""
    def __init__(self, middleware_func: Callable[[Any], Any]):
        self.middleware_func = middleware_func
    
    def process(self, event: Any) -> Optional[Any]:
        """Process event through middleware"""
        try:
            return self.middleware_func(event)
        except Exception as e:
            logger.error(f"Error in event middleware: {e}")
            return event  # Return original event on error


class EnhancedEventBus:
    """Enhanced in-process event bus with persistence and filtering"""

    def __init__(self, persistence_path: Optional[str] = None, max_history: int = 10000):
        self._handlers: Dict[type, List[Callable]] = defaultdict(list)
        self._middleware: List[EventMiddleware] = []
        self._filters: Dict[type, List[EventFilter]] = defaultdict(list)
        
        # Event history for replay and debugging
        self._event_history: List[Dict[str, Any]] = []
        self.max_history = max_history
        
        # Persistence settings
        self.persistence_path = persistence_path
        self._persistence_enabled = persistence_path is not None
        
        # Initialize persistence directory
        if self._persistence_enabled:
            self._ensure_persistence_dir()
        
        logger.info(f"Enhanced Event Bus initialized with persistence: {self._persistence_enabled}")

    def _ensure_persistence_dir(self):
        """Ensure persistence directory exists"""
        if self.persistence_path:
            os.makedirs(os.path.dirname(self.persistence_path), exist_ok=True)

    def subscribe(self, event_type: type, handler: Callable) -> None:
        """Subscribe a handler to an event type"""
        self._handlers[event_type].append(handler)
        logger.info(f"Subscribed {handler.__name__} to {event_type.__name__}")

    def unsubscribe(self, event_type: type, handler: Callable) -> None:
        """Unsubscribe a handler from an event type"""
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
                logger.info(f"Unsubscribed {handler.__name__} from {event_type.__name__}")
            except ValueError:
                logger.warning(f"Handler {handler.__name__} not found for {event_type.__name__}")

    def publish(self, event: Any) -> None:
        """Publish an event to all subscribed handlers"""
        event_type = type(event)
        event_id = getattr(event, 'event_id', str(uuid.uuid4()))
        timestamp = getattr(event, 'timestamp', datetime.now())
        
        logger.info(f"Publishing {event_type.__name__} event (ID: {event_id})")

        # Apply filters for this event type
        filters = self._filters.get(event_type, [])
        for event_filter in filters:
            if not event_filter.should_process(event):
                logger.debug(f"Event {event_id} filtered out by {event_filter}")
                return

        # Run middleware chain
        processed_event = event
        for middleware in self._middleware:
            processed_event = middleware.process(processed_event)
            if processed_event is None:
                logger.warning(f"Event {event_id} blocked by middleware")
                return

        # Store event in history
        self._store_event(processed_event, event_type, event_id, timestamp)

        # Persist event if enabled
        if self._persistence_enabled:
            self._persist_event(processed_event, event_type, event_id, timestamp)

        # Notify handlers (including those subscribed to parent classes)
        # We collect all handlers from the MRO to ensure we catch subscriptions to base classes
        handlers_to_notify = []
        for cls in event_type.__mro__:
            if cls in self._handlers:
                handlers_to_notify.extend(self._handlers[cls])
        
        # Remove duplicates while preserving order (if a handler is subscribed to multiple levels)
        # Note: In Python 3.7+, dict keys preserve insertion order
        unique_handlers = list(dict.fromkeys(handlers_to_notify))

        for handler in unique_handlers:
            try:
                handler(processed_event)
            except Exception as e:
                logger.error(f"Error in handler {handler.__name__}: {e}", exc_info=True)

    def add_filter(self, event_type: type, filter_func: Callable[[Any], bool]) -> None:
        """Add a filter for a specific event type"""
        event_filter = EventFilter(filter_func)
        self._filters[event_type].append(event_filter)
        logger.info(f"Added filter for {event_type.__name__}")

    def add_middleware(self, middleware_func: Callable[[Any], Any]) -> None:
        """Add middleware that runs before event handlers"""
        middleware = EventMiddleware(middleware_func)
        self._middleware.append(middleware)
        logger.info("Added event middleware")

    def _store_event(self, event: Any, event_type: type, event_id: str, timestamp: datetime) -> None:
        """Store event in history for replay and debugging"""
        event_data = {
            'event_id': event_id,
            'timestamp': timestamp.isoformat(),
            'event_type': event_type.__name__,
            'event_data': self._serialize_event(event)
        }
        
        self._event_history.append(event_data)
        
        # Trim history if it exceeds max size
        if len(self._event_history) > self.max_history:
            self._event_history = self._event_history[-self.max_history:]

    def _serialize_event(self, event: Any) -> Dict[str, Any]:
        """Serialize event data for storage"""
        data = {}
        if hasattr(event, '__dict__'):
            # For dataclass objects
            try:
                data = asdict(event)
            except:
                data = event.__dict__
        elif isinstance(event, dict):
            data = event
        else:
            return {'value': str(event)}
            
        # Recursively convert datetime objects to strings
        return self._make_json_serializable(data)

    def _make_json_serializable(self, data: Any) -> Any:
        """Recursively convert objects to JSON serializable format"""
        if isinstance(data, dict):
            return {k: self._make_json_serializable(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._make_json_serializable(v) for v in data]
        elif isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, uuid.UUID):
            return str(data)
        elif hasattr(data, 'value') and isinstance(data.value, int): # Enum
             return data.value
        elif hasattr(data, 'name') and isinstance(data.name, str): # Enum
             return data.name
        return data

    def _persist_event(self, event: Any, event_type: type, event_id: str, timestamp: datetime) -> None:
        """Persist event to file for replay"""
        if not self.persistence_path:
            return

        try:
            event_data = {
                'event_id': event_id,
                'timestamp': timestamp.isoformat(),
                'event_type': event_type.__name__,
                'event_data': self._serialize_event(event)
            }
            
            with open(self.persistence_path, 'a') as f:
                f.write(json.dumps(event_data) + '\n')
        except Exception as e:
            logger.error(f"Failed to persist event {event_id}: {e}")

    def get_event_history(self, event_type: Optional[type] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get event history, optionally filtered by type"""
        history = self._event_history
        
        if event_type:
            type_name = event_type.__name__
            history = [e for e in history if e['event_type'] == type_name]
        
        if limit:
            history = history[-limit:]
        
        return history

    def replay_events(self, event_type: Optional[type] = None, since: Optional[datetime] = None) -> None:
        """Replay events from history"""
        history = self.get_event_history(event_type)
        
        if since:
            since_str = since.isoformat()
            history = [e for e in history if e['timestamp'] >= since_str]
        
        logger.info(f"Replaying {len(history)} events")
        
        for event_record in history:
            try:
                # Recreate event object
                event_data = event_record['event_data']
                event_type_name = event_record['event_type']
                
                # For now, just republish the data
                # In a full implementation, we'd reconstruct the actual event objects
                self.publish(event_data)
            except Exception as e:
                logger.error(f"Error replaying event {event_record['event_id']}: {e}")

    def clear(self) -> None:
        """Clear all handlers, middleware, and history"""
        self._handlers.clear()
        self._middleware.clear()
        self._filters.clear()
        self._event_history.clear()
        logger.info("Event bus cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        return {
            'handlers_count': sum(len(handlers) for handlers in self._handlers.values()),
            'middleware_count': len(self._middleware),
            'filters_count': sum(len(filters) for filters in self._filters.values()),
            'history_size': len(self._event_history),
            'persistence_enabled': self._persistence_enabled,
            'subscribed_types': list(self._handlers.keys())
        }


# Backward compatibility
SimpleEventBus = EnhancedEventBus
