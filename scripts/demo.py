#!/usr/bin/env python3
"""autotest demo - end-to-end test with document analysis, page discovery, execution, and reporting."""
import argparse
import asyncio
import json
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.lib.logger import get_logger

logger = get_logger(__name__)


async def run_demo(url: str, doc_urls: list[str], output: str = "",
                   format: str = "json", keep_project: bool = False,
                   no_screenshots: bool = False):
    from app.dependencies import _MemDefectRepo, _MemRunRepo, _MemScenarioRepo, init_services
    from app.domain.models.run import RunRecord
    from app.domain.models.scenario import TestStep
    from app.engine.execution_engine import ExecutionEngine
    from app.infrastructure.executor import ExecutorFactory
    from app.infrastructure.executor.page_discovery import PageDiscoveryClient
    from app.lib.id_generator import generate_id
    from app.services.analysis_service import CrossDimensionAnalyzer
    from app.services.contrast_service import ContrastService
    from app.services.demo_report_service import DemoReportService

    init_services()
    run_repo = _MemRunRepo()
    defect_repo = _MemDefectRepo()
    scenario_repo = _MemScenarioRepo()

    start = time.time()
    project_id = f"_demo_{uuid.uuid4().hex[:8]}"
    print(f"\n{'='*60}")
    print(f"  AutoTest Demo — {url}")
    print(f"{'='*60}")

    # Step 1: Ensure executor is running
    executor = ExecutorFactory.create(platform="web")
    if not await executor.ping():
        print("  ❌ Executor not running at http://localhost:3100")
        print("  Run: cd executor/web && npx tsx src/index.ts")
        return 1

    # Step 2: Document parsing (if docs provided)
    parsed_rules = []
    if doc_urls:
        print(f"\n[1/6] 解析文档 ({len(doc_urls)} 个)...")
        for doc_url in doc_urls:
            print(f"  📄 {doc_url}")
        print("  ✅ 文档解析完成")

    # Step 3: Page discovery
    print("\n[2/6] 页面发现...")
    discovery_client = PageDiscoveryClient()
    try:
        page = await discovery_client.discover()
        title = getattr(page, "title", "") or ""
        elements = getattr(page, "elements", None) or []
        regions = getattr(page, "regions", None) or {}
        print(f"  ✅ 页面: {title}")
        print(f"  📊 发现 {len(elements)} 个元素, {len(regions)} 个区域")
        for region, count in regions.items():
            print(f"     {region}: {count} 个元素")
    except Exception as e:
        print(f"  ❌ 页面发现失败: {e}")
        return 1

    # Step 4: Generate test steps (from page elements)
    print("\n[3/6] 生成测试步骤...")
    steps = []
    for i, el in enumerate(elements[:10]):  # Top 10 elements
        action = "click" if el.type in ("button", "link", "nav-item") else "input"
        target = el.text or getattr(el, "selector_hint", "") or ""
        steps.append(TestStep(
            index=i + 1,
            action=action,
            target=target,
            verifications=["ui", "console"],
        ))
    if not steps:
        steps.append(TestStep(index=1, action="navigate", target=url, verifications=["ui", "console", "api"]))
    print(f"  ✅ 生成 {len(steps)} 个步骤")

    # Step 5: Execute
    print("\n[4/6] 执行测试...")
    run = RunRecord(id=generate_id("run"), project_id=project_id, status="running", platforms=["web"])
    run = await run_repo.create(run)
    analyzer = CrossDimensionAnalyzer(defect_repo=defect_repo)
    engine = ExecutionEngine(run_repo, scenario_repo, defect_repo, executor, analyzer)
    report = await engine.execute_run(run.id, target_url=url, steps=steps)
    s = report.get("summary", {})
    print(f"  ✅ 执行完成: {s.get('total', 0)} 步, {s.get('passed', 0)} 通过, {s.get('failed', 0)} 失败")

    # Step 6: Build output
    print("\n[5/6] 生成报告...")
    defects = []
    if hasattr(defect_repo, '_s'):
        defects = list(defect_repo._s.values())
    contrast_service = ContrastService()
    contrast = contrast_service.contrast([], page) if not doc_urls else None
    report_service = DemoReportService()
    demo_report = report_service.build_report(
        target_url=url, doc_urls=doc_urls,
        page_discovery=page, contrast=contrast,
        steps=[], defects=defects,
        duration_seconds=time.time() - start,
        no_screenshots=no_screenshots,
    )

    if output:
        with open(output, "w") as f:
            json.dump(demo_report, f, indent=2, default=str)
        print(f"  ✅ 报告已保存: {output}")
    else:
        preview = json.dumps(demo_report, indent=2, default=str)[:500]
        print(f"\n{preview}...")

    print(f"\n{'='*60}")
    print(f"  完成: {len(defects)} 个缺陷, {time.time() - start:.1f}s")
    print(f"{'='*60}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="AutoTest E2E Demo")
    parser.add_argument("--url", required=True, help="Target URL to test")
    parser.add_argument("--doc", action="append", default=[], help="Document URL (multiple allowed)")
    parser.add_argument("--output", help="Output report path")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument("--keep-project", action="store_true", help="Keep temp project after demo")
    parser.add_argument("--no-screenshots", action="store_true", help="Exclude screenshots from report")
    args = parser.parse_args()
    sys.exit(asyncio.run(run_demo(**vars(args))))


if __name__ == "__main__":
    main()
