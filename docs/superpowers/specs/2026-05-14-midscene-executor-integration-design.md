# AutoTest — Midscene 执行器全链路集成设计文档

> 版本: 1.1 | 日期: 2026-05-14 | 状态: 已审核修订
> 审核修复: M1-M6（运行时崩溃）, S1-S4（关键架构问题）, S7-S8（验证/Docker）, N5-N6（超时保护）
> 审核者: Code Reviewer
>
> 变更摘要:
> - [M1] `c.to_dict()` → Pydantic v2 `model_dump()`, TestCase→ExecutableCase 转换逻辑明确化
> - [M2] ExecutorClient ABC 新增 `mode` 抽象属性 + MockExecutorClient 补齐所有新方法
> - [M3] WS 回调注册修复为 lambda 延迟求值 + 内联 async handler 定义
> - [M4] 拆除并行执行路径，改为扩展现有 ExecutionEngine
> - [M5] CDP Fetch.enable 合并为单次调用双 stage pattern + 单处理器模式
> - [M6] 通过 project_repo.get_by_id() 获取入口配置，不走不存在的 run.project.entries
> - [S1] 执行流程改为 ExecutionEngine 类方法 + 完整的生命周期管理
> - [S2] MockExecutorClient 实现所有新方法 (ping/create_run/start_run/get_run_progress/cancel_run)
> - [S3] WS 重连逻辑重写为 connect_with_reconnect() + 抛出 ConnectionClosed 触发重连
> - [S4] create_executor_client() 标记废弃 + 迁移方案
> - [S7] Layer 1 增加 curl 验收命令示例
> - [S8] Dockerfile CMD 改为 "npm start"
> - [N5/N6] RunState 增加 stepTimeoutMs / runTimeoutMs / continueOnFailure 字段
> 基于需求规格说明书 v2.0，架构设计文档 ADD v1.0

---

## 1. 概述

### 1.1 目标

将当前 Mock 模式的执行器切换为真实 Midscene.js PageAgent 驱动，实现**输入被测 URL → AI 视觉定位 → 浏览器执行 → CDP 数据采集 → 四维校验 → 缺陷报告**的全链路闭环。

### 1.2 当前状态

| 组件 | 完成度 | 关键缺口 |
|------|--------|----------|
| Node.js 执行器 | ~70% | 有 CDP、Midscene Agent、截图、console 捕获、DOM fallback |
| Python WebExecutorClient | ~50% | 缺少 navigate 调用、网络详情结构映射、WS 实时推送 |
| 执行器编排 | ~30% | 无 ExecutorFactory、无多步骤运行编排/重试/取消 |
| Docker 集成 | ~20% | executor 服务在 docker-compose 中缺失，浏览器安装未配置 |

### 1.3 三层推进策略

```
Layer 1: Executor 内部强化 (Node.js)      ← 坚实底座
Layer 2: Python 客户端增强                ← 无缝对接
Layer 3: 全流程验证                        ← 可运行验证
```

每层都是可用增量，Layer 1 完成即可通过 curl 验证（详见下文验收步骤），Layer 2 完成后可通过 CLI 全流程验证。

**Layer 1 验收步骤（curl）**：
```bash
# 1. 健康检查
curl http://localhost:3100/health
# → {"status":"ok","browserReady":false,...}

# 2. 创建运行
curl -X POST http://localhost:3100/run/create \
  -H "Content-Type: application/json" \
  -d '{"run_id":"run_001","entry":{"url":"https://example.com"},"cases":[{"id":"c1","name":"测试","steps":[{"index":1,"action":"navigate","target":"https://example.com"}]}]}'
# → {"run_id":"run_001","status":"created"}

# 3. 启动执行（注意此时浏览器会启动并运行步骤）
curl -X POST http://localhost:3100/run/run_001/start
# → {"run_id":"run_001","status":"running"}

# 4. 轮询进度
curl http://localhost:3100/run/run_001/progress
# → {"run_id":"run_001","status":"completed","results":[...]}
```

---

## 2. Layer 1: Executor 内部强化 (Node.js)

### 2.1 代码结构重构

将当前单文件 `src/index.ts` 拆分为职责清晰的模块：

