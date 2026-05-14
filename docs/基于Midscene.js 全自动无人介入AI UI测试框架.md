# AutoTest — 全自动 AI UI 测试框架

> 输入地址即完成测试。覆盖 PC Web、H5、Android、iOS。全自动完成文档理解、业务拆解、全平台执行、多维校验。生成高质量结构化参考数据，AI 开发工具和开发者可直接用于定位和修复缺陷。

---

# 一、痛点与解决思路

## 1.1 传统测试的深层痛点

大多数人谈测试痛点只停留在"耗时、维护成本高"。但更深层的问题是：**测试产出的价值没有被真正兑现**。

### 痛点一：测试和修正是两个断裂的环节

```
传统流程：
写用例 → 执行 → 发现失败 → 人工看日志 → 定位代码 → 修复 → 重新验证
                                      ↑
                                这里有一个巨大的断层
```

测试框架只负责"报错"，不负责"帮助修复"。测试人员花了 80% 的精力跑测试，但开发人员拿到失败报告后，仍然需要：
- 重新复现才能定位问题
- 查看截图猜测哪里不对
- 翻控制台日志找异常
- 查网络请求确认数据
- 在代码里翻找对应的逻辑

**每一个环节都在重复消耗人力**。

### 痛点二：测试结果的消费方不是人，而是 AI

2026 年的现实：越来越多的代码由 AI 助手（Claude Code、Cursor、Copilot）生成。但测试框架的输出格式仍然是给"人看的"——HTML 报告、截图、PDF。

```
AI 开发工具需要的是：
{structured, machine-readable, actionable data}
而不是：
{HTML report, screenshot.png, "test failed"}
```

### 痛点三：传统测试的维度孤立，不做交叉论断

```
传统自动化校验模式：
  UI 检查 → pass/fail（独立）
  截图比对 → pass/fail（独立）
  两者互不关联，各自报告

但真实 Bug 往往是跨维度的：
  "API 返回了 500，所以前端才报 JS Error，所以页面才空白"
  ↑  这是一个因果链，不是三个独立问题
```

**传统框架的问题不是维度少，而是维度之间彼此孤立，不做交叉分析**：

```
真实场景：
  API 返回 500 ❌
  控制台 JS Error ❌
  页面空白 ❌
  ─────────────────
  传统报告：3 个独立失败，开发者自己串起来
  AutoTest：API 500 → 导致 JS 解析失败 → 页面渲染中断（一条因果链）
```

**最致命的问题**：多个维度各自报错时，开发者收到的是一堆零散信号，需要自己脑补因果关系。这等于把"诊断"的工作推给了人。

### 痛点四：脚本维护成本 > 编写成本

```
行业共识（来自 Google Testing Blog）：
  自动化测试的维护成本 = 编写成本的 2-3 倍/年
  页面每改版一次 → 20-50% 的脚本需要更新

根源：DOM 定位（XPath/CSS/ID）天生脆弱
  页面布局微调 → CSS 类名变 → 脚本挂
  组件升级 → DOM 结构变 → 脚本挂
  最离谱：加了个空格 → 截图 diff 失败
```

### 痛点五：多平台测试 = 多倍痛苦

```
Web 一套 Playwright 脚本
Android 一套 Appium 脚本
iOS 一套 XCTest 脚本
↓
每套都要写、都要维护、都要调试
↓
同一个 Bug 在三套脚本里各报一次
↓
三份完全不兼容的报告
```

## 1.2 AutoTest 的核心解题思路

### 思路一：让测试产出"可消费的结构化数据"

```
传统测试产出： pass/fail + 截图 → 人看
AutoTest 产出： 结构化 JSON → AI 工具消费
  ├── 每一步的截图（base64 内嵌）
  ├── 每一步的控制台日志（结构化）
  ├── 每一步的网络请求快照
  ├── 校验结果（四维 × 置信度）
  ├── AI 根因分析（自然语言描述）
  └── AI 修复建议（可执行的自然语言指令）
```

**关键区别**：AutoTest 的输出设计初衷是"给 AI 读"，而不是"给人读"。AI 开发工具拿到这份数据后，可以直接理解失败原因并生成修复代码。

### 思路二：视觉驱动，从根源消除 DOM 脆弱性

```
传统：XPath: //div[@class="login-btn"]/span → 改 class 就挂
AutoTest：截图 → AI 识别"登录按钮"坐标 → 点击 → 改 UI 也不挂
```

### 思路三：地址驱动，从根源消除脚本编写

```
传统：人工写 Playwright 代码 → 人月级工作
AutoTest：输入 PRD 文档地址 → AI 自动生成 → 分钟级
```

### 思路四：四维校验，一次执行覆盖全部质量维度

```
测试失败 ≠ 按钮没点到
  ├── 按钮点到了，但 API 返回 500 → API 校验败露
  ├── 按钮点到了，但控制台报 JS Error → 控制台校验败露
  ├── 按钮点到了，但页面跳转错了 → 业务校验败露
  └── 按钮根本没渲染出来 → UI 校验败露
```

---

## 1.3 AutoTest vs 传统方案的差异矩阵

| 维度 | Playwright/Selenium | Appium | Cypress | AutoTest |
|---|---|---|---|---|
| **定位方式** | CSS/XPath/ID | XPath/ID | 选择器 | **纯视觉（截图+AI）** |
| **跨平台** | 仅 Web | Web+Android+iOS | 仅 Web | **全平台统一** |
| **脚本创建** | 人工编写 | 人工编写 | 人工编写 | **AI 自动生成** |
| **测试数据价值** | pass/fail | pass/fail | pass/fail | **结构化缺陷数据，含完整复现上下文** |
| **校验维度** | 功能 | 功能 | 功能 | **UI+控制台+API+业务** |
| **页面改版影响** | 脚本全挂 | 脚本全挂 | 脚本全挂 | **零影响** |
| **输出格式** | HTML 报告 | HTML 报告 | HTML 报告 | **结构化 JSON（AI 可消费）** |
| **AI 修复能力** | 无 | 无 | 无 | **输出修复参考数据，给开发者/AI 编程助手定位修复用** |

---

# 二、业务域划分

## 2.1 业务域全景

```
┌─────────────────────────────────────────────────────────────┐
│                     AutoTest 业务域地图                       │
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌───────────────┐   │
│  │ 项目管理域    │───▶│ 文档解析域   │───▶│  知识库域      │   │
│  │              │    │              │    │               │   │
│  │ Project      │    │ Document     │    │ KnowledgeBase │   │
│  │ Config       │    │ Parse        │    │ BusinessRules │   │
│  │ Platform     │    │ Extract      │    │ UIStandards   │   │
│  │ Entry        │    │ Clean        │    │ Permissions   │   │
│  └─────────────┘    └─────────────┘    └───────┬──────────┘   │
│                                                  │            │
│                                                  ▼            │
│  ┌─────────────┐    ┌─────────────┐    ┌───────────────┐   │
│  │ 场景生成域   │◀───│ 知识库域     │    │  综合分析域    │   │
│  │             │    │（继续使用）   │    │               │   │
│  │ ScenarioGen │    │             │    │               │   │
│  │ TestMatrix  │    │             │    │               │   │
│  │ PathGen     │    │             │    │               │   │
│  └──────┬──────┘    └─────────────┘    └───────────────┘   │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  执行调度域                           │   │
│  │  TaskQueue | PlatformRouter | Concurrency | Retry     │   │
│  └────────┬────────┬────────┬──────────────────────────┘   │
│           │        │        │                              │
│           ▼        ▼        ▼                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                   │
│  │ Web 执行  │ │Android   │ │ iOS 执行  │                   │
│  │ Player    │ │Executor  │ │ Executor │                   │
│  └──────────┘ └──────────┘ └──────────┘                   │
│         │         │          │                              │
│         └─────────┴──────────┘                              │
│                      ▼                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   四维校验域                          │   │
│  │  UIVerify | ConsoleVerify | APIVerify | BizVerify     │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   缺陷分析域                          │   │
│  │  DefectClassify | RootCause | FixSuggest | FixApply   │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         ▼                                  │
│  ┌─────────────┐    ┌────────────────────────────────┐     │
│  │ 报告域       │    │  参考数据接口域                   │     │
│  │ ReportGen   │    │  StructuredOutput → MCP → AI    │     │
│  │ Export      │    │  开发工具自动消费                 │     │
│  └─────────────┘    └────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## 2.2 各业务域详解

### 域一：项目管理域

```
职责：管理测试项目和配置
实体：Project, PlatformEntry, DocumentRef
事件：ProjectCreated, ProjectConfigChanged
```

| 行为 | 输入 | 输出 |
|---|---|---|
| 创建项目 | name + platforms + entries + docs | project_id |
| 更新配置 | project_id + 变更字段 | — |
| 删除项目 | project_id | — |
| 列出项目 | — | Project[] |

### 域二：文档解析域

```
职责：拉取文档内容、AI 提取结构化规则
实体：DocumentRaw, ParsedChapter, ExtractionResult
事件：DocumentParsed, DocumentParseFailed
```

| 行为 | 输入 | 输出 |
|---|---|---|
| 解析文档 | DocumentRef[] | ExtractionResult |
| 重试解析失败文档 | DocumentRef | ExtractionResult |
| 对比文档版本差异 | old_kb_id, new_kb | DiffReport |

### 域三：知识库域

```
职责：存储业务规则、UI 标准、权限规则，版本管理
实体：KnowledgeBase, BusinessRule, UIStandard, PermissionRule
值对象：BusinessLine, Flow, Step, ComponentSpec, Role
```

| 行为 | 输入 | 输出 |
|---|---|---|
| 创建知识库 | ExtractionResult | kb_id |
| 查询规则 | kb_id, 条件 | BusinessRule[] |
| 版本对比 | v1, v2 | DiffReport |
| 人工修正规则 | kb_id + 修改内容 | 新版本知识库 |

### 域四：场景生成域

```
职责：从知识库自动生成测试场景矩阵
实体：TestScenario, TestCase, TestStep
事件：ScenariosGenerated, ScenarioGenerationFailed
```

| 行为 | 输入 | 输出 |
|---|---|---|
| 生成场景 | kb_id + platforms | TestScenario[] |
| 修订场景 | scenario_id + 用户修改 | 更新后场景 |
| 预览场景 | project_id | 场景矩阵视图 |
| 导出场景矩阵 | project_id | 结构化场景清单 |

### 域五：执行调度域

```
职责：编排执行计划、分配平台、管理并发和重试
实体：RunPlan, RunRecord, Task
事件：RunStarted, RunCompleted, RunCancelled, TaskFailed
```

| 行为 | 输入 | 输出 |
|---|---|---|
| 创建执行计划 | project_id + platforms + scope | run_id |
| 取消执行 | run_id | — |
| 查询进度 | run_id | RunProgress |
| 重试 | run_id + case_ids | 新 run_id |

### 域六：平台执行域

```
职责：在各平台上执行具体的测试步骤
实体：PlatformExecutionContext, StepExecutionResult
```

各平台执行器职责：

| 执行器 | 平台 | 驱动 | 特有职责 |
|---|---|---|---|
| **WebExecutor** | PC Web / H5 | Playwright + Midscene.web | DOM 读取（L1 OCR）、网络拦截 |
| **AndroidExecutor** | Android | ADB + Midscene.android | logcat 采集、ANR 检测、Activity 管理 |
| **iOSExecutor** | iOS | WDA + Midscene.ios | syslog 采集、Crash 检测、键盘管理 |

### 域七：四维校验域

```
职责：对执行步骤执行四维度校验
实体：VerificationReport, DimensionResult
```

| 校验维度 | 校验内容 | 数据来源 | 判定方式 |
|---|---|---|---|
| **UI 渲染** | 文案、颜色、尺寸、布局、组件存在 | 截图 → OCR / DOM 文本 | 对照 UI 基准库 |
| **控制台** | JS Error、Waring、原生 Crash、ANR | console API / logcat / syslog | Error 级别过滤 |
| **API** | 状态码、响应结构、字段值、响应时间 | 网络请求拦截 | 对照预期结果 |
| **业务结果** | URL 变化、页面状态、提示信息 | 页面状态截图 | 对照业务规则 |

### 域八：综合分析域

> 这是 AutoTest 区别于所有测试框架的核心——**不是"四个维度独立校验"，而是"多维度交叉验证，输出综合论断"**。

```
职责：采集 UI / 控制台 / API 多维度数据，交叉验证，输出综合论断
实体：CrossDimensionReport, EvidenceChain, SynthesisConclusion
```

#### 核心逻辑

```yaml
输入:
  - 步骤截图（UI 状态）
  - 控制台日志（前端状态）
  - 网络请求/响应（API 状态）
  - 业务规则（预期结果）

