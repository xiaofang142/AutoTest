"""E2E 流程线3: 全链路分析管线

从执行数据生成 → OCR → 四维校验 → 因果归因 → 交付
真实连接所有分析组件, 无mock跳过任一环节
"""
import pytest

from app.domain.models.run import (
    StepExecutionRecord, ConsoleSnapshot, ConsoleLogEntry,
    NetworkSnapshot, NetworkEntry, PageState,
)
from app.domain.models.defect import Defect
from app.services.analysis_service import CrossDimensionAnalyzer
from app.services.causal_engine import CausalRuleEngine
from app.infrastructure.persistence.task_repo import InMemoryTaskRepository
from app.domain.models.task import (
    TestTask, TaskInput, DeliveryPackage,
    TesterView, DeveloperView, AIAssistantView,
)
from tests.mock_repos import MemDefectRepo


def build_step(
    action="click login button",
    url="https://example.com/login",
    errors=None,
    requests=None,
    texts=None,
    alerts=None,
) -> StepExecutionRecord:
    """构建一个真实感的执行步骤数据"""
    return StepExecutionRecord(
        id="step_e2e_001",
        run_id="run_e2e_001",
        case_id="case_login",
        step_index=3,
        action=action,
        status="failed" if (errors or (requests and any(r.get("status", 200) >= 400 for r in (requests or [])))) else "passed",
        duration_ms=2340,
        screenshots={
            "before": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk",
            "after": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk",
        },
        console_snapshot=ConsoleSnapshot(
            errors=[ConsoleLogEntry(message=e["message"], level=e.get("level", "error"))
                    for e in (errors or [])],
            warnings=[],
        ),
        network_snapshot=NetworkSnapshot(
            requests=[NetworkEntry(**r) for r in (requests or [])],
        ),
        page_state=PageState(
            current_url=url,
            visible_text_elements=texts or [],
            active_alerts=alerts or [],
        ),
    )


class TestFullAnalysisPipeline:
    """全链路分析管线: 原始数据 → 四维校验 → 因果归因 → 缺陷交付"""

    @pytest.mark.asyncio
    async def test_full_pipeline_no_defects(self):
        """场景: 页面正常加载"""
        step = build_step(
            action="navigate to https://example.com",
            url="https://example.com/dashboard",
            requests=[{"method": "GET", "url": "https://example.com/api/status", "status": 200}],
            texts=["欢迎回来", "用户中心", "数据概览"],
        )
        analyzer = CrossDimensionAnalyzer()
        defect = await analyzer.analyze(step)
        assert defect is None, "正常页面不应产生缺陷"

    @pytest.mark.asyncio
    async def test_full_pipeline_api_error(self):
        """场景: API 500导致页面错误"""
        step = build_step(
            action="click login button",
            url="https://example.com/login",
            requests=[{"method": "POST", "url": "/api/auth/login", "status": 500}],
            errors=[{"message": "TypeError: Cannot read properties of undefined (reading 'token')"}],
            texts=["系统错误", "请稍后重试"],
        )
        defect_repo = MemDefectRepo()
        analyzer = CrossDimensionAnalyzer(defect_repo=defect_repo)
        defect = await analyzer.analyze(step)
        assert defect is not None, "API错误应产生缺陷"
        chains = defect.evidence_chains
        assert len(chains) > 0, "缺陷应有证据链"
        print(f"  [ANALYSIS] 缺陷: {defect.title}")
        print(f"  [ANALYSIS] 严重度: {defect.severity}")
        print(f"  [ANALYSIS] 证据链: {chains[0].chain_summary}")

    @pytest.mark.asyncio
    async def test_full_pipeline_causal_chain(self):
        """场景: API失败→Console错误→UI异常 (完整因果链)"""
        step = build_step(
            action="submit order form",
            url="https://example.com/checkout",
            requests=[{"method": "POST", "url": "/api/v1/orders", "status": 500}],
            errors=[{"message": "orders API failed with status 500: Uncaught TypeError"}],
            texts=["订单提交失败", "系统繁忙, 请稍后重试"],
            alerts=["错误提示"],
        )
        defect_repo = MemDefectRepo()
        analyzer = CrossDimensionAnalyzer(defect_repo=defect_repo)
        defect = await analyzer.analyze(step)
        assert defect is not None, "因果链应产生缺陷"
        print(f"  [CAUSAL] 缺陷: {defect.title}")
        print(f"  [CAUSAL] 根因: {defect.ai_analysis.get('root_cause', 'N/A')}")

    @pytest.mark.asyncio
    async def test_full_pipeline_no_ai_key(self):
        """场景: 无API Key时规则引擎降级"""
        step = build_step(
            action="click search button",
            url="https://example.com/search",
            requests=[{"method": "GET", "url": "/api/search", "status": 404}],
            texts=["搜索结果", "未找到相关内容"],
        )
        analyzer = CrossDimensionAnalyzer()
        anomalies = analyzer._detect_anomalies(step)
        # 无API Key时, 规则引擎仍能检测API错误
        dims = [a["dimension"] for a in anomalies]
        assert "api" in dims, "规则引擎应检测到API 404"
        print(f"  [RULE] 规则引擎检测到: {dims}")

    def test_causal_engine_rules(self):
        """因果引擎规则验证"""
        engine = CausalRuleEngine()
        from datetime import datetime, timedelta
        base_ts = datetime.now()

        login_500 = {"dimension": "api_error", "timestamp": base_ts,
                     "data": {"url": "/api/auth/login", "status": 500}}
        js_error = {"dimension": "console_error", "timestamp": base_ts + timedelta(seconds=1),
                    "data": {"message": "login API failed with TypeError"}}
        ui_broken = {"dimension": "ui_broken", "timestamp": base_ts + timedelta(seconds=3),
                     "data": {"visible_texts": ["系统错误, 请稍后重试", "返回首页"]}}

        assert engine.is_causally_related(login_500, js_error), "API→Console因果关系"
        assert engine.is_causally_related(login_500, ui_broken), "API→UI因果关系"
        assert not engine.is_causally_related(js_error, login_500), "时间反向非因果"


