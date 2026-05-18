# AutoTest 待完成任务清单

> 生成日期: 2026-05-15
> 来源: 全量文档+代码头脑风暴审核
> 状态: 待执行

---

## P0 — 核心功能短板

### Task 1: 创建 taskStore.ts (Pinia 状态管理)

**问题**: `web/src/stores/` 目录只有 README.md，无实际 store 文件。页面刷新后任务列表数据丢失，用户体验差。

**目标**: 创建 Pinia store 集中管理任务状态，支持数据持久化(async storage)或 API 实时获取。

**涉及文件**:
- Create: `web/src/stores/taskStore.ts`
- Modify: `web/src/views/TaskList.vue` (接入 store)
- Modify: `web/src/views/TaskDetail.vue` (接入 store)
- Modify: `web/src/views/Dashboard.vue` (接入 store)

**验收标准**:
- TaskList 从 store 读取而非直接 API 调用
- 创建任务后 store 自动更新
- 启动任务后 store 自动轮询状态

### Task 2: TaskDetail 启动按钮前后端联调

**问题**: TaskDetail 已有"启动任务"按钮和 WebSocket 客户端，但未确认 start_task API → TaskOrchestrator 管线的完整联调是否正常。

**目标**: 验证从前端点击"启动任务"→ API 调用 → TaskOrchestrator 执行 → WebSocket 推送 → 前端自动刷新的完整链路。

**涉及文件**:
- Verify: `web/src/views/TaskDetail.vue`
- Verify: `app/api/v1/tasks.py` (start_task)
- Verify: `app/engine/task_orchestrator.py` (run_pipeline)

**验收标准**:
- 点击启动后按钮变为 loading
- WebSocket 推送 stage 变更时页面自动更新
- 任务完成后显示交付包

---

## P1 — 体验增强

### Task 3: 执行器 AI 视觉 Level 0

**问题**: 文档描述的执行器降级链第一级为 "AI 视觉定位 (Midscene)"，但当前实现 3 级全是 DOM 定位。缺少 AI 视觉识别。

**目标**: 在 step-executor.ts 的 Level 0 之前加入 AI 视觉定位层，调用 Midscene Agent 或截图+LLM 定位。

**涉及文件**:
- Modify: `executor/web/src/step-executor.ts`
- Modify: `executor/web/src/index.ts`
- Create: `executor/web/src/ai-visual.ts` (可选的 AI 视觉模块)

**验收标准**:
- AI 视觉置信度 ≥ 0.6 时使用 AI 定位
- AI 定位失败时降级到 Level 0 (Playwright DOM)
- 不影响现有 163 个测试

---

## P2 — 技术债

### Task 4: 缺陷中心页面

**问题**: 当前缺陷分散在各个 task 详情页中，没有统一的缺陷列表视图。

**目标**: 创建缺陷中心页面，聚合所有任务的缺陷，支持按严重度/类型/状态筛选。

**涉及文件**:
- Create: `web/src/views/DefectCenter.vue`
- Modify: `web/src/router.ts`
- Modify: `web/src/App.vue` (导航菜单)
- Create: `web/src/api/defectApi.ts` (如果不存在独立的缺陷 API 封装)

**验收标准**:
- 展示所有缺陷列表 (严重度/类型/标题/所属任务)
- 支持按严重度筛选
- 点击跳转到缺陷详情页

---

## 技术债务备忘 (低优先级)

| # | 事项 | 说明 | 建议时机 |
|---|------|------|---------|
| TD-1 | 基础设施组件未持久化 | webhook_service/feature_flags 重启丢失 | 生产部署前 |
| TD-2 | WebSocket 重连机制 | 当前未实现断线重连 | P3 |
| TD-3 | 前端错误边界 | 未捕获的 API 异常处理 | P3 |
| TD-4 | 国际化 i18n | 所有用户面对硬编码中文 | P4 |
| TD-5 | Docker compose 生产配置 | 当前为开发配置 | 生产部署前 |

---

## 当前状态总览

| 指标 | 值 |
|------|-----|
| 单元测试 | 213 passed (1 env-skip) |
| Python 文件 | 107 |
| 前端文件 | 15 |
| 设计文档 | 13 (已同步) |
| 需求覆盖 | 37/37 (100%) |
| 已知致命问题 | 0 |
| 待完成任务 | 4 |
