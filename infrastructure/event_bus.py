"""
Simple In-Process Event Bus
No network calls, just clean module communication
"""

from typing import Dict, List, Callable
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class SimpleEventBus:
    """Simple in-process event bus for module communication"""

    def __init__(self):
        self._handlers: Dict[type, List[Callable]] = defaultdict(list)
        self._middleware: List[Callable] = []

    def subscribe(self, event_type: type, handler: Callable) -> None:
        """Subscribe a handler to an event type"""
        self._handlers[event_type].append(handler)
        logger.info(f"Subscribed {handler.__name__} to {event_type.__name__}")

    def unsubscribe(self, event_type: type, handler: Callable) -> None:
        """Unsubscribe a handler from an event type"""
        if event_type in self._handlers:
            self._handlers[event_type].remove(handler)
            logger.info(f"Unsubscribed {handler.__name__} from {event_type.__name__}")

    def publish(self, event) -> None:
        """Publish an event to all subscribed handlers"""
        event_type = type(event)
        logger.info(f"Publishing {event_type.__name__} event")

        # Run middleware
        for middleware in self._middleware:
            event = middleware(event)
            if event is None:
                logger.warning(f"Event {event_type.__name__} blocked by middleware")
                return

        # Notify handlers
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in handler {handler.__name__}: {e}", exc_info=True)

    def add_middleware(self, middleware: Callable) -> None:
        """Add middleware that runs before event handlers"""
        self._middleware.append(middleware)

    def clear(self) -> None:
        """Clear all handlers (useful for testing)"""
        self._handlers.clear()
        self._middleware.clear()
        logger.info("Event bus cleared")
