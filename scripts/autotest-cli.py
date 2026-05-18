#!/usr/bin/env python3
"""AutoTest CLI - AI-driven UI testing from the command line.

Usage:
    autotest run --url https://staging.com
    autotest run --url https://staging.com --doc prd.md
    autotest run --url https://staging.com --output report.json
    autotest project list
    autotest health
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import click

from app.lib.logger import get_logger

logger = get_logger(__name__)


# ── helpers ──────────────────────────────────────────────────────────────────

def _ensure_project_root():
    """Make sure we can import app modules."""
    root = os.path.join(os.path.dirname(__file__), "..")
    if root not in sys.path:
        sys.path.insert(0, root)


def _format_duration(ms: int) -> str:
    if ms < 1000:
        return f"{ms}ms"
    return f"{ms / 1000:.1f}s"


def _status_icon(status: str) -> str:
    return "✅" if status == "passed" else "❌" if status == "failed" else "⚠️"


# ── run command ──────────────────────────────────────────────────────────────

@click.command()
@click.option("--url", "-u", required=True, help="Target URL to test")
@click.option("--doc", "-d", multiple=True, help="Document URL(s) for business rule extraction")
@click.option("--name", "-n", default="", help="Run name (default: auto-generated)")
@click.option("--output", "-o", default="", help="Path to save JSON report")
@click.option("--wait/--async", default=True, hidden=True)
def run(url, doc, name, output, wait):
    """一键执行：检测执行器 → 加载场景 → 执行 → 分析 → 报告。"""
    asyncio.run(_run_impl(url, list(doc), name, output))


async def _run_impl(url: str, doc_urls: list[str], name: str, output: str):
    from app.domain.models.run import RunRecord
    from app.domain.models.scenario import TestStep
    from app.engine.execution_engine import ExecutionEngine
    from app.infrastructure.executor import ensure_executor_running
    from app.infrastructure.executor.page_discovery import PageDiscoveryClient
    from app.infrastructure.executor.web_executor_client import WebExecutorClient
    from app.lib.id_generator import generate_id
    from app.services.analysis_service import CrossDimensionAnalyzer
    from tests.mock_repos import MemDefectRepo, MemRunRepo, MemScenarioRepo

    run_name = name or f"AutoTest — {url}"

    click.echo(f"\n{'='*56}")
    click.echo(f"  {run_name}")
    click.echo(f"{'='*56}")

    # 1. Ensure executor running
    click.echo("\n  [1/5] 执行器... ", nl=False)
    executor_ok = await ensure_executor_running()
    click.echo("✅" if executor_ok else "⚠️ 降级")

    executor = WebExecutorClient()

    # 2. Load scenarios
    click.echo("  [2/5] 加载场景...")

    if doc_urls:
        click.echo(f"        文档模式 ({len(doc_urls)} 个)")
        # For now, fall through to generic — doc parsing integration TBD
        steps = _generic_scenarios([], url)
    else:
        click.echo("        快速模式")
        try:
            disc = PageDiscoveryClient()
            # Navigate first via executor, then discover
            nav = await executor.navigate(url)
            if nav.success:
                discovered = await disc.discover()
                elements = [
                    {"text": e.text, "type": e.type}
                    for e in discovered.elements
                ]
                steps = _generic_scenarios(elements, url)
                click.echo(f"        发现 {len(elements)} 个元素, {len(steps)} 步")
            else:
                raise RuntimeError("Navigate failed")
        except Exception as e:
            click.echo(f"        页面发现失败 ({e}), 使用默认场景")
            steps = [
                TestStep(index=1, action="navigate", target=url,
                         verifications=["ui", "console", "api"]),
            ]

    # 3. Execute
    click.echo(f"  [3/5] 执行 ({len(steps)} 步)...")
    run_repo = MemRunRepo()
    defect_repo = MemDefectRepo()
    scenario_repo = MemScenarioRepo()
    analyzer = CrossDimensionAnalyzer(defect_repo=defect_repo)
    engine = ExecutionEngine(
        run_repo=run_repo, scenario_repo=scenario_repo,
        defect_repo=defect_repo, executor=executor, analyzer=analyzer,
    )

    run_id = generate_id("run")
    run = RunRecord(id=run_id, project_id="__cli__", name=run_name, platforms=["web"])
    await run_repo.create(run)

    result = await engine.execute_run(run_id, target_url=url, steps=steps)
    summary = result.get("summary", {})
    defects_list = result.get("defects", [])

    # 4. Report
    click.echo("\n  [4/5] 报告...")
    click.echo(f"\n{'='*56}")
    click.echo(f"  {run_name}")
    click.echo(f"{'='*56}")
    click.echo(f"  目标: {url}")
    click.echo(f"  状态: {result.get('status', '?')}  "
               f"({summary.get('total', 0)} 步, {len(defects_list)} 缺陷)")
    click.echo()
    for st in result.get("steps", []):
        icon = _status_icon(st["status"])
        dur = _format_duration(st.get("duration_ms", 0))
        click.echo(f"  [{st['step_index']}] {icon}  {st['action'][:45]:45s} {dur}")
    click.echo()
    if defects_list:
        click.echo(f"  缺陷 ({len(defects_list)}):")
        for d in defects_list:
            click.echo(f"    [{d['severity']:6s}] {d['title'][:60]}")
    else:
        click.echo("  缺陷: 0 🎉")
    click.echo(f"{'='*56}")

    # 5. Save report
    if output:
        report = {
            "name": run_name, "url": url, "status": result.get("status"),
            "summary": summary,
            "steps": result.get("steps", []),
            "defects": defects_list,
        }
        with open(output, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        click.echo(f"\n  报告: {output}")

    if defects_list:
        raise SystemExit(1)


def _generic_scenarios(elements: list[dict], target_url: str) -> list:
    """从页面发现结果生成通用测试步骤。"""
    from app.domain.models.scenario import TestStep

    steps = []
    steps.append(TestStep(
        index=1, action="navigate", target=target_url,
        verifications=["ui", "console", "api"],
    ))

    idx = 2
    seen = set()
    for el in elements[:10]:
        text = (el.get("text") or "").strip()
        el_type = el.get("type", "")
        if not text or text in seen:
            continue
        seen.add(text)

        if el_type == "button":
            steps.append(TestStep(
                index=idx, action="click", target=text,
                verifications=["ui", "console"],
            ))
            idx += 1
        elif el_type == "input" and idx <= 8:
            steps.append(TestStep(
                index=idx, action="type", target=text, value="test",
                verifications=["ui"],
            ))
            idx += 1

        if idx > 10:
            break

    if len(steps) == 1:
        steps.append(TestStep(
            index=2, action="analyze", target="page",
            verifications=["ui", "console", "api", "business"],
        ))

    return steps


# ── existing commands (project, doc, run, defect, health) ────────────────────
# These use ASGITransport to call the FastAPI app in-process.

@click.group()
def cli():
    """AutoTest — AI-driven automated UI testing framework."""
    pass


@cli.group()
def project():
    """Manage test projects."""
    pass


@project.command("create")
@click.option("--name", "-n", required=True)
@click.option("--url", "-u", required=True)
@click.option("--platform", "-p", default="web")
def project_create(name, url, platform):
    """Create a new test project."""
    asyncio.run(_api_call("POST", "/projects", {
        "name": name, "platforms": [platform],
        "entries": [{"platform": platform, "url": url}],
    }))


@project.command("list")
def project_list():
    """List all projects."""
    asyncio.run(_api_call("GET", "/projects"))


@project.command("get")
@click.argument("project_id")
def project_get(project_id):
    """Get project details."""
    asyncio.run(_api_call("GET", f"/projects/{project_id}"))


@project.command("delete")
@click.argument("project_id")
def project_delete(project_id):
    """Delete a project."""
    asyncio.run(_api_call("DELETE", f"/projects/{project_id}"))


@cli.group()
def doc():
    """Manage documents."""
    pass


@doc.command("add")
@click.argument("project_id")
@click.option("--url", "-u", required=True)
@click.option("--type", "-t", default="prd")
def doc_add(project_id, url, type):
    """Add a document to a project."""
    asyncio.run(_api_call("POST", f"/projects/{project_id}/documents",
                          {"url": url, "type": type}))


@doc.command("parse")
@click.argument("project_id")
def doc_parse(project_id):
    """Trigger document parsing."""
    asyncio.run(_api_call("POST", f"/projects/{project_id}/documents/parse",
                          {"document_ids": []}))


@cli.group()
def run_group():
    """Manage test runs."""
    pass


@run_group.command("get")
@click.argument("run_id")
def run_get(run_id):
    """Get run details."""
    asyncio.run(_api_call("GET", f"/runs/{run_id}"))


@run_group.command("cancel")
@click.argument("run_id")
def run_cancel(run_id):
    """Cancel a test run."""
    asyncio.run(_api_call("POST", f"/runs/{run_id}/cancel"))


@cli.group()
def defect():
    """Manage defects."""
    pass


@defect.command("list")
@click.argument("run_id")
def defect_list(run_id):
    """List defects in a run."""
    asyncio.run(_api_call("GET", f"/runs/{run_id}/defects"))


@defect.command("get")
@click.argument("defect_id")
def defect_get(defect_id):
    """Get defect details."""
    asyncio.run(_api_call("GET", f"/defects/{defect_id}"))


@cli.command("health")
def health():
    """Check API health."""
    asyncio.run(_api_call("GET", "/health"))


# ── transport helper ─────────────────────────────────────────────────────────

async def _api_call(method, path, data=None):
    import httpx

    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        if method == "GET":
            resp = await c.get(f"/api/v1{path}")
        elif method == "POST":
            resp = await c.post(f"/api/v1{path}", json=data or {})
        elif method == "DELETE":
            resp = await c.delete(f"/api/v1{path}")
        else:
            raise ValueError(f"Unknown method: {method}")

        if resp.status_code >= 400:
            click.echo(f"Error {resp.status_code}: {resp.text}", err=True)
            return

        body = resp.json()
        if isinstance(body, dict) and "data" in body:
            click.echo(json.dumps(body["data"], indent=2, ensure_ascii=False))
        else:
            click.echo(json.dumps(body, indent=2, ensure_ascii=False))


# ── register run command at top level ────────────────────────────────────────
cli.add_command(run)

if __name__ == "__main__":
    cli()
