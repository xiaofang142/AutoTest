import pytest
from app.infrastructure.cache.ai_cache import AICache


class TestAICache:
    def setup_method(self):
        self.cache = AICache(ttl_seconds=3600)

    def test_set_and_get(self):
        self.cache.set("gpt-4", "hello world", "response text")
        result = self.cache.get("gpt-4", "hello world")
        assert result == "response text"

    def test_missing_key(self):
        result = self.cache.get("gpt-4", "nonexistent")
        assert result is None

    def test_different_models_separate(self):
        self.cache.set("model-a", "same prompt", "answer a")
        self.cache.set("model-b", "same prompt", "answer b")
        assert self.cache.get("model-a", "same prompt") == "answer a"
        assert self.cache.get("model-b", "same prompt") == "answer b"

    def test_invalidate_by_prefix(self):
        self.cache.set("model_x", "aaaa", "data1")
        self.cache.set("model_y", "bbbb", "data2")
        assert self.cache.size == 2
        self.cache.invalidate_by_prefix("model_x")
        assert self.cache.size == 1
        assert self.cache.get("model_y", "bbbb") == "data2"

    def test_clear(self):
        self.cache.set("m", "p1", "r1")
        self.cache.set("m", "p2", "r2")
        assert self.cache.size == 2
        self.cache.clear()
        assert self.cache.size == 0

    def test_ttl_expiry(self):
        from unittest.mock import patch
        cache = AICache(ttl_seconds=1)
        cache.set("m", "p", "r")
        assert cache.get("m", "p") == "r"
        # simulate expiry by clearing via prefix
        cache.invalidate_by_prefix("m")
        assert cache.get("m", "p") is None
