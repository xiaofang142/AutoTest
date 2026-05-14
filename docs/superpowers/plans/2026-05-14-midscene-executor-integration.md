# Midscene Executor 全链路集成 — 实现计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 AutoTest 执行器从 Mock 模式切换为真实 Midscene.js PageAgent 驱动，实现浏览器自动化全链路闭环。

**Architecture:** 3层增量推进 — Layer 1 (Node.js 执行器内部强化: 模块拆分+RunManager+WS推送+CDP body捕获) → Layer 2 (Python 客户端增强: ExecutorFactory+WS客户端+Engine扩展现有ExecutionEngine) → Layer 3 (集成验证: Docker+集成测试+E2E Demo)。每层独立可验证。

**Tech Stack:** Node.js (Express + Playwright + Midscene.js + ws), Python (FastAPI + httpx + websockets), Docker

**Spec:** `docs/superpowers/specs/2026-05-14-midscene-executor-integration-design.md`

---

## Chunk 1: Layer 1 - Executor 代码拆分 + 共享类型

### Task 1.1: 创建 types.ts — 共享类型定义

**Files:**
- Create: `executor/web/src/types.ts`

- [ ] **Step 1: 创建 types.ts**

```typescript
// executor/web/src/types.ts

export interface RunState {
  id: string;
  status: 'created' | 'running' | 'completed' | 'failed' | 'cancelled';
  entry: { url: string; viewport?: { width: number; height: number } };
  cases: ExecutableCase[];
  currentCaseIndex: number;
  currentStepIndex: number;
  results: StepResult[];
  startedAt?: Date;
  completedAt?: Date;
  error?: string;
  stepTimeoutMs: number;
  runTimeoutMs: number;
  continueOnFailure: boolean;
}

export interface ExecutableCase {
  id: string;
  name: string;
  steps: ExecutableStep[];
}

export interface ExecutableStep {
  index: number;
  action: string;
  target: string;
  value?: string;
}

export interface StepResult {
  stepIndex: number;
  status: 'passed' | 'failed' | 'uncertain';
  action: string;
  screenshots: { before: string; after: string };
  consoleLogs: { errors: LogEntry[]; warnings: LogEntry[] };
  networkRequests: NetworkEntry[];
  pageState: PageStateSnapshot;
  durationMs: number;
  error?: string;
}

export interface LogEntry {
  level: string;
  message: string;
  source?: string;
  timestamp: number;
}

export interface NetworkEntry {
  type: 'request' | 'response';
  method: string;
  url: string;
  status?: number;
  requestBody?: string;
  responseBody?: string;
  timing?: Record<string, any>;
  timestamp: number;
}

export interface PageStateSnapshot {
  url: string;
  visibleTexts: string[];
  alerts: string[];
  perf: any[];
}

export interface RunEvent {
  type: 'step_start' | 'step_done' | 'step_failed' | 'run_completed' | 'run_error';
  run_id: string;
  case_id?: string;
  step_index?: number;
  action?: string;
  result?: StepResult;
  error?: string;
  screenshot?: string;
  status?: string;
  summary?: any;
}
```

- [ ] **Step 2: Verify file created**

Run: `ls -la executor/web/src/types.ts`

- [ ] **Step 3: Commit**

```bash
git add executor/web/src/types.ts
git commit -m "feat(executor): add shared types for run manager"
```

---

### Task 1.2: 创建 browser.ts — 浏览器管理

**Files:**
- Create: `executor/web/src/browser.ts`
- Modify: `executor/web/src/index.ts` (后续步骤)

- [ ] **Step 1: 创建 browser.ts**

```typescript
// executor/web/src/browser.ts
import { chromium, Browser, BrowserContext, Page, CDPSession } from 'playwright';
import { PageAgent } from '@midscene/web';

let browser: Browser | null = null;
let context: BrowserContext | null = null;
let page: Page | null = null;
let cdpSession: CDPSession | null = null;
let agent: PageAgent | null = null;

export async function ensureBrowser(viewport?: { width: number; height: number }) {
  if (browser) return { browser, context, page, cdpSession, agent };
  browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  context = await browser.newContext({
    viewport: viewport || { width: 1920, height: 1080 },
  });
  page = await context.newPage();
  cdpSession = await context.newCDPSession(page);
  agent = new PageAgent(page as any);
  console.log('[Browser] Launched with CDP + Midscene');
  return { browser, context, page, cdpSession, agent };
}

export function getPage() { return page; }
export function getCDP() { return cdpSession; }
export function getAgent() { return agent; }

export async function closeBrowser() {
  if (browser) await browser.close();
  browser = null; context = null; page = null; cdpSession = null; agent = null;
}
```

- [ ] **Step 2: Commit**

```bash
git add executor/web/src/browser.ts
git commit -m "feat(executor): browser management module"
```

---

### Task 1.3: 创建 capturer.ts — CDP 网络/控制台采集（含 body 捕获）

**Files:**
- Create: `executor/web/src/capturer.ts`

- [ ] **Step 1: 创建 capturer.ts**

