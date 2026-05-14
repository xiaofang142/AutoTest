# End-to-End Demo — 实现计划

**Goal:** 实现 `autotest demo --url X --doc Y` 全链路闭环：文档解析+页面发现→角色×流程场景生成→Midscene执行→四维校验→因果链→结构化输出

**Architecture:** 4 Phase 增量推进。Phase 1 (页面发现器: TypeScript DOM提取+Python模型) → Phase 2 (对照验证+场景生成增强) → Phase 3 (CLI demo命令编排) → Phase 4 (报告聚合+MCP工具)

**Spec:** `docs/superpowers/specs/2026-05-14-end-to-end-demo-design.md`

---

## Chunk 1: Phase 1 — 页面发现器 (TypeScript + Python)

### Task 1.1: 新增 /agent/discover 端点 (TypeScript)

**Files:**
- Create: `executor/web/src/discovery/page-discoverer.ts`
- Modify: `executor/web/src/index.ts`
- Test: Manual via curl

- [ ] **Step 1: 创建 page-discoverer.ts**

```typescript
// executor/web/src/discovery/page-discoverer.ts
import { Page } from 'playwright';

export interface DiscoveredElement {
  type: 'button' | 'link' | 'input' | 'select' | 'textarea' | 'heading' | 'nav-item';
  text: string;
  selectorHint: string;
  isVisible: boolean;
  region: 'header' | 'nav' | 'main' | 'sidebar' | 'footer' | 'dialog' | 'unknown';
}

export interface PageDiscoveryResult {
  title: string;
  url: string;
  elements: DiscoveredElement[];
  regions: Record<string, number>;
  screenshot: string;
}

const MAX_ELEMENTS = 50;
const MAX_TEXT_ELEMENTS = 80;
const MAX_NAV_DEPTH = 3;

export async function discover(page: Page): Promise<PageDiscoveryResult> {
  const result = await page.evaluate((opts) => {
    const { maxEl, maxText, maxNav } = opts;
    const elements: any[] = [];
    const regions: Record<string, number> = {};

    function getRegion(el: Element): string {
      let parent = el.closest('header,nav,main,aside,footer,dialog,[role="banner"],[role="navigation"],[role="main"],[role="complementary"],[role="contentinfo"]');
      if (parent) {
        const tag = parent.tagName.toLowerCase();
        if (tag === 'header' || parent.getAttribute('role') === 'banner') return 'header';
        if (tag === 'nav' || parent.getAttribute('role') === 'navigation') return 'nav';
        if (tag === 'main' || parent.getAttribute('role') === 'main') return 'main';
        if (tag === 'aside' || parent.getAttribute('role') === 'complementary') return 'sidebar';
        if (tag === 'footer' || parent.getAttribute('role') === 'contentinfo') return 'footer';
        if (tag === 'dialog' || parent.getAttribute('role') === 'dialog') return 'dialog';
      }
      return 'unknown';
    }

    function addElement(el: Element, type: string, text: string) {
      if (elements.length >= maxEl) return;
      if (!text?.trim()) return;
      const region = getRegion(el);
      regions[region] = (regions[region] || 0) + 1;
      elements.push({
        type, text: text.trim().slice(0, 100),
        selectorHint: el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (el.className ? '.' + el.className.split(' ').join('.') : ''),
        isVisible: (el as HTMLElement).offsetParent !== null,
        region,
      });
    }

    // Buttons
    document.querySelectorAll('button, [role="button"]').forEach(el => addElement(el, 'button', (el as HTMLElement).innerText));
    // Links
    document.querySelectorAll('a[href]').forEach(el => addElement(el, 'link', (el as HTMLElement).innerText));
    // Inputs
    document.querySelectorAll('input:not([type="hidden"])').forEach(el => {
      const input = el as HTMLInputElement;
      addElement(el, 'input', input.placeholder || input.name || input.type);
    });
    // Selects
    document.querySelectorAll('select').forEach(el => addElement(el, 'select', (el as HTMLElement).innerText.slice(0, 50)));
    // Textareas
    document.querySelectorAll('textarea').forEach(el => addElement(el, 'textarea', (el as HTMLTextAreaElement).placeholder || ''));
    // Headings
    document.querySelectorAll('h1,h2,h3').forEach(el => addElement(el, 'heading', (el as HTMLElement).innerText));
    // Nav items (nav > li > a, nav > a)
    document.querySelectorAll('nav a, nav li, [role="navigation"] a, [role="navigation"] li').forEach(el => addElement(el, 'nav-item', (el as HTMLElement).innerText.slice(0, 80)));
    // Text content (limited)
    document.querySelectorAll('p,label,li,span').forEach(el => {
      if (elements.length >= maxEl + maxText) return;
      addElement(el, 'text', (el as HTMLElement).innerText.slice(0, 150));
    });

    return { elements, regions };
  }, { maxEl: MAX_ELEMENTS, maxText: MAX_TEXT_ELEMENTS, maxNav: MAX_NAV_DEPTH });

  const screenshot = await page.screenshot({ type: 'png', fullPage: true });
  return {
    title: await page.title(),
    url: page.url(),
    elements: result.elements,
    regions: result.regions,
    screenshot: `data:image/png;base64,${screenshot.toString('base64')}`,
  };
}
```

- [ ] **Step 2: 在 index.ts 注册端点**

