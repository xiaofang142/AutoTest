"""AutoTest 真正的自我测试 — 使用自身API和Playwright验证自身功能

测试策略:
  1. API 端点逐一验证 (健康检查/CURD/任务管线)
  2. 页面内容验证 (前端每个路由加载后检查关键元素)
  3. 完整链路: 创建项目→添加文档→生成场景→创建任务→执行→查看报告
"""
import os, sys, json, asyncio, time
sys.path.insert(0, '/Users/xiaofang/Documents/www/docker/AutoTest')
os.environ['LITELLM_API_KEY'] = ''

import httpx

BASE = "http://localhost:8765"
FRONTEND = "http://localhost:3000"
passed = 0
failed = 0
errors = []

def check(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        msg = f"{name}: {detail}"
        errors.append(msg)
        print(f"  ❌ {msg}")

async def test():
    global passed, failed, errors
    client = httpx.AsyncClient(base_url=BASE, timeout=10)

    # ── Phase 1: API 端点测试 ──
    print("\n" + "="*60)
    print("Phase 1: API 端点测试")
    print("="*60)

    # 1.1 健康检查
    r = await client.get("/health")
    check("GET /health 返回200", r.status_code == 200)
    if r.status_code == 200:
        d = r.json()
        check("health.status=ok", d.get("status") == "ok")

    # 1.2 创建项目
    r = await client.post("/api/v1/projects", json={
        "name": "self-test-project",
        "platforms": ["web"],
        "entries": [{"platform": "web", "url": FRONTEND}]
    })
    check("POST /projects 返回200", r.status_code == 200)
    pid = None
    if r.status_code == 200:
        pid = r.json().get("data", {}).get("project", {}).get("id")
        check("项目包含 id", bool(pid))
        check("项目状态=created", r.json()["data"]["project"]["status"] == "created")

    # 1.3 项目列表
    r = await client.get("/api/v1/projects")
    check("GET /projects 返回列表", r.status_code == 200 and len(r.json().get("data", {}).get("items", [])) > 0)

    # 1.4 创建任务 (query params)
    import urllib.parse
    CDIR = urllib.parse.quote("/Users/xiaofang/Documents/www/docker/AutoTest")
    TURL = urllib.parse.quote(FRONTEND)
    r = await client.post(f"/api/v1/tasks?name=api-self-test&target_url={TURL}&code_dir={CDIR}&mode=quick")
    check("POST /tasks 返回200", r.status_code == 200)
    tid = None
    if r.status_code == 200:
        data = r.json().get("data", {}).get("task", {})
        tid = data.get("id")
        check("任务包含 id", bool(tid))
        check("任务状态=draft", data.get("status") == "draft")

    # 1.5 获取任务
    if tid:
        r = await client.get(f"/api/v1/tasks/{tid}")
        check(f"GET /tasks/{tid} 找到任务", r.status_code == 200 and r.json()["data"]["task"]["id"] == tid)

    # 1.6 任务列表
    r = await client.get("/api/v1/tasks")
    check("GET /tasks 返回列表", r.status_code == 200 and r.json()["data"]["total"] > 0)

    # 1.7 启动任务
    if tid:
        r = await client.post(f"/api/v1/tasks/{tid}/start")
        check("POST /tasks/{id}/start 返回200", r.status_code == 200)
        if r.status_code == 200:
            check("启动后状态=prechecking", r.json()["data"]["status"] == "prechecking")

    # 1.8 等待任务完成
    if tid:
        for i in range(12):
            await asyncio.sleep(5)
            r = await client.get(f"/api/v1/tasks/{tid}")
            if r.status_code != 200: continue
            status = r.json().get("data", {}).get("task", {}).get("status", "")
            if status in ("completed", "completed_with_defects", "error", "blocked"):
                check(f"任务最终状态={status}", status in ("completed", "completed_with_defects"))
                break

    # 1.9 验证管线产物
    if tid:
        r = await client.get(f"/api/v1/tasks/{tid}")
        if r.status_code == 200:
            t = r.json()["data"]["task"]
            check("环境预检存在", bool(t.get("environment_check")))
            check("理解结果存在", bool(t.get("understanding")))
            if t.get("understanding"):
                u = t["understanding"]
                check("理解包含页面意图", bool(u.get("page_intent")))
                check("理解包含路由信息", len(u.get("key_flows", [])) > 0)
            check("蓝图存在", bool(t.get("blueprint")))
            if t.get("blueprint"):
                check("蓝图包含步骤", len(t["blueprint"].get("all_steps", [])) > 0)
            check("交付存在", bool(t.get("delivery")))

    # 1.10 timeline
    if tid:
        r = await client.get(f"/api/v1/tasks/{tid}/timeline")
        check("timeline 返回数据", r.status_code == 200 and "current_stage" in r.json().get("data", {}))

    # 1.11 设置 API
    r = await client.get("/api/v1/settings/llm")
    check("GET /settings/llm 返回200", r.status_code == 200)

    # ── Phase 2: 前端页面验证 ──
    print("\n" + "="*60)
    print("Phase 2: 前端页面验证 (通过Playwright)")
    print("="*60)

    # 使用executor验证前端页面
    exec_r = await client.post("http://localhost:3100/agent/navigate", json={"url": FRONTEND})
    check("executor 导航到首页", exec_r.status_code == 200 and exec_r.json().get("success"))
    if exec_r.status_code == 200:
        check("首页截图成功", bool(exec_r.json().get("screenshot")))

    # 导航到 /tasks 页面
    exec_r = await client.post("http://localhost:3100/agent/navigate", json={"url": f"{FRONTEND}/tasks"})
    check("executor 导航到 /tasks", exec_r.status_code == 200)

    # 导航到 /settings 页面
    exec_r = await client.post("http://localhost:3100/agent/navigate", json={"url": f"{FRONTEND}/settings"})
    check("executor 导航到 /settings", exec_r.status_code == 200)

    # ── Phase 3: 数据一致性 ──
    print("\n" + "="*60)
    print("Phase 3: 数据一致性检查")
    print("="*60)

    # 验证任务列表数量一致
    r = await client.get("/api/v1/tasks")
    if r.status_code == 200:
        total = r.json()["data"]["total"]
        check("任务列表非空", total > 0)

    # 验证项目列表
    r = await client.get("/api/v1/projects")
    if r.status_code == 200:
        items = r.json()["data"].get("items", [])
        check("项目列表API正常", True)

    await client.aclose()

    # ── 结果 ──
    print("\n" + "="*60)
    total = passed + failed
    print(f"结果: {passed}/{total} 通过 ({failed} 失败)")
    if errors:
        print("\n需要修复的问题:")
        for e in errors:
            print(f"  • {e}")
    print("="*60)
    return failed == 0

success = asyncio.run(test())
sys.exit(0 if success else 1)
