"""CausalRuleEngine + LLMCausalJudge for defect attribution.

Handles ~80% of causality patterns deterministically (no LLM cost),
with LLM fallback for edge cases.
"""
from datetime import datetime, timedelta
from typing import Any, Optional


class CausalRuleEngine:
    """Deterministic causal relationship detection engine."""

    def __init__(self):
        self._time_windows: dict[tuple[str, str], timedelta] = {
            ("api_error", "console_error"): timedelta(seconds=2),
            ("api_error", "ui_broken"): timedelta(seconds=5),
            ("console_error", "ui_broken"): timedelta(seconds=3),
        }

    def is_causally_related(self, event_a: dict, event_b: dict) -> bool:
        ts_a = event_a.get("timestamp")
        ts_b = event_b.get("timestamp")
        if not ts_a or not ts_b:
            return False

        if isinstance(ts_a, str):
            ts_a = datetime.fromisoformat(ts_a)
        if isinstance(ts_b, str):
            ts_b = datetime.fromisoformat(ts_b)

        diff = ts_b - ts_a
        if diff < timedelta(milliseconds=50):
            return False

        key = (event_a.get("dimension"), event_b.get("dimension"))
        window = self._time_windows.get(key, timedelta(seconds=5))
        if diff > window:
            return False

        check_map = {
            ("api_error", "console_error"): self._check_api_to_console,
            ("api_error", "ui_broken"): self._check_api_to_ui,
            ("console_error", "ui_broken"): self._check_console_to_ui,
            ("api_error", "api_error"): self._check_api_cascade,
        }
        checker = check_map.get(key)
        return checker(event_a, event_b) if checker else False

    def _check_api_to_console(self, a: dict, b: dict) -> bool:
        api_url = a.get("data", {}).get("url", "")
        console_msg = b.get("data", {}).get("message", "")
        path = api_url.rstrip("/").split("/")[-1] if "/" in api_url else api_url
        return path in console_msg if path else False

    def _check_api_to_ui(self, a: dict, b: dict) -> bool:
        texts = b.get("data", {}).get("visible_texts", [])
        patterns = ["系统错误", "网络错误", "加载失败", "请稍后重试", "error", "failed"]
        return any(any(p in t.lower() for p in patterns) for t in texts)

    def _check_console_to_ui(self, a: dict, b: dict) -> bool:
        msg = a.get("data", {}).get("message", "")
        return "Uncaught" in msg or "unhandled" in msg.lower()

    def _check_api_cascade(self, a: dict, b: dict) -> bool:
        return a.get("data", {}).get("status") == 401 and b.get("data", {}).get("status") == 401


class LLMCausalJudge:
    """LLM fallback for ambiguous causality patterns."""

    def __init__(self, ai_service=None):
        self._ai = ai_service

    async def judge(self, event_a: dict, event_b: dict) -> bool:
        if not self._ai:
            return False
        prompt = f"""Determine if these two anomaly events are causally related.
Event A (earlier): dimension={event_a.get('dimension')} type={event_a.get('type')} data={event_a.get('data')}
Event B (later): dimension={event_b.get('dimension')} type={event_b.get('type')} data={event_b.get('data')}
Criteria: (1) Could A cause B? (2) Same business module? (3) Reasonable time gap?
Answer YES or NO."""
        try:
            result = await self._ai.analyze_merged({"causal_question": prompt})
            return "YES" in str(result).upper()
        except Exception:
            return False