Add to index.ts:
```typescript
import { discover } from './discovery/page-discoverer.js';

app.post('/agent/discover', async (req, res) => {
  try {
    const { page } = await ensureBrowser();
    const result = await discover(page);
    res.json({ success: true, ...result });
  } catch (e: any) {
    res.status(500).json({ success: false, message: e.message });
  }
});
```

- [ ] **Step 3: TypeScript 编译验证**

Run: `cd executor/web && npx tsc --noEmit`
Expected: No errors

### Task 1.2: 页面发现 Python 模型 + 客户端

**Files:**
- Create: `app/domain/models/discovery.py`
- Create: `app/infrastructure/executor/page_discovery.py`

- [ ] **Step 1: 创建 discovery.py 模型**

```python
from pydantic import BaseModel
from typing import Optional


class DiscoveredElement(BaseModel):
    type: str
    text: str
    selector_hint: str = ""
    is_visible: bool = True
    region: str = "unknown"


class PageDiscoveryResult(BaseModel):
    title: str = ""
    url: str = ""
    elements: list[DiscoveredElement] = []
    regions: dict[str, int] = {}
    screenshot: str = ""
```

- [ ] **Step 2: 创建 page_discovery.py 客户端**

```python
from app.domain.models.discovery import PageDiscoveryResult, DiscoveredElement
from app.config import settings


class PageDiscoveryClient:
    def __init__(self, executor_url: str = ""):
        self._url = (executor_url or settings.executor_web_url).rstrip("/")

    async def discover(self) -> PageDiscoveryResult:
        import httpx
        async with httpx.AsyncClient(timeout=30) as c:
            resp = await c.post(f"{self._url}/agent/discover", timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return PageDiscoveryResult(
                title=data.get("title", ""),
                url=data.get("url", ""),
                elements=[DiscoveredElement(**e) for e in data.get("elements", [])],
                regions=data.get("regions", {}),
                screenshot=data.get("screenshot", ""),
            )
```

---

## Chunk 2: Phase 2 — 对照验证 + 场景增强

### Task 2.1: 对照验证服务

**Files:**
- Create: `app/services/contrast_service.py`
- Modify: `app/engine/chain_builder.py`

- [ ] **Step 1: 创建 contrast_service.py**

```python
class ContrastService:
    def contrast(self, rules: list[BusinessRule], page: PageDiscoveryResult) -> ContrastReport:
        """文档规则 vs 页面元素对照。匹配策略: 关键词包含匹配。"""
        matched, missing, extra, conflict = [], [], [], []
        page_texts = set(e.text.lower() for e in page.elements if e.text)
        for rule in rules:
            rule_keywords = self._extract_keywords(rule.content)
            found = any(kw in page_texts for kw in rule_keywords)
            if found:
                matched.append(rule)
            else:
                missing.append(rule)
        page_types = set(e.type for e in page.elements)
        # ... detect extra and conflict
        return ContrastReport(matched=matched, missing=missing, extra=extra, conflict=conflict)

    def _extract_keywords(self, text: str) -> list[str]:
        import re
        return [w for w in re.split(r'[\s,，。.；;:：()（）]', text) if len(w) >= 2][:10]
```

- [ ] **Step 2: 增强 ChainBuilder**

Modify `_build_scenario()` to accept page elements and use real element text as step targets instead of abstract page names.

---

## Chunk 3: Phase 3 — CLI demo 命令

### Task 3.1: 创建 demo.py

**Files:**
- Create: `scripts/demo.py`
- Modify: `app/domain/models/run.py` (新增 uncertain status)
- Modify: `app/domain/models/scenario.py` (新增 expected_status)

- [ ] **Step 1: 创建 demo.py 主流程**

```python
#!/usr/bin/env python3
"""autotest demo --url X [--doc Y] [--output Z]"""
import argparse, asyncio, sys, os, json, uuid
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

async def run_demo(url: str, doc_urls: list[str], output: str, format: str, keep_project: bool, no_screenshots: bool):
    # 1. 创建临时项目
    # 2. 解析文档 (如有)
    # 3. 页面发现
    # 4. 对照验证
    # 5. 生成场景
    # 6. 执行 + 四维校验
    # 7. 因果链分析
    # 8. 输出报告
    ...

def main():
    parser = argparse.ArgumentParser(description="AutoTest E2E Demo")
    parser.add_argument("--url", required=True)
    parser.add_argument("--doc", action="append", default=[])
    parser.add_argument("--output")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument("--keep-project", action="store_true")
    parser.add_argument("--no-screenshots", action="store_true")
    args = parser.parse_args()
    asyncio.run(run_demo(**vars(args)))

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 模型变更**

Add `"uncertain"` to allowed values in `StepExecutionRecord.status` documentation.
Add `expected_status: str = "success"` to `TestScenario` model.

---

## Chunk 4: Phase 4 — 报告聚合 + MCP

### Task 4.1: DemoReportService + MCP 工具

**Files:**
- Create: `app/services/demo_report_service.py`
- Modify: `app/api/mcp/server.py`

- [ ] **Step 1: 创建 demo_report_service.py**

```python
class DemoReportService:
    def build_report(self, demo_run, scenarios, defects, page_discovery, contrast) -> dict:
        """聚合 demo 全量数据为结构化 JSON (符合 spec §6.1 结构)"""
        ...
```

- [ ] **Step 2: 修改 MCP server**

Add `get_demo_report(run_id: str, format: str = "compact") -> dict` tool.