处理:
  不是分别校验再拼报告，而是:
  1. 采集所有维度的原始数据
  2. 寻找维度间的因果关系（API 报错 → 前端 JS Error？）
  3. 构建证据链（一条链串联多个维度的异常）
  4. 输出综合论断（一个 Bug，附完整证据链，而不是 N 个独立失败）

输出:
  综合论断 + 证据链（一个缺陷一条链，不重复不遗漏）
```

#### 综合论断 vs 独立校验的对比

```
传统独立校验（API + 控制台 + UI 各报各的）:
  ❌ API 校验: /v1/orders 返回 500
  ❌ 控制台校验: TypeError: Cannot read 'orderId'
  ❌ UI 校验: 页面未显示订单列表
  📋 报告: 3 个独立失败
  👨‍💻 开发者: "这到底是一个 Bug 还是三个 Bug？先看 API……再看控制台……哦原来是一个问题"

AutoTest 综合论断:
  🔗 证据链 #1:
     源: 前端请求 /v1/orders 缺少 shipping_address 字段
     ↓
     果1: API 返回 500（缺少必填字段 -> NullPointerException）
     果2: 前端 catch 到 500 后尝试读取 orderId → TypeError
     果3: UI 显示空白 + "系统错误"提示
     ─────────────────────────────────────────
     结论: 1 个 Bug，3 个表象。前端少传了参数。

    ✅ 一个 Bug 一条链，开发者一眼看透。
```

| 行为 | 输入 | 输出 |
|---|---|---|
| 多维度采集 | 截图 + 控制台 + API 请求/响应 | 原始数据包 |
| 构建证据链 | 原始数据包 + 时间序列 | EvidenceChain[]（一条因果链串起多个维度） |
| 综合论断 | EvidenceChain[] + 业务规则 | SynthesisConclusion（一个缺陷一条结论） |
| 输出诊断报告 | SynthesisConclusion | 结构化诊断数据（含完整上下文，可直接给开发者和 AI 工具） |

### 域九：报告域

```
职责：生成结构化测试报告，供人类和 AI 消费
实体：TestReport, CrossPlatformReport
```

| 报告类型 | 消费方 | 格式 |
|---|---|---|
| 执行摘要 | 人（预览） | HTML / Markdown |
| 完整记录 | 人（回放） | HTML（含截图内嵌） |
| **结构化缺陷数据** | **AI 开发工具** | **JSON（含完整上下文）** |
| **AI 修复指令** | **Claude Code / OpenCode** | **MCP Tool 输出** |

### 域十：参考数据接口域

```
职责：将缺陷数据转化为结构化参考数据，通过 MCP 协议对外提供
```

这是 AutoTest 区别于所有测试框架的核心能力——产出"可以直接用来定位和修复 Bug 的完整参考数据"，而不是一堆看不懂的 pass/fail。

---

# 三、高质量测试结果数据设计

## 3.1 设计目标

```
测试结果的输出，必须达到这个标准：
随便找一个 AI 编程助手（Claude Code / Cursor / Copilot），
把这份数据丢给它，它就能理解 Bug 在哪、为什么发生、怎么修。

不需要人写复现步骤、不需要人截图说明、不需要人翻译日志。
```

## 3.2 结构化缺陷数据 Schema

```json
{
  "defect": {
    "id": "def_001",
    "type": "api_error",
    "severity": "high",
    "title": "创建订单 API 返回 500 Internal Server Error",
    "project": "电商后台",
    "platform": "web",
    "browser": "Chromium 130",
    "viewport": "1920×1080",
    "timestamp": "2026-05-14T14:30:00Z"
  },
  "step_context": {
    "business_line": "订单流程",
    "case_id": "tc_order_user_positive_003",
    "case_description": "普通用户正常创建一笔订单",
    "step_index": 3,
    "step_action": "点击'提交订单'按钮",
    "step_target": "提交订单按钮（页面底部，蓝色，320x40）"
  },
  "screenshots": {
    "before_click": "data:image/png;base64,...",
    "after_click": "data:image/png;base64,...",
    "error_state": "data:image/png;base64,..."
  },
  "console_logs": {
    "errors": [
      {
        "level": "error",
        "message": "Uncaught (in promise) TypeError: Cannot read properties of undefined (reading 'orderId')",
        "source": "app.7f3a2b.js:1:24356",
        "stack": "  at createOrder (app.7f3a2b.js:1:24356)\n  at HTMLButtonElement.onClick (app.7f3a2b.js:1:24501)",
        "timestamp": "14:30:01.234"
      }
    ],
    "warnings": [
      {
        "level": "warning",
        "message": "Deprecated API: .order() will be removed in v2.0",
        "source": "utils.js:1:8921"
      }
    ]
  },
  "api_calls": [
    {
      "request": {
        "method": "POST",
        "url": "https://api.example.com/v1/orders",
        "headers": {
          "content-type": "application/json",
          "authorization": "Bearer eyJ..."
        },
        "body": {
          "product_id": "prod_001",
          "quantity": 1,
          "address_id": "addr_001"
        }
      },
      "response": {
        "status": 500,
        "status_text": "Internal Server Error",
        "headers": { "content-type": "application/json" },
        "body": {
          "error": {
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred"
          }
        },
        "timing": {
          "start": "14:30:01.000",
          "end": "14:30:01.450",
          "duration_ms": 450
        }
      }
    }
  ],
  "page_state": {
    "current_url": "https://admin.example.com/orders/create/confirm",
    "visible_text_elements": [
      "确认订单", "商品名称: AI 鼠标", "数量: 1", "总价: ¥299.00",
      "提交订单", "系统错误，请稍后重试"
    ],
    "active_errors": [
      "页面顶部出现红色错误提示条: '系统错误，请稍后重试'"
    ]
  },
  "ai_analysis": {
    "failure_point": "点击'提交订单'后，后端 API /v1/orders 返回 500",
    "root_cause": "前端创建订单请求中缺少 shipping_address 字段，后端 OrderController.create() 未对必填字段做空值校验，导致 NullPointerException",
    "confidence": "high",
    "evidence": [
      "请求 body 中有 address_id 但没有 shipping_address 对象",
      "前端未将 address_id 反查为完整地址再提交",
      "控制台 JS Error 提示 Cannot read properties of undefined (reading 'orderId')——后端返回 500 后前端尝试读取不存在的 orderId"
    ]
  },
  "fix_suggestion": {
    "target": "前端",
    "file_hint": "src/api/orders.ts 或类似订单 API 调用文件",
    "description": "在提交订单前，需要将 address_id 反查为完整的 shipping_address 对象（包含 name、phone、province、city、district、detail），然后再 POST 给后端",
    "code_snippet": "// 修复前\nconst orderData = {\n  product_id,\n  quantity,\n  address_id  // ❌ 后端需要的是完整地址对象\n}\n\n// 修复后\nconst addressDetail = await getAddressDetail(address_id)\nconst orderData = {\n  product_id,\n  quantity,\n  shipping_address: {        // ✅ 补充完整地址对象\n    name: addressDetail.name,\n    phone: addressDetail.phone,\n    province: addressDetail.province,\n    city: addressDetail.city,\n    district: addressDetail.district,\n    detail: addressDetail.detail\n  }\n}",
    "estimated_effort": "1 个文件，约 10 行修改"
  },
  "cross_dimension_analysis": {
    "synthesis_conclusion": {
      "bug_count": 1,
      "is_single_cause": true,
      "summary": "1 个根因（前端缺参）→ 3 个表象（API 500 + JS Error + 页面空白），表象数量不意味着 Bug 数量",
      "primary_dimension": "api",
      "trigger_dimension": "api（/v1/orders 返回 500 是第一个异常信号）"
    },
    "evidence_chains": [
      {
        "chain_id": "chain_001",
        "root_trigger": {
          "dimension": "api",
          "event": "POST /v1/orders 返回 500 Internal Server Error",
          "timestamp": "14:30:01.450"
        },
        "propagation": [
          {
            "step": 1,
            "dimension": "api",
            "event": "前端 POST /v1/orders 缺少 shipping_address",
            "direction": "cause→effect 的起点"
          },
          {
            "step": 2,
            "dimension": "api",
            "event": "后端 NullPointerException → 返回 500",
            "direction": "← 后端未做空值校验"
          },
          {
            "step": 3,
            "dimension": "console",
            "event": "前端 catch(500) → TypeError('Cannot read orderId')",
            "direction": "← 前端异常处理未覆盖 500 情况"
          },
          {
            "step": 4,
            "dimension": "ui",
            "event": "页面显示空白 + 错误提示条",
            "direction": "← JS Error 导致渲染中断"
          }
        ],
        "chain_type": "api_error → console_error → ui_break",
        "chain_summary": "前端请求缺参 → 后端 500 → 前端异常处理不完善 → 页面渲染中断"
      }
    ],
    "dimension_correlations": {
      "independent_anomalies": [],
      "cascading_anomalies": [
        {
          "trigger": "api_error",
          "affected": ["console_error", "ui_broken"],
          "relation": "因果链"
        }
      ],
      "false_positives_excluded": [
        {
          "dimension": "console",
          "event": "Deprecated API warning on .order()",
          "reason": "与当前缺陷无关，是独立的废弃 API 警告",
          "excluded": true
        }
      ]
    }
  }
}
```

## 3.3 每步执行的完整数据采集

```yaml
执行步骤 N 的数据包（StepExecutionRecord）:
├── metadata
│   ├── step_index: int
│   ├── action: str              # 操作描述
│   ├── platform: str            # web/android/ios
│   ├── status: passed/failed/uncertain
│   └── duration_ms: int
│
├── screenshot_before: base64     # 操作前截图
├── screenshot_after: base64      # 操作后截图
│
├── console_snapshot
│   ├── errors: LogEntry[]       # 仅 ERROR 级别
│   ├── warnings: LogEntry[]     # 仅 WARNING 级别
│   └── full_log: LogEntry[]     # 完整日志（可选，按需）
│
├── network_snapshot
│   ├── requests: NetworkEntry[] # 该步骤期间的所有网络请求
│   └── failed: NetworkEntry[]   # 其中失败的请求
│
├── page_state                    # 操作后的页面状态（快照）
│   ├── url: str
│   ├── visible_texts: str[]
│   ├── active_alerts: str[]     # 页面上的错误/成功提示
│   └── key_components: [{name, visible, text}]
│
├── verifications
│   ├── ui:      {status, detail, confidence, ocr_level}
│   ├── console: {status, detail, error_count}
│   ├── api:     {status, detail, failed_request_count}
│   └── business:{status, detail}
│
└── raw_data                      # 原始数据（调试用）
    ├── screenshot_bytes: bytes
    ├── dom_snapshot: str
    └── raw_logs: str
```

## 3.4 质量指标

```yaml
每步执行的校验结果，不是简单的 pass/fail，而是：

置信度体系:
  ui校验置信度: 0-1    # OCR 识别准确度
  api校验置信度: 0-1    # 字段匹配度
  业务校验置信度: 0-1   # LLM 判断确信度

判定规则:
  all 置信度 ≥ 0.9 → pass
  any 置信度 < 0.6 → fail
  0.6-0.9 → uncertain（标记，不阻断执行，最终汇总展示）

缺陷分级:
  P0: 阻塞性（页面崩溃、API 500、核心流程不可用）
  P1: 严重（功能错误、数据错误）
  P2: 一般（UI 错位、文案错误）
  P3: 建议（性能、警告、体验）
```

---

# 四、从测试失败到高质量参考数据

## 4.1 核心定位

AutoTest 的职责止步于"产出高质量参考数据"。修 Bug 是开发者/AI 工具的事，AutoTest 不修 Bug。

```
传统测试的产出：
  "测试失败" → 开发者要自己复现 → 自己找日志 → 自己定位 → 猜修复方案
                 ↑ 每个环节重复劳动，每次都要做一遍

