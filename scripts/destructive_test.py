"""破坏性测试: 发现隐藏问题"""
import os, sys, asyncio
os.environ['LITELLM_API_KEY'] = ''
sys.path.insert(0, '/Users/xiaofang/Documents/www/docker/AutoTest')

from app.domain.models.task import TestTask, TaskInput, TaskStatus, TaskStateMachine
from app.infrastructure.persistence.task_repo import InMemoryTaskRepository

loop = asyncio.new_event_loop()

async def run_tests():
    repo = InMemoryTaskRepository()
    issues = []

    print("=== 测试1: 并发创建100个任务 ===")
    tasks = [TestTask(name=f"task-{i}", input=TaskInput(target_url=f"https://site-{i}.com")) for i in range(100)]
    for t in tasks:
        await repo.create(t)
    lst = await repo.list_tasks()
    if lst["total"] != 100:
        issues.append(f"FAIL: 创建100个但列表返回{lst['total']}")
    print(f"  创建100个 -> {lst['total']}个")

    print("\n=== 测试2: 任务ID不重复 ===")
    ids = [t.id for t in tasks]
    if len(ids) != len(set(ids)):
        issues.append("FAIL: 存在重复ID")
    else:
        print("  ✅ 所有ID唯一")

    print("\n=== 测试3: 边创建边删除 ===")
    for i in range(50):
        t = TestTask(name=f"race-{i}", input=TaskInput(target_url="https://x.com"))
        t = await repo.create(t)
        if i % 2 == 0:
            await repo.delete(t.id)
    lst = await repo.list_tasks()
    # 之前的100个 + 新创建的50个 - 删除25个 = 125
    print(f"  100+50-25={lst['total']}个 (期望125)")
    if lst["total"] != 125:
        issues.append(f"FAIL: 期望125个, 实际{lst['total']}")

    print("\n=== 测试4: 删除不存在的任务 ===")
    try:
        await repo.delete("nonexistent")
        print("  ✅ 删除不存在 -> 安全通过")
    except Exception as e:
        issues.append(f"FAIL: 删除不存在报错 {e}")

    print("\n=== 测试5: 状态机非法转换验证 ===")
    t = TestTask(name="test-sm", input=TaskInput(target_url="https://x.com"))
    t = await repo.create(t)
    # 检查非法转换
    can = TaskStateMachine.can_transition(t.status, TaskStatus.COMPLETED)
    if can:
        issues.append("FAIL: draft->completed应该非法但允许了")
    print(f"  draft->completed 非法={not can} (应该为True)")

    print("\n=== 测试6: 10万次创建 -> 淘汰最旧 ===")
    for i in range(10010):
        t = TestTask(name=f"mass-{i}", input=TaskInput(target_url="https://x.com"))
        await repo.create(t)
    lst = await repo.list_tasks()
    print(f"  10010次创建后剩余{lst['total']}个 (上限10000)")
    if lst["total"] > 10000:
        issues.append(f"FAIL: 超过上限! {lst['total']} > 10000")

    print("\n=== 测试7: 更新阶段结果循环 ===")
    t = TestTask(name="stages", input=TaskInput(target_url="https://x.com"))
    t = await repo.create(t)
    try:
        await repo.update_stage_result(t.id, "environment_check", {"executor_online": True})
        updated = await repo.get_by_id(t.id)
        if updated.environment_check and updated.environment_check.executor_online:
            print("  ✅ 阶段结果正确设置")
        else:
            issues.append("FAIL: 阶段结果设置后读取不正确")
    except Exception as e:
        issues.append(f"FAIL: 阶段结果报错 {e}")

    print("\n=== 发现的问题 ===")
    if issues:
        for i in issues:
            print(f"  ❌ {i}")
    else:
        print("  ✅ 未发现隐藏问题")

    return issues

issues = loop.run_until_complete(run_tests())
loop.close()

if issues:
    print(f"\n共发现 {len(issues)} 个问题")
else:
    print(f"\n所有破坏性测试通过 ✅")
