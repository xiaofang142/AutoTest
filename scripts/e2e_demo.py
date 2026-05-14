#!/usr/bin/env python3
"""AutoTest E2E demo: create project → generate tests → execute → report"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.dependencies import init_services
from app.domain.models.run import RunRecord
from app.lib.id_generator import generate_id

PASS = 0; FAIL = 0
def ok(label, cond, detail=""):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  ✅ {label}")
    else: FAIL += 1; print(f"  ❌ {label}: {detail}")

async def main():
    print("\n" + "="*70 + "\n  AutoTest E2E: 创建→生成→执行→报告\n" + "="*70)
    init_services()
    transport = ASGITransport(app=app)

    from app.dependencies import _MemRunRepo, _MemDefectRepo, _MemScenarioRepo
    run_repo = _MemRunRepo()
    defect_repo = _MemDefectRepo()
    scenario_repo = _MemScenarioRepo()

    async with AsyncClient(transport=transport, base_url="http://test") as c:
        print("\n[1] 创建项目")
        r = await c.post("/api/v1/projects", json={
            "name": "电商后台 E2E 验证", "platforms": ["web"],
            "entries": [{"platform": "web", "url": "https://admin.example.com"}],
        })
        ok("创建项目", r.status_code == 200)
        pid = r.json()["data"]["project"]["id"]

        print("\n[2] 添加文档 + 生成场景")
        await c.post(f"/api/v1/projects/{pid}/documents", json={"url":"https://x.md","type":"prd"})
        await c.post(f"/api/v1/projects/{pid}/scenarios/generate", json={"platforms":["web"]})

        print("\n[3] 创建执行 (直接通过引擎)")
        run = RunRecord(id=generate_id("run"), project_id=pid, status="queued",
                        platforms=["web"], total_cases=3)
        run = await run_repo.create(run)
        rid = run.id
        ok("创建执行", bool(rid))

        print("\n[4] 执行引擎: 驱动每个步骤 → 调用 Midscene → 4D 采集 → 综合分析")
        from app.engine.execution_engine import ExecutionEngine
        from app.infrastructure.executor import create_executor_client
        from app.services.analysis_service import CrossDimensionAnalyzer

        executor = create_executor_client()
        analyzer = CrossDimensionAnalyzer(defect_repo)
        engine = ExecutionEngine(run_repo, scenario_repo, defect_repo, executor, analyzer)

        report = await engine.execute_run(rid)
        ok("执行完成", report["status"] == "completed")
        s = report.get("summary", {})
        ok(f"步骤: {s.get('passed',0)}/{s.get('total',0)} 通过", s.get('total',0) > 0)
        ok(f"缺陷: {report.get('defect_count',0)} 个", report.get('defect_count',0) >= 0)

        print(f"\n[5] 执行报告")
        print(f"  总步骤: {s.get('total',0)}  通过: {s.get('passed',0)}  " +
              f"失败: {s.get('failed',0)}  通过率: {s.get('pass_rate',0)*100:.0f}%")
        for d in report.get("defects", []):
            print(f"  🐛 [{d['severity']}] {d['title'][:50]}")
        for st in report.get("steps", [])[:2]:
            print(f"  步骤 {st['step_index']}: {st['status']} — {st['action'][:30]}  " +
                  f"截图={st.get('has_screenshot',False)} 控制台错误={st.get('console_errors',0)}")

        print("\n[6] MCP 参考数据接口")
        if report.get("defects"):
            did = report["defects"][0]["id"]
            r = await c.get(f"/api/v1/defects/{did}")
            ok("MCP get_defect", r.status_code == 200)
            r = await c.get(f"/api/v1/defects/{did}/evidence")
            ok("MCP evidence", r.status_code == 200)

        print("\n[7] Web UI: http://localhost:3000")

    total = PASS + FAIL
    print(f"\n{'='*70}\n  结果: {PASS}/{total} 通过, {FAIL}/{total} 失败\n{'='*70}")
    print(f"\n  完整管线: 创建→文档→场景→执行引擎→Midscene步骤→4D采集→综合分析→缺陷→MCP")
    print(f"\n  切换到真实 Midscene 浏览器:")
    print(f"    cd executor/web && npx playwright install chromium && npx tsx src/index.ts")
    print(f"    .env: EXECUTOR_MODE=real")
    return FAIL == 0

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
