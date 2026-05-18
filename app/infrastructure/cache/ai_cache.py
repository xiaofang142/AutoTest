import hashlib
import json
from datetime import datetime, timedelta


class AICache:
    """In-memory AI call cache to reduce duplicate token consumption.

    Caches by (model + prompt_hash) with configurable TTL.
    """

    def __init__(self, ttl_seconds: int = 3600):
        self._cache: dict[str, tuple[bytes, datetime]] = {}
        self._ttl = timedelta(seconds=ttl_seconds)

    def _make_key(self, model: str, prompt: str) -> str:
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        return f"{model}:{prompt_hash}"

    def get(self, model: str, prompt: str) -> str | None:
        key = self._make_key(model, prompt)
        entry = self._cache.get(key)
        if entry is None:
            return None
        data, expire_at = entry
        if datetime.now() > expire_at:
            del self._cache[key]
            return None
        return data.decode()

    def set(self, model: str, prompt: str, result: str, ttl: int | None = None):
        key = self._make_key(model, prompt)
        expire = datetime.now() + timedelta(seconds=ttl or self._ttl.seconds)
        self._cache[key] = (result.encode(), expire)

    def invalidate_by_prefix(self, prefix: str):
        to_delete = [k for k in self._cache if prefix in k]
        for k in to_delete:
            del self._cache[k]

    def clear(self):
        self._cache.clear()

    @property
    def size(self) -> int:
        return len(self._cache)