AutoTest 的产出：
  结构化缺陷数据 + 完整上下文 + AI 根因分析 + 修复参考建议
                 ↓
  开发者/AI 工具直接拿到"全部信息" → 理解问题 → 修复
```

**关键原则**：
1. AutoTest 产出证据，不下结论（AI 分析仅供参考，不替代人工判断）
2. AutoTest 提供完整上下文，不省略细节（截图、日志、API 快照全部附上）
3. AutoTest 的参考数据是"给修 Bug 的人用的"，不是给自己用的

## 4.2 缺陷报告的结构化输出

每次发现缺陷，AutoTest 产出包含完整参考数据的 JSON：

```json
{
  "defect": {
    "id": "def_001",
    "type": "api_error",
    "severity": "high",
    "title": "创建订单 API 返回 500 Internal Server Error"
  },
  "reproduction_steps": [
    {"step": 1, "action": "打开登录页", "url": "https://admin.example.com/login"},
    {"step": 2, "action": "输入用户名", "value": "admin@example.com"},
    {"step": 3, "action": "输入密码"},
    {"step": 4, "action": "点击登录"},
    {"step": 5, "action": "进入订单创建页"},
    {"step": 6, "action": "选择商品", "value": "AI 鼠标 × 1"},
    {"step": 7, "action": "点击提交订单", "result": "❌ API 500", "这里是失败步骤"}
  ],
  "evidence": {
    "screenshots": {
      "before_step": "base64...",
      "after_step": "base64...",
      "error_state": "base64..."
    },
    "console_logs": {
      "errors": [
        {
          "message": "Uncaught TypeError: Cannot read properties of undefined (reading 'orderId')",
          "source": "app.7f3a2b.js:1:24356",
          "stack": "  at createOrder (app.7f3a2b.js:1:24356)\n  at HTMLButtonElement.onClick (app.7f3a2b.js:1:24501)"
        }
      ]
    },
    "api_calls": [
      {
        "request": {
          "method": "POST",
          "url": "https://api.example.com/v1/orders",
          "headers": {"content-type": "application/json"},
          "body": {"product_id": "prod_001", "quantity": 1, "address_id": "addr_001"}
        },
        "response": {
          "status": 500,
          "body": {"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"}}
        }
      }
    ],
    "page_state": {
      "url": "https://admin.example.com/orders/create/confirm",
      "visible_alerts": ["系统错误，请稍后重试"]
    }
  },
  "ai_reference": {
    "root_cause_analysis": "前端请求体中有 address_id 但没有 shipping_address 对象。后端 OrderController.create() 未对必填字段做空值校验，收到缺字段的请求后抛出 NullPointerException，返回 500。",
    "root_cause_confidence": "high",
    "root_cause_evidence": [
      "请求 body 中有 address_id 但无 shipping_address",
      "API 响应 500 但未返回业务错误码，说明是未捕获的异常",
      "前端控制台 JS Error 提示 'Cannot read properties of undefined'——后端返回 500 后前端尝试读取不存在的 orderId"
    ],
    "fix_reference": {
      "problem_location": "前端订单提交逻辑缺少 address_id → shipping_address 的反查转换",
      "affected_layer": "前端 / API 调用层",
      "code_reference": "订单 API 调用文件，预计在 src/api/orders.ts 附近",
      "expected_changes": "提交订单前，通过 address_id 获取完整地址对象（name, phone, province, city, district, detail），拼接到请求 body 中",
      "code_snippet": {
        "before": "const orderData = { product_id, quantity, address_id }",
        "after": "const addr = await getAddressDetail(address_id)\nconst orderData = {\n  product_id, quantity,\n  shipping_address: {\n    name: addr.name, phone: addr.phone,\n    province: addr.province, city: addr.city,\n    district: addr.district, detail: addr.detail\n  }\n}"
      }
    }
  },
  "platform_context": {
    "platform": "web",
    "browser": "Chromium 130",
    "viewport": "1920×1080",
    "timestamp": "2026-05-14T14:30:00Z"
  }
}
```

## 4.3 每条缺陷数据的设计意图

| 字段 | 给谁用的 | 用途 |
|---|---|---|
| `defect` | 所有人 | 一眼知道是什么问题 |
| `reproduction_steps` | 开发者/AI | 不需要自己复现，直接知道第几步出的错 |
| `evidence.screenshots` | 人 | 截图一看就懂 |
| `evidence.console_logs` | 开发者/AI | JS Error 直接定位代码行号 |
| `evidence.api_calls` | 开发者/AI | 请求/响应完整数据，不需要抓包 |
| `evidence.page_state` | 人 | 页面上有什么错误提示 |
| `ai_reference.root_cause_analysis` | 开发者/AI | AI 分析的根因（参考，不百分百准确） |
| `ai_reference.root_cause_evidence` | 开发者 | 为什么 AI 这么判断，可追溯可质疑 |
| `ai_reference.fix_reference` | AI 编程助手 | 代码修改参考，不是"自动执行"，是"给出方向" |

## 4.4 消费参考数据的典型场景

```bash
# 场景 1：开发者在 Claude Code 中查看缺陷
> autotest get-defect def_001
# → 返回完整的结构化缺陷数据
# → 开发者直接看到：报错原因 + 错误 API + JS Error + 修复参考
# → 不需要离开 IDE 去翻测试报告

# 场景 2：AI 编程助手参考缺陷数据辅助修复
> autotest get-defect def_001 --format compact
# → AI 拿到结构化数据后，可以：
#   1. 读取 fixes_reference.code_snippet 理解修复方向
#   2. 读取 console_logs 定位源码
#   3. 读取 api_calls 理解请求/响应
#   4. 在对话中向开发者提出修复方案

# 场景 3：开发者直接看 HTML 报告
> autotest report run_001 --format html
# → 完整带截图的报告，适合快速浏览
```

## 4.5 MCP 参考数据接口

```python
@mcp.tool()
def get_defect(defect_id: str, format: str = "full") -> dict:
    """
    获取缺陷的完整参考数据。
    format: full（完整含截图base64）| compact（不含截图，适合 AI 处理）
    返回值包含完整的复现步骤、证据链、AI 分析参考。
    """
    defect = defect_repo.get_by_id(defect_id)
    if format == "compact":
        # 移除截图 base64 以减少 token 消耗
        defect.evidence.screenshots = {}
    return defect.to_dict()

@mcp.tool()
def list_defects(run_id: str, severity: str | None = None) -> list[dict]:
    """
    列出执行记录中的所有缺陷。
    用于批量查看，每条只返回摘要信息。
    """
    ...
```

---

# 五、技术分层

## 5.1 六层架构

```
┌───────────────────────────────────────────────────────────────┐
│                     接口层（路由 + 协议适配）                    │
│  REST API | MCP Server | WebSocket | CLI                      │
├───────────────────────────────────────────────────────────────┤
│                     业务编排层（Service）                       │
│  ProjectService | RunService | ReportService                  │
├───────────────────────────────────────────────────────────────┤
│                     领域层（Domain）                           │
│  Project | RunRecord | KnowledgeBase | TestCase | Defect      │
├───────────────────────────────────────────────────────────────┤
│                     基础设施接口层（Interface）                  │
│  ProjectRepository | RunRepository | AIService | OCRService   │
├───────────────────────────────────────────────────────────────┤
│                     基础设施实现层（Infrastructure）             │
│  SQLAlchemy | LiteLLM | PaddleOCR | MidsceneService           │
├───────────────────────────────────────────────────────────────┤
│                     执行器层（独立服务）                         │
│  Midscene Web | Midscene Android | Midscene iOS | Playwright  │
└───────────────────────────────────────────────────────────────┘
```

## 5.2 业务域与分层映射

```
业务域                主要驻留层
──────────────────────────────────────────────────
项目管理域            接口 + 业务编排 + 领域
文档解析域            业务编排 + 基础设施（AI）
知识库域              领域（实体 + 值对象）
场景生成域            业务编排 + 领域
综合分析域            基础设施（多维采集）+ 业务编排（交叉论断）
执行调度域            业务编排 + 基础设施（Celery）
平台执行域            执行器层（独立 Node 服务）
四维校验域            基础设施（OCR + 日志 + 网络）
缺陷分析域            业务编排 + 基础设施（AI）
报告域                业务编排 + 接口
参考数据接口域         接口（MCP）
```

---

# 六、传统测试痛点对应方案

| 痛点 | 在 AutoTest 中的解决方式 | 所在章节 |
|---|---|---|
| **测试和修正是断裂的** | 结构化参考数据，开发者/AI 工具直接拿来修 | 三、四 |
| **测试结果只有人能看** | 结构化 JSON + MCP 接口，AI 原生消费 | 三 |
| **脚本维护成本高** | 视觉驱动（页面改版零影响）+ AI 生成（无需人工写） | 一 |
| **一维校验覆盖不全** | 四维校验（UI + 控制台 + API + 业务） | 校验域 |
| **多平台多套脚本** | 统一 PlatformDriver 接口 + 同一套 AI 视觉引擎 | 平台执行域 |
| **Bug 复现困难** | 每步完整数据包（截图 + 日志 + API + 页面状态） | 3.3 |
| **定位根因耗时** | AI 自动根因分析 + 证据链 | 3.2 ai_analysis |
| **修复建议靠猜** | AI 生成修复建议 + 代码 diff + 影响文件定位 | 3.2 fix_suggestion |

---

# 七、综合分析引擎：如何从"多维度数据"到"一条证据链"

> 传统四维校验是四个独立的水桶。综合分析引擎是把四个桶的水倒在一起，找到哪里漏。

## 7.1 核心问题

```
测试执行中会产生多个维度的数据：
  ├── UI 截图
  ├── 控制台日志
  ├── API 请求/响应
  └── 页面状态

这些数据不是孤立的。一个 Bug 通常会在多个维度上留下痕迹。
问题是：如何从多个维度的信号中，还原出"这一个 Bug"的全貌？

单个维度的视角：
  API 校验: "500 了"                    → 后端问题？
  控制台校验: "JS Error"               → 前端问题？
  UI 校验: "页面空白"                   → 渲染问题？
  ─────────────────────────────────
  三个维度各报各的 → 开发者要自己串

综合分析的视角：
  API 500（报错） → JS Error（处理失败） → 页面空白（结果）
  ─────────────────────────────────
  一条证据链串起来 → 一个 Bug，三个表象
```

## 7.2 综合分析管线

```
Step 执行完成
  │
  ├── 1. 多维度原始数据采集（并行）
  │     ├── UI:
  │     │   ├── 操作前后截图
  │     │   ├── DOM 可见文本（Web）
  │     │   └── 页面 URL + 标题
  │     ├── 控制台:
  │     │   ├── error 级别日志（带堆栈）
  │     │   ├── warning 级别日志
  │     │   └── 时间戳
  │     ├── API:
  │     │   ├── 请求方法 + URL + headers + body
  │     │   ├── 响应状态码 + headers + body
  │     │   └── 耗时
  │     └── 业务:
  │         ├── 预期结果
  │         └── 实际页面状态
  │
  ├── ▶ 2. 单维度初步判定（快速过滤）
  │     每个维度独立判断是否异常
  │     无异常 → 直接 pass（不进入综合分析，节省 Token）
  │     有异常 → 标记异常级别 + 进入综合分析
  │
  ├── 3. 跨维度时空关联（核心）
  │     以时间为轴，将所有维度的异常信号对齐到同一时间线
  │     输出：时序对齐的异常事件列表
  │
  ├── 4. 证据链构建
  │     寻找事件间的因果关系：A → B → C
  │     输出：一条或多条证据链
  │
  ├── 5. 综合论断
  │     对每条证据链总结：
  │     ├── 根因是什么（哪个维度最先异常）
  │     ├── 传播路径（异常如何扩散到其他维度）
  │     ├── 表现数量（N 个表象 ≠ N 个 Bug）
  │     └── 排除误报（独立异常不做关联）
  │
  └── 6. 输出诊断报告
        综合论断 + 证据链 + 原始数据（完整上下文）
