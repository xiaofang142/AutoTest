"""WebSocket client for executor event streaming."""
import asyncio
import json
from typing import Callable, Optional

from app.lib.logger import get_logger

logger = get_logger(__name__)

EventHandler = Callable[[dict], None]


class ExecutorWSClient:
    """WebSocket client that receives real-time events from the executor.

    Supports auto-reconnect with exponential backoff and event dispatching
    to registered callbacks by event type.
    """

    def __init__(self, url: str):
        self._url = url
        self._ws: Optional["websockets.WebSocketClientProtocol"] = None
        self._handlers: dict[str, list[EventHandler]] = {}
        self._running = False
        self._reconnect_delays = [2, 4, 8, 16, 32]

    def on(self, event: str, handler: EventHandler) -> None:
        """Register a callback for a specific event type.

        The handler receives the parsed JSON payload (dict).
        """
        self._handlers.setdefault(event, []).append(handler)

    async def connect(self) -> None:
        """Establish a single WebSocket connection."""
        import websockets
        self._ws = await websockets.connect(self._url)
        self._running = True
        logger.info("WS connected: %s", self._url)

    async def disconnect(self) -> None:
        """Close the WebSocket connection."""
        self._running = False
        if self._ws:
            await self._ws.close()
            self._ws = None
        logger.info("WS disconnected")

    async def connect_with_reconnect(self) -> None:
        """Connect and automatically reconnect on disconnect with exponential backoff.

        Runs until disconnect() is called. Dispatches received JSON events
        to registered callbacks by event type.
        """
        attempt = 0
        while self._running:
            try:
                await self.connect()
                attempt = 0
                if self._ws is None:
                    raise ConnectionError("WS not connected")
                async for raw in self._ws:
                    try:
                        data = json.loads(raw)
                        event_type = data.get("type", "")
                        payload = data.get("payload", data)
                        handlers = self._handlers.get(event_type, [])
                        for h in handlers:
                            h(payload)
                    except json.JSONDecodeError:
                        logger.warning("WS received non-JSON message: %s", raw[:100])
            except Exception as e:
                if not self._running:
                    break
                delay = self._reconnect_delays[min(attempt, len(self._reconnect_delays) - 1)]
                logger.warning("WS disconnected: %s. Reconnecting in %ss...", e, delay)
                await asyncio.sleep(delay)
                attempt += 1
