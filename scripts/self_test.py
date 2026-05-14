#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.dependencies import init_services
import asyncio

PASS = 0; FAIL = 0

def check(label, condition, detail=""):
    global PASS, FAIL
    if condition: PASS += 1; print(f"  ✅ {label}")
    else: FAIL += 1; print(f"  ❌ {label}: {detail}")

async def run():
    print("\n" + "="*60 + "\n  AutoTest SELF-TEST\n" + "="*60)
    init_services()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/health")
        check("Health returns 200", r.status_code == 200)
        check("Status ok", r.json().get("status") == "ok")

        r = await c.post("/api/v1/projects", json={"name": "自测", "platforms": ["web"]})
        check("Create project", r.status_code == 200 and r.json()["code"] == 0)
        pid = r.json()["data"]["project"]["id"]
        check("Project ID valid", bool(pid))

        r = await c.get(f"/api/v1/projects/{pid}")
        check("Get project", r.status_code == 200)

        r = await c.get("/api/v1/projects")
        check("List projects", r.status_code == 200 and any(p["id"]==pid for p in r.json()["data"]["items"]))

        r = await c.put(f"/api/v1/projects/{pid}", json={"name": "更新"})
        check("Update project", r.status_code == 200)

        r = await c.delete(f"/api/v1/projects/{pid}")
        check("Delete project", r.status_code == 204)

        r = await c.get(f"/api/v1/projects/{pid}")
        check("Verify deleted", r.status_code == 404)

        r = await c.post("/api/v1/projects", json={"name": "文档", "platforms": ["web"]})
        pid = r.json()["data"]["project"]["id"]

        r = await c.post(f"/api/v1/projects/{pid}/documents", json={"url": "https://x.md", "type": "prd"})
        check("Add document", r.status_code == 200)

        r = await c.get(f"/api/v1/projects/{pid}/documents")
        check("List documents", r.status_code == 200 and len(r.json()["data"]["items"]) > 0)

        r = await c.post("/api/v1/projects", json={"name": "执行", "platforms": ["web"]})
        pid = r.json()["data"]["project"]["id"]

        r = await c.post(f"/api/v1/projects/{pid}/runs", json={"platforms": ["web"]})
        check("Create run", r.status_code == 200)
        rid = r.json()["data"]["id"]
        check("Run ID valid", bool(rid))

        r = await c.get(f"/api/v1/runs/{rid}")
        check("Get run", r.status_code == 200)

        r = await c.get(f"/api/v1/runs/{rid}/progress")
        check("Run progress", r.status_code == 200)

        r = await c.post(f"/api/v1/runs/{rid}/cancel")
        check("Cancel run", r.status_code == 200)

        r = await c.get("/api/v1/projects/proj_nonexist")
        check("404 on missing", r.status_code == 404)

        r = await c.post("/api/v1/projects", json={"name": "", "platforms": ["web"]})
        check("422 on empty name", r.status_code == 422)

    total = PASS + FAIL
    print(f"\n{'='*60}\n  RESULT: {PASS}/{total} passed, {FAIL}/{total} failed\n{'='*60}")
    return FAIL == 0

if __name__ == "__main__":
    success = asyncio.run(run())
    sys.exit(0 if success else 1)