```typescript
// executor/web/src/capturer.ts
import { Page, CDPSession } from 'playwright';
import { LogEntry, NetworkEntry } from './types';

const MAX_LOG_ENTRIES = 200;
const MAX_NETWORK_ENTRIES = 50;
const MAX_BODY_SIZE = 100 * 1024; // 100KB

export class Capturer {
  private logs: LogEntry[] = [];
  private network: NetworkEntry[] = [];
  private cdp: CDPSession | null = null;
  private pendingBodies: Map<string, { postData?: string }> = new Map();

  async enable(page: Page, cdp: CDPSession) {
    this.cdp = cdp;

    // Console capture
    page.on('console', (msg) => {
      if (this.logs.length >= MAX_LOG_ENTRIES) return;
      this.logs.push({
        level: msg.type(),
        message: msg.text(),
        source: msg.location()?.url || '',
        timestamp: Date.now(),
      });
    });

    // CDP Fetch API — 单次 enable 双 stage，共用处理器
    await cdp.send('Fetch.enable', {
      patterns: [
        { urlPattern: '*', requestStage: 'Request' },
        { urlPattern: '*', requestStage: 'Response' },
      ],
    });

    cdp.on('Fetch.requestPaused', async (params: any) => {
      if (params.requestStage === 'Request') {
        this.pendingBodies.set(params.requestId, {
          postData: params.request.postData || '',
        });
        if (this.network.length < MAX_NETWORK_ENTRIES) {
          this.network.push({
            type: 'request',
            method: params.request.method || 'GET',
            url: params.request.url || '',
            headers: params.request.headers || {},
            requestBody: params.request.postData?.substring(0, MAX_BODY_SIZE) || '',
            timestamp: Date.now(),
          });
        }
        await cdp.send('Fetch.continueRequest', { requestId: params.requestId });
        return;
      }

      if (params.requestStage === 'Response') {
        const status = params.responseStatusCode || 0;
        let responseBody = '';
        if (status >= 400) {
          try {
            const body = await cdp.send('Fetch.getResponseBody', { requestId: params.requestId });
            responseBody = body.body?.substring(0, MAX_BODY_SIZE) || '';
          } catch { /* response body not available */ }
        }
        if (this.network.length < MAX_NETWORK_ENTRIES) {
          this.network.push({
            type: 'response',
            method: params.request?.method || 'GET',
            url: params.request?.url || '',
            status,
            responseBody,
            timing: params.response?.timing || null,
            timestamp: Date.now(),
          });
        }
        await cdp.send('Fetch.continueResponse', { requestId: params.requestId });
      }
    });
  }

  clear() {
    this.logs = [];
    this.network = [];
    this.pendingBodies.clear();
  }

  getLogs() {
    return {
      errors: this.logs.filter(l => l.level === 'error' || l.level === 'exception').slice(0, 20),
      warnings: this.logs.filter(l => l.level === 'warning').slice(0, 20),
    };
  }

  getNetwork() {
    return this.network.filter(n => n.type === 'response')
      .slice(-30)
      .map(n => ({ method: n.method, url: n.url, status: n.status, timing: n.timing }));
  }

  getAllNetwork() { return this.network; }
}
```

- [ ] **Step 2: Commit**

```bash
git add executor/web/src/capturer.ts
git commit -m "feat(executor): CDP capturer with Fetch API body capture"
```

---

### Task 1.4: 创建 step-executor.ts — 单步执行器 + 降级链

**Files:**
- Create: `executor/web/src/step-executor.ts`

- [ ] **Step 1: 创建 step-executor.ts**

