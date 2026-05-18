import pytest
from datetime import datetime, timedelta
from app.services.causal_engine import CausalRuleEngine


class TestCausalRuleEngine:
    def setup_method(self):
        self.engine = CausalRuleEngine()

    def _make_event(self, dimension: str, url: str = "", status: int = 200,
                    message: str = "", texts: list[str] = None,
                    ts_offset: int = 1) -> dict:
        ts = datetime.now() + timedelta(seconds=ts_offset)
        data = {}
        if url:
            data["url"] = url
        if status:
            data["status"] = status
        if message:
            data["message"] = message
        if texts is not None:
            data["visible_texts"] = texts
        return {"dimension": dimension, "data": data, "timestamp": ts.isoformat()}

    def test_api_error_to_console_error(self):
        a = self._make_event("api_error", url="/api/v1/orders", status=500, ts_offset=0)
        b = self._make_event("console_error", message="orders API failed with status 500", ts_offset=1)
        assert self.engine.is_causally_related(a, b)

    def test_unrelated_events_not_linked(self):
        a = self._make_event("console_error", message="deprecated API called", ts_offset=0)
        b = self._make_event("ui_broken", texts=["page loaded ok"], ts_offset=10)
        assert not self.engine.is_causally_related(a, b)

    def test_reverse_time_order_not_linked(self):
        a = self._make_event("api_error", url="/api/test", status=500, ts_offset=5)
        b = self._make_event("console_error", message="test error", ts_offset=0)
        assert not self.engine.is_causally_related(a, b)

    def test_too_close_events_not_linked(self):
        a = self._make_event("api_error", url="/api/test", status=500, ts_offset=0)
        b = self._make_event("console_error", message="test error", ts_offset=0.001)
        assert not self.engine.is_causally_related(a, b)

    def test_api_cascade_401(self):
        a = self._make_event("api_error", url="/api/auth/refresh", status=401, ts_offset=0)
        b = self._make_event("api_error", url="/api/orders", status=401, ts_offset=0.5)
        assert self.engine.is_causally_related(a, b)

    def test_api_error_to_ui_error(self):
        a = self._make_event("api_error", url="/api/data", status=500, ts_offset=0)
        b = self._make_event("ui_broken", texts=["系统错误，请稍后重试"], ts_offset=2)
        assert self.engine.is_causally_related(a, b)

    def test_different_dimension_not_in_rules(self):
        a = self._make_event("ui_broken", texts=["some error"], ts_offset=0)
        b = self._make_event("api_error", url="/api/test", status=500, ts_offset=1)
        assert not self.engine.is_causally_related(a, b)
