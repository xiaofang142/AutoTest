"""E2E 业务流2: 开发者完整流程

模拟开发者操作:
  1. 创建项目 → 上传PRD文档
  2. 解析文档 → 提取业务规则
  3. 构建知识库 → 查看规则
  4. 生成测试场景
  5. 创建执行 → 执行测试
  6. 查看报告 → 查看缺陷
"""
import pytest
from unittest.mock import AsyncMock

from app.domain.models.project import Project, PlatformEntry
from app.domain.models.task import TestTask, TaskInput
from app.services.document_service import DocumentService
from app.services.knowledge_service import KnowledgeService
from app.services.scenario_service import ScenarioService
from app.engine.execution_engine import ExecutionEngine
from app.engine.task_orchestrator import TaskOrchestrator
from app.infrastructure.persistence.task_repo import InMemoryTaskRepository
from tests.mock_repos import (
    MemProjectRepo, MemDocRepo, MemKBRepo,
    MemScenarioRepo, MemRunRepo,
)


SAMPLE_PRD = """
# 电商后台 v2.1

## 用户登录
- 输入用户名密码登录
- 成功后跳转仪表盘
- 失败显示错误提示
- 30分钟无操作自动退出

## 商品管理
- 管理员可新增/编辑/删除商品
- 商品: 名称/价格/库存/分类
- 列表支持分页和搜索

## 订单管理
- 用户下单 → 待支付 → 已支付 → 已发货 → 已完成
"""


@pytest.fixture
def project_repo():
    return MemProjectRepo()


@pytest.fixture
def doc_repo():
    return MemDocRepo()


@pytest.fixture
def kb_repo():
    return MemKBRepo()


@pytest.fixture
def scenario_repo():
    return MemScenarioRepo()


class TestDeveloperE2EFlow:
    """开发者流程：项目→文档→知识→场景→执行→报告"""

    @pytest.mark.asyncio
    async def test_full_dev_workflow(self, project_repo, doc_repo, kb_repo, scenario_repo):
        """10步完整开发者工作流"""

        # 步骤1: 创建项目
        project = Project(
            name="电商后台管理系统",
            description="全量回归测试",
            platforms=["web"],
            entries=[PlatformEntry(platform="web", url="https://admin.example.com",
                                    viewport={"width": 1920, "height": 1080})],
        )
        project = await project_repo.create(project)
        assert project.id is not None
        assert project.status == "created"
        print(f"[PASS] 项目创建: {project.name} (id={project.id})")

        # 步骤2: 添加文档
        doc_svc = DocumentService(doc_repo, kb_repo=kb_repo)
        doc = await doc_svc.add_document(
            project.id, url="https://example.com/prd.md", doc_type="prd",
        )
        assert doc.id is not None
        assert doc.status == "pending"
        print(f"[PASS] 文档添加: type={doc.type}, status={doc.status}")

        # 步骤3: 创建知识库
        kb_svc = KnowledgeService(kb_repo)
        kb = await kb_svc.create_knowledge_base(project.id)
        assert kb is not None
        assert kb.project_id == project.id
        assert kb.version >= 1
        print(f"[PASS] 知识库创建: v{kb.version}, grade={kb.quality_grade}")

        # 步骤4: 验证知识库关联
        found_kb = await kb_svc.get_knowledge_base(project.id)
        assert found_kb is not None
        assert found_kb.id == kb.id
        print(f"[PASS] 知识库查询: project_id={found_kb.project_id}")

        # 步骤5: 生成测试场景
        s_svc = ScenarioService(scenario_repo, kb_repo=kb_repo)
        scenarios = await s_svc.generate_scenarios(project.id, platforms=["web"])
        assert len(scenarios) > 0
        print(f"[PASS] 场景生成: {len(scenarios)}个场景")

        # 步骤6: 验证场景内容
        for i, scenario in enumerate(scenarios):
            assert scenario.name is not None
            assert scenario.project_id == project.id
            for case in scenario.cases:
                for step in case.steps:
                    assert step.action, f"场景{i}步骤{step.index}缺少action"
        print(f"[PASS] 场景验证: 所有步骤可执行")

        # 步骤7: 创建自动测试任务
        task_repo = InMemoryTaskRepository()
        task = TestTask(
            name=f"自动回归-{project.name}",
            input=TaskInput(target_url="https://admin.example.com"),
        )
        task = await task_repo.create(task)
        assert task.id.startswith("task_")
        print(f"[PASS] 任务创建: {task.name}")

        # 步骤8: 执行测试
        mock_engine = AsyncMock(spec=ExecutionEngine)
        mock_engine.executor_ping.return_value = True
        mock_engine.execute_run.return_value = {
            "run_id": "run_dev_001",
            "status": "completed",
            "summary": {"total": 5, "passed": 5, "failed": 0, "defects": 1},
            "defects": [{"id": "def_001", "severity": "low", "title": "UI minor issue"}],
            "steps": [
                {"step_index": i, "action": f"step_{i}", "status": "passed", "duration_ms": 150}
                for i in range(5)
            ],
        }
        run_repo = MemRunRepo()
        orch = TaskOrchestrator(task_repo, mock_engine, run_repo)
        result = await orch.run_pipeline(task.id)
        assert result["status"] in ("completed", "completed_with_defects")
        print(f"[PASS] 执行管线: {result['status']}")

        # 步骤9: 验证交付
        updated = await task_repo.get_by_id(task.id)
        assert updated.delivery is not None
        assert updated.delivery_ready is True
        assert updated.delivery.ai_assistant_view.task_summary == task.name
        print(f"[PASS] 交付验证: 等级{updated.auto_level.value}")

        # 步骤10: 验证完整追溯
        assert updated.run_id != ""
        assert updated.environment_check is not None
        assert updated.understanding is not None
        assert updated.blueprint is not None
        print(f"[PASS] 全链路追溯: task→run→precheck→understand→blueprint→delivery")

        print("\n========== 开发者完整流程通过! ==========")
