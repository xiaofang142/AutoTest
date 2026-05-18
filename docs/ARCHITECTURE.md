# AutoTest 架构设计文档 (ADD)

> 版本: 3.0
> 日期: 2026-05-15
> 状态: 生效 (代码已落地)
> 本文定位: 定义 AutoTest 的系统分层、核心数据流、业务对象与接口边界
> 关联文档:
> - [REQUIREMENTS.md](./REQUIREMENTS.md)
> - [全自动AI测试闭环设计.md](./全自动AI测试闭环设计.md)
> - [自动测试任务模型设计.md](./自动测试任务模型设计.md)

---

## 1. 系统架构

### 1.1 VNext 架构主线

本版本开始，架构主线统一为:

```text
TestTask
  -> EnvironmentCheck
  -> UnderstandingResult
  -> TestBlueprint
  -> ExecutionRun
  -> Defect
  -> DeliveryPackage
```

说明:

- `TestTask` 是产品层的一等聚合对象
- `Project` 主要负责长期配置与归档
- `Run` 主要负责执行阶段
- `DeliveryPackage` 负责面向测试、开发者与 AI 助手的最终交付

```
┌─────────────────────────────────────────────────────┐
│                    Web UI (Vue 3)                     │
│         http://localhost:3000                         │
└──────────────────────────┬──────────────────────────┘
                           │ HTTP /api/*
                           ▼
┌─────────────────────────────────────────────────────┐
│                API Server (FastAPI)                   │
│         http://localhost:8765                         │
│                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │ 项目管理      │  │ 文档解析     │  │ 执行引擎    │  │
│  │ ProjectSvc   │  │ DocumentSvc  │  │ Engine     │  │
│  └──────────────┘  └──────────────┘  └──────┬─────┘  │
│                                              │        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────┴─────┐  │
│  │ 综合分析      │  │ MCP 接口     │  │ 执行器客户端│  │
│  │ Analyzer     │  │ FastMCP      │  │ Executor   │  │
│  └──────────────┘  └──────────────┘  └──────┬─────┘  │
│                                              │        │
└──────────────────────────────────────────────┼────────┘
                                               │ HTTP
┌──────────────────────────────────────────────┴────────┐
│              Executor (Node.js + Pure Playwright)        │
│         http://localhost:3100                           │
│                                                         │
│  3-Level DOM Chain (Locator → querySelector → XPath)   │
│  CDP Network + Console Capture                          │
│  Smart Screenshot + PageState Snapshot                  │
└─────────────────────────────────────────────────────────┘
```

## 2. 核心数据流

### 2.1 统一闭环骨架

无论是快速模式还是文档驱动模式，系统都建议统一走以下八阶段:

1. 测试入口
2. 环境预检
3. 测试对象理解
4. 测试蓝图生成
5. 执行编排
6. 多维校验
7. 缺陷归因
8. 结果交付

### 2.2 任务驱动数据流

```text
用户输入 URL / 文档
  │
  ▼
创建 TestTask
  │
  ▼
EnvironmentCheck
  │
  ▼
UnderstandingResult
  │
  ▼
TestBlueprint
  │
  ▼
ExecutionRun
  │
  ▼
Defect + RepairContext
  │
  ▼
DeliveryPackage
```

### 2.3 快速模式 (无文档)

```
用户: 输入 URL
  │
  ▼
创建 TestTask
  │
  ▼
页面发现
  │
  ▼
生成最小测试蓝图
  │
  ▼
ExecutionRun
  │
  ▼
多维校验 + 缺陷交付
```

### 2.4 完整模式 (有文档)

```
用户: 输入 URL + 上传文档 .md
  │
  ▼
创建 TestTask
  │
  ▼
文档理解 + 页面理解
  │
  ▼
生成业务测试蓝图
  │
  ▼
ExecutionRun
  │
  ▼
多维校验 + 缺陷交付
```

## 3. 关键技术选型

| 组件 | 技术 | 用途 |
|------|------|------|
| Web 框架 | FastAPI + Uvicorn | REST API |
| 执行引擎 | Pure Playwright (3-level DOM) | 浏览器控制 + 元素定位 + CDP 采集 |
| 本地 OCR | PaddleOCR (常驻) | 截图文字提取，无需 API key |
| AI 分析 | LiteLLM + LLM 合并分析 | OCR + DOM + Console + Network 多信号融合 |
| 前端 | Vue 3 + Element Plus + Vite | 管理界面 |
| 存储 | 内存 (默认) | 项目/执行/缺陷数据 |
| CLI | Click | 命令行操作 |