```

## 7.3 时空关联算法

```python
async def cross_dimension_analysis(step_data: StepExecutionData) -> CrossDimensionReport:
    """跨维度综合分析：时间对齐 → 因果发现 → 证据链构建"""

    # Step 1: 时间对齐
    timeline = Timeline()
    # 将各维度数据按时间戳对齐到同一时间线
    for entry in step_data.console_logs.errors:
        timeline.add_event(entry.timestamp, "console", entry)

    for req in step_data.network_snapshot.requests:
        timeline.add_event(req.timing.start, "api_start", req)
        timeline.add_event(req.timing.end, "api_end", req)

    if step_data.screenshot_after:
        timeline.add_event(step_data.timestamp, "screenshot", step_data.screenshot_after)

    # Step 2: 异常检测（每个维度独立判断）
    anomalies = []
    if has_api_error(step_data.network_snapshot):
        anomalies.append(Anomaly("api", step_data.network_snapshot.failed_requests))
    if has_console_error(step_data.console_logs):
        anomalies.append(Anomaly("console", step_data.console_logs.errors))
    if has_ui_anomaly(step_data.page_state, step_data.expected):
        anomalies.append(Anomaly("ui", step_data.page_state.active_alerts))

    # 无异常 → 直接通过
    if not anomalies:
        return CrossDimensionReport(status="pass", anomalies=[])

    # Step 3: 时序因果发现
    # 按时间排序异常事件
    sorted_events = sort_by_timestamp(anomalies)

    # 寻找因果链：如果 A 发生在 B 之前，且 A 和 B 在语义上相关，则 A 可能是 B 的原因
    chains = []
    used_events = set()

    for i, event_a in enumerate(sorted_events):
        if event_a.id in used_events:
            continue
        chain = EvidenceChain(root=event_a)
        for j, event_b in enumerate(sorted_events):
            if j <= i or event_b.id in used_events:
                continue
            if await is_causally_related(event_a, event_b):
                chain.add_link(event_a, event_b)
                used_events.add(event_b.id)
        if len(chain.links) > 0:  # 至少有一个关联
            chains.append(chain)
            used_events.add(event_a.id)

    # 未关联的异常：独立事件，不是当前 Bug 的一部分
    independent = [e for e in sorted_events if e.id not in used_events]

    return CrossDimensionReport(
        status="fail",
        anomalies=anomalies,
        synthesis=SynthesisConclusion(
            bug_count=len(chains),
            evidence_chains=chains,
            independent_anomalies=independent,
        )
    )


async def is_causally_related(event_a: Anomaly, event_b: Anomaly) -> bool:
    """判断两个异常事件是否有因果关系。

    判断依据：
    1. 时序：A 在 B 之前（≥ 50ms，排除并发记录差异）
    2. 语义：A 的类型是否能解释 B 的发生
       - api_error → console_error：API 报错可能导致前端 JS 异常
       - console_error → ui_broken：JS 异常可能导致渲染中断
       - api_error → ui_broken：API 报错可能导致页面空数据
    3. 来源：涉及同一业务模块（通过 URL/API path 匹配）
    """
    # 时序检查
    time_diff = event_b.timestamp - event_a.timestamp
    if time_diff < 0.05:  # 50ms 内的视为并发
        return False

    # 语义关联检查
    causal_rules = [
        ("api_error", "console_error"),    # API 报错 → JS 处理异常
        ("api_error", "ui_broken"),         # API 报错 → 页面数据缺失
        ("console_error", "ui_broken"),     # JS Error → 渲染中断
        ("api_error", "api_error"),         # API 级联失败
    ]
    if (event_a.dimension, event_b.dimension) not in causal_rules:
        return False

    # 业务模块匹配
    # 如果两个异常涉及同一个 API 路径或页面 URL，关联性显著提高
    if event_a.business_module == event_b.business_module:
        return True

    # 用 LLM 做最后判断（低置信度场景）
    llm_verdict = await llm_judge_causal_relation(event_a, event_b)
    return llm_verdict
```

## 7.4 维度相关性规则库

```yaml
已知因果关系规则（不断积累扩展）:
  api_error → console_error:
    条件: API 返回 4xx/5xx 的 500ms 内，控制台出现 JS Error
    典型场景:
      - 后端返回 500 → 前端 .catch() 代码未处理 → TypeError
      - API 返回 403 → 前端未判断权限 → 空白页
    误报排除:
      - API 返回 404（可能是无关的资源加载）
      - 控制台 Error 发生在前 200ms（可能是页面自身的初始化错误）

  console_error → ui_broken:
    条件: 控制台出现未捕获异常后，页面关键组件未渲染
    典型场景:
      - JS 解析失败 → 组件 render() 中断 → 页面区域空白
      - 第三方 SDK 加载失败 → 相关功能区域不可用
    误报排除:
      - console.error 但页面正常（被 error boundary 捕获）
      - 非关键组件的渲染失败

  api_error → api_error:
    条件: 请求 A 失败后，请求 B 因依赖 A 的数据也失败
    典型场景:
      - 登录 token 过期 → 后续所有需要鉴权的 API 都 401
      - 获取用户信息失败 → 依赖用户信息的接口全部异常

  api_slow → ui_broken:
    条件: API 响应 > 5s，页面因等待超时显示空白或 loading
    典型场景:
      - 列表接口超时 → 页面显示"加载中"不动
      - 提交接口超时 → 按钮一直 loading 状态
```

## 7.5 综合论断的输出

```yaml
综合论断的输出，是给"修 Bug 的人"最重要的信息：

输出结构:
  bug_count: int
    # 真正的 Bug 数量（不是异常事件数量）
    # API 500 + JS Error + UI 空白 = 1 个 Bug，不是 3 个

  evidence_chains: EvidenceChain[]
    # 每个 Bug 对应一条证据链
    # 链 = 根因 → 传播 → 表现

  excluded: Anomaly[]
    # 被排除的异常（与当前 Bug 无关）
    # 比如"一个废弃 API 警告"不是这个 Bug 的原因

  summary: str
    # 一句话总结，给开发者第一眼就理解
    # "1 个根因（前端缺参）→ 3 个表象（API 500 + JS Error + 页面空白）"
```

### 诊断报告示例

```
📋 执行步骤 #3 "点击提交订单" 综合分析结果
────────────────────────────────────────
❌ 发现 1 个缺陷，涉及 3 个维度

🔗 证据链:
  始 → API: 请求缺少必填字段 → 后端返回 500 (14:30:01.450)
  传 → 控制台: .catch(500) 未处理 → TypeError (14:30:01.510)
  终 → UI: 渲染中断 → 页面空白 + 错误提示 (14:30:01.600)
  ────────────────────────────────────────
  结论: 1 个 Bug（前端逻辑缺陷），3 个表象。不是 API 问题。

📊 维度统计:
  API:   ✅ 正常请求 12 | ❌ 失败 1（已关联）
  控制台: ✅ 无异常 0    | ❌ Error 1（已关联） | ⚠️ Warning 1（已排除）
  UI:    ✅ 正常渲染 0   | ❌ 异常 1（已关联）

🔇 已排除误报:
  - Warning: .order() 废弃警告（独立于当前 Bug 的其他问题）
```

## 7.6 与传统四维校验的本质区别

```
传统四维校验:
  各维度独立检查，独立报告
  → UI pass/fail
  → 控制台 pass/fail
  → API pass/fail
  → 业务 pass/fail
  → "不清楚这三个失败是不是同一个 Bug"
  ↔ 开发者是最终的"串接者"

综合分析引擎:
  各维度先独立检查 → 有异常才进入综合分析
  → 时间对齐 → 因果发现 → 证据链构建 → 综合论断
  → "1 个 Bug，3 个表象，证据链在这里"
  ↔ 框架负责串接，开发者拿来就用
```

---

# 八、业务建模工程化：如何从"AI 猜"到"工程化准确"

> 这是框架前置环节的核心挑战。AI 提取业务规则不是"一次 Prompt 搞定"的事。
> 必须用工程化手段，将"AI 可能出错"这个事实纳入系统设计，用多阶段 Pipeline + 校验门 +
> 冲突消解 + 人工确认环，把准确率从"可能 70%"推到"工程可信 95%+"。

> 这是整个框架最核心的技术挑战。AI 提取业务规则不是"一次 Prompt 搞定"的事。
> 必须用工程化手段，将"AI 可能出错"这个事实纳入系统设计，用多阶段 Pipeline + 校验门 +
> 冲突消解 + 人工确认环，把准确率从"可能 70%"推到"工程可信 95%+"。

## 8.1 核心问题：AI 提取的"概率性" vs 工程需要的"确定性"

### 问题本质

```
AI 模型（LLM/VL）的输出是概率性的：
同一个 Prompt 问 10 次，可能得到 10 个不同的结果。
├── 8 次基本正确
├── 1 次遗漏了关键规则
└── 1 次产生了幻觉（编造不存在的规则）

而测试系统需要的是确定性的业务模型：
├── 这个系统有哪些角色？ → 确定的角色清单
├── 这个角色能做什么？ → 确定的权限集合
└── 这个业务流程是怎样的？ → 确定的步骤序列
```

AutoTest 的工程化思路：**不依赖单次 AI 调用的准确率，而是用多阶段流水线 + 校验机制，将最终输出的准确率推到工程可信水平**。

### 工程化目标

```
文档 → 业务模型的准确率目标：
├── 角色清单覆盖： ≥ 98%（最多遗漏 1 个角色）
├── 权限规则准确： ≥ 95%（规则与文档一致，无误报）
├── 业务流程完整： ≥ 90%（主流程不缺步骤，分支场景覆盖 80%+）
└── 冲突检测率：   100%（文档间自相矛盾的地方全部标记）
```

## 8.2 整体 Pipeline 设计

```
文档 URL
  │
  ├── Stage 1: 原始采集
  │     目标：获取原始文档内容
  │     输出：{raw_markdown, metadata, structure}
  │     ⚡ 失败处理：重试 3 次 → 跳过 → 标记"文档不可用"
  │
  ├── ▶ 校验门 1：内容完整性
  │     检查：文档是否成功拉取、是否有正文内容、是否匹配预期平台
  │     失败：标记文档异常，不进入下一阶段
  │
  ├── Stage 2: 内容结构化
  │     目标：将非结构化文档拆分为有结构的章节
  │     输出：[{heading, content, level, type}]
  │     方法：标题层级解析 + 语义段落分割
  │
  ├── ▶ 校验门 2：结构合理性
  │     检查：章节数量是否合理（不是 1 篇论文拆出 200 节）、
  │           每节是否有实质内容（不是只有标题）
  │     失败：调整分割参数重试 → 标记为"结构异常"
  │
  ├── Stage 3: 规则提取（核心）
  │     目标：从每个章节中提取结构化规则
  │     方法：多策略并行提取（见 7.3）
  │     输出：多个候选规则集
  │
  ├── ▶ 校验门 3：规则一致性（核心）
  │     目标：消除候选规则间的冲突（见 7.4）
  │     方法：冲突检测 → 置信度裁决 → 人工标记
  │     输出：唯一规则集 + 冲突清单
  │
  ├── Stage 4: 业务链构建
  │     目标：将孤立的规则串联为完整业务流程
  │     方法：依赖分析 + 拓扑排序（见 7.5）
  │     输出：业务链 DAG
  │
  ├── ▶ 校验门 4：业务链完整性
  │     目标：检查是否存在断裂的业务链
  │     方法：遍历 DAG → 标记断头节点 → 提示补全
  │     输出：完整业务链 + 建议补充的缺失环节
  │
  ├── Stage 5: 场景生成
  │     目标：从业务链生成可执行的测试用例
  │     输出：测试矩阵（完整场景）
  │
  └── ▶ 校验门 5：场景覆盖度
       目标：量化场景覆盖是否达到阈值
       输出：覆盖报告 + 已/未覆盖场景清单
```

## 8.3 多策略并行提取

单次 AI 调用不可靠。工程化的解法：**同一份内容用多种策略并行提取，交叉验证**。

```
同一章节内容
  │
  ├── 策略 A：通用提取 Prompt
  │     用标准 Prompt 提取业务流程、角色、规则
  │     优点：覆盖广
  │     缺点：对特殊文档格式适应性差
  │
  ├── 策略 B：结构化 Prompt（Schema-guided）
  │     用严格 JSON Schema 约束输出格式
  │     优点：输出格式稳定，解析零失败
  │     缺点：可能遗漏 Schema 未定义的边缘信息
  │
  ├── 策略 C：多轮追问
  │     第一轮：提取你认为重要的业务规则
  │     第二轮：针对第一轮输出追问细节
  │     "你提到用户登录有验证码，验证码的规则是什么？"
  │     优点：深度挖掘，减少遗漏
  │     缺点：Token 消耗高，耗时翻倍
  │
  └── 策略 D：反向校验 Prompt
       不提取规则，而是问"有哪些规则可能被我漏掉？"
       优点：捕获边缘情况
       缺点：输出不稳定