```
executor/web/src/
  ├── index.ts          ← Express 路由注册 + HTTP 服务启动
  ├── browser.ts        ← Playwright 浏览器管理（单例/池/生命周期）
  ├── run-manager.ts    ← RunManager（多步运行编排）
  ├── step-executor.ts  ← 单步执行器（AI→降级→采集）
  ├── capturer.ts       ← CDP 网络/控制台采集（含 body 捕获）
  ├── reporter.ts       ← WebSocket 实时进度推送
  └── types.ts          ← 共享类型定义
```

### 2.2 状态管理器 (RunManager)

**职责**：管理多步骤测试运行的全生命周期。

```typescript
// types.ts
interface RunState {
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
  stepTimeoutMs: number;   // 单步超时（默认 30000ms）
  runTimeoutMs: number;     // 运行全局超时（默认 1800000ms = 30min）
  continueOnFailure: boolean; // 失败后是否继续执行后续步骤
}

interface ExecutableCase {
  id: string;
  name: string;
  steps: ExecutableStep[];
}

interface ExecutableStep {
  index: number;
  action: string;    // click | input | navigate | scroll | wait
  target: string;    // 自然语言目标描述
  value?: string;    // 输入值
}

interface StepResult {
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
```

**API 端点**：

```
POST /run/create
  Body: { run_id, entry: { url, viewport }, cases: [...] }
  → { run_id, status: "created" }

POST /run/{run_id}/start
  → { run_id, status: "running" }  (异步，通过 WS 推结果)

POST /run/{run_id}/cancel
  → { success: true }

GET  /run/{run_id}/progress
  → { run_id, status, progress: 0.45, currentCase, currentStep, results: [...] }

GET  /run/{run_id}/status
  → 完整 RunState
```

**执行流程**：

```
RunManager.execute(run_id):
  1. 获取 run state (含 timeout 配置)
  2. 创建全局超时定时器（runTimeoutMs）
  3. 更新 status = running
  4. 导航到 entry.url（被测系统入口）
  5. for each case in cases:
       for each step in case.steps:
         6. 通过 WS 推送 step_start
         7. 调用 StepExecutor.execute(step, stepTimeoutMs)
         8. 保存结果到 results[]
         9. 通过 WS 推送 step_done / step_failed
         10. 如果 failed 且 continueOnFailure == false → 终止整个运行
  6. 清除超时定时器
  7. 更新 status = completed/failed
  8. 通过 WS 推送 run_completed
```

### 2.3 降级链 (StepExecutor)

**职责**：执行单个步骤，包含 4 级降级链：

```
Level 0: Midscene AI Visual (PageAgent.ai)
  方式: 自然语言 → AI 视觉定位 → 坐标点击
  置信度阈值: ≥ 0.6
  失败处理: → Level 1

Level 1: Playwright Role/Text 匹配
  方式: getByRole → getByText → getByPlaceholder
  失败处理: → Level 2

Level 2: DOM querySelectorAll + 文本过滤
  方式: 遍历按钮/链接/输入框 → 文本匹配 → 点击
  失败处理: → Level 3

Level 3: XPath 匹配
  方式: $x("//button[contains(text(),'...')]") → 点击
  失败处理: → step.status = "failed"
```

**每个 step 的数据采集**：
```
操作前截图 (viewport) → 执行操作 → 等待 800ms → 操作后截图
→ 采集 console logs → 采集 network responses → 采集 page state
→ 返回完整的 StepResult
```

### 2.4 CDP 网络 Body 捕获增强 (Capturer)

**当前**：只捕获 method/url/status，不捕获 request body / response body。

**增强方案**：使用 CDP Fetch API 替换 Network 事件模式。

