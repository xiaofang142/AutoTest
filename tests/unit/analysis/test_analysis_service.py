from unittest.mock import AsyncMock

import pytest

from app.domain.models.run import (
    ConsoleLogEntry,
    ConsoleSnapshot,
    NetworkEntry,
    NetworkSnapshot,
    PageState,
    StepExecutionRecord,
)
from app.services.analysis_service import CrossDimensionAnalyzer


@pytest.fixture
def defect_repo_mock():
    return AsyncMock()


@pytest.fixture
def analyzer(defect_repo_mock):
    return CrossDimensionAnalyzer(defect_repo=defect_repo_mock)


def make_step(**kwargs) -> StepExecutionRecord:
    return StepExecutionRecord(
        id=kwargs.get("id", "step_001"),
        run_id=kwargs.get("run_id", "run_001"),
        case_id=kwargs.get("case_id", "tc_001"),
        step_index=kwargs.get("step_index", 1),
        action=kwargs.get("action", "click"),
        platform=kwargs.get("platform", "web"),
        status=kwargs.get("status", "passed"),
        console_snapshot=kwargs.get("console_snapshot", ConsoleSnapshot()),
        network_snapshot=kwargs.get("network_snapshot", NetworkSnapshot()),
        page_state=kwargs.get("page_state", PageState()),
    )


class TestVerifyUI:
    def test_pass_no_issues(self, analyzer):
        step = make_step(page_state=PageState(current_url="https://ok.com", active_alerts=[]))
        result = analyzer.verify_ui(step)
        assert result.status == "pass"

    def test_error_alert_detected(self, analyzer):
        step = make_step(page_state=PageState(active_alerts=["系统错误，请稍后重试"]))
        result = analyzer.verify_ui(step)
        assert result.status == "failed"

    def test_no_screenshot_warning(self, analyzer):
        step = make_step(screenshots={})
        result = analyzer.verify_ui(step)
        # Empty screenshots dict → no "after" or "before" → warning issue appended
        # Warning-only issues → status remains "pass"
        assert result.status == "pass"


class TestVerifyConsole:
    def test_pass_no_errors(self, analyzer):
        step = make_step()
        result = analyzer.verify_console(step)
        assert result.status == "pass"

    def test_error_detected(self, analyzer):
        step = make_step(console_snapshot=ConsoleSnapshot(
            errors=[ConsoleLogEntry(level="error", message="TypeError: undefined is not a function", source="app.js")]))
        result = analyzer.verify_console(step)
        assert result.status == "failed"

    def test_warning_only(self, analyzer):
        step = make_step(console_snapshot=ConsoleSnapshot(
            warnings=[ConsoleLogEntry(level="warning", message="Deprecated API", source="lib.js")]))
        result = analyzer.verify_console(step)
        assert result.status == "uncertain"


class TestVerifyAPI:
    def test_pass_all_ok(self, analyzer):
        step = make_step(network_snapshot=NetworkSnapshot(
            requests=[NetworkEntry(method="GET", url="https://api.example.com/data", status=200)]))
        result = analyzer.verify_api(step)
        assert result.status == "pass"

    def test_5xx_error(self, analyzer):
        step = make_step(network_snapshot=NetworkSnapshot(
            requests=[NetworkEntry(method="GET", url="https://api.example.com/data", status=500)]))
        result = analyzer.verify_api(step)
        assert result.status == "failed"

    def test_4xx_warning(self, analyzer):
        step = make_step(network_snapshot=NetworkSnapshot(
            requests=[NetworkEntry(method="GET", url="https://api.example.com/data", status=404)]))
        result = analyzer.verify_api(step)
        assert result.status == "uncertain"


