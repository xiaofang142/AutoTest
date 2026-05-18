"""AutoTest 真实功能自测 — 测试系统自身API的逻辑正确性"""
import os, sys, json, asyncio
sys.path.insert(0, '/Users/xiaofang/Documents/www/docker/AutoTest')

os.environ['LITELLM_API_KEY'] = ''

from app.domain.models.task import (
    TestTask, TaskInput, TaskStatus, TaskMode, TaskStateMachine,
    DeliveryPackage, TesterView, DeveloperView, AIAssistantView
)
from app.domain.models.run import RunRecord, StepExecutionRecord
from app.domain.models.defect import Defect
from app.infrastructure.persistence.task_repo import InMemoryTaskRepository
from app.services.causal_engine import CausalRuleEngine
from app.lib.event_bus import EventBus, DomainEvent
from app.infrastructure.cache.ai_cache import AICache
from tests.mock_repos import MemRunRepo

passed = 0
failed = 0

def test(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name}: {detail}")

print("=" * 60)
print("AutoTest 真实功能自测")
print("=" * 60)

# ── 1. TestTask 生命周期 ──
print("\n--- 1. TestTask 生命周期 ---")
loop = asyncio.new_event_loop()
repo = InMemoryTaskRepository()
task = loop.run_until_complete(repo.create(TestTask(
    name="功能自测任务",
    input=TaskInput(target_url="http://localhost:3000",
                    code_dir="/Users/xiaofang/Documents/www/docker/AutoTest"),
    mode=TaskMode.QUICK,
)))
test("创建任务", task.id.startswith("task_"), f"id={task.id}")
test("初始状态为 draft", task.status == TaskStatus.DRAFT, f"status={task.status}")
test("URL 正确", task.input.target_url == "http://localhost:3000")
test("代码目录正确", task.input.code_dir == "/Users/xiaofang/Documents/www/docker/AutoTest")

# ── 2. 状态机 ──
print("\n--- 2. 状态机 ---")
test("draft→prechecking 合法", TaskStateMachine.can_transition(TaskStatus.DRAFT, TaskStatus.PRECHECKING))
test("draft→completed 非法", not TaskStateMachine.can_transition(TaskStatus.DRAFT, TaskStatus.COMPLETED))
test("completed 是终态", TaskStateMachine.is_terminal(TaskStatus.COMPLETED))
test("running 不是终态", not TaskStateMachine.is_terminal(TaskStatus.RUNNING))

loop.run_until_complete(repo.update_status(task.id, "prechecking", "prechecking"))
t = loop.run_until_complete(repo.get_by_id(task.id))
test("状态切换为 prechecking", t.status == "prechecking")

# ── 3. TaskRepository ──
print("\n--- 3. TaskRepository ---")
t2 = loop.run_until_complete(repo.create(TestTask(name="task2", input=TaskInput(target_url="https://x.com"))))
lst = loop.run_until_complete(repo.list_tasks())
test("列表返回所有任务", lst["total"] == 2, f"total={lst['total']}")
loop.run_until_complete(repo.delete(t2.id))
lst2 = loop.run_until_complete(repo.list_tasks())
test("删除后只剩1个", lst2["total"] == 1)

# ── 4. 因果引擎 ──
print("\n--- 4. 因果引擎 ---")
engine = CausalRuleEngine()
from datetime import datetime, timedelta
a = {"dimension": "api_error", "timestamp": datetime.now(), "data": {"url": "/api/login", "status": 500}}
b = {"dimension": "console_error", "timestamp": datetime.now() + timedelta(seconds=1), "data": {"message": "login failed with status 500"}}
c = {"dimension": "ui_broken", "timestamp": datetime.now() + timedelta(seconds=3), "data": {"visible_texts": ["系统错误"]}}
test("API→Console 因果关系", engine.is_causally_related(a, b))
test("API→UI 因果关系", engine.is_causally_related(a, c))
test("时间反向非因果", not engine.is_causally_related(c, a))

# ── 5. 交付包 ──
print("\n--- 5. 交付包 ---")
pkg = DeliveryPackage(
    tester_view=TesterView(summary="测试完成，发现2个缺陷"),
    developer_view=DeveloperView(root_cause="API 500"),
    ai_assistant_view=AIAssistantView(task_summary="功能测试", reproduction_steps=["步骤1", "步骤2"]),
    regression_entry={"target_url": "http://localhost:3000"},
)
test("交付包三类视图", pkg.tester_view.summary != "" and pkg.developer_view.root_cause != "" and len(pkg.ai_assistant_view.reproduction_steps) == 2)
test("回归入口", pkg.regression_entry["target_url"] == "http://localhost:3000")

# ── 6. EventBus ──
print("\n--- 6. EventBus ---")
bus = EventBus()
received = []
async def handler(e): received.append(e.payload)
bus.subscribe("test.event", handler)
loop.run_until_complete(bus.publish(DomainEvent("test.event", {"msg": "hello"})))
test("事件发布订阅", len(received) == 1 and received[0]["msg"] == "hello")

# ── 7. AICache ──
print("\n--- 7. AICache ---")
cache = AICache()
cache.set("gpt-4", "test prompt", "test response")
test("缓存写入读取", cache.get("gpt-4", "test prompt") == "test response")
test("不存在的key返回None", cache.get("gpt-4", "nope") is None)

# ── 8. RunRecord ──
print("\n--- 8. RunRecord ---")
run_repo = MemRunRepo()
run = RunRecord(id="run_test_001", project_id="proj_001", task_id=task.id, name="self-test-run")
loop.run_until_complete(run_repo.create(run))
found = loop.run_until_complete(run_repo.get_by_id("run_test_001"))
test("RunRecord创建", found is not None and found.task_id == task.id)

# ── 9. 缺陷严重度分类 ──
print("\n--- 9. 缺陷模型 ---")
d1 = Defect(id="def_001", run_id="run_1", severity="high", title="API 500")
d2 = Defect(id="def_002", run_id="run_1", severity="low", title="UI 错位")
test("高风险缺陷识别", d1.severity == "high" and d2.severity == "low")
test("缺陷属于运行", d1.run_id == "run_1" and d2.run_id == "run_1")

# ── 结果 ──
print(f"\n{'='*60}")
total = passed + failed
print(f"结果: {passed}/{total} 通过", end="")
if failed > 0:
    print(f", {failed} 失败")
else:
    print(" ✅ 全部通过!")
print(f"{'='*60}")

loop.close()