```typescript
class Capturer {
  async enable(page: Page): Promise<void> {
    const cdp = await page.context().newCDPSession(page);

    // ⚠️ Fetch.enable 是幂等的：必须在一次调用中注册所有 stage，
    // 否则第二次调用会覆盖第一次的 pattern
    await cdp.send('Fetch.enable', {
      patterns: [
        { urlPattern: '*', requestStage: 'Request' },
        { urlPattern: '*', requestStage: 'Response' },
      ]
    });

    // 使用单个 requestPaused 处理器，通过 params.requestStage 区分阶段
    cdp.on('Fetch.requestPaused', async (params) => {
      if (params.requestStage === 'Request') {
        // 读取 request body，后续步骤重建时由 Python 端发起
        capturedBody[params.requestId] = {
          postData: params.request.postData || '',
          headers: params.request.headers || {},
        };
        await cdp.send('Fetch.continueRequest', { requestId: params.requestId });
        return;
      }

      if (params.requestStage === 'Response') {
        // 只在 4xx/5xx 或 request 包含 JSON body 时获取 response body
        const status = params.responseStatusCode || 0;
        if (status >= 400) {
          try {
            const body = await cdp.send('Fetch.getResponseBody', {
              requestId: params.requestId,
            });
            // body.body 是 base64，body.base64Encoded 指示是否 base64
            capturedResponses[params.requestId] = {
              status,
              body: body.body?.substring(0, 100 * 1024), // 100KB 截断
            };
          } catch {
            // response body 可能不可读（如重定向、流式响应）
          }
        }
        await cdp.send('Fetch.continueResponse', { requestId: params.requestId });
      }
    });
  }

  // 限制: body > 100KB 截断
  // 过滤: URL 中的图片/字体/媒体资源不记录 body（通过 pattern 精细化或运行时过滤）
}
```

**数据上限保护**：
```
console logs cap:    200 条/step
network entries cap: 50 条/step
body 大小限制:       100 KB
截图格式:           PNG base64
```

### 2.5 WebSocket 实时进度推送 (Reporter)

```typescript
class Reporter {
  private clients: Map<run_id, Set<WebSocket>> = new Map();

  // WS 端点: /ws/run/{run_id}
  handleUpgrade(req, socket, head) { ... }

  // 事件推送
  push(run_id, event: RunEvent) {
    // event 类型:
    //   { type: "step_start",   run_id, case_id, step_index, action }
    //   { type: "step_done",    run_id, case_id, step_index, result }
    //   { type: "step_failed",  run_id, case_id, step_index, error, screenshot }
    //   { type: "run_completed", run_id, status, summary }
    //   { type: "run_error",    run_id, error }
  }
}
```

---

## 3. Layer 2: Python 客户端增强

### 3.1 ExecutorFactory（替换 create_executor_client）

**位置**：`app/infrastructure/executor/__init__.py`

**职责**：统一的执行器工厂。⚠️ **替换**现有的独立函数 `create_executor_client()`，两者共存的话会导致调用方混淆。

**迁移步骤**：
1. 在 `__init__.py` 中新增 `ExecutorFactory` 类
2. 将 `create_executor_client()` 标记为 `@deprecated("use ExecutorFactory.create() instead")` 
3. 更新所有引用 `create_executor_client` 的导入为 `ExecutorFactory.create`
4. 一个发布周期后移除废弃函数

```python
class ExecutorFactory:
    @staticmethod
    def create(platform: str = "web", mode: str | None = None) -> ExecutorClient:
        mode = mode or settings.executor_mode
        if mode == "mock":
            return MockExecutorClient()
        if platform == "web":
            return WebExecutorClient(base_url=settings.executor_web_url)
        raise ValueError(f"Unsupported platform: {platform}")

    @staticmethod
    async def health_check(platform: str = "web") -> bool:
        """检查执行器是否在线，离线时自动降级到 mock"""
        client = ExecutorFactory.create(platform=platform, mode="real")
        try:
            return await client.ping()
        except Exception:
            logger.warning(f"Executor {platform} offline, will fallback to mock")
            return False
```

**使用场景**：
```
ExecutionEngine.execute_run():
  1. executor = ExecutorFactory.create(platform="web")
  2. 先 ping 检查连通性
  3. 不通 → 降级记录 + 使用 MockExecutorClient 继续
```

### 3.2 WebSocket 客户端

**位置**：`app/infrastructure/executor/ws_client.py`