合并阶段：
  A ∩ B ∩ C ∩ D → 高置信度规则（直接入库）
  (A ∪ B ∪ C) - (A ∩ B ∩ C) → 候选规则（需二次确认）
  仅 D 产出 → 低置信度规则（标记待人工确认）
  任何策略报告矛盾 → 触发冲突消解流程
```

### 提取 Prompt 的工程化设计

```yaml
# prompt_templates/document_parse.yaml
# 不是"一段 Prompt 打天下"，而是多角色 Prompt 协作

roles:
  - role: "业务分析师"
    system: |
      你是一个资深的业务分析师。你需要从产品需求文档中提取完整的业务流程。
      关注：用户操作步骤、系统响应、页面跳转、数据流转。
      忽略：背景介绍、项目目标、技术方案。
    stages:
      - name: "提取流程"
        prompt: "从以下文档中提取所有业务流程，用列表形式列出每个流程的完整步骤序列"

  - role: "测试架构师"
    system: |
      你是一个测试架构师。你需要从需求文档中提取所有可测试的规则。
      关注：输入校验、边界条件、异常处理、权限控制。
      忽略：界面布局描述、色彩规范。
    stages:
      - name: "提取规则"
        prompt: "从以下文档中提取所有可测试的规则，包括输入约束、异常场景、权限控制"

  - role: "UI 规范师"
    system: |
      你是一个 UI 规范师。你需要从设计文档中提取可量化的 UI 标准。
      关注：文案、颜色、尺寸、间距、组件规范。
    stages:
      - name: "提取 UI 标准"
        prompt: "从以下文档中提取 UI 相关规范，只提取有明确数值或可对比的信息"
```

**多角色 Prompt 的原理**：每个角色只关注自己擅长的领域，降低单次提取的复杂度。每个角色只输出自己领域的信息，最后合并。

## 8.4 冲突检测与消解

这是工程化的关键——文档之间、规则之间必然存在冲突，必须系统化处理。

### 冲突类型

```
冲突类型
├── 类型 A：同义冲突
│    文档 A："管理员可以删除用户"
│    文档 B："超级管理员可以删除用户"
│    本质：同一件事不同表述
│    处理：语义相似度匹配 → 合并
│
├── 类型 B：层级冲突
│    文档 A："管理员有全部权限"
│    文档 B："管理员不可以导出数据"
│    本质：概略描述 vs 精确例外
│    处理：以精确描述为准，概略描述降级为注释
│
├── 类型 C：矛盾冲突
│    文档 A："验证码 60 秒有效"
│    文档 B："验证码 5 分钟有效"
│    本质：同一规则不同标准
│    处理：标记为"信息冲突"，无法自动裁决，需要人工确认
│
├── 类型 D：遗漏冲突
│    文档 A 提到角色 A，文档 B 没提到
│    本质：信息缺失
│    处理：以存在的为准，标记"信息来自单一来源"
│
└── 类型 E：版本冲突
      文档 A 是 v2.0："登录改为手机号+验证码"
      文档 B 是 v1.0："登录使用账号+密码"
      本质：文档版本不一致
      处理：检查文档元数据中的版本信息，以最新版本为准
```

### 冲突消解 Pipeline

```
候选规则集合
  │
  ├── 1. 语义去重
  │     方法：embedding 向量化 → 余弦相似度 ≥ 0.85 → 视为同义
  │     输出：去重后的规则集
  │
  ├── 2. 层级关系检测
  │     方法：规则 A 的语义范围是否包含规则 B
  │     "管理员有全部权限" ⊃ "管理员可以登录" → 保留"可以登录"，注释"全部权限"
  │
  ├── 3. 矛盾检测 → 无法自动裁决
  │     方法：规则 A 和规则 B 断言同一对象但结论互斥
  │     输出：冲突清单 [rule_a, rule_b, conflict_reason]
  │
  └── 4. 置信度排序
        方法：每条规则附加 confidence 分数
        confidence = (extraction_strategies_match_count / total_strategies) × llm_self_score
        低置信度规则 → 标记为"候选"，不进入自动场景生成
```

### 冲突标记的数据结构

```json
{
  "conflict_id": "conflict_001",
  "type": "contradiction",
  "source_a": {
    "document_url": "https://xxx.feishu.cn/wiki/prd",
    "rule_text": "验证码 60 秒有效",
    "extracted_by": "业务分析师策略",
    "confidence": 0.92
  },
  "source_b": {
    "document_url": "https://xxx.feishu.cn/wiki/spec",
    "rule_text": "验证码 5 分钟有效",
    "extracted_by": "测试架构师策略",
    "confidence": 0.88
  },
  "resolution": "pending",   // pending | resolved | wontfix
  "resolution_note": "",
  "suggested_action": "建议与产品经理确认验证码有效期的正确值"
}
```

## 8.5 业务链构建

### 从孤立规则到完整业务链

单条规则是孤立的。业务链是把规则串联成完整流程。

```
孤立规则集合：
├── "登录需要用户名和密码"
├── "密码错误 5 次锁定账号"
├── "登录成功后跳转首页"
├── "首页显示用户信息"
├── "用户信息包括头像和昵称"
├── "订单需要登录才能查看"
└── ...

业务链构建（经过依赖分析 + 拓扑排序）：
├── 业务链：用户登录
│     Step 1: 打开登录页
│     Step 2: 输入用户名 + 密码
│     Step 3: 点击登录
│     Step 4: 系统验证凭据
│       ├── 成功 → 跳转首页
│       │     Step 5: 首页显示用户头像和昵称 → 链结束
│       └── 失败 → 显示错误提示
│             Step 5: 错误 5 次 → 锁定账号 → 链结束
│
├── 业务链：查看订单
│     Step 1: 登录（前置依赖）
│     Step 2: 导航到订单中心
│     Step 3: 查看订单列表
│     └── ...
│
└── ...
```

### 依赖分析算法

```python
async def build_business_chains(rules: list[BusinessRule]) -> list[BusinessChain]:
    """从业务规则构建完整的业务链 DAG"""

    # Step 1: 从规则中提取页面/资源/操作引用
    pages: dict[str, PageNode] = {}
    for rule in rules:
        # AI 提取规则中提及的页面和操作
        refs = await ai_extract_references(rule.description)
        for ref in refs:
            # 构建引用图
            if ref.type == "page":
                pages[ref.name] = PageNode(
                    name=ref.name,
                    actions=ref.actions,
                    transitions=ref.transitions,
                )

    # Step 2: 构建页面跳转图 → DAG
    graph = DiGraph()
    for page_name, page in pages.items():
        graph.add_node(page_name)
        for transition in page.transitions:
            graph.add_edge(page_name, transition.target_page)

    # Step 3: 拓扑排序 → 可执行的流程步骤序列
    # 如果 DAG 有环（A→B→C→A），不一定是出错了
    # 可能是业务回环（订单→支付→订单详情），保留为环
    topo_order = topological_sort(graph)

    # Step 4: 识别断头节点（只有入没有出的页面）
    # 这些可能是文档遗漏的页面，标记为"链不完整"
    dead_ends = find_dead_ends(graph)
    if dead_ends:
        for node in dead_ends:
            suggest_continuation = await ai_suggest_pages(node, rules)
            report_chain_gap(node, suggest_continuation)

    return build_chains_from_dag(graph, rules)
```

### 业务链完整性评分

```yaml
完整性评分维度:
  节点完整度:
    - 已知页面 / (已知页面 + 推断缺失页面)
    - 分数 ≥ 0.8 → 绿色（可以直接用）
    - 分数 0.5-0.8 → 黄色（建议人工补充）
    - 分数 < 0.5 → 红色（文档信息不足，不建议自动生成场景）

  边完整度:
    - 已确认跳转 / 总跳转数
    - 推断跳转不计入确认数

  规则覆盖度:
    - 已关联规则 / (已关联 + 未关联规则)
    - 未关联规则表示提取了但无法放入任何业务链
    - 可能是不重要的细节规则，也可能是重大遗漏
```

## 8.6 场景生成的质量保障

### 测试用例的**确定性**保证

AI 生成的测试用例需要保证：

```yaml
确定性保证:
  1. 每一步都是可执行的
     - "输入用户名" → ✅ 可执行
     - "确保系统正常" → ❌ 不可执行

  2. 每一步都有明确的预期结果
     - "点击登录 → URL 跳转到 /dashboard" → ✅ 可校验
     - "点击登录 → 应该成功" → ❌ 含糊

  3. 每一步的校验维度明确
     - 第 2 步检查: UI + API
     - 第 4 步检查: 控制台 + 业务结果

  4. 异常场景有明确的触发条件
     - "输入密码错误 5 次" → ✅ 可复现
     - "系统异常" → ❌ 无法触发
```

### 场景覆盖的**完整性**保证

```python
async def measure_scenario_coverage(kb: KnowledgeBase, scenarios: list[TestCase]) -> CoverageReport:
    """量化场景覆盖是否达到阈值"""

    # 1. 规则覆盖率
    all_rules = extract_all_rules_from_kb(kb)
    covered_rules = set()
    for scenario in scenarios:
        case_rules = extract_rules_from_scenario(scenario)
        covered_rules.update(case_rules)
    rule_coverage = len(covered_rules) / len(all_rules)

    # 2. 页面覆盖率
    all_pages = kb.get_all_pages()
    covered_pages = set()
    for scenario in scenarios:
        covered_pages.update(scenario.get_all_page_refs())
    page_coverage = len(covered_pages) / len(all_pages)

    # 3. 角色覆盖率
    all_roles = kb.roles
    covered_roles = set()
    for scenario in scenarios:
        covered_roles.add(scenario.role)
    role_coverage = len(covered_roles) / len(all_roles)

    # 4. 路径类型分布
    type_distribution = {
        "positive": sum(1 for s in scenarios if s.type == "positive"),
        "boundary": sum(1 for s in scenarios if s.type == "boundary"),
        "abnormal": sum(1 for s in scenarios if s.type == "abnormal"),
        "permission": sum(1 for s in scenarios if s.type == "permission"),
    }

    report = CoverageReport(
        rule_coverage=rule_coverage,
        page_coverage=page_coverage,
        role_coverage=role_coverage,
        type_distribution=type_distribution,
        gaps=[],
    )

    # 报告未覆盖项
    if rule_coverage < 0.85:
        uncovered = all_rules - covered_rules
        for rule in uncovered:
            report.gaps.append(GapItem(
                type="uncovered_rule",
                detail=f"规则未被任何场景覆盖: {rule.description}",
                suggestion="考虑补充该规则的测试场景",
            ))

    return report
```

### 场景质量的 5 级评级

```
S 级：完美覆盖
   规则覆盖 ≥ 95%，页面覆盖 ≥ 95%，角色覆盖 100%
   正向/边界/异常/权限四类路径完整，无遗漏
   → 可直接用于生产回归

A 级：良好覆盖
   规则覆盖 ≥ 85%，页面覆盖 ≥ 85%，角色覆盖 ≥ 90%
   四类路径基本完整，有少量边缘遗漏
   → 建议人工补充遗漏后用于生产

B 级：基本覆盖
   规则覆盖 ≥ 70%，页面覆盖 ≥ 70%，角色覆盖 ≥ 80%
   缺少部分异常或权限路径
   → 仅建议用于增量测试，不宜替代全量回归

C 级：覆盖不足
   规则覆盖 ≥ 50%
   只覆盖了主流程，异常/边界路径大量缺失
   → 建议补充文档信息后重新生成

D 级：不可用
   规则覆盖 < 50%
   文档信息不足或提取质量不够
   → 不生成测试，提示用户补充文档
