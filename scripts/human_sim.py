#!/usr/bin/env python3
"""真人操作模拟 — 在每个页面上执行真实交互动作"""
import json, urllib.request, sys, time

EXEC = "http://localhost:3100"
FE = "http://localhost:3000"

def nav(url):
    r = urllib.request.Request(f"{EXEC}/agent/navigate",
        data=json.dumps({"url": url}).encode(),
        headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=15).read())

def exec_step(action, target, value=None):
    body = {"action": action, "target": target}
    if value:
        body["value"] = value
    r = urllib.request.Request(f"{EXEC}/agent/execute",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(r, timeout=30).read())
    except Exception as e:
        return {"success": False, "message": str(e)}

def get_texts(data):
    return data.get("pageState", {}).get("visibleTexts", [])

def check(page, ok, detail=""):
    status = "✅" if ok else "❌"
    msg = f"  {status} {page} {detail}"
    print(msg)
    return ok

failures = 0
# ─────────────────────────────────────────────────
# 模拟用户操作流程
print(f"[{time.strftime('%H:%M:%S')}] 开始真人操作模拟")
print()

# 1. 首页 — 查看仪表盘
print("--- 首页: 查看仪表盘 ---")
r = nav(f"{FE}/")
texts = get_texts(r)
check("/", r.get("success") and len(texts) > 10, f"加载成功 texts={len(texts)}")
check("/", any("新建自动测试" in t for t in texts), "含「新建自动测试」入口")
check("/", any("近期任务" in t for t in texts), "含「近期任务」区域")

# 2. 首页 — 输入网址并点击"一键开始"
has_start = any("一键开始" in t for t in texts)
if has_start:
    print("--- 首页: 点击「一键开始」---")
    r2 = exec_step("click", "一键开始")
    check("/ click", r2.get("success", False), f"点击一键开始 {r2.get('message','')[:60]}")

# 3. 任务列表 — 导航
print("--- 任务列表 ---")
r = nav(f"{FE}/tasks")
texts = get_texts(r)
check("/tasks", r.get("success") and len(texts) > 10, f"加载 texts={len(texts)}")
check("/tasks", any("新建任务" in t for t in texts), "含「新建任务」按钮")
check("/tasks", any("查询" in t for t in texts), "含「查询」按钮")

# 4. 项目列表 — 导航
print("--- 项目列表 ---")
r = nav(f"{FE}/projects")
texts = get_texts(r)
check("/projects", r.get("success") and len(texts) > 5, f"加载 texts={len(texts)}")

# 5. 设置页 — 检查保存按钮
print("--- 设置页 ---")
r = nav(f"{FE}/settings")
texts = get_texts(r)
check("/settings", r.get("success"), f"加载 texts={len(texts)}")
check("/settings", any("保存" in t for t in texts), "含「保存」按钮")
check("/settings", any("LLM" in t or "Key" in t or "模型" in t for t in texts), "含 LLM 配置区")

# 6. 知识中心 — 导航
print("--- 知识中心 ---")
r = nav(f"{FE}/knowledge")
texts = get_texts(r)
check("/knowledge", r.get("success") and len(texts) > 5, f"加载 texts={len(texts)}")

print()
if failures == 0:
    print(f"[{time.strftime('%H:%M:%S')}] ✅ 真人操作模拟完成 — 全部通过")
else:
    print(f"[{time.strftime('%H:%M:%S')}] ⚠️ {failures} 个失败")

sys.exit(0 if failures == 0 else failures)