```python
class ExecutorWSClient:
    """接收执行器 WebSocket 实时进度"""
    
    def __init__(self, executor_url: str, run_id: str):
        self.ws_url = f"{executor_url.replace('http://','ws://').replace('https://','wss://')}/ws/run/{run_id}"
        self._callbacks: dict[str, list[Callable]] = defaultdict(list)
        self._ws: WebSocket | None = None
        self._reconnect_count = 0
        self._max_reconnect = 5

    def on(self, event: str, callback: Callable):
        """注册事件回调"""
        # 事件: step_start, step_done, step_failed, run_completed, run_error
        self._callbacks[event].append(callback)

    async def connect(self):
        """建立连接并开始监听
        
        ⚠️ 当 WS 关闭时（正常关闭或异常断开），`async for` 正常退出不抛异常。
        因此外层调用方无法区分"正常结束"和"意外断开"。
        解决方法：在监听结束后抛出 ConnectionClosed，使重连逻辑可捕获。
        """
        self._ws = await connect(self.ws_url)
        try:
            async for msg in self._ws:
                event = json.loads(msg)
                event_type = event.get("type", "")
                event_data = event.get("data", {})
                for cb in self._callbacks.get(event_type, []):
                    await cb(event_data)
        finally:
            # WS 关闭后（无论是正常还是异常）抛异常触发重连
            if self._reconnect_count < self._max_reconnect:
                raise websockets.exceptions.ConnectionClosed(
                    0, "Connection closed, reconnecting..."
                )

    async def disconnect(self):
        if self._ws:
            await self._ws.close()

    async def connect_with_reconnect(self):
        """自动重连版的 connect（指数退避: 2s, 4s, 8s, 16s, 32s）"""
        while self._reconnect_count <= self._max_reconnect:
            try:
                await self.connect()
                return  # 正常结束（所有步骤完成），不重连
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

### 3.3 WebExecutorClient 增强

**ExecutorClient 接口更新**：

```python
# app/interfaces/executor_client.py

class ExecutorClient(ABC):
    @property
    @abstractmethod
    def mode(self) -> str:
        """返回 'real' 或 'mock'，供调用方判断是否需要真实浏览器"""
        ...

    @abstractmethod
    async def ping(self) -> bool:
        """健康检查"""
        ...

    @abstractmethod
    async def execute_step(self, step: TestStep, context: dict) -> StepExecutionRecord:
        ...

    @abstractmethod
    async def take_screenshot(self) -> str:
        ...

    @abstractmethod
    async def get_page_state(self) -> dict:
        ...
```

**MockExecutorClient 补齐**（必须实现所有新增接口）：

```python
class MockExecutorClient(ExecutorClient):
    @property
    def mode(self) -> str:
        return "mock"

    async def ping(self) -> bool:
        return False  # mock 模式不连接真实执行器

    async def navigate(self, url: str, viewport: dict | None = None) -> NavigateResult:
        return NavigateResult(success=True, screenshot="", current_url=url)

    async def create_run(self, run_id: str, entry: dict, cases: list) -> dict:
        return {"run_id": run_id, "status": "created"}

    async def start_run(self, run_id: str) -> dict:
        return {"run_id": run_id, "status": "running"}

    async def get_run_progress(self, run_id: str) -> dict:
        return {"run_id": run_id, "status": "completed", "progress": 1.0}

    async def cancel_run(self, run_id: str) -> None:
        pass
    # ... 现有 execute_step/take_screenshot/get_page_state 保持不变
```

**WebExecutorClient 新增方法**：

    async def ping(self) -> bool:
        """健康检查"""
        resp = await self._client.get(f"{self.base_url}/health", timeout=10)
        return resp.json().get("status") == "ok"

    async def navigate(self, url: str, viewport: dict | None = None) -> NavigateResult:
        """导航到目标 URL"""
        resp = await self._client.post(f"{self.base_url}/agent/navigate", json={
            "url": url,
        }, timeout=30)
        data = resp.json()
        return NavigateResult(
            success=data["success"],
            screenshot=data.get("screenshot", ""),
            current_url=data.get("url", "")
        )

    async def create_run(self, run_id: str, entry: dict, cases: list[TestCase]) -> dict:
        """在执行器端创建运行
        
        cases: Python 领域模型 TestCase 列表，发送前转换为 Node.js ExecutableCase 格式。
        转换规则: TestCase.steps → ExecutableStep { index, action, target, value } 1:1 映射。
        """
        executable_cases = [
            {
                "id": c.id,
                "name": c.name,
                "steps": [
                    {"index": s.index, "action": s.action, "target": s.target, "value": s.value}
                    for s in (c.steps or [])
                ],
            }
            for c in cases
        ]
        resp = await self._client.post(f"{self.base_url}/run/create", json={
            "run_id": run_id,
            "entry": entry,
            "cases": executable_cases,
        }, timeout=30)
        return resp.json()

    async def start_run(self, run_id: str) -> dict:
        """启动执行（异步）"""
        resp = await self._client.post(f"{self.base_url}/run/{run_id}/start", timeout=10)
        return resp.json()

    async def get_run_progress(self, run_id: str) -> dict:
        """查询执行进度"""
        resp = await self._client.get(f"{self.base_url}/run/{run_id}/progress", timeout=10)
        return resp.json()

    async def cancel_run(self, run_id: str) -> None:
        """取消执行"""
        await self._client.post(f"{self.base_url}/run/{run_id}/cancel", timeout=10)
```

