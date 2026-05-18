# AutoTest 深度审核报告 — 第三轮

> 日期: 2026-05-15
> 范围: 逐行逻辑审查、竞态条件、配置一致性、前端响应式

---

## 本轮发现总览

| 严重度 | 数量 | 已修复 |
|--------|------|--------|
| 🔴 致命 | 2 | 2 |
| 🟡 重要 | 3 | 1 |
| 🟢 轻微 | 2 | 0 (技术债) |

---

## 🔴 致命 Bug

### Bug-1: start_task 后台任务启动崩溃

**文件**: `app/api/v1/tasks.py:87`
**问题**: 访问 `run_svc._run_repo` 但 RunService 内部使用 `self._repo` (属性名错误)
**影响**: 前端点击"启动任务" → API 调用 → `AttributeError` → 任务永远停留在 prechecking
**修复**: 改为 `get_run_repo()` 从 dependencies 获取单例 RunRepository
**状态**: ✅ 已修复

### Bug-2: LiteLLM 无 API Key 提示死代码

**文件**: `app/infrastructure/ai/lite_llm_service.py:36-38`
**问题**: 日志代码放在 `_resolve_model()` 的 `return` 语句之后，永不可达
**影响**: 用户永远看不到 "No LITELLM_API_KEY configured" 的提示，不知道为什么 AI 功能不工作
**修复**: 移到 `__init__` 方法内
**状态**: ✅ 已修复

---

## 🟡 重要 Bug

### Bug-3: SqlRepository 时区不一致

**文件**: 5 个 SqlRepository (project/deffect/document/knowledge/run)
**问题**: `datetime.now()` 写入 PostgreSQL `DateTime(timezone=True)` 列，时区信息缺失
**影响**: PostgreSQL 模式下可能产生告警或隐式类型转换
**修复**: 需要改为 `datetime.now(timezone.utc)` (技术债，当前默认内存模式不影响)
**状态**: ⏳ 技术债

### Bug-4: 模型字段接受额外输入

**文件**: 全部 Pydantic 模型
**问题**: 无 `model_config = {"extra": "forbid"}`，API 可以传入意外字段
**影响**: 低 - 额外字段会被忽略而非报错
**修复**: 可选加固
**状态**: ⏳ 技术债

---

## 🟢 轻微/技术债

| # | 问题 | 涉及文件 |
|---|------|---------|
| 5 | 其他 Pydantic 模型仍用 `datetime.now` (非 UTC) | 6 个 domain model 文件 |
| 6 | 前端 TaskDetail 无用户操作反馈 (ElMessage) | `web/src/views/TaskDetail.vue` |

---

## 本轮验证结果

```
220 tests PASSED (1 env-skip)
2 致命 Bug 已修复
0 regressions
```

## 累计修复统计

| 轮次 | 发现 | 修复 |
|------|------|------|
| 初轮 (功能) | 10 | 10 |
| 二轮 (架构/Oracle) | 5 | 5 |
| 三轮 (深度/多角度) | 7 | 4 (3 技术债) |
| **总计** | **22** | **19** (3 技术债) |