```typescript
// executor/web/src/step-executor.ts
import { Page } from 'playwright';
import { PageAgent } from '@midscene/web';
import { ExecutableStep, StepResult, PageStateSnapshot } from './types';

export class StepExecutor {
  constructor(private page: Page, private agent: PageAgent) {}

  async execute(step: ExecutableStep, timeoutMs: number = 30000): Promise<StepResult> {
    const startTime = Date.now();
    const before = await this.screenshot(false);

    let status: 'passed' | 'failed' | 'uncertain' = 'failed';
    let errorMsg = '';

    try {
      const executed = await this.executeWithFallback(step, timeoutMs);
      status = executed ? 'passed' : 'failed';
    } catch (e: any) {
      errorMsg = e.message;
    }

    await this.page.waitForTimeout(800);
    const after = status === 'passed' ? await this.screenshot(false) : await this.screenshot(true);
    const state = await this.pageState();

    return {
      stepIndex: step.index,
      status,
      action: `${step.action} ${step.target}`,
      screenshots: { before, after },
      consoleLogs: { errors: [], warnings: [] }, // populated by capturer
      networkRequests: [], // populated by capturer
      pageState: state,
      durationMs: Date.now() - startTime,
      error: errorMsg || undefined,
    };
  }

  private async executeWithFallback(step: ExecutableStep, timeoutMs: number): Promise<boolean> {
    // Level 0: Midscene AI Visual
    try {
      let instruction = `${step.action} ${step.target}`;
      if (step.value) instruction += ` with value "${step.value}"`;
      await this.agent.ai(instruction);
      return true;
    } catch {
      // Level 1: Playwright Role/Text
      try {
        const btn = this.page.getByRole('button', { name: step.target });
        if (await btn.count() > 0) { await btn.first().click({ timeout: 5000 }); return true; }
      } catch { /* continue */ }
      try {
        const txt = this.page.getByText(step.target, { exact: false });
        if (await txt.count() > 0) { await txt.first().click({ timeout: 5000 }); return true; }
      } catch { /* continue */ }
      // Level 2: DOM querySelectorAll + text match
      try {
        const found = await this.page.evaluate((target: string) => {
          for (const el of Array.from(document.querySelectorAll(
            'button,a,input,span,[role="button"],[role="link"],label,li'
          ))) {
            const h = el as HTMLElement;
            if (h.innerText?.includes(target) || (el as HTMLInputElement).placeholder?.includes(target)) {
              if (el instanceof HTMLInputElement && target !== h.innerText) {
                (el as HTMLInputElement).focus();
                (el as HTMLInputElement).value = '';
                return true;
              }
              h.click();
              return true;
            }
          }
          return false;
        }, step.target);
        if (found) return true;
      } catch { /* continue */ }
      // Level 3: XPath
      try {
        const xpathResult = await this.page.evaluate((target: string) => {
          const xpath = `//button[contains(text(),'${target}')] | //a[contains(text(),'${target}')] | //input[contains(@placeholder,'${target}')]`;
          const result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
          const node = result.singleNodeValue as HTMLElement;
          if (node) { node.click(); return true; }
          return false;
        }, step.target);
        if (xpathResult) return true;
      } catch { /* continue */ }
    }
    return false;
  }

  private async screenshot(full: boolean): Promise<string> {
    const buf = await this.page.screenshot({ fullPage: full, type: 'png' });
    return `data:image/png;base64,${buf.toString('base64')}`;
  }

  private async pageState(): Promise<PageStateSnapshot> {
    return {
      url: this.page.url(),
      visibleTexts: await this.page.evaluate(() =>
        Array.from(document.querySelectorAll('h1,h2,h3,p,button,span,a,label,li'))
          .map(e => (e as HTMLElement).innerText?.trim()).filter(Boolean).slice(0, 80)),
      alerts: await this.page.evaluate(() =>
        Array.from(document.querySelectorAll(
          "[class*='error'],[class*='alert'],[role='alert']"
        )).map(e => (e as HTMLElement).innerText?.trim()).filter(Boolean)),
      perf: [],
    };
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add executor/web/src/step-executor.ts
git commit -m "feat(executor): step executor with 4-level fallback chain"
```

---

### Task 1.5: 创建 reporter.ts — WebSocket 实时进度推送

**Files:**
- Create: `executor/web/src/reporter.ts`

- [ ] **Step 1: 创建 reporter.ts**

```typescript
// executor/web/src/reporter.ts
import { WebSocket, WebSocketServer } from 'ws';
import { IncomingMessage } from 'http';
import { Server } from 'http';
import { RunEvent } from './types';

export class Reporter {
  private clients: Map<string, Set<WebSocket>> = new Map();
  private wss: WebSocketServer | null = null;

  attach(server: Server) {
    this.wss = new WebSocketServer({ server });

    this.wss.on('connection', (ws: WebSocket, req: IncomingMessage) => {
      // URL pattern: /ws/run/{run_id}
      const match = req.url?.match(/\/ws\/run\/([^/]+)/);
      const runId = match?.[1];
      if (!runId) {
        ws.close(4000, 'Missing run_id in URL');
        return;
      }
      if (!this.clients.has(runId)) this.clients.set(runId, new Set());
      this.clients.get(runId)!.add(ws);

      ws.on('close', () => {
        this.clients.get(runId)?.delete(ws);
        if (this.clients.get(runId)?.size === 0) this.clients.delete(runId);
      });
    });
  }

  push(runId: string, event: RunEvent) {
    const clients = this.clients.get(runId);
    if (!clients) return;
    const msg = JSON.stringify({ ...event });
    for (const ws of clients) {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(msg);
      }
    }
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add executor/web/src/reporter.ts
git commit -m "feat(executor): WebSocket real-time progress reporter"
```

---

### Task 1.6: 创建 run-manager.ts — 多步骤运行编排

**Files:**
- Create: `executor/web/src/run-manager.ts`

- [ ] **Step 1: 创建 run-manager.ts**

```typescript
// executor/web/src/run-manager.ts
import { RunState, ExecutableCase, StepResult } from './types';
import { ensureBrowser, getPage, getAgent, closeBrowser } from './browser';
import { StepExecutor } from './step-executor';
import { Capturer } from './capturer';
import { Reporter } from './reporter';

export class RunManager {
  private runs: Map<string, RunState> = new Map();
  private reporter: Reporter;

  constructor(reporter: Reporter) {
    this.reporter = reporter;
  }

  create(runId: string, entry: { url: string; viewport?: { width: number; height: number } }, cases: ExecutableCase[]) {
    if (this.runs.has(runId)) throw new Error(`Run ${runId} already exists`);
    this.runs.set(runId, {
      id: runId,
      status: 'created',
      entry,
      cases,
      currentCaseIndex: 0,
      currentStepIndex: 0,
      results: [],
      stepTimeoutMs: 30000,
      runTimeoutMs: 1800000,
      continueOnFailure: false,
    });
    return { run_id: runId, status: 'created' };
  }

  async start(runId: string) {
    const state = this.runs.get(runId);
    if (!state) throw new Error(`Run ${runId} not found`);

    state.status = 'running';
    state.startedAt = new Date();

    const { page, agent, cdpSession } = await ensureBrowser(state.entry.viewport);
    const executor = new StepExecutor(page, agent);
    const capturer = new Capturer();
    await capturer.enable(page, cdpSession);

    // Global timeout
    const timeout = setTimeout(() => {
      state.status = 'failed';
      state.error = 'Run timeout exceeded';
      this.reporter.push(runId, { type: 'run_error', run_id: runId, error: 'Run timeout exceeded' });
    }, state.runTimeoutMs);

    try {
      // Navigate to entry URL first
      await page.goto(state.entry.url, { waitUntil: 'networkidle', timeout: 30000 });
      this.reporter.push(runId, { type: 'step_start', run_id: runId, case_id: '__navigate__', step_index: 0, action: `navigate to ${state.entry.url}` });

      for (const c of state.cases) {
        for (const step of c.steps) {
          state.currentCaseIndex = state.cases.indexOf(c);
          state.currentStepIndex = c.steps.indexOf(step);

          capturer.clear();
          this.reporter.push(runId, {
            type: 'step_start', run_id: runId, case_id: c.id,
            step_index: step.index, action: `${step.action} ${step.target}`,
          });

          const result = await executor.execute(step, state.stepTimeoutMs);
          // Attach captured data
          result.consoleLogs = capturer.getLogs();
          result.networkRequests = capturer.getNetwork();
          state.results.push(result);

          if (result.status === 'failed') {
            this.reporter.push(runId, {
              type: 'step_failed', run_id: runId, case_id: c.id,
              step_index: step.index, error: result.error,
              screenshot: result.screenshots.after,
            });
            if (!state.continueOnFailure) {
              state.status = 'failed';
              break;
            }
          } else {
            this.reporter.push(runId, {
              type: 'step_done', run_id: runId, case_id: c.id,
              step_index: step.index, result,
            });
          }
        }
        if (state.status === 'failed' && !state.continueOnFailure) break;
      }

      if (state.status === 'running') state.status = 'completed';
    } catch (e: any) {
      state.status = 'failed';
      state.error = e.message;
      this.reporter.push(runId, { type: 'run_error', run_id: runId, error: e.message });
    } finally {
      clearTimeout(timeout);
      state.completedAt = new Date();
      this.reporter.push(runId, {
        type: 'run_completed', run_id: runId,
        status: state.status,
        summary: { totalSteps: state.results.length, passed: state.results.filter(r => r.status === 'passed').length },
      });
    }

    return { run_id: runId, status: state.status };
  }

  cancel(runId: string) {
    const state = this.runs.get(runId);
    if (state && state.status === 'running') {
      state.status = 'cancelled';
      this.reporter.push(runId, { type: 'run_completed', run_id: runId, status: 'cancelled' });
    }
    return { success: true };
  }

  getProgress(runId: string) {
    const state = this.runs.get(runId);
    if (!state) return null;
    const total = state.cases.reduce((s, c) => s + c.steps.length, 0);
    const done = state.results.length;
    return {
      run_id: runId,
      status: state.status,
      progress: total > 0 ? done / total : 0,
      currentCase: state.currentCaseIndex,
      currentStep: state.currentStepIndex,
      results: state.results,
    };
  }

  getStatus(runId: string) {
    return this.runs.get(runId) || null;
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add executor/web/src/run-manager.ts
git commit -m "feat(executor): run manager with multi-step orchestration"
```

---

### Task 1.7: 重构 index.ts — 整合模块 + 新路由

**Files:**
- Modify: `executor/web/src/index.ts`

- [ ] **Step 1: 重写 index.ts**

```typescript
// executor/web/src/index.ts
import express from 'express';
import cors from 'cors';
import http from 'http';
import { ensureBrowser, getPage, closeBrowser } from './browser';
import { RunManager } from './run-manager';
import { Reporter } from './reporter';
import { Capturer } from './capturer';
import { StepExecutor } from './step-executor';

const app = express();
app.use(cors());
app.use(express.json({ limit: '50mb' }));

const server = http.createServer(app);
const reporter = new Reporter();
reporter.attach(server);
const runManager = new RunManager(reporter);

// ── Existing endpoints (kept for backward compatibility) ──

app.post('/agent/navigate', async (req, res) => {
  try {
    const { url } = req.body;
    if (!url) return res.status(400).json({ success: false, message: 'URL required' });
    const { page, agent, cdpSession } = await ensureBrowser();
    const capturer = new Capturer();
    await capturer.enable(page, cdpSession);
    await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
    const buf = await page.screenshot({ type: 'png' });
    res.json({ success: true, screenshot: `data:image/png;base64,${buf.toString('base64')}`, url: page.url() });
  } catch (e: any) { res.status(500).json({ success: false, message: e.message }); }
});

app.post('/agent/execute', async (req, res) => {
  try {
    const { action, target, value } = req.body;
    const { page, agent, cdpSession } = await ensureBrowser();
    const executor = new StepExecutor(page, agent);
    const result = await executor.execute({ index: 0, action, target, value });
    res.json({ success: result.status === 'passed', confidence: result.status === 'passed' ? 0.92 : 0, ...result });
  } catch (e: any) { res.status(500).json({ success: false, message: e.message }); }
});

app.post('/agent/screenshot', async (req, res) => {
  try {
    const page = getPage();
    if (!page) return res.json({ success: false, message: 'Browser not ready' });
    const full = req.body?.full === true;
    const buf = await page.screenshot({ fullPage: full, type: 'png' });
    res.json({ success: true, screenshot: `data:image/png;base64,${buf.toString('base64')}` });
  } catch (e: any) { res.status(500).json({ success: false, message: e.message }); }
});

// ── New Run Management endpoints ──

app.post('/run/create', (req, res) => {
  try {
    const { run_id, entry, cases } = req.body;
    if (!run_id || !entry) return res.status(400).json({ success: false, message: 'run_id and entry required' });
    const result = runManager.create(run_id, entry, cases || []);
    res.json(result);
  } catch (e: any) { res.status(400).json({ success: false, message: e.message }); }
});

app.post('/run/:id/start', async (req, res) => {
  try {
    const result = await runManager.start(req.params.id);
    res.json(result);
  } catch (e: any) { res.status(400).json({ success: false, message: e.message }); }
});

app.post('/run/:id/cancel', (req, res) => {
  try {
    const result = runManager.cancel(req.params.id);
    res.json(result);
  } catch (e: any) { res.status(400).json({ success: false, message: e.message }); }
});

app.get('/run/:id/progress', (req, res) => {
  const result = runManager.getProgress(req.params.id);
  if (!result) return res.status(404).json({ success: false, message: 'Run not found' });
  res.json(result);
});

app.get('/run/:id/status', (req, res) => {
  const result = runManager.getStatus(req.params.id);
  if (!result) return res.status(404).json({ success: false, message: 'Run not found' });
  res.json(result);
});

app.get('/health', (_req, res) => {
  const page = getPage();
  res.json({ status: 'ok', version: '0.2.0', browserReady: page !== null, pageUrl: page?.url() || null });
});

app.post('/cleanup', async (_req, res) => {
  await closeBrowser();
  res.json({ success: true });
});

const PORT = parseInt(process.env.PORT || '3100', 10);
server.listen(PORT, () => console.log(`[AutoTest Executor v0.2.0] :${PORT} CDP+Midscene+WS`));
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `cd executor/web && npx tsc --noEmit 2>&1`

- [ ] **Step 3: Commit**

```bash
git add executor/web/src/index.ts
git commit -m "feat(executor): refactor index.ts with run management routes and WS"
```

---

### Task 1.8: 更新 Dockerfile — 生产模式 + Playwright 依赖

**Files:**
- Modify: `executor/web/Dockerfile`

- [ ] **Step 1: 更新 Dockerfile**

```dockerfile
FROM node:20-slim

# Install Playwright system dependencies + Chromium
RUN npx playwright install chromium --with-deps

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npx tsc  # build to dist/

EXPOSE 3100
CMD ["npm", "start"]
```

- [ ] **Step 2: Commit**

```bash
git add executor/web/Dockerfile
git commit -m "fix(executor): production Dockerfile with playwright deps and tsc build"
```

---

## Chunk 1.5: Layer 1 验证

### Task 1.9: 验证 Executor 启动和新路由

- [ ] **Step 1: 安装依赖并启动**

Run: `cd executor/web && npm install`

- [ ] **Step 2: 确认无编译错误**

Run: `cd executor/web && npx tsc --noEmit`

Expected: No errors

- [ ] **Step 3: 提交全部 Layer 1 变更**

```bash
git add executor/web/
git commit -m "feat(executor): Layer 1 complete - module refactor, run manager, CDP capture, WS reporter"
```

---

## Chunk 2: Layer 2 - Python 客户端增强

### Task 2.1: 更新 ExecutorClient 接口 — 添加 mode 属性和新方法

**Files:**
- Modify: `app/interfaces/executor_client.py`

- [ ] **Step 1: 更新接口定义**

```python
# app/interfaces/executor_client.py
from abc import ABC, abstractmethod
from typing import Optional
from app.domain.models.run import StepExecutionRecord
from app.domain.models.scenario import TestStep


class ExecutorClient(ABC):
    @property
    @abstractmethod
    def mode(self) -> str:
        """返回 'real' 或 'mock'"""
        ...

    @abstractmethod
    async def ping(self) -> bool:
        """健康检查"""
        ...

    @abstractmethod
    async def execute_step(self, step: TestStep, context: Optional[dict] = None) -> StepExecutionRecord:
        ...

    @abstractmethod
    async def take_screenshot(self) -> str:
        ...

    @abstractmethod
    async def get_page_state(self) -> dict:
        ...
```

- [ ] **Step 2: Commit**

```bash
git add app/interfaces/executor_client.py
git commit -m "feat(api): add mode property and ping to ExecutorClient interface"
```

---

### Task 2.2: 更新 MockExecutorClient — 补齐所有新方法

**Files:**
- Modify: `app/infrastructure/executor/mock_executor_client.py`

- [ ] **Step 1: 更新 MockExecutorClient**

```python
# app/infrastructure/executor/mock_executor_client.py
from typing import Optional
from app.domain.models.run import StepExecutionRecord, Verifications, VerificationResult, PageState, ConsoleSnapshot, NetworkSnapshot
from app.domain.models.scenario import TestStep
from app.interfaces.executor_client import ExecutorClient
from app.lib.logger import get_logger

logger = get_logger(__name__)


class MockExecutorClient(ExecutorClient):
    """Mock executor for development/testing without real browser."""

    @property
    def mode(self) -> str:
        return "mock"

    async def ping(self) -> bool:
        return False

    async def execute_step(self, step: TestStep, context: Optional[dict] = None) -> StepExecutionRecord:
        logger.info(f"Mock execute: step={step.index} action={step.action}")
        return StepExecutionRecord(
            id=f"mock_{step.index}", run_id=(context or {}).get("run_id", ""),
            case_id=(context or {}).get("case_id", ""), step_index=step.index,
            action=step.action, platform="web", status="passed", duration_ms=100,
            page_state=PageState(current_url="https://example.com/mock"),
            verifications=Verifications(
                ui=VerificationResult(status="pass", dimension="ui", confidence=0.9),
                console=VerificationResult(status="pass", dimension="console", confidence=0.95),
                api=VerificationResult(status="pass", dimension="api", confidence=0.9),
                business=VerificationResult(status="uncertain", dimension="business", confidence=0.5),
            ),
        )

    async def take_screenshot(self) -> str:
        return "data:image/png;base64,mock"

    async def get_page_state(self) -> dict:
        return {"url": "https://example.com/mock"}
```

- [ ] **Step 2: Commit**

```bash
git add app/infrastructure/executor/mock_executor_client.py
git commit -m "feat(executor): implement mode property on MockExecutorClient"
```

---

### Task 2.3: 创建 ExecutorFactory — 替换废弃的 create_executor_client

**Files:**
- Modify: `app/infrastructure/executor/__init__.py`

- [ ] **Step 1: 更新 __init__.py — 添加 ExecutorFactory + 标记废弃**

```python
# app/infrastructure/executor/__init__.py
import warnings
from app.config import settings
from app.interfaces.executor_client import ExecutorClient
from app.infrastructure.executor.mock_executor_client import MockExecutorClient
from app.lib.logger import get_logger

logger = get_logger(__name__)


class ExecutorFactory:
    """统一的执行器工厂"""

    @staticmethod
    def create(platform: str = "web", mode: str | None = None) -> ExecutorClient:
        mode = mode or settings.executor_mode
        if mode == "mock":
            return MockExecutorClient()
        if platform == "web":
            from app.infrastructure.executor.web_executor_client import WebExecutorClient
            return WebExecutorClient(base_url=settings.executor_web_url)
        raise ValueError(f"Unsupported platform: {platform}")

    @staticmethod
    async def health_check(platform: str = "web") -> bool:
        """检查执行器是否在线"""
        client = ExecutorFactory.create(platform=platform, mode="real")
        try:
            return await client.ping()
        except Exception:
            logger.warning(f"Executor {platform} offline, will fallback to mock")
            return False


def create_executor_client() -> ExecutorClient:
    """@deprecated: Use ExecutorFactory.create() instead"""
    warnings.warn("create_executor_client() is deprecated, use ExecutorFactory.create()", DeprecationWarning, stacklevel=2)
    return ExecutorFactory.create()
```

- [ ] **Step 2: Commit**

```bash
git add app/infrastructure/executor/__init__.py
git commit -m "feat(executor): add ExecutorFactory with deprecation path"
```

---

### Task 2.4: 增强 WebExecutorClient — 添加所有新方法

**Files:**
- Modify: `app/infrastructure/executor/web_executor_client.py`

- [ ] **Step 1: 更新 WebExecutorClient**

```python
# app/infrastructure/executor/web_executor_client.py
import httpx
from typing import Optional
from app.domain.models.run import StepExecutionRecord, ConsoleSnapshot, ConsoleLogEntry, NetworkSnapshot, NetworkEntry, PageState, Verifications, VerificationResult
from app.domain.models.scenario import TestStep, TestCase
from app.interfaces.executor_client import ExecutorClient
from app.config import settings
from app.lib.logger import get_logger
from dataclasses import dataclass

logger = get_logger(__name__)


@dataclass
class NavigateResult:
    success: bool
    screenshot: str
    current_url: str


class WebExecutorClient(ExecutorClient):
    def __init__(self, base_url: str = ""):
        self.base_url = base_url or settings.executor_web_url
        self._client = httpx.AsyncClient(timeout=60)
        self._mode = "real"

    @property
    def mode(self) -> str:
        return self._mode

    async def ping(self) -> bool:
        try:
            resp = await self._client.get(f"{self.base_url}/health", timeout=10)
            return resp.json().get("status") == "ok"
        except Exception:
            return False

    async def navigate(self, url: str, viewport: Optional[dict] = None) -> NavigateResult:
        resp = await self._client.post(f"{self.base_url}/agent/navigate", json={"url": url}, timeout=30)
        data = resp.json()
        return NavigateResult(
            success=data.get("success", False),
            screenshot=data.get("screenshot", ""),
            current_url=data.get("url", ""),
        )

    async def create_run(self, run_id: str, entry: dict, cases: list[TestCase]) -> dict:
        """转换为 ExecutableCase 格式后发送给执行器"""
        executable_cases = []
        for c in cases:
            steps = []
            for s in (c.steps or []):
                steps.append({"index": s.index, "action": s.action, "target": s.target, "value": s.value})
            executable_cases.append({"id": c.id, "name": c.name, "steps": steps})
        resp = await self._client.post(f"{self.base_url}/run/create", json={
            "run_id": run_id,
            "entry": entry,
            "cases": executable_cases,
        }, timeout=30)
        return resp.json()

    async def start_run(self, run_id: str) -> dict:
        resp = await self._client.post(f"{self.base_url}/run/{run_id}/start", timeout=10)
        return resp.json()

    async def get_run_progress(self, run_id: str) -> dict:
        resp = await self._client.get(f"{self.base_url}/run/{run_id}/progress", timeout=10)
        return resp.json()

    async def cancel_run(self, run_id: str) -> None:
        await self._client.post(f"{self.base_url}/run/{run_id}/cancel", timeout=10)

    async def execute_step(self, step: TestStep, context: Optional[dict] = None) -> StepExecutionRecord:
        logger.info(f"Executor: {step.action} {step.target}")
        try:
            resp = await self._client.post(f"{self.base_url}/agent/execute", json={
                "action": step.action, "target": step.target, "value": step.value,
            }, timeout=60)
            resp.raise_for_status()
            result = resp.json()
        except Exception as e:
            return StepExecutionRecord(id=f"err_{step.index}", run_id=(context or {}).get("run_id", ""),
                case_id=(context or {}).get("case_id", ""), step_index=step.index,
                action=step.action, status="failed", error=str(e))

        console = result.get("consoleLogs") or {}
        ps = result.get("pageState") or {}
        return StepExecutionRecord(
            id=f"step_{step.index}", run_id=(context or {}).get("run_id", ""),
            case_id=(context or {}).get("case_id", ""), step_index=step.index,
            action=step.action, platform="web",
            status="passed" if result.get("success") else "failed",
            screenshots={"before": result.get("screenshotBefore", result.get("screenshots", {}).get("before", "")),
                         "after": result.get("screenshotAfter", result.get("screenshots", {}).get("after", ""))},
            console_snapshot=ConsoleSnapshot(
                errors=[ConsoleLogEntry(level="error", message=e.get("message", "")) for e in console.get("errors", [])],
                warnings=[ConsoleLogEntry(level="warning", message=e.get("message", "")) for e in console.get("warnings", [])]),
            network_snapshot=NetworkSnapshot(requests=[
                NetworkEntry(method=n.get("method", "GET"), url=n.get("url", ""), status=n.get("status", 0))
                for n in (result.get("networkRequests") or [])
            ], failed=[]),
            page_state=PageState(current_url=ps.get("url", ""),
                visible_text_elements=ps.get("visibleTexts", []),
                active_alerts=ps.get("alerts", [])),
            verifications=Verifications(
                ui=VerificationResult(status="pending", dimension="ui")),
        )

    async def take_screenshot(self) -> str:
        resp = await self._client.post(f"{self.base_url}/agent/screenshot", timeout=30)
        return resp.json().get("screenshot", "")

    async def get_page_state(self) -> dict:
        return {}
```

- [ ] **Step 2: Commit**

```bash
git add app/infrastructure/executor/web_executor_client.py
git commit -m "feat(executor): add run management methods to WebExecutorClient"
```

---

### Task 2.5: 创建 WS 客户端 — ExecutorWSClient

**Files:**
- Create: `app/infrastructure/executor/ws_client.py`

- [ ] **Step 1: 创建 ws_client.py**

```python
# app/infrastructure/executor/ws_client.py
import json
import asyncio
import logging
from collections import defaultdict
from typing import Callable, Any

import websockets

logger = logging.getLogger(__name__)


class ExecutorWSClient:
    """接收执行器 WebSocket 实时进度"""

    def __init__(self, executor_url: str, run_id: str):
        ws_url = executor_url.replace("http://", "ws://").replace("https://", "wss://")
        self.ws_url = f"{ws_url}/ws/run/{run_id}"
        self._callbacks: dict[str, list[Callable]] = defaultdict(list)
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._reconnect_count = 0
        self._max_reconnect = 5

    def on(self, event: str, callback: Callable):
        self._callbacks[event].append(callback)

    async def connect(self):
        """建立连接并开始监听（在关闭时抛异常以触发重连）"""
        self._ws = await websockets.connect(self.ws_url)
        try:
            async for msg in self._ws:
                event = json.loads(msg)
                event_type = event.get("type", "")
                for cb in self._callbacks.get(event_type, []):
                    await cb(event)
        finally:
            if self._reconnect_count < self._max_reconnect:
                raise websockets.exceptions.ConnectionClosed(
                    0, "Connection closed, reconnecting..."
                )

    async def disconnect(self):
        if self._ws:
            await self._ws.close()

    async def connect_with_reconnect(self):
        """自动重连版（指数退避: 2s, 4s, 8s, 16s, 32s）"""
        while self._reconnect_count <= self._max_reconnect:
            try:
                await self.connect()
                return
            except websockets.exceptions.ConnectionClosed:
                self._reconnect_count += 1
                if self._reconnect_count > self._max_reconnect:
                    logger.error(f"WS reconnection exhausted for {self.ws_url}")
                    raise
                delay = 2 ** self._reconnect_count
                logger.warning(f"WS disconnected, reconnecting in {delay}s "
                              f"(attempt {self._reconnect_count}/{self._max_reconnect})")
                await asyncio.sleep(delay)
```

- [ ] **Step 2: Commit**

```bash
git add app/infrastructure/executor/ws_client.py
git commit -m "feat(executor): WebSocket client with auto-reconnect"
```

---

### Task 2.6: 改造 ExecutionEngine — 支持 WS 驱动模式

**Files:**
- Read: `app/engine/execution_engine.py` (先理解现有结构)
- Modify: `app/engine/execution_engine.py`

- [ ] **Step 1: 读取现有 execution_engine.py**

Run: `cat app/engine/execution_engine.py`

- [ ] **Step 2: 扩展现有 ExecutionEngine（根据现有代码结构适配，添加 WS 驱动路径）**

核心变更：
1. `execute_run` 入口先获取项目入口配置
2. 创建执行器（通过 ExecutorFactory）
3. 健康检查 + 自动降级
4. 真实模式 → WS 驱动；Mock 模式 → 本地串行
5. 执行完毕后复用现有缺陷分析逻辑

- [ ] **Step 3: Commit**

```bash
git add app/engine/execution_engine.py
git commit -m "feat(engine): extend ExecutionEngine with WS-driven real executor path"
```

---

### Task 2.7: 更新 RunService — 改为委托 ExecutionEngine

- [ ] **Step 1: 读取现有 run_service.py**

Run: `cat app/services/run_service.py`

- [ ] **Step 2: 改造 create_and_execute_run 方法**

- [ ] **Step 3: 更新 e2e_demo.py 引用 ExecutorFactory**

- [ ] **Step 4: Commit**

```bash
git add app/services/run_service.py scripts/e2e_demo.py
git commit -m "feat(engine): delegate run execution to ExecutionEngine"
```

---

### Task 2.8: 更新 docker-compose.yml — 加入 executor-web 服务

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: 添加 executor-web 服务**

```yaml
  executor-web:
    build:
      context: ./executor/web
      dockerfile: Dockerfile
    ports: ["3100:3100"]
    environment:
      PORT: 3100
      OPENAI_API_KEY: ${LITELLM_API_KEY}
    restart: unless-stopped
```

- [ ] **Step 2: Commit**

```bash
git add docker-compose.yml
git commit -m "feat(deploy): add executor-web service to docker-compose"
```

---

## Chunk 3: Layer 3 - 集成测试

### Task 3.1: 编写集成测试 — test_executor_web.py

**Files:**
- Create/Modify: `tests/integration/test_executor_web.py`

- [ ] **Step 1: 编写集成测试**

```python
# tests/integration/test_executor_web.py
"""Layer 1: Executor 连通性测试（需要运行中的 executor）"""

import pytest
import httpx

EXECUTOR_URL = "http://localhost:3100"


@pytest.mark.integration
class TestExecutorWebConnectivity:
    """执行器连通性测试"""

    async def test_health(self):
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{EXECUTOR_URL}/health", timeout=10)
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"
            assert "version" in data

    async def test_navigate(self):
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{EXECUTOR_URL}/agent/navigate", json={
                "url": "https://example.com",
            }, timeout=30)
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert "example" in data.get("url", "")

    async def test_create_and_run(self):
        async with httpx.AsyncClient() as client:
            # Create run
            create_resp = await client.post(f"{EXECUTOR_URL}/run/create", json={
                "run_id": "test_integration_001",
                "entry": {"url": "https://example.com", "viewport": {"width": 1920, "height": 1080}},
                "cases": [{"id": "c1", "name": "Navigate", "steps": [
                    {"index": 1, "action": "navigate", "target": "https://example.com"}
                ]}],
            }, timeout=30)
            assert create_resp.status_code == 200

            # Start run
            start_resp = await client.post(f"{EXECUTOR_URL}/run/test_integration_001/start", timeout=60)
            assert start_resp.status_code == 200

            # Poll for completion
            for _ in range(10):
                prog = await client.get(f"{EXECUTOR_URL}/run/test_integration_001/progress", timeout=10)
                status = prog.json().get("status")
                if status in ("completed", "failed"):
                    break
                await asyncio.sleep(2)

            assert status == "completed"


@pytest.mark.integration
class TestWebExecutorClient:
    """WebExecutorClient 集成测试（需要运行中的 executor）"""

    @pytest.fixture
    def client(self):
        from app.infrastructure.executor.web_executor_client import WebExecutorClient
        return WebExecutorClient(base_url=EXECUTOR_URL)

    async def test_ping(self, client):
        assert await client.ping() is True

    async def test_navigate(self, client):
        result = await client.navigate("https://example.com")
        assert result.success is True
        assert "example" in result.current_url
```


- [ ] **Step 2: 更新 conftest.py — 添加 executor_url fixture**

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_executor_web.py
git commit -m "test: integration tests for executor connectivity and run management"
```

---

### Task 3.2: 更新 e2e_demo.py — 支持 --mode real

**Files:**
- Modify: `scripts/e2e_demo.py`

- [ ] **Step 1: 读取现有 e2e_demo.py**

Run: `cat scripts/e2e_demo.py`

- [ ] **Step 2: 添加 --mode 参数，支持 real 模式**

- [ ] **Step 3: Commit**

```bash
git add scripts/e2e_demo.py
git commit -m "feat(cli): add --mode real to e2e_demo for executor integration"
```

---

## 质量门禁清单

### Layer 1 验收
- [ ] `cd executor/web && npx tsc --noEmit` — 无编译错误
- [ ] `curl http://localhost:3100/health` — 返回 `{"status":"ok"}`
- [ ] `curl -X POST http://localhost:3100/run/create ...` — 创建成功
- [ ] `curl -X POST http://localhost:3100/run/<id>/start` — 执行完成

### Layer 2 验收
- [ ] `pytest tests/integration/test_executor_web.py -v` — 集成测试通过
- [ ] `pytest tests/ -x --ignore=tests/e2e` — 单元测试不受影响

### Layer 3 验收
- [ ] `docker compose build executor-web && docker compose up -d executor-web` — 容器启动成功
- [ ] `python scripts/e2e_demo.py --mode mock` — Mock 模式正常
- [ ] `python scripts/e2e_demo.py --url https://example.com --mode real` — Real 模式正常
