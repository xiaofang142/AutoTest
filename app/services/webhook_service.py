import hashlib
import hmac
import json
from typing import Any

import httpx

from app.lib.logger import get_logger

logger = get_logger(__name__)


class WebhookService:
    """Simple webhook dispatcher with HMAC signing and retry."""

    def __init__(self):
        self._subscriptions: dict[str, list[dict]] = {}

    def subscribe(self, event_type: str, url: str, secret: str = ""):
        if event_type not in self._subscriptions:
            self._subscriptions[event_type] = []
        self._subscriptions[event_type].append({"url": url, "secret": secret})
        logger.info("Webhook subscribed: %s -> %s", event_type, url)

    def unsubscribe(self, event_type: str, url: str):
        subs = self._subscriptions.get(event_type, [])
        self._subscriptions[event_type] = [s for s in subs if s["url"] != url]

    async def dispatch(self, event_type: str, payload: dict):
        for sub in self._subscriptions.get(event_type, []):
            await self._send_with_retry(sub["url"], event_type, payload, sub["secret"])

    async def _send_with_retry(self, url: str, event_type: str, payload: dict, secret: str, max_retries: int = 3):
        body = json.dumps({"event_type": event_type, "payload": payload}, ensure_ascii=False)
        headers = {"Content-Type": "application/json"}
        if secret:
            sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
            headers["X-AutoTest-Signature"] = sig

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(url, content=body, headers=headers)
                    if resp.status_code < 500:
                        return
            except Exception as e:
                logger.warning("Webhook attempt %d/%d failed for %s: %s", attempt + 1, max_retries, url, e)