```

## 8.7 人工确认环（Human-in-the-Loop）

工程化的关键不是"消灭人工"，而是**让人工干预发生在正确的位置，且最小化**。

```
Pipeline 中的人工确认点：
  │
  ├── 确认点 1：文档解析后（✅ 可选，首次强烈建议）
  │     展示：AI 提取的业务规则、角色清单、UI 标准
  │     操作：勾选/删除/修改规则
  │     时机：项目首次创建时
  │
  ├── 确认点 2：业务链预览（✅ 可选，首次建议）
  │     展示：业务链 DAG 图、每个链的步骤
  │     操作：补充缺失节点、删除错误跳转
  │     时机：项目首次创建时
  │
  ├── 确认点 3：场景预览（✅ 可选）
  │     展示：测试矩阵（业务线×角色×场景类型）
  │     操作：删除/新增/修改用例
  │     时机：每次场景重新生成时
  │
  └── 确认点 4：冲突裁决（✅ 必选，无法自动消解时）
       展示：冲突规则清单（来源、原文、差异）
       操作：选择以哪个规则为准，或输入正确值
       时机：冲突自动消解失败时
```

**设计原则**：

```yaml
人工确认设计原则:
  1. 首次全面确认，后续抽样确认
     - 首次创建项目时，建议完整过一遍 AI 提取结果
     - 后续文档更新后，只展示变更部分

  2. 默认信任，异常告警
     - AI 置信度 ≥ 0.9 的规则 → 直接入库，不打扰用户
     - 置信度在 0.7-0.9 的规则 → 黄色提示
     - 置信度 < 0.7 或检测到冲突 → 红色告警，必须确认

  3. 每一次人工确认都在训练模型
     - 用户修改了某个规则 → 记录差异 → 作为后续提取的 few-shot 示例
     - 用户标记了误报 → 调整置信度阈值

  4. 可跳过，可回退
     - 所有确认点都可以跳过（默认使用 AI 结果）
     - 任何时候可以回退到上一步修改
```

## 8.8 知识库版本化与增量更新

### 版本化

```json
{
  "kb_id": "kb_001",
  "project_id": "proj_001",
  "version": 3,
  "created_at": "2026-05-14T10:00:00Z",
  "source_documents": [
    { "url": "https://.../prd", "version": "2.1", "last_fetched": "2026-05-14T10:00:00Z" },
    { "url": "https://.../ui",  "version": "1.3", "last_fetched": "2026-05-14T10:00:00Z" }
  ],
  "changelog": [
    { "version": 1, "change": "初始知识库构建", "rules_count": 45 },
    { "version": 2, "change": "新增订单业务线（文档更新）", "rules_added": 12, "rules_removed": 0 },
    { "version": 3, "change": "修改验证码有效期规则（人工修正）", "rules_modified": 1 }
  ],
  "quality_score": {
    "overall": "A",
    "rule_coverage": 0.91,
    "confidence": 0.88,
    "human_reviewed": true
  }
}
```

### 增量更新

```python
async def incremental_update(project_id: str) -> KnowledgeBase:
    """增量更新知识库：只处理变更的文档，复用已有的规则"""

    old_kb = await knowledge_repo.get_latest(project_id)

    # 1. 检测文档变更
    changed_docs = []
    for doc_ref in old_kb.source_documents:
        if await document_has_changed(doc_ref):
            changed_docs.append(doc_ref)

    if not changed_docs:
        return old_kb  # 无变更，直接返回

    # 2. 只重新解析变更的文档
    new_rules = []
    for doc_ref in changed_docs:
        extract = await parse_single_document(doc_ref)
        new_rules.extend(extract.rules)

    # 3. 对比新旧规则
    old_rules = old_kb.get_all_rules()
    added = detect_new_rules(new_rules, old_rules)
    removed = detect_removed_rules(new_rules, old_rules)
    modified = detect_modified_rules(new_rules, old_rules)

    # 4. 只对变更部分执行冲突检测
    conflicts = await detect_conflicts(added + modified)

    # 5. 构建新版本知识库
    new_kb = old_kb.create_next_version(
        added=added,
        removed=removed,
        modified=modified,
        conflicts=conflicts,
    )

    return new_kb
```

## 8.9 质量监控与持续改进

```
每个知识库版本打一个质量标签：
├── S: 完美（置信度 ≥ 0.95，人工确认通过）
├── A: 良好（置信度 ≥ 0.85，无未消解冲突）
├── B: 可用（置信度 ≥ 0.70，有少量候选规则）
├── C: 需人工（置信度 < 0.70 或有关键冲突未消解）
└── D: 不可用（文档拉取失败或提取完全失败）

自动追踪指标：
├── 知识库版本号
├── 规则总数
├── 规则覆盖率（已覆盖 vs 应覆盖的估算）
├── 平均置信度
├── 未消解冲突数
├── 人工确认率（用户修改了多少 AI 提取结果）
└── 场景生成通过率（生成的有效场景 / 总生成场景）
```

---

# 九、开发路线图

| 阶段 | 里程碑 | 核心交付 |
|---|---|---|
| **Phase 1** | 核心打底 | 项目管理 + 文档解析 + 知识库 + Web 执行 + CLI |
| **Phase 2** | 四维校验 | UI/Console/API/业务 校验管线 + 结构化输出 |
| **Phase 3** | 缺陷分析 AI | AI 根因分析 + 修复建议生成 + MCP 修复接口 |
| **Phase 4** | 多平台 | Android + iOS 执行器 + 跨平台对比 |
| **Phase 5** | 参考数据深化 | 增强截图标注 + 日志结构化 + 代码引用链接 + 项目结构理解 |

---

> **一句话总结**：AutoTest 不只是"找到 Bug"，而是产出**AI 可消费的结构化缺陷数据**，让 AI 开发工具可以直接把 Bug 修掉。

---

# 十、用户角色与用户故事

## 10.1 角色定义

```yaml
角色全景:
  ┌──────────────────────────────────────────────────────┐
  │     AutoTest 用户生态                                   │
  │                                                      │
  │  ┌──────────────┐  ┌──────────────┐                   │
  │  │  QA 测试工程师 │  │  SDET         │                   │
  │  │（主要使用者）  │  │（脚本/框架维护） │                   │
  │  └──────┬───────┘  └──────┬───────┘                   │
  │         │                  │                           │
  │         ▼                  ▼                           │
  │  ┌─────────────────────────────────────────────┐     │
  │  │              AutoTest 系统                     │     │
  │  └─────────────────────────────────────────────┘     │
  │         │                  │                           │
  │         ▼                  ▼                           │
  │  ┌──────────────┐  ┌──────────────┐                   │
  │  │ 产品经理/业务    │  │  AI 编程助手    │                   │
  │  │（消费报告）    │  │（消费缺陷数据）  │                   │
  │  └──────────────┘  └──────────────┘                   │
  └──────────────────────────────────────────────────────┘
```

| 角色 | 职级 | 核心诉求 | 使用频率 | 技术能力 |
|------|------|----------|----------|----------|
| QA 测试工程师 | P5-P7 | 减少重复劳动，快速验证 | 每日 | 中等（会写脚本） |
| SDET / QA 开发 | P6-P8 | 维护测试框架，集成 CI | 每周 | 高（会编程） |
| 产品经理/业务 | P6-P8 | 查看测试覆盖报告 | 按需 | 低（只看报告） |
| AI 编程助手 | - | 消费结构化缺陷数据直接修复 | 自动 | 极高（MCP协议） |
| 技术管理者 | P8+ | 质量趋势、团队效率 | 每周 | 中（看仪表板） |

## 10.2 用户故事

### QA 测试工程师 — 15 个故事

```yaml
US-001: 一键接入测试
  As a: QA 测试工程师
  I want: 输入项目地址/文档链接即可自动生成测试
  So that: 无需手动编写任何测试脚本
  验收标准:
    - 输入 PRD 文档 URL 后自动抽取业务规则
    - 自动生成可执行的测试场景
    - 整个过程无需人工干预
  Phase: 1 | 优先级: P0

US-002: 全自动无人执行
  As a: QA 测试工程师
  I want: 一键启动全量回归测试，自动在 Web/App 上执行
  So that: 测试执行完全无人值守
  验收标准:
    - 支持定时执行（每晚凌晨运行）
    - 支持 CI 触发执行（代码合入后自动运行）
    - 执行过程中无需人工介入
    - 浏览器/设备自动管理
  Phase: 1 | 优先级: P0

US-003: 缺陷根因一目了然
  As a: QA 测试工程师
  I want: 测试失败时直接看到 AI 分析的根因和修复建议
  So that: 不需要自己翻日志、看截图、猜问题
  验收标准:
    - 每个失败步骤输出结构化缺陷数据
    - 包含根因分析（自然语言描述）
    - 包含修复建议（可执行的自然语言指令或代码 diff）
    - 包含完整的证据链（截图+日志+API快照）
  Phase: 3 | 优先级: P0

US-004: 多平台一次执行
  As a: QA 测试工程师
  I want: 同一个测试用例同时在 Web、Android、iOS 上执行
  So that: 不需要为每个平台维护不同的脚本
  验收标准:
    - 一次配置，多平台执行
    - 输出跨平台对比报告
    - 平台特有逻辑自动适配
  Phase: 4 | 优先级: P1

US-005: 报告直观可读
  As a: QA 测试工程师
  I want: 看到带截图的 HTML 报告，一眼知道哪些用例失败
  So that: 快速向团队同步测试结果
  验收标准:
    - HTML 报告内嵌截图
    - 失败用例高亮并关联缺陷
    - 支持导出分享
  Phase: 1 | 优先级: P1

US-006: 增量更新知识库
  As a: QA 测试工程师
  I want: PRD 更新后只重新解析变更部分
  So that: 不需要每次从头解析
  验收标准:
    - 自动检测文档是否变更
    - 只处理变更内容
    - 保留已有的人工确认结果
  Phase: 2 | 优先级: P1

US-007: 人工介入修正提取结果
  As a: QA 测试工程师
  I want: 在 AI 自动生成的规则中发现错误时可以手动修正
  So that: 保证知识库的准确性
  验收标准:
    - 规则列表可编辑
    - 冲突可手动裁决
    - 修正后的规则作为后续 few-shot 示例
  Phase: 1 | 优先级: P1

US-008: 按需重试失败用例
  As a: QA 测试工程师
  I want: 只重新执行失败的测试用例，而不是全部重跑
  So that: 节省验证时间
  验收标准:
    - 支持选择特定用例重试
    - 支持选择特定平台重试
    - 重试次数和策略可配置
  Phase: 2 | 优先级: P2

US-009: 实时查看执行进度
  As a: QA 测试工程师
  I want: 在执行过程中实时看到进度和中间结果
  So that: 不需要等到全部跑完才知道结果
  验收标准:
    - WebSocket 推送实时进度
    - 每个步骤完成后可查看截图
    - 发现缺陷立即推送
  Phase: 1 | 优先级: P1

US-010: 异常场景智能识别
  As a: QA 测试工程师
  I want: AI 自动识别文档中的异常场景和边界条件
  So that: 不需要自己手动设计异常用例
  验收标准:
    - 自动生成边界值测试
    - 自动生成异常路径测试
    - 自动生成权限测试
  Phase: 2 | 优先级: P1

US-011: 版本回归对比
  As a: QA 测试工程师
  I want: 对比两次执行结果的差异
  So that: 快速知道新版本引入了哪些新问题
  验收标准:
    - 两次执行的缺陷差异对比
    - 新增/修复/未解决的缺陷分类
    - 覆盖率变化趋势
  Phase: 3 | 优先级: P2

US-012: 执行历史追溯
  As a: QA 测试工程师
  I want: 查看过去 N 次执行的历史记录和趋势
  So that: 了解质量趋势和回归情况
  验收标准:
    - 执行历史列表（含摘要）
    - 通过率趋势图
    - 缺陷趋势图
  Phase: 2 | 优先级: P2

US-013: 覆盖度量化
  As a: QA 测试工程师
  I want: 看到当前测试场景对业务规则的覆盖率
  So that: 知道哪些业务场景没有被覆盖
  验收标准:
    - 规则/页面/角色三维覆盖率
    - S/A/B/C/D 评级
    - 未覆盖项清单
  Phase: 2 | 优先级: P1

US-014: 误报标记与反馈
  As a: QA 测试工程师
  I want: 标记 AI 误报的缺陷
  So that: 系统可以学习并减少重复误报
  验收标准:
    - 缺陷详情页有"误报"标记按钮
    - 标记后系统记录并调整策略
    - 类似场景不再重复报警
  Phase: 3 | 优先级: P2

