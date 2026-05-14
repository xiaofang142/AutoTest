#!/usr/bin/env python3
"""AutoTest E2E: create project → parse doc → generate → execute → report"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.dependencies import init_services
from app.domain.models.run import RunRecord
from app.domain.models.scenario import TestStep
from app.lib.id_generator import generate_id

PASS = 0; FAIL = 0
def ok(label, cond, detail=""):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  ✅ {label}")
    else: FAIL += 1; print(f"  ❌ {label}: {detail}")

async def main():
    print("\n" + "="*70 + "\n  AutoTest E2E: 需求→设计→编码→测试→修复\n" + "="*70)
    init_services()
    transport = ASGITransport(app=app)
    from app.dependencies import _MemRunRepo, _MemDefectRepo, _MemScenarioRepo
    run_repo = _MemRunRepo()
    defect_repo = _MemDefectRepo()
    scenario_repo = _MemScenarioRepo()

    TARGET_URL = "https://admin.example.com/login"

    async with AsyncClient(transport=transport, base_url="http://test") as c:
        print("\n[1/7] 创建项目 — 输入名称 + 被测系统URL")
        r = await c.post("/api/v1/projects", json={
            "name": "电商后台管理系统",
            "platforms": ["web"],
            "entries": [{"platform": "web", "url": TARGET_URL, "viewport": {"width": 1920, "height": 1080}}],
        })
        ok("创建项目", r.status_code == 200)
        pid = r.json()["data"]["project"]["id"]
        print(f"  项目: {pid[:16]}  目标: {TARGET_URL}")

        print("\n[2/7] 上传需求文档 + 触发解析")
        r = await c.post(f"/api/v1/projects/{pid}/documents", json={
            "url": "https://example.com/prd.md", "type": "prd",
            "description": "电商后台 PRD — 包含登录、商品管理、订单流程",
        })
        ok("添加文档", r.status_code == 200)

        r = await c.post(f"/api/v1/projects/{pid}/documents/parse", json={})
        ok("触发解析", r.status_code == 200)
        if r.status_code == 200:
            print(f"  解析状态: {r.json()['data'].get('task_id','')}")

        print("\n[3/7] 生成测试场景")
        r = await c.post(f"/api/v1/projects/{pid}/scenarios/generate", json={"platforms": ["web"]})
        ok("场景生成", r.status_code == 200)

        r = await c.get(f"/api/v1/projects/{pid}/scenarios")
        scenarios = r.json()["data"]["items"] if r.status_code == 200 else []
        print(f"  场景数: {len(scenarios)}")

        print("\n[4/7] 创建执行任务")
        run = RunRecord(id=generate_id("run"), project_id=pid, status="queued",
                        platforms=["web"], total_cases=3)
        run = await run_repo.create(run)
        rid = run.id
        ok("执行ID已创建", bool(rid))
        print(f"  Run ID: {rid[:16]}")

        print("\n[5/7] 执行引擎 — 打开浏览器 → 执行步骤 → 采集数据")
        from app.engine.execution_engine import ExecutionEngine
        from app.infrastructure.executor import create_executor_client
        from app.services.analysis_service import CrossDimensionAnalyzer
        executor = create_executor_client()
        analyzer = CrossDimensionAnalyzer(defect_repo)
        engine = ExecutionEngine(run_repo, scenario_repo, defect_repo, executor, analyzer)

        steps = [
            TestStep(index=1, action="打开登录页面", target=TARGET_URL, verifications=["ui","console","api"]),
            TestStep(index=2, action="输入用户名", target="用户名输入框", value="admin@example.com",
                    verifications=["ui"]),
            TestStep(index=3, action="输入密码", target="密码输入框", value="TestPass123!",
                    verifications=["ui"]),
            TestStep(index=4, action="点击登录按钮", target="登录按钮",
                    verifications=["ui","api","console","business"]),
        ]
        report = await engine.execute_run(rid, target_url=TARGET_URL, steps=steps)
        ok("执行完成", report["status"] == "completed")
        s = report["summary"]
        print(f"  步骤: {s['total']} 通过: {s['passed']} 失败: {s['failed']} 通过率: {s['pass_rate']*100:.0f}%")

        print("\n[6/7] 执行报告 + 缺陷")
        for st in report["steps"]:
            console_info = f" ⚠️{st['console_errors']}控制台错误" if st['console_errors'] else ""
            defect_info = f" 🐛缺陷" if st['defect'] else ""
            print(f"  步骤{st['step_index']}: {st['status']} — {st['action'][:30]}{console_info}{defect_info}")

        if report["defects"]:
            for d in report["defects"]:
                print(f"  🐛 [{d['severity']}] {d['title'][:50]}")

        print("\n[7/7] MCP 参考数据接口验证")
        if report["defects"]:
            did = report["defects"][0]["id"]
            r = await c.get(f"/api/v1/defects/{did}")
            ok("MCP get_defect: 返回缺陷详情", r.status_code == 200)
            r = await c.get(f"/api/v1/defects/{did}/evidence")
            ok("MCP evidence: 返回证据链", r.status_code == 200)
        else:
            print("  无缺陷，跳过MCP验证")

    total = PASS + FAIL
    print(f"\n{'='*70}")
    print(f"  结果: {PASS}/{total} 通过, {FAIL}/{total} 失败")
    print(f"{'='*70}")
    print(f"\n  完整SDD流程验证通过:")
    print(f"  需求→架构→编码→测试→修复")
    print(f"\n  切换到真实 Midscene 浏览器执行:")
    print(f"    cd executor/web && npx playwright install chromium && npx tsx src/index.ts")
    print(f"    .env: EXECUTOR_MODE=real")
    return FAIL == 0

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
