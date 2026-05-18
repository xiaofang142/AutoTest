"""AutoTest 全量测试 — 页面/交互/API/动态路由 全覆盖"""
import os, sys, json, asyncio, urllib.parse
sys.path.insert(0, '/Users/xiaofang/Documents/www/docker/AutoTest')
os.environ['LITELLM_API_KEY'] = ''
import httpx

BASE = "http://localhost:8765"
FE = "http://localhost:3000"
EXEC = "http://localhost:3100"

passed = 0
failed = 0
issues = []

def check(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        issues.append(f"{name}: {detail}")
        print(f"  ❌ {name}: {detail}")

async def nav(url):
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{EXEC}/agent/navigate", json={"url": url}, timeout=15)
        if r.status_code != 200:
            return {"success": False}
        return r.json()

async def clo(state):
    texts = state.get("pageState", {}).get("visibleTexts", [])
    return [t.strip() for t in texts]

async def main():
    global passed, failed

    # ────── PHASE 1: 前端页面全覆盖 ──────
    print("\n" + "="*60)
    print("PHASE 1: 前端页面全覆盖 (9页)")
    print("="*60)

    pages = {
        "/": "Dashboard",
        "/tasks": "TaskList",
        "/projects": "ProjectList",
        "/knowledge": "KnowledgeCenter",
        "/settings": "Settings",
        "/tasks/fake-001": "TaskDetail",
        "/projects/fake-001": "ProjectDetail",
        "/defects/fake-001": "DefectDetail",
        "/runs/fake-001": "RunDetail",
    }
    for path, name in pages.items():
        r = await nav(f"{FE}{path}")
        ok = r.get("success") and r.get("pageState", {}).get("visibleTexts", [])
        check(f"{name:20} {path:25} loads", ok)

    # ────── PHASE 2: 交互测试 ──────
    print("\n" + "="*60)
    print("PHASE 2: 交互测试 (点击/输入)")
    print("="*60)

    # 首页: 点击"一键开始"
    r = await nav(f"{FE}/")
    if r.get("success"):
        btn = next((t for t in await clo(r) if "一键开始" in t), None)
        check("首页存在[一键开始]按钮", bool(btn))

    # /settings: 检查LLM配置区
    r = await nav(f"{FE}/settings")
    if r.get("success"):
        texts = await clo(r)
        check("设置页含LLM配置", any("Key" in t or "模型" in t for t in texts))
        check("设置页含保存按钮", any("保存" in t for t in texts))

    # /tasks: 检查过滤和新建按钮
    r = await nav(f"{FE}/tasks")
    if r.get("success"):
        texts = await clo(r)
        check("任务页含新建按钮", any("新建" in t for t in texts))
        check("任务页含状态过滤", any("状态" in t or "全部" in t for t in texts))

    # /projects: 检查项目列表
    r = await nav(f"{FE}/projects")
    if r.get("success"):
        texts = await clo(r)
        check("项目页含创建按钮", any("新建" in t or "创建" in t for t in texts))

    # 导航到首页, 检查右上角状态
    r = await nav(f"{FE}/")
    if r.get("success"):
        texts = await clo(r)
        check("首页显示系统状态", any("系统正常" in t or "系统异常" in t for t in texts))
        check("首页显示近期任务区", any("近期任务" in t or "任务" in t for t in texts))

    # ────── PHASE 3: API全端点测试 ──────
    print("\n" + "="*60)
    print("PHASE 3: API 端点测试")
    print("="*60)

    async with httpx.AsyncClient(base_url=BASE, timeout=10) as c:

        # 3.1 健康检查
        r = await c.get("/health")
        check("GET /health", r.status_code == 200 and r.json().get("status") == "ok")

        # 3.2 项目CRUD
        r = await c.post("/api/v1/projects", json={"name":"t","platforms":["web"],"entries":[{"platform":"web","url":FE}]})
        check("POST /projects", r.status_code == 200)
        pid = r.json().get("data",{}).get("project",{}).get("id","")
        check("  project_id存在", bool(pid))

        r = await c.get("/api/v1/projects")
        check("GET /projects", r.status_code == 200 and r.json()["data"]["total"] > 0)

        r = await c.get(f"/api/v1/projects/{pid}")
        check(f"GET /projects/{pid}", r.status_code == 200)

        r = await c.put(f"/api/v1/projects/{pid}", json={"name":"updated"})
        check(f"PUT /projects/{pid}", r.status_code == 200)

        r = await c.delete(f"/api/v1/projects/{pid}")
        check(f"DELETE /projects/{pid}", r.status_code == 204)

        # 3.3 文档API
        r = await c.post(f"/api/v1/projects/{pid}/documents", json={"url":"https://x.com/prd","type":"prd"})
        check("POST /documents", r.status_code == 200)

        # 3.4 任务API
        CDIR = urllib.parse.quote("/Users/xiaofang/Documents/www/docker/AutoTest")
        TURL = urllib.parse.quote(FE)
        r = await c.post(f"/api/v1/tasks?name=api-full-test&target_url={TURL}&code_dir={CDIR}&mode=quick")
        check("POST /tasks (含代码分析)", r.status_code == 200)
        tid = r.json().get("data",{}).get("task",{}).get("id","")
        check("  task_id存在", bool(tid))

        r = await c.get(f"/api/v1/tasks/{tid}")
        check(f"GET /tasks/{tid}", r.status_code == 200)
        t = r.json().get("data",{}).get("task",{})
        check("  task含code_dir", t.get("input",{}).get("code_dir","").endswith("AutoTest"))

        r = await c.get("/api/v1/tasks")
        check("GET /tasks (列表)", r.status_code == 200 and r.json()["data"]["total"] > 0)

        r = await c.post(f"/api/v1/tasks/{tid}/start")
        check(f"POST /tasks/{tid}/start", r.status_code == 200 and r.json()["data"]["status"] == "prechecking")

        # 等待任务完成
        for i in range(15):
            await asyncio.sleep(4)
            r = await c.get(f"/api/v1/tasks/{tid}")
            s = r.json().get("data",{}).get("task",{}).get("status","")
            if s in ("completed","completed_with_defects","error","blocked"):
                break
        check(f"任务完成 status={s}", s in ("completed","completed_with_defects"))
        t = r.json().get("data",{}).get("task",{})
        check("  环境预检", bool(t.get("environment_check")))
        check("  理解结果", bool(t.get("understanding")))
        check("  蓝图", bool(t.get("blueprint")))
        check("  交付包", bool(t.get("delivery")))

        # 3.5 子资源API
        r = await c.get(f"/api/v1/tasks/{tid}/timeline")
        check(f"GET /tasks/{tid}/timeline", r.status_code == 200)
        r = await c.get(f"/api/v1/tasks/{tid}/defects")
        check(f"GET /tasks/{tid}/defects", r.status_code == 200)
        r = await c.get(f"/api/v1/tasks/{tid}/delivery")
        check(f"GET /tasks/{tid}/delivery", r.status_code in (200, 40003))
        r = await c.get(f"/api/v1/tasks/{tid}/environment-check")
        check(f"GET /tasks/{tid}/environment-check", r.status_code == 200)
        r = await c.get(f"/api/v1/tasks/{tid}/understanding")
        check(f"GET /tasks/{tid}/understanding", r.status_code == 200)
        r = await c.get(f"/api/v1/tasks/{tid}/blueprint")
        check(f"GET /tasks/{tid}/blueprint", r.status_code == 200)

        # 3.6 设置API
        r = await c.get("/api/v1/settings/llm")
        check("GET /settings/llm", r.status_code == 200)

        # 3.7 错误边界
        r = await c.get("/api/v1/tasks/nonexistent")
        check("查询不存在任务返回40001", r.status_code == 200 and r.json().get("code") == 40001)

    # ────── PHASE 4: 动态路由错误处理 ──────
    print("\n" + "="*60)
    print("PHASE 4: 前端错误处理验证")
    print("="*60)

    for path, expected in [
        ("/tasks/fake-001", "Task not found"),
        ("/nonexistent-route", None),
    ]:
        r = await nav(f"{FE}{path}")
        ok = r.get("success", False)
        check(f"{path:25} 页面不崩溃", ok)
        if ok and expected:
            texts = await clo(r)
            check(f"  显示正确错误: {expected}", any(expected in t for t in texts))

    # ────── 报告 ──────
    print("\n" + "="*60)
    total = passed + failed
    pct = round(passed / total * 100)
    print(f"结果: {passed}/{total} 通过 ({pct}%)")
    if issues:
        print(f"\n问题 ({len(issues)}):")
        for i in issues:
            print(f"  • {i}")
    else:
        print("\n✅ 全部通过，0个问题")
    print("="*60)

asyncio.run(main())
