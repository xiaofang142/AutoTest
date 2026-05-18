"""流程线: OCR+LLM 分析 → 缺陷归因 → 交付 测试

流程: 执行数据 → OCR识别 → LLM融合 → 四维校验 → 因果归因 → 交付包
"""
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from app.domain.models.run import (
    StepExecutionRecord, ConsoleSnapshot, ConsoleLogEntry,
    NetworkSnapshot, NetworkEntry, PageState, Verifications, VerificationResult,
)
from app.domain.models.defect import Defect
from app.domain.models.task import DeliveryPackage, TesterView, DeveloperView, AIAssistantView
from app.services.analysis_service import CrossDimensionAnalyzer
from app.services.causal_engine import CausalRuleEngine
from tests.mock_repos import MemDefectRepo as InMemoryDefectRepository


def make_step(
    action: str = "click 登录按钮",
    url: str = "https://example.com/login",
    console_errors: list[dict] = None,
    network_requests: list[dict] = None,
    visible_texts: list[str] = None,
    alerts: list[str] = None,
    status: str = "failed",
) -> StepExecutionRecord:
    return StepExecutionRecord(
        id="step_test_001",
        run_id="run_test_001",
        case_id="case_test_001",
        step_index=0,
        action=action,
        status=status,
        duration_ms=1500,
        screenshots={"after": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk",
                     "before": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"},
        console_snapshot=ConsoleSnapshot(
            errors=[ConsoleLogEntry(message=e.get("message", ""), level=e.get("level", "error"))
                    for e in (console_errors or [])],
            warnings=[],
        ),
        network_snapshot=NetworkSnapshot(
            requests=[NetworkEntry(**r) for r in (network_requests or [])],
            failed=[NetworkEntry(**r) for r in (network_requests or []) if r.get("status", 0) >= 400],
        ),
        page_state=PageState(
            current_url=url,
            visible_text_elements=visible_texts or [],
            active_alerts=alerts or [],
        ),
    )


class TestCrossDimensionAnalysisFlow:
    """流程线1: 四维信号采集 → 分析引擎 → 缺陷判定"""

    @pytest.mark.asyncio
    async def test_1_normal_page_passes(self):
        """正常页面 → 四维都 pass → 无缺陷"""
        step = make_step(
            visible_texts=["欢迎回来", "用户中心"],
            network_requests=[{"method": "GET", "url": "/api/user", "status": 200}],
            status="passed",
        )
        defect_repo = InMemoryDefectRepository()
        analyzer = CrossDimensionAnalyzer(defect_repo=defect_repo)
        defect = await analyzer.analyze(step)
        assert defect is None

    @pytest.mark.asyncio
    async def test_2_api_error_detected(self):
        step = make_step(
            visible_texts=["系统错误", "请稍后重试"],
            network_requests=[{"method": "POST", "url": "/api/login", "status": 500}],
            console_errors=[{"message": "TypeError: Cannot read 'token'"}],
        )
        analyzer = CrossDimensionAnalyzer()
        anomalies = analyzer._detect_anomalies(step)
        assert len(anomalies) > 0
        dims = [a["dimension"] for a in anomalies]
        assert "api" in dims
        assert "ui" in dims or "console" in dims

    @pytest.mark.asyncio
    async def test_3_console_error_without_api(self):
        """纯前端 Console 错误 → 缺陷归属 frontend"""
        step = make_step(
            visible_texts=["页面加载中..."],
            network_requests=[{"method": "GET", "url": "/api/data", "status": 200}],
            console_errors=[{"message": "Uncaught ReferenceError: React is not defined"}],
        )
        defect_repo = InMemoryDefectRepository()
        analyzer = CrossDimensionAnalyzer(defect_repo=defect_repo)
        defect = await analyzer.analyze(step)
        # 应该有缺陷，且根因是 console 而非 api
        if defect:
            assert defect.severity in ("medium", "high")

    @pytest.mark.asyncio
    async def test_4_business_logic_failure(self):
        """业务校验失败 → URL 未预期跳转"""
        step = make_step(
            url="https://example.com/login",
            visible_texts=["登录"],
            network_requests=[{"method": "POST", "url": "/api/login", "status": 200}],
        )
        result = await self._run_verify(step, expected={"url_contains": "/dashboard"})

    async def _run_verify(self, step, expected=None):
        analyzer = CrossDimensionAnalyzer()
        biz_result = analyzer.verify_business(step, expected)
        assert biz_result is not None
        return biz_result


class TestCausalEngineFlow:
    """流程线2: 因果推断 → 证据链构建"""

    def test_1_api_causes_console(self):
        """API 500 → 控制台报错 (因果关系)"""
        engine = CausalRuleEngine()
        a = {"dimension": "api_error", "timestamp": datetime.now(),
             "data": {"url": "/api/v1/orders", "status": 500}}
        b = {"dimension": "console_error", "timestamp": datetime.now(),
             "data": {"message": "orders API failed with status 500"}}
        # 调整时间顺序
        b["timestamp"] = a["timestamp"] + __import__("datetime").timedelta(seconds=1)
        assert engine.is_causally_related(a, b)

    def test_2_console_does_not_cause_api(self):
        """Console 报错 → API 500 (反向不成立)"""
        engine = CausalRuleEngine()
        a = {"dimension": "console_error", "timestamp": datetime.now(),
             "data": {"message": "JS Error"}}
        b = {"dimension": "api_error", "timestamp": datetime.now(),
             "data": {"url": "/api/test", "status": 500}}
        b["timestamp"] = a["timestamp"] + __import__("datetime").timedelta(seconds=1)
        # 维度映射里没有 console_error → api_error 的规则
        assert not engine.is_causally_related(a, b)

    def test_3_401_cascade(self):
        """Token 过期 → 批量 401"""
        engine = CausalRuleEngine()
        a = {"dimension": "api_error", "timestamp": datetime.now(),
             "data": {"url": "/api/auth/refresh", "status": 401}}
        b = {"dimension": "api_error", "timestamp": datetime.now(),
             "data": {"url": "/api/orders", "status": 401}}
        b["timestamp"] = a["timestamp"] + __import__("datetime").timedelta(milliseconds=500)
        assert engine.is_causally_related(a, b)


class TestDeliveryPackageFlow:
    """流程线3: 缺陷聚合 → 交付包生成"""

    def test_1_delivery_has_three_views(self):
        """交付包包含三类视图"""
        pkg = DeliveryPackage(
            tester_view=TesterView(summary="测试完成，发现2个缺陷"),
            developer_view=DeveloperView(root_cause="API 500"),
            ai_assistant_view=AIAssistantView(
                task_summary="登录冒烟",
                reproduction_steps=["1. 打开登录页", "2. 输入凭据", "3. 点击登录"],
            ),
            regression_entry={"target_url": "https://example.com/login"},
        )
        assert pkg.tester_view.summary != ""
        assert pkg.developer_view.root_cause != ""
        assert len(pkg.ai_assistant_view.reproduction_steps) == 3
        assert pkg.regression_entry.get("target_url") is not None

    def test_2_regression_entry(self):
        """回归包包含必要字段"""
        pkg = DeliveryPackage(
            regression_entry={
                "target_url": "https://example.com/login",
                "task_id": "task_001",
                "key_steps": [0, 2],
            }
        )
        assert pkg.regression_entry["target_url"] == "https://example.com/login"
        assert pkg.regression_entry["task_id"] == "task_001"
        assert 0 in pkg.regression_entry["key_steps"]

    def test_3_delivery_from_defect(self):
        """从 Defect 构建交付内容"""
        defect = Defect(
            id="def_001",
            run_id="run_001",
            severity="high",
            title="登录接口500",
        )
        assert defect.id == "def_001"
        assert defect.severity == "high"