### 3.4 ExecutionEngine 改造（核心）

**重要决策**：不创建新的 `RunService` 执行路径。而是扩展现有的 `app/engine/execution_engine.py`。
现有 `ExecutionEngine` 已经是编排中心（执行→分析→保存），改造让它同时支持 WS 驱动模式。

**ExecutionEngine 扩展**：

```python
# app/engine/execution_engine.py

class ExecutionEngine:
    """执行引擎：现有编排逻辑 + WS 驱动模式扩展"""

    async def execute_run(self, run_id: str):
        """入口 - 先获取项目入口配置，再派发到 real 或 mock 执行"""
        run = await run_repo.get_by_id(run_id)

        # 1. 获取项目入口配置（⚠️ 用 project_repo 查，不走 run.project.entries）
        project = await project_repo.get_by_id(run.project_id)
        entry = project.entries[0] if project.entries else None
        if not entry:
            raise ValueError(f"Project {run.project_id} has no platform entries")

        # 2. 创建执行器（含健康检查和自动降级）
        executor = ExecutorFactory.create(platform="web")
        is_real = executor.mode == "real"
        if is_real and not await ExecutorFactory.health_check("web"):
            logger.warning("Executor offline, falling back to mock")
            executor = MockExecutorClient()
            is_real = False

        # 3. 更新运行状态
        await run_repo.update_status(run_id, "running")

        # 4. 选择执行路径
        if is_real:
            await self._execute_via_executor(run_id, entry, executor, run)
        else:
            await self._execute_local(run_id, executor, run)

        # 5. 分析缺陷（复用现有逻辑）
        await self.analysis_service.analyze_run(run_id)

        # 6. 完成
        await run_repo.update_status(run_id, "completed")

    async def _execute_via_executor(
        self, run_id: str, entry: PlatformEntry,
        executor: WebExecutorClient, run: RunRecord
    ):
        """真实执行器路径 — WS 驱动"""
        cases = await scenario_repo.get_cases_for_run(run_id)

        # 通知 executor 创建运行
        await executor.create_run(run_id, {
            "url": entry.url,
            "viewport": entry.viewport or {"width": 1920, "height": 1080}
        }, cases)

        # 注册 WS 回调 — ⚠️ 使用 lambda 包装避免立即求值
        ws_client = ExecutorWSClient(settings.executor_web_url, run_id)

        async def on_step_done(data: dict):
            """WS step_done 回调：保存步骤结果"""
            result = StepExecutionRecord.from_executor_data(data)
            await run_repo.save_step_result(run_id, data["case_id"], result)
            await self._push_progress(run_id)

        async def on_run_completed(data: dict):
            """WS run_completed 回调：最终状态更新"""
            await run_repo.update_status(run_id, data.get("status", "completed"))
            ws_client.disconnect()

        ws_client.on("step_done", on_step_done)
        ws_client.on("run_completed", on_run_completed)
        ws_client.on("run_error", lambda data: asyncio.create_task(
            run_repo.update_status(run_id, "failed")
        ))

        # 连接 WS（启动后台监听）+ 通过 start_run 触发执行
        # ⚠️ 先连接 WS 再 start_run，避免丢失事件
        ws_task = asyncio.create_task(ws_client.connect_with_reconnect())
        await executor.start_run(run_id)

        # 等待运行完成（监听器会自动更新状态），最多等 30 分钟
        try:
            await asyncio.wait_for(
                self._wait_for_completion(run_id, executor),
                timeout=1800
            )
        except asyncio.TimeoutError:
            await run_repo.update_status(run_id, "failed")
        finally:
            ws_task.cancel()

    async def _wait_for_completion(self, run_id: str, executor: WebExecutorClient):
        """轮询等待执行完成（WS 断线时的兜底机制）"""
        while True:
            progress = await executor.get_run_progress(run_id)
            if progress.get("status") in ("completed", "failed", "cancelled"):
                break
            await asyncio.sleep(2)

    async def _execute_local(self, run_id: str, executor: ExecutorClient, run: RunRecord):
        """Mock 模式：本地串行执行（现有逻辑保留）"""
        cases = await scenario_repo.get_cases_for_run(run_id)
        for case in cases:
            for step in case.steps:
                result = await executor.execute_step(step, {"run_id": run_id, "case_id": case.id})
                await run_repo.save_step_result(run_id, case.id, result)
                await self._push_progress(run_id)
```