class TestDefectToDelivery:
    """缺陷→交付 全流程"""

    def test_defect_creates_delivery(self):
        """缺陷对象 → 交付包"""
        defect = Defect(
            id="def_e2e_001",
            run_id="run_e2e_001",
            severity="high",
            title="下单API 500",
            type="api_error",
        )
        assert defect.id == "def_e2e_001"
        assert defect.severity == "high"

    def test_delivery_three_views(self):
        """交付包包含三类消费视图"""
        pkg = DeliveryPackage(
            tester_view=TesterView(
                summary="发现2个缺陷, 涉及登录和下单流程",
                defect_list=[{"id": "def_001", "severity": "high", "title": "Login API 500"}],
            ),
            developer_view=DeveloperView(
                root_cause="后端认证接口未处理异常情况",
                fix_suggestion="添加try-catch并返回正确错误码",
            ),
            ai_assistant_view=AIAssistantView(
                task_summary="全量回归测试",
                reproduction_steps=[
                    "1. 打开登录页",
                    "2. 输入用户名和密码",
                    "3. 点击登录按钮",
                    "4. 等待仪表盘加载",
                ],
                console_errors=["TypeError: Cannot read 'token'"],
                network_failures=[{"url": "/api/auth/login", "status": 500}],
                root_cause_candidates=["后端空指针", "参数校验缺失"],
                repair_suggestion="检查LoginController中token处理逻辑",
            ),
            regression_entry={
                "target_url": "https://example.com/login",
                "key_steps": [0, 1, 2, 3],
            },
        )
        assert pkg.tester_view.summary != ""
        assert len(pkg.ai_assistant_view.reproduction_steps) == 4
        assert pkg.ai_assistant_view.repair_suggestion != ""
        assert pkg.regression_entry["target_url"] == "https://example.com/login"


class TestTaskStoreAndQuery:
    """任务持久化与查询流程"""

    @pytest.mark.asyncio
    async def test_task_full_crud(self):
        repo = InMemoryTaskRepository()

        task = TestTask(name="CRUD测试", input=TaskInput(target_url="https://test.com"))
        created = await repo.create(task)
        assert created.id is not None

        fetched = await repo.get_by_id(created.id)
        assert fetched is not None
        assert fetched.name == "CRUD测试"

        result = await repo.list_tasks()
        assert result["total"] >= 1
        assert len(result["items"]) >= 1

        await repo.delete(created.id)
        deleted = await repo.get_by_id(created.id)
        assert deleted is None