## 4. 核心业务对象

| 对象 | 责任 |
|------|------|
| `TestTask` | 承载一次完整自动测试生命周期 |
| `TaskInput` | 承载用户输入与系统补全信息 |
| `EnvironmentCheck` | 承载环境与能力预检结果 |
| `UnderstandingResult` | 承载页面与文档理解结果 |
| `TestBlueprint` | 承载自动生成的测试蓝图 |
| `ExecutionRun` | 承载真实执行过程 |
| `Defect` | 承载问题对象 |
| `RepairContext` | 承载开发者与 AI 助手可消费的修复上下文 |
| `DeliveryPackage` | 承载多视角交付结果 |

## 5. 接口边界

架构文档只定义接口分层边界，不重复维护具体端点清单。

当前接口分为:

- 项目与任务入口
- 文档与解析入口
- 执行与进度入口
- 报告、缺陷与交付入口
- MCP / AI 消费入口

具体路径、请求体、响应体和错误码，以 [API接口规范.md](./API接口规范.md) 为准。

## 6. OCR+LLM 分析管线增强

### 6.1 EnhancedOCR 三层管线

```
截图(base64)
  │
  ├── Stage 1: 图片预处理 (enhanced_ocr_service.py)
  │   ├── 自适应二值化 → 处理光照不均
  │   ├── 中值滤波去噪
  │   ├── CLAHE 对比度增强
  │   └── 文本纠偏 (旋转 >2° 自动校正)
  │
  ├── Stage 2: OCR 识别 + 布局分析
  │   ├── PaddleOCR 本地文字提取 (无外部依赖)
  │   └── 按坐标分类: header/main/sidebar/footer/modal
  │
  └── Stage 3: DOM-OCR 坐标对齐
      └── IoU(60%) + 文本相似度(40%) 加权匹配
```

### 6.2 Chain-of-Thought LLM 分析

```
lite_llm_service.py → CoT 6步推理链:
  步骤1: API层检查 (最可靠信号: 4xx/5xx/超时)
  步骤2: Console层检查 (JS Error: 级联效应 vs 前端Bug)
  步骤3: UI层检查 (OCR+DOM交叉验证: 错误关键词/白屏/弹窗)
  步骤4: 业务层检查 (URL跳转/关键元素存在性)
  步骤5: 综合判断 (ROOT CAUSE vs CASCADING EFFECT)
  步骤6: 输出 JSON { dimensions, root_cause, fix_suggestion, reasoning[] }
```

### 6.3 降级策略

```
有 LLM API Key → CoT 分析 → 维度判断 → 证据链
无 LLM API Key → _simple_analysis() 规则引擎: 4维独立校验 + 关键词匹配
CoT 失败 → 重试1次 → 仍失败 → 规则引擎兜底
```

### 6.4 跨步上下文

```
CrossStepContext 维护最近10步的分析结果
  → 步骤N+1 分析时携带步骤N的状态
  → 例: 步骤2 API 500 → 步骤3 页面白屏 → 合并为同一因果链
```

## 7. 代码分析管线 (NEW)

### 7.1 输入

```
TaskInput.code_dir = "/path/to/project"
  → CodeAnalysisService.analyze_codebase()
```

### 7.2 扫描内容 (框架无关)

| 扫描项 | 检测方式 | 支持框架 |
|--------|---------|---------|
| 路由 | 正则匹配 router 配置文件 | Vue Router / React Router / Uniapp / Express / FastAPI |
| 页面元素 | Vue/JSX/HTML 模板解析 | Vue / React / HTML |
| API 端点 | 路由方法定义 | Express / FastAPI / NestJS |
| 文档文件 | .md 文件扫描 | 任意框架 |

### 7.3 如何影响测试管线

```
_understand() 阶段:
  CodeAnalysisService.enhance_understanding()
    → 添加 key_flows: "路由 /login → LoginPage.vue"
    → 添加 risk_points: "API POST /api/login"
    → completeness +0.2

_plan() 阶段:
  CodeAnalysisService.generate_blueprint_steps()
    → 为每个路由生成 navigate 步骤
    → 为每个按钮生成 click 步骤
    → 为每个输入框生成 input 步骤
    → 为每个 API 生成 verify_api 步骤
```

## 8. 架构对齐结论

后续架构演进建议遵循以下原则:

- 外部产品主线以 `TestTask` 驱动
- 内部实现继续复用 `Project`、`Run`、`Defect` 等既有模块
- 执行完成不等于闭环完成，必须继续经过多维校验、缺陷归因与交付阶段
- 结构化结果对象优先于页面展示结果
