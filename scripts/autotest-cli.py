#!/usr/bin/env python3
"""AutoTest CLI - command line interface for the AutoTest API."""
import asyncio, json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import click
import httpx
from app.main import app


async def _call(method, path, data=None):
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
            click.echo(f"Error: {resp.text}", err=True)
            return None
        return resp.json().get("data")


@click.group()
def cli():
    """AutoTest - AI-driven automated UI testing framework."""
    pass


@cli.group()
def project():
    """Manage test projects."""
    pass


@project.command("create")
@click.option("--name", "-n", required=True, help="Project name")
@click.option("--url", "-u", required=True, help="Application URL")
@click.option("--platform", "-p", default="web", help="Platform (web/android/ios)")
def project_create(name, url, platform):
    """Create a new test project."""
    async def run():
        data = await _call("POST", "/projects", {
            "name": name, "platforms": [platform],
            "entries": [{"platform": platform, "url": url}],
        })
        if data:
            p = data["project"]
            click.echo(f"✅ Project created: {p['id']}")
            click.echo(f"   Name: {p['name']}")
            click.echo(f"   Status: {p['status']}")
    asyncio.run(run())


@project.command("list")
def project_list():
    """List all projects."""
    async def run():
        data = await _call("GET", "/projects")
        if data:
            for p in data["items"]:
                click.echo(f"  {p['id'][:16]}  {p['name']:20s} [{p['status']}]")
    asyncio.run(run())


@project.command("get")
@click.argument("project_id")
def project_get(project_id):
    """Get project details."""
    async def run():
        data = await _call("GET", f"/projects/{project_id}")
        if data:
            click.echo(json.dumps(data, indent=2, ensure_ascii=False))
    asyncio.run(run())


@project.command("delete")
@click.argument("project_id")
def project_delete(project_id):
    """Delete a project."""
    async def run():
        await _call("DELETE", f"/projects/{project_id}")
        click.echo(f"✅ Project {project_id} deleted")
    asyncio.run(run())


@cli.group()
def doc():
    """Manage documents."""
    pass


@doc.command("add")
@click.argument("project_id")
@click.option("--url", "-u", required=True, help="Document URL")
@click.option("--type", "-t", default="prd", help="Document type (prd/ui_spec/api_doc)")
def doc_add(project_id, url, type):
    """Add a document to a project."""
    async def run():
        data = await _call("POST", f"/projects/{project_id}/documents", {"url": url, "type": type})
        if data:
            click.echo(f"✅ Document added: {data['id']}")
    asyncio.run(run())


@doc.command("list")
@click.argument("project_id")
def doc_list(project_id):
    """List documents in a project."""
    async def run():
        data = await _call("GET", f"/projects/{project_id}/documents")
        if data:
            for d in data["items"]:
                click.echo(f"  {d['id'][:16]}  {d['type']:8s} {d['status']:12s} {d['url']}")
    asyncio.run(run())


@doc.command("parse")
@click.argument("project_id")
def doc_parse(project_id):
    """Trigger document parsing."""
    async def run():
        data = await _call("POST", f"/projects/{project_id}/documents/parse", {"document_ids": []})
        if data:
            click.echo(f"✅ Parse triggered: {data.get('task_id', '')}")
    asyncio.run(run())


@cli.group()
def run():
    """Manage test runs."""
    pass


@run.command("create")
@click.argument("project_id")
@click.option("--platform", "-p", default="web", help="Platform")
def run_create(project_id, platform):
    """Create and start a test run."""
    async def run_async():
        data = await _call("POST", f"/projects/{project_id}/runs", {"platforms": [platform]})
        if data:
            click.echo(f"✅ Run created: {data['id']}")
            click.echo(f"   Status: {data['status']}")
    asyncio.run(run_async())


@run.command("get")
@click.argument("run_id")
def run_get(run_id):
    """Get run details."""
    async def run_async():
        data = await _call("GET", f"/runs/{run_id}")
        if data:
            click.echo(f"Status: {data['status']}")
            click.echo(f"Total: {data['total_cases']}, Passed: {data['passed_count']}, Failed: {data['failed_count']}")
    asyncio.run(run_async())


@run.command("cancel")
@click.argument("run_id")
def run_cancel(run_id):
    """Cancel a test run."""
    async def run_async():
        await _call("POST", f"/runs/{run_id}/cancel")
        click.echo(f"✅ Run {run_id} cancelled")
    asyncio.run(run_async())


@cli.group()
def defect():
    """Manage defects."""
    pass


@defect.command("list")
@click.argument("run_id")
def defect_list(run_id):
    """List defects in a run."""
    async def run_async():
        data = await _call("GET", f"/runs/{run_id}/defects")
        if data:
            for d in data["items"]:
                click.echo(f"  {d['id'][:16]}  [{d['severity']:6s}] {d['title'][:50]}")
    asyncio.run(run_async())


@defect.command("get")
@click.argument("defect_id")
def defect_get(defect_id):
    """Get defect details."""
    async def run_async():
        data = await _call("GET", f"/defects/{defect_id}")
        if data:
            click.echo(json.dumps(data, indent=2, ensure_ascii=False))
    asyncio.run(run_async())


@cli.command("health")
def health():
    """Check API health."""
    async def run_async():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/health")
            click.echo(json.dumps(resp.json(), indent=2))
    asyncio.run(run_async())


if __name__ == "__main__":
    cli()
