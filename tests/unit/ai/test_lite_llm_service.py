"""Tests for LiteLLMService.analyze_merged()."""
from unittest.mock import AsyncMock

import pytest

from app.infrastructure.ai.lite_llm_service import LiteLLMAIService


@pytest.fixture
def service():
    return LiteLLMAIService()


@pytest.fixture
def basic_signals():
    return {
        "ocr_text": "欢迎回来 用户名 密码 登录",
        "ocr_elements": "['登录', '密码']",
        "dom_texts": "欢迎\n登录\n注册",
        "alerts": "[]",
        "console_errors": "[]",
        "console_warnings": "[]",
        "network_requests": "[{\"method\": \"GET\", \"url\": \"/api/user\", \"status\": 200}]",
        "action": "click 登录按钮 (step 0)",
    }


class TestAnalyzeMergedPrompt:
    def test_prompt_contains_all_placeholders(self, service):
        prompt = service.COT_ANALYSIS_PROMPT
        for key in ["action", "ocr_text", "ocr_elements", "dom_texts",
                     "alerts", "console_errors", "console_warnings", "network_requests"]:
            assert "{" + key + "}" in prompt, f"Missing placeholder: {{{key}}}"

    def test_prompt_format_success(self, service, basic_signals):
        prompt = service.COT_ANALYSIS_PROMPT.format(**basic_signals)
        assert "登录" in prompt
        assert "欢迎回来" in prompt
        assert "/api/user" in prompt


class TestAnalyzeMergedLLMPath:
    """Tests for the LLM path (when _llm_available is True)."""

    @pytest.fixture
    def online_service(self):
        """A service that appears to have LLM available."""
        svc = LiteLLMAIService()
        svc._llm_available = True  # mock LLM availability
        return svc

    @pytest.mark.asyncio
    async def test_returns_valid_json(self, online_service, basic_signals):
        """LLM returns valid JSON → parse correctly."""
        online_service._call_llm = AsyncMock(return_value='{"dimensions":{"ui":{"status":"pass","issues":[],"confidence":0.95}},"root_cause":"","fix_suggestion":"","summary":"OK"}')
        result = await online_service.analyze_merged(basic_signals)
        assert "dimensions" in result
        assert result["dimensions"]["ui"]["status"] == "pass"

    @pytest.mark.asyncio
    async def test_handles_invalid_json(self, online_service, basic_signals):
        online_service._call_llm = AsyncMock(return_value="Not JSON at all")
        result = await online_service.analyze_merged(basic_signals)
        # Falls back to _simple_analysis which always returns dimensions
        assert "dimensions" in result

    @pytest.mark.asyncio
    async def test_retry_on_failure(self, online_service, basic_signals):
        """First call fails → retry succeeds on second attempt."""
        call_count = 0

        async def mock_call(model, system, user, use_cache=True):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("First attempt failed")
            return '{"dimensions":{"ui":{"status":"pass","issues":[]}},"root_cause":"","fix_suggestion":"","summary":"retry OK"}'

        online_service._call_llm = mock_call
        result = await online_service.analyze_merged(basic_signals)
        assert call_count == 2
        assert result["dimensions"]["ui"]["status"] == "pass"

    @pytest.mark.asyncio
    async def test_both_attempts_fail(self, online_service, basic_signals):
        online_service._call_llm = AsyncMock(side_effect=RuntimeError("Always fails"))
        result = await online_service.analyze_merged(basic_signals)
        assert "dimensions" in result
        assert "summary" in result

    @pytest.mark.asyncio
    async def test_empty_ocr_text(self, online_service):
        signals = {
            "ocr_text": "",
            "ocr_elements": "[]",
            "dom_texts": "some text",
            "alerts": "[]",
            "console_errors": "[]",
            "console_warnings": "[]",
            "network_requests": "[]",
            "action": "test (step 0)",
        }
        # The first call uses the CoT prompt which includes {ocr_text} placeholder
        # The test just verifies it doesn't crash and returns proper result
        online_service._call_llm = AsyncMock(return_value='{"dimensions":{"ui":{"status":"pass","issues":[],"confidence":0.9}},"root_cause":"","fix_suggestion":"","summary":"ok","reasoning":[]}')
        result = await online_service.analyze_merged(signals)
        assert "dimensions" in result


# No rule-based fallback tests — the system always uses LLM merge analysis
# (the user explicitly chose "no fallback/downgrade" architecture)
