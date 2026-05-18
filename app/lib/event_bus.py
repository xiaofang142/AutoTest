from collections import defaultdict
from datetime import datetime
from typing import Any, Callable
from app.lib.logger import get_logger

logger = get_logger(__name__)


class DomainEvent:
    def __init__(self, event_type: str, payload: dict, source: str = ""):
        self.event_id = f"evt_{int(datetime.now().timestamp() * 1000000)}"
        self.event_type = event_type
        self.timestamp = datetime.now()
        self.source = source
        self.payload = payload


class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable):
        self._handlers[event_type].append(handler)

    async def publish(self, event: DomainEvent):
        for handler in self._handlers.get(event.event_type, []):
            try:
                await handler(event)
            except Exception as e:
                logger.error("Event handler failed for %s: %s", event.event_type, e)

    def reset(self):
        self._handlers.clear()


event_bus = EventBus()