class TestVerifyBusiness:
    def test_url_match(self, analyzer):
        step = make_step(page_state=PageState(current_url="https://example.com/dashboard"))
        result = analyzer.verify_business(step, expected={"url_contains": "dashboard"})
        assert result.status == "pass"

    def test_url_mismatch(self, analyzer):
        step = make_step(page_state=PageState(current_url="https://example.com/login"))
        result = analyzer.verify_business(step, expected={"url_contains": "dashboard"})
        assert result.status == "failed"


class TestDetectAnomalies:
    def test_no_anomalies(self, analyzer):
        step = make_step()
        anomalies = analyzer._detect_anomalies(step)
        assert len(anomalies) == 0

    def test_detects_console_error(self, analyzer):
        step = make_step(console_snapshot=ConsoleSnapshot(
            errors=[ConsoleLogEntry(level="error", message="Error!", source="test.js")]))
        anomalies = analyzer._detect_anomalies(step)
        dims = [a["dimension"] for a in anomalies]
        assert "console" in dims


class TestSeverity:
    def test_api_error_is_high(self, analyzer):
        anomalies = [{"dimension": "api", "issues": [], "confidence": 0.95}]
        assert analyzer._determine_severity(anomalies) == "high"

    def test_ui_and_console_is_high(self, analyzer):
        anomalies = [{"dimension": "ui", "issues": [], "confidence": 0.9},
                      {"dimension": "console", "issues": [], "confidence": 0.98}]
        assert analyzer._determine_severity(anomalies) == "high"

    def test_console_only_is_medium(self, analyzer):
        anomalies = [{"dimension": "console", "issues": [], "confidence": 0.98}]
        assert analyzer._determine_severity(anomalies) == "medium"


class TestAnalyze:
    async def test_analyze_no_defect(self, analyzer):
        step = make_step()
        result = await analyzer.analyze(step)
        assert result is None

    async def test_analyze_creates_defect(self, defect_repo_mock):
        """Test LLM merge analysis path detects defects."""
        ai_mock = AsyncMock()
        ai_mock.analyze_merged = AsyncMock(return_value={
            "dimensions": {
                "console": {"status": "fail", "issues": [{"detail": "Critical JS error"}], "confidence": 0.95},
            },
            "root_cause": "app.js crashed with unhandled error",
            "fix_suggestion": "Add error boundary",
            "summary": "Console error detected in app.js",
        })
        analyzer = CrossDimensionAnalyzer(defect_repo=defect_repo_mock, ai_service=ai_mock)
        step = make_step(console_snapshot=ConsoleSnapshot(
            errors=[ConsoleLogEntry(level="error", message="Critical error", source="app.js")]))
        defect_repo_mock.create = AsyncMock(side_effect=lambda x: x)
        result = await analyzer.analyze(step)
        assert result is not None
        assert result.severity in ("high", "medium", "low")
        assert len(result.evidence_chains) > 0
        assert "Console error" in result.title

    async def test_analyze_all_signals_collected(self, defect_repo_mock):
        """Test that all 4 signal types are properly collected in llm_analysis."""
        ai_mock = AsyncMock()
        ai_mock.analyze_merged = AsyncMock(return_value={
            "dimensions": {"ui": {"status": "fail", "issues": [], "confidence": 0.8}},
            "root_cause": "", "fix_suggestion": "", "summary": "UI issue",
        })
        analyzer = CrossDimensionAnalyzer(defect_repo=defect_repo_mock, ai_service=ai_mock)
        step = make_step(
            page_state=PageState(current_url="https://example.com/login",
                                 visible_text_elements=["欢迎", "登录", "用户名"],
                                 active_alerts=["系统错误"]),
            network_snapshot=NetworkSnapshot(
                requests=[NetworkEntry(method="GET", url="/api/data", status=500)]),
        )
        result = await analyzer.analyze(step)
        assert result is not None
        assert step.llm_analysis is not None
        assert "ocr_text" in step.llm_analysis
        assert "signals" in step.llm_analysis
        assert "dom_texts" in step.llm_analysis["signals"]
        assert "network_requests" in step.llm_analysis["signals"]
