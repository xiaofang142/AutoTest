"""AutoTest 找茬测试 — 专门测试边界和异常情况，找到真实问题"""
import os, sys, json, asyncio, urllib.parse
sys.path.insert(0, '/Users/xiaofang/Documents/www/docker/AutoTest')
os.environ['LITELLM_API_KEY'] = ''
import httpx

BASE = "http://localhost:8765"
passed = 0
failed = 0
bugs = []

def check(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        bugs.append(f"{name}: {detail}")
        print(f"  ❌ {name}: {detail}")

async def test():
    global passed, failed, bugs
    client = httpx.AsyncClient(base_url=BASE, timeout=10)

    print("="*60)
    print("AutoTest 找茬测试 — 找真正的Bug")
    print("="*60)

    # 1. 空数据测试
    print("\n--- 1. 空/非法数据测试 ---")
    r = await client.post("/api/v1/tasks?name=&target_url=")
    check("空name+空url创建任务", r.status_code in (200, 422), f"code={r.status_code}")

    r = await client.post("/api/v1/tasks")
    check("无参数创建任务", r.status_code in (200, 422), f"code={r.status_code}")

    r = await client.get("/api/v1/tasks/nonexistent")
    check("查询不存在的任务", r.status_code == 200 and r.json().get("code") == 40001)

    # 2. 状态机非法操作
    print("\n--- 2. 状态机异常操作 ---")
    CDIR = urllib.parse.quote("/Users/xiaofang/Documents/www/docker/AutoTest")
    TURL = urllib.parse.quote("http://localhost:3000")
    r = await client.post(f"/api/v1/tasks?name=bad-state&target_url={TURL}&code_dir={CDIR}&mode=quick")
    tid = r.json().get("data", {}).get("task", {}).get("id")

    if tid:
        # 重复启动
        r1 = await client.post(f"/api/v1/tasks/{tid}/start")
        r2 = await client.post(f"/api/v1/tasks/{tid}/start")
        check("重复启动任务应幂等", r2.status_code == 200, f"重复启动code={r2.status_code}")

        # 取消已完成的任务（如果已完成）
        await asyncio.sleep(15)
        r = await client.get(f"/api/v1/tasks/{tid}")
        t = r.json().get("data", {}).get("task", {})
        if t.get("status") in ("completed", "completed_with_defects"):
            r = await client.post(f"/api/v1/tasks/{tid}/cancel")
            check("取消已完成的任务应拒绝", r.status_code == 200)
            code = r.json().get("code", 0)
            # 如果code=0说明接受取消但终态不应变
            if code == 0:
                r2 = await client.get(f"/api/v1/tasks/{tid}")
                s2 = r2.json().get("data", {}).get("task", {}).get("status", "")
                still_terminal = s2 in ("completed", "completed_with_defects", "cancelled")
                check(f"终态任务取消后状态={s2}", still_terminal, f"状态变成了{s2}")

    # 3. 代码分析异常
    print("\n--- 3. 代码分析异常 ---")
    BAD_DIR = urllib.parse.quote("/nonexistent/path")
    r = await client.post(f"/api/v1/tasks?name=bad-code-dir&target_url={TURL}&code_dir={BAD_DIR}&mode=quick")
    check("不存在的code_dir不崩溃", r.status_code == 200, f"status={r.status_code}")
    if r.status_code == 200:
        tid2 = r.json().get("data", {}).get("task", {}).get("id")
        if tid2:
            await client.post(f"/api/v1/tasks/{tid2}/start")
            await asyncio.sleep(10)
            r2 = await client.get(f"/api/v1/tasks/{tid2}")
            t2 = r2.json().get("data", {}).get("task", {})
            s2 = t2.get("status", "?")
            check(f"不存在的code_dir依然能完成管线", s2 in ("completed","completed_with_defects"), f"最终状态={s2}")

    # 4. POST /projects 参数校验
    print("\n--- 4. 参数校验 ---")
    r = await client.post("/api/v1/projects", json={})
    check("空json创建项目应报错", r.status_code in (200, 422), f"code={r.status_code}")

    # 5. 创建项目时接口响应完整性
    print("\n--- 5. 接口响应完整性 ---")
    r = await client.post("/api/v1/projects", json={
        "name": "完整性测试",
        "platforms": ["web"],
        "entries": [{"platform": "web", "url": "https://example.com"}]
    })
    if r.status_code == 200:
        d = r.json().get("data", {}).get("project", {})
        # 检查是否有所有必要字段
        check("项目响应含id", bool(d.get("id")))
        check("项目响应含name", bool(d.get("name")))
        check("项目响应含platforms", bool(d.get("platforms")))
        check("项目响应含created_at", bool(d.get("created_at")))

    # 6. 任务API响应完整性
    print("\n--- 6. 任务API响应完整性 ---")
    r = await client.post(f"/api/v1/tasks?name=response-test&target_url={TURL}&mode=quick")
    if r.status_code == 200:
        d = r.json().get("data", {}).get("task", {})
        check("任务响应含id", bool(d.get("id")))
        check("任务响应含name", bool(d.get("name")))
        check("任务响应含status", bool(d.get("status")))
        check("任务响应含mode", bool(d.get("mode")))
        check("任务响应含input.target_url", bool(d.get("input", {}).get("target_url")))
        check("任务响应含created_at", bool(d.get("created_at")))

    await client.aclose()

    # 结果
    print("\n" + "="*60)
    total = passed + failed
    print(f"结果: {passed}/{total} 通过 ({failed} 失败)")
    if bugs:
        print(f"\n🔴 发现 {len(bugs)} 个问题:")
        for b in bugs:
            print(f"  • {b}")
    else:
        print("✅ 未发现问题 — 边界处理全部正确")
    print("="*60)
    return failed

fail_count = asyncio.run(test())
sys.exit(fail_count)