US-015: CLI 快速操作
  As a: QA 测试工程师
  I want: 在命令行快速启动测试和查看结果
  So that: 不需要打开浏览器操作
  验收标准:
    - `autotest run start` 启动测试
    - `autotest defect get <id>` 查看缺陷
    - `autotest report get <run_id>` 查看报告
  Phase: 1 | 优先级: P1
```

### SDET / QA 开发 — 8 个故事

```yaml
US-SDET-001: 自定义校验规则
  As a: SDET
  I want: 在 AI 自动校验之外，添加自定义的校验逻辑
  So that: 覆盖 AI 无法处理的特殊业务场景
  验收标准:
    - 提供插件化校验接口
    - 支持 Python 脚本自定义校验
    - 自定义校验与 AI 校验结果合并
  Phase: 3 | 优先级: P2

US-SDET-002: 场景模板复用
  As a: SDET
  I want: 将通用的测试场景保存为模板
  So that: 不同项目可以复用已有场景
  验收标准:
    - 场景可导出为模板
    - 模板可导入到新项目
    - 模板支持参数化
  Phase: 2 | 优先级: P2

US-SDET-003: CI 集成
  As a: SDET
  I want: 将 AutoTest 集成到 CI/CD 流水线
  So that: 每次代码合入自动触发回归测试
  验收标准:
    - 提供 CLI 命令用于 CI 调用
    - 执行结果以 JUnit XML 格式输出
    - 支持 GitHub Actions / GitLab CI / Jenkins 等
  Phase: 1 | 优先级: P1

US-SDET-004: 执行器集群管理
  As a: SDET
  I want: 管理多个执行器节点的状态
  So that: 确保执行资源充足并按需扩容
  验收标准:
    - 执行器节点状态看板
    - 节点增减不影响正在执行的任务
    - 队列积压时自动告警
  Phase: 2 | 优先级: P2

US-SDET-005: API 集成
  As a: SDET
  I want: 通过 REST API 管理项目和执行
  So that: 集成到内部工具平台
  验收标准:
    - 完整 REST API
    - API Key 认证
    - OpenAPI 文档可浏览
  Phase: 1 | 优先级: P1

US-SDET-006: 自定义执行器
  As a: SDET
  I want: 添加自定义平台执行器
  So that: 支持测试内部自研平台
  验收标准:
    - 提供执行器 SDK/接口规范
    - 实现 PlatformExecutor 接口即可接入
    - 自定义执行器与内置执行器同等对待
  Phase: 4 | 优先级: P3

US-SDET-007: 性能基准对比
  As a: SDET
  I want: 在测试中自动采集页面性能数据
  So that: 发现性能退化
  验收标准:
    - 采集 LCP/FID/CLS 等 Web Vitals
    - 对比前后版本的性能差异
    - 性能退化超阈值自动告警
  Phase: 5 | 优先级: P3

US-SDET-008: 数据脱敏配置
  As a: SDET
  I want: 配置敏感信息的脱敏规则
  So that: 截图和日志中不泄露用户数据
  验收标准:
    - 支持正则表达式配置脱敏字段
    - 截图中的敏感区域自动模糊
    - 日志中的 Token/密码自动替换
  Phase: 2 | 优先级: P2
```

### 产品经理/业务 — 4 个故事

```yaml
US-PM-001: 覆盖度报告
  As a: 产品经理
  I want: 看到新功能在发布前已经通过自动化测试验证
  So that: 有信心上线
  验收标准:
    - 可查看功能覆盖率报告
    - 可查看执行通过率
    - 可查看未覆盖的功能点
  Phase: 2 | 优先级: P1

US-PM-002: 质量趋势看板
  As a: 产品经理
  I want: 看到项目维度的质量趋势
  So that: 了解整体质量走向
  验收标准:
    - 通过率趋势图表
    - 缺陷发现/修复趋势
    - 版本对比
  Phase: 3 | 优先级: P2

US-PM-003: 一键分享报告
  As a: 产品经理
  I want: 将测试报告一键分享给团队
  So that: 同步测试结果
  验收标准:
    - 生成公开分享链接
    - 报告含执行摘要
    - 移动端可查看
  Phase: 2 | 优先级: P2

US-PM-004: 文档变更通知
  As a: 产品经理
  I want: 文档更新时自动触发测试重新生成
  So that: 测试始终与最新需求对齐
  验收标准:
    - 文档变更自动检测
    - 增量更新知识库
    - 差异报告通知
  Phase: 3 | 优先级: P3
```

### AI 编程助手 — 3 个故事

```yaml
US-AI-001: 消费缺陷数据自动修复
  As a: Claude Code / Cursor / Copilot
  I want: 通过 MCP 协议获取缺陷的结构化数据
  So that: 自动理解 Bug 根因并生成修复代码
  验收标准:
    - MCP get_defect 返回完整结构化数据
    - AI 工具可直接消费
    - 包含修复建议和代码 diff
  Phase: 3 | 优先级: P0

US-AI-002: 获取复现步骤
  As a: AI 编程助手
  I want: 拿到缺陷的完整复现步骤
  So that: 不需要人工写复现说明
  验收标准:
    - 缺陷数据包含操作步骤序列
    - 每步有截图和输入值
    - 失败步骤明确标记
  Phase: 3 | 优先级: P0

US-AI-003: 修复验证闭环
  As a: AI 编程助手
  I want: 修复代码后触发 AutoTest 重新验证
  So that: 确认修复是否有效
  验收标准:
    - 提供"验证修复"接口
    - 只运行关联用例
    - 返回修复验证结果
  Phase: 3 | 优先级: P2
```

---

# 十一、术语表 (Glossary)

```yaml
术语定义（按字母序）:

  AutoTest:
    定义: 本系统的名称，一个基于 Midscene.js 的全自动 AI UI 测试框架。
    别名: 无

  四维校验 (4-D Verification):
    定义: 对每个测试步骤，从 UI 渲染、控制台日志、API 请求/响应、业务结果四个维度独立校验。
    涉及: 校验域

  业务线 (Business Line):
    定义: 一组相关的业务流程，如"用户登录""创建订单""商品管理"。一个业务线包含多个业务链。
    示例: user_login, order_flow, product_management

  业务链 (Business Chain):
    定义: 从业务规则构建的有向无环图，描述一个完整的业务流程步骤序列。
    参见: 知识库

  业务规则 (Business Rule):
    定义: AI 从产品文档中提取的可测试规则，包括流程步骤、角色权限、UI 标准等。
    分类: flow | rule | permission | ui

  场景覆盖度 (Coverage Grade):
    定义: S/A/B/C/D 五级评分，衡量测试场景对业务规则/页面/角色的覆盖程度。
    阈值: S≥95%, A≥85%, B≥70%, C≥50%, D<50%

  因果规则引擎 (Causal Rule Engine):
    定义: 综合分析引擎中的静态规则引擎，基于已知因果模式（如 api_error→console_error）快速判断异常间的因果关系。覆盖约 80% 场景。

  证据链 (Evidence Chain):
    定义: 综合分析引擎的输出，将多个维度的异常信号串联为一条因果链。一个 Bug 对应一条证据链。
    示例: API 500 → JS Error → UI 空白

  综合分析 (Cross-Dimension Analysis):
    定义: AutoTest 的核心差异化能力。不满足于各维度独立校验，而是通过时间对齐、因果发现、证据链构建，将多个信号还原为一个 Bug 的全貌。
    参见: 四维校验, 证据链

  执行器 (Executor):
    定义: 实际执行测试步骤的服务。分为 Web Executor (Playwright+Midscene.web)、Android Executor (ADB+Midscene.android)、iOS Executor (WDA+Midscene.ios)。

  Flow (流程规则):
    定义: 描述用户操作步骤和系统响应的业务规则。最常见的规则类型。
    示例: "用户输入用户名密码后点击登录，系统验证凭据，成功后跳转首页"

  Human-in-the-Loop (人工确认环):
    定义: 在 AI 自动处理的 Pipeline 中设置的人工确认点，用于修正 AI 输出。遵循"首次全量确认，后续增量确认"原则。

  知识库 (Knowledge Base):
    定义: 从产品文档中抽取的结构化业务知识集合，是场景生成和业务校验的数据源。版本化管理。

  Midscene.js:
    定义: 核心 AI 视觉驱动引擎。通过截图+AI 模型识别 UI 元素位置，实现自然语言驱动的 UI 操作，消除对 DOM 选择器的依赖。

  MCP (Model Context Protocol):
    定义: 开放协议，定义 AI 模型与外部工具/数据源的交互方式。AutoTest 通过 MCP Server 向 AI 开发工具提供缺陷参考数据。

  多策略并行提取 (Multi-Strategy Extraction):
    定义: 文档解析阶段的核心工程化策略。同一文档用 4 种不同策略（通用/结构化/追问/反向）并行提取规则，交叉验证提高准确率。

  项目 (Project):
    定义: AutoTest 中的顶层业务实体。一个项目包含一个被测系统的完整配置、文档引用、知识库、测试场景和执行历史。

  规则冲突 (Rule Conflict):
    定义: 多策略提取或跨文档提取中出现的规则矛盾。分 5 种类型：同义冲突、层级冲突、矛盾冲突、遗漏冲突、版本冲突。

  SDD (Specification-Driven Development):
    定义: 本项目的开发方法论。以详尽的规格定义为驱动的开发方式，在编码前完成架构、API、数据库、详细设计等全部文档。

  测试场景 (Test Scenario):
    定义: 一组相关测试用例的集合。按业务线×角色×类型（正向/边界/异常/权限）组织。

  测试用例 (Test Case):
    定义: 单个可执行的测试，包含前置条件、步骤序列、预期结果。

  时间对齐 (Timeline Alignment):
    定义: 综合分析的第一步。将各维度的异常信号按时间戳对齐到统一时间线，为因果发现奠定基础。

  UI 标准 (UI Standard):
    定义: 从 UI 设计文档中提取的可量化 UI 规范，如颜色、字号、间距、组件尺寸等。用于 UI 校验维度。

  视觉驱动 (Vision-Driven):
    定义: AutoTest 的核心定位方式。不依赖 DOM 选择器（XPath/CSS），而是通过截图+AI 模型识别 UI 元素。页面改版零影响。
```

---

# 十二、非功能性需求 (NFRs)

## 12.1 性能需求

```yaml
API 响应时间（P95，排除 AI 调用）:
  ┌──────────────────────────────┬──────────┬──────────┐
  │ 操作类型                      │ 目标(P95) │ 熔断阈值  │
  ├──────────────────────────────┼──────────┼──────────┤
  │ 常规查询（列表、详情）          │ 200ms    │ 2s       │
  │ 写操作（创建、更新）            │ 500ms    │ 5s       │
  │ 报告生成（含截图）              │ 5s       │ 30s      │
  │ 文件上传（截图，<10MB）         │ 3s       │ 10s      │
  │ 执行进度查询（WebSocket）       │ 100ms    │ 1s       │
  └──────────────────────────────┴──────────┴──────────┘

AI 调用延迟:
  ┌──────────────────────────────┬──────────┬──────────┐
  │ AI 操作                      │ 目标(P95) │ 超时阈值  │
  ├──────────────────────────────┼──────────┼──────────┤
  │ 规则提取（单文档）              │ 60s      │ 180s     │
  │ 根因分析                      │ 15s      │ 30s      │
  │ 修复建议生成                   │ 20s      │ 45s      │
  │ 因果判断（LLM 兜底）            │ 5s       │ 15s      │
  │ 视觉定位（Midscene 单步）       │ 5s       │ 15s      │
  └──────────────────────────────┴──────────┴──────────┘

执行性能:
  ┌──────────────────────────────┬──────────┐
  │ 指标                          │ 目标      │
  ├──────────────────────────────┼──────────┤
  │ 单步执行（简单点击/输入）         │ <5s      │
  │ 单步执行（复杂 AI 定位）         │ <10s     │
  │ 单用例（10 步级）                │ <60s     │
  │ 100 用例回归（4 并发）           │ <30min   │
  │ 单机并发浏览器数                │ 4-8 实例  │
  └──────────────────────────────┴──────────┘