---

## 4. Layer 3: 全流程验证

### 4.1 Docker 集成

**docker-compose.yml 补充**：

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

**executor/web/Dockerfile**：

```dockerfile
FROM node:20-slim
RUN npx playwright install chromium --with-deps
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
EXPOSE 3100
# ⚠️ 生产环境用 npm start（编译后的 dist/index.js），不要用 dev 模式的热重载
CMD ["npm", "start"]
```

### 4.2 集成测试

测试目录：`tests/integration/test_executor_web.py`

**测试用例**：

| # | 测试 | 验证点 | 条件 |
|---|------|--------|------|
| 1 | 健康检查 | 返回 `{status: "ok", browserReady: true/false}` | 执行器在线 |
| 2 | 导航到目标 URL | URL 变更、返回截图 | 执行器在线 |
| 3 | 单步执行 (click) | 状态为 passed/failed、含截图/console/network | 执行器在线 |
| 4 | 单步执行 (input) | 输入框文本变更 | 执行器在线 |
| 5 | Mock 模式执行 | 状态为 passed，不依赖浏览器 | 无视执行器 |
| 6 | 执行器离线降级 | 自动切换到 MockExecutorClient | 执行器不可用 |
| 7 | 端到端全流程 | 项目创建 → 场景 → 执行 → 报告 | 全服务在线 |

### 4.3 E2E Demo 脚本

更新 `scripts/e2e_demo.py`：

```
scripts/e2e_demo.py --url https://example.com --mode real

输出:
  ✅ Execution completed
  ├── Cases executed: 5
  ├── Steps passed: 12/15
  ├── Defects found: 2
  ├── Report: http://localhost:8000/api/v1/runs/run_xxx/report
  └── Duration: 45.2s
```

---

## 5. API 变更概要

### 5.1 Executor Node.js 新增端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /run/create | 创建运行 |
| POST | /run/{id}/start | 启动执行 |
| POST | /run/{id}/cancel | 取消执行 |
| GET | /run/{id}/progress | 查询进度 |
| GET | /run/{id}/status | 获取完整状态 |
| WS | /ws/run/{id} | 实时进度推送 |

### 5.2 Python 后端无 API 变更

后端 API 接口不变（Project/Run/Report/Defect endpoints 保持兼容），`RunService` 内部改造。

---

## 6. 配置项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| EXECUTOR_MODE | mock | mock / real，切换执行模式 |
| EXECUTOR_WEB_URL | http://localhost:3100 | Web 执行器地址 |
| EXECUTOR_TIMEOUT | 60000 | 执行器请求超时 (ms) |
| EXECUTOR_MAX_RETRIES | 3 | 通信失败重试次数 |
| EXECUTOR_WS_RECONNECT | 5 | WS 断线最大重连次数 |

---

## 7. 不在此范围内

- Android / iOS 执行器（当前只做 Web）
- 执行器节点集群管理（单实例）
- 执行器资源池（池化浏览器实例）
- 被测应用截图 OCR 校验（当前只做四维校验基础版）

---

## 8. 质量门禁

Layer 交付标准：

| Layer | 通过标准 |
|-------|----------|
| Layer 1 | 单元测试通过，RunManager 可完成多步骤运行并返回完整结果 |
| Layer 2 | WebExecutorClient 集成测试通过，健康检查+降级机制生效 |
| Layer 3 | E2E Demo 可在 `EXECUTOR_MODE=real` 下成功运行完整流程 |