吞吐量:
  ┌──────────────────────────────┬──────────┐
  │ 指标                          │ 目标      │
  ├──────────────────────────────┼──────────┤
  │ API 吞吐                      │ 1000 QPS │
  │ 并发 AI 调用                   │ 20       │
  │ 并发执行用例                    │ 50       │
  │ 日执行用例上限                  │ 5000     │
  └──────────────────────────────┴──────────┘
```

## 12.2 可用性需求

```yaml
服务可用性:
  API 服务: 99.5%（月度停机 ≤ 3.6 小时）
  MCP 服务: 99.9%（AI 工具随时需要调用）
  执行器服务: 99%（允许短时不可用，任务排队）

故障恢复:
  计划内停机: < 30 分钟（升级维护）
  计划外故障: 
    - API 宕机: < 5 分钟恢复
    - 数据库宕机: < 15 分钟恢复（主从切换）
    - 执行器宕机: 任务自动重调度 < 2 分钟

执行可靠性:
  单步执行成功率: ≥ 99%（排除被测应用本身的 Bug）
  测试结果误报率: ≤ 5%
  AI 提取成功率: ≥ 95%（文档内容合规时）
```

## 12.3 可扩展性需求

```yaml
水平扩展:
  API 服务: 无状态，支持 2-8 节点
  执行器: 无状态，支持 2-20 节点
  Celery Worker: 支持 2-10 节点

数据规模:
  单项目最大文档数: 50
  单项目最大规则数: 500
  单项目最大用例数: 500
  单次执行最大步骤数: 5000
  截图单文件大小上限: 10MB
  产品数据保留期: 
    - 活跃数据: 30 天
    - 归档数据: 永久

平台扩展:
  新增执行器平台: 实现 PlatformExecutor 接口（5 个方法）即可接入
  Phase 4 目标: 支持 Web + Android + iOS
```

## 12.4 安全性需求

```yaml
认证与授权:
  API: API Key (32 位) 或 JWT
  项目隔离: 项目间数据完全隔离
  操作审计: 所有写操作记录审计日志

数据安全:
  传输: 全部 HTTPS
  存储: 截图和日志中的敏感信息自动脱敏
  Token/密码: 不在日志中明文记录

执行安全:
  执行器沙箱: 隔离的浏览器环境
  网络限制: 执行器只能访问被测应用和目标网络
  资源限制: 单执行器 CPU/内存上限
```

## 12.5 可维护性需求

```yaml
部署与运维:
  部署方式: Docker Compose / K8s
  配置管理: 环境变量 + ConfigMap
  日志: 结构化 JSON 日志
  监控: Prometheus metrics 端点
  告警: P1/P2/P3 分级告警

代码质量:
  测试覆盖率: ≥ 80%
  类型检查: mypy strict mode
  Lint: ruff 全规则启用
  API 文档: OpenAPI 自动生成
```

---

# 十三、竞品差异化矩阵

## 13.1 全维度对比

```yaml
对比维度: 选择对用户有实际意义的 12 个维度

维度 1: 测试创建方式
  Playwright:    人工编写脚本（天级）
  Selenium:      人工编写脚本（天级）
  Cypress:       人工编写脚本（天级）
  Appium:        人工编写脚本（天级）
  AutoTest:      AI 自动生成（分钟级）

维度 2: 元素定位方式
  Playwright:    CSS/XPath/ID（DOM 耦合）
  Selenium:      CSS/XPath/ID（DOM 耦合）
  Cypress:       选择器（DOM 耦合）
  Appium:        XPath/ID（DOM 耦合）
  AutoTest:      纯视觉（截图+AI，改 UI 零影响）

维度 3: 跨平台支持
  Playwright:    仅 Web
  Selenium:      Web + Android (limited)
  Cypress:       仅 Web
  Appium:        Android + iOS
  AutoTest:      Web + Android + iOS（统一 AI 视觉引擎）

维度 4: 脚本维护成本（年）
  Playwright:    编写成本的 2-3 倍
  Selenium:      编写成本的 2-3 倍
  Cypress:       编写成本的 2-3 倍
  Appium:        编写成本的 2-3 倍
  AutoTest:      趋近于零（视觉驱动+AI 生成）

维度 5: 校验维度
  Playwright:    功能断言为主
  Selenium:      功能断言为主
  Cypress:       功能+网络
  Appium:        功能断言为主
  AutoTest:      UI + 控制台 + API + 业务（四维）

维度 6: 缺陷诊断能力
  Playwright:    pass/fail + 截图
  Selenium:      pass/fail + 截图
  Cypress:       pass/fail + 截图 + 视频回放
  Appium:        pass/fail + 截图
  AutoTest:      结构化缺陷数据 + 根因分析 + 修复建议 + 完整上下文

维度 7: 输出格式
  Playwright:    HTML 报告
  Selenium:      HTML 报告
  Cypress:       HTML 报告 + 视频
  Appium:        HTML 报告
  AutoTest:      JSON（AI 可消费）+ HTML（人看）+ MCP（工具消费）

维度 8: AI 修复能力
  Playwright:    无
  Selenium:      无
  Cypress:       无
  Appium:        无
  AutoTest:      输出修复参考数据，AI 开发工具直接消费

维度 9: 页面改版影响
  Playwright:    脚本全挂（DOM 变更）
  Selenium:      脚本全挂（DOM 变更）
  Cypress:       脚本全挂（DOM 变更）
  Appium:        脚本全挂（DOM 变更）
  AutoTest:      零影响（视觉驱动）

维度 10: 因果分析
  Playwright:    无
  Selenium:      无
  Cypress:       无
  Appium:        无
  AutoTest:      证据链构建 + 多维度交叉验证

维度 11: 文档理解
  Playwright:    无
  Selenium:      无
  Cypress:       无
  Appium:        无
  AutoTest:      AI 自动理解 PRD/UI 规范生成测试

维度 12: 人工介入需求
  Playwright:    高频（脚本维护、调试）
  Selenium:      高频
  Cypress:       中频
  Appium:        高频
  AutoTest:      低频（首次确认 AI 提取结果）
```

## 13.2 AutoTest 的不可替代性

```yaml
AutoTest 做对而其他框架做不到的 5 件事:

1. 从文档到测试的全自动化
   输入: PRD 文档 URL → 输出: 可执行的测试用例
   这是 AutoTest 与所有传统框架的根本区别。
   传统框架自动化的是"执行"环节，AutoTest 自动化的是"生成"环节。

2. 测试产出 = AI 开发工具的输入
   AutoTest 的结构化缺陷数据是给 AI 编程助手"吃"的。
   不是给人看的 HTML 报告，而是可以直接用来定位和修复 Bug 的结构化参考数据。

3. 多维度交叉验证而非独立校验
   传统: UI 报错 + API 报错 + 控制台报错 = 3 个独立失败
   AutoTest: API 500 → JS Error → UI 空白 = 1 个缺陷 + 1 条证据链
   这不是维度更多，而是维度之间的关系被理解。

4. 页面改版零影响
   视觉驱动意味着 UI 随便改，测试不用改。
   这不是维护成本低，而是维护成本趋近于零。

5. AI 提取的工程化准确率保证
   不是"一次 Prompt 搞定"，而是多策略并行提取 + 交叉验证 + 冲突消解。
   把 AI 从"可能会猜错"推到"工程可信 95%+"。
```

---

# 十四、风险分析与缓解策略

## 14.1 技术风险

```yaml
R-01: AI 提取质量不达标
  概率: 中 | 影响: 高
  描述: AI 从文档提取业务规则的质量（召回率/精确率）达不到工程化阈值
  缓解:
    - 多策略并行提取（4 策略交叉验证）
    - 置信度分级（≥0.9 直接入库，<0.7 标记待人工确认）
    - 人工确认环（Human-in-the-Loop）
    - 知识库版本化（可回退到旧版本）
  触发条件: 召回率 < 80% 或精确率 < 85%
  应急: 临时增加人工确认环节，同时调优 Prompt

R-02: AI 视觉定位不稳定
  概率: 中 | 影响: 高
  描述: Midscene.js 的 AI 视觉定位在不同页面、不同 UI 风格下准确率波动
  缓解:
    - 同时使用 OCR 和 DOM 文本作为双重定位
    - 支持用户提供元素截图作为 few-shot 参考
    - 定位失败自动重试（更换 Prompt 表述）
    - 策略降级: AI 视觉 → DOM 文本匹配 → XPath 备用
  触发条件: 单步定位失败率 > 5%
  应急: 切换到 DOM 文本模式

R-03: 执行器浏览器兼容性问题
  概率: 低 | 影响: 中
  描述: 被测应用在特定浏览器上表现异常导致测试失败
  缓解:
    - 支持 Chromium/Firefox/WebKit 切换
    - 基于 Playwright，天然跨浏览器
    - 测试报告标注浏览器版本
  触发条件: 浏览器兼容性导致的误报率 > 3%

R-04: AI Token 成本失控
  概率: 中 | 影响: 中
  描述: 大规模解析和执行中 AI 调用量巨大，Token 成本超出预算
  缓解:
    - 文档解析: 增量更新（只处理变更）
    - AI 调用: 缓存相同内容的调用结果
    - 模型分级: 核心分析用 GPT-4o，边缘判断用 GPT-4o-mini
    - Token 预算: 每次执行设定 Token 上限
    - 成本看板: 实时显示 Token 消耗
  触发条件: 月度 AI 成本超预算 20%
  应急: 切换到低成本模型

R-05: 长时间执行中断
  概率: 低 | 影响: 高
  描述: 大规模回归执行中因为网络/设备/服务问题中断，已完成的步骤数据丢失
  缓解:
    - 每步执行结果实时持久化（不缓存，立即写库）
    - 支持断点续跑（从中断的用例开始重试）
    - Celery 任务自动重试
    - 执行器心跳检测 + 超时自动重分配
  触发条件: 执行中断超过 2 分钟
  应急: 自动重新调度失败任务

R-06: 多文档冲突复杂度过高
  概率: 中 | 影响: 中
  描述: 多个产品文档之间存在大量无法自动消解的冲突，需要频繁人工介入
  缓解:
    - 冲突自动检测 + 分类（5 种类型）
    - 自动消解策略覆盖大部分场景
    - 冲突预览界面让用户一目了然
    - 版本信息自动提取辅助裁决
  触发条件: 未消解冲突占比 > 20%
```

## 14.2 项目风险

```yaml
R-07: 开发资源不足
  概率: 中 | 影响: 高
  描述: Phase 1-5 的开发工作量被低估，实际交付周期远超计划
  缓解:
    - 每个 Phase 都有明确范围边界
    - Phase 1 仅覆盖 Web 平台，降低起步复杂度
    - 核心 Pipeline 优先可运行，增强迭代
  触发条件: Phase 1 延迟超过 2 周
  应急: 裁剪 Phase 1 范围，只保留最核心功能

R-08: 依赖服务不可用
  概率: 低 | 影响: 高
  描述: 外部依赖（OpenAI API、GitHub、Docker Registry）服务中断
  缓解:
    - AI 多模型供应商（OpenAI + Claude + GLM）
    - 本地 Fallback 能力（PaddleOCR 本地运行不需要云端）
    - 离线模式: 拉取文档后本地处理
  触发条件: 上游 AI 服务中断 > 30 分钟
  应急: 切换到备用 AI 供应商
```

## 14.3 风险矩阵总览

```yaml
风险优先矩阵（概率×影响）:

  高影响:
    ├── R-01 AI提取质量 (中概率) → 🔴 最高优先级
    ├── R-05 执行中断 (低概率) → 🟡 需预案
    ├── R-07 开发资源 (中概率) → 🔴 最高优先级
    └── R-08 依赖服务 (低概率) → 🟡 需预案

  中影响:
    ├── R-02 视觉定位 (中概率) → 🟡 需监控
    ├── R-04 Token成本 (中概率) → 🟡 需监控
    └── R-06 文档冲突 (中概率) → 🟢 可接受

  低影响:
    └── R-03 浏览器兼容 (低概率) → 🟢 可接受

应对策略:
  🔴 高优先级: 需要在设计和实现阶段投入资源主动缓解
  🟡 需预案: 建立监控告警+应急预案，但不提前投入大量开发资源
  🟢 可接受: 保持现状，问题出现时再处理
```

