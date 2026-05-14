# AutoTest — 软件架构设计文档 (Architecture Design Document)

> 版本: 1.0 | 最后更新: 2026-05-14 | 状态: 初始草稿
> 基于 SDD (Specification-Driven Development) 方法

---

## 修订历史

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|----------|
| 1.0 | 2026-05-14 | AutoTest 架构组 | 初始架构设计 |

---

## 目录

1. [引言](#1-引言)
2. [架构视图](#2-架构视图)
3. [六层架构详解](#3-六层架构详解)
4. [业务域架构映射](#4-业务域架构映射)
5. [技术选型与决策](#5-技术选型与决策)
6. [关键架构决策 (ADRs)](#6-关键架构决策-adrs)
7. [质量属性设计](#7-质量属性设计)
8. [安全架构](#8-安全架构)
9. [部署架构](#9-部署架构)
10. [演进架构](#10-演进架构)

---

## 1. 引言

### 1.1 目的

本文档描述 AutoTest 系统的软件架构设计，涵盖系统分层、组件交互、技术选型、关键架构决策和质量属性设计。本文档面向架构师、开发人员和技术管理者。

### 1.2 范围

本文档覆盖 AutoTest v1.0 的全部架构层面，包括：

- 六层架构的分层设计与职责
- 十大业务域在分层中的落位
- 核心技术选型及其决策理由
- 关键架构决策记录 (ADRs)
- 质量属性（性能、可用性、可扩展性、安全性）的设计考量

### 1.3 参考文档

| 文档 | 位置 |
|------|------|
| 需求规格说明书 | `docs/基于Midscene.js 全自动无人介入AI UI测试框架.md` |
| API 接口规范 | `docs/API接口规范.md` |
| 数据库设计 | `docs/数据库设计.md` |
| 详细设计说明书 | `docs/详细设计说明书.md` |

---

## 2. 架构视图

### 2.1 系统上下文 (Context Diagram)

```
┌─────────────────────────────────────────────────────────┐
│                    外部系统边界                           │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │
│  │          │  │          │  │ AI 开发工具            │  │
│  │  用户     │  │ CI/CD    │  │ (Claude Code/Cursor/  │  │
│  │ (Web UI) │  │ (Jenkins/│  │  Copilot)             │  │
│  │          │  │  GitHub  │  │                       │  │
│  │          │  │  Actions)│  │  MCP 协议 ←→          │  │
│  └─────┬────┘  └─────┬────┘  └──────────┬───────────┘  │
│        │             │                  │               │
│        ▼             ▼                  ▼               │
│  ┌─────────────────────────────────────────────────┐    │
│  │               AutoTest 系统                      │    │
│  │  全自动 AI UI 测试框架（六层架构）                │    │
│  └─────────────────────────────────────────────────┘    │
│        │             │                  │               │
│        ▼             ▼                  ▼               │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │
│  │ 被测 Web │  │被测 Android│  │ 被测 iOS App        │  │
│  │ 应用     │  │ 应用      │  │                     │  │
│  └──────────┘  └──────────┘  └──────────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 2.2 容器视图 (Container Diagram)

```
┌───────────────────────────────────────────────────────────────────┐
│ AutoTest 系统容器图                                                 │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                     API Gateway (Nginx/Kong)                  │  │
│  │             路由 / 限流 / 认证 / 日志                          │  │
│  └─────────────────────────┬───────────────────────────────────┘  │
│                            │                                      │
│         ┌──────────────────┼──────────────────┐                   │
│         ▼                  ▼                  ▼                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐        │
│  │  Web UI      │  │  MCP Server  │  │  CLI (Click)     │        │
│  │  (Vue 3 +    │  │  (FastMCP)   │  │  命令行工具       │        │
│  │   Element+)  │  │              │  │                  │        │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘        │
│         │                 │                   │                   │
│         └─────────────────┼───────────────────┘                   │
│                           ▼                                       │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │              Backend Service (FastAPI)                     │   │
│  │  ProjectSvc | RunSvc | ReportSvc | KnowledgeSvc | ...    │   │
│  └──────────────────────────┬────────────────────────────────┘   │
│                             │                                     │
│              ┌──────────────┼──────────────┐                     │
│              ▼              ▼              ▼                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │  PostgreSQL  │  │  Redis       │  │  Celery      │           │
│  │  主数据库     │  │  缓存/队列    │  │  任务队列     │           │
│  └──────────────┘  └──────────────┘  └──────┬───────┘           │
│                                             │                     │
│              ┌──────────────────────────────┼──────────────┐     │
│              ▼              ▼              ▼              ▼     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────┐ │
│  │  Web         │  │  Android     │  │  iOS         │  │      │ │
│  │  Executor    │  │  Executor    │  │  Executor    │  │  AI  │ │
│  │  (Node.js)   │  │  (Node.js)   │  │  (Node.js)   │  │  Svc │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────┘ │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

---

## 3. 六层架构详解

### 3.1 架构全景

```
┌───────────────────────────────────────────────────────────────────┐
│  第1层: 接口层 (Interface Layer)                                   │
│  REST API (FastAPI) | MCP Server (FastMCP) | WebSocket | CLI      │
├───────────────────────────────────────────────────────────────────┤
│  第2层: 业务编排层 (Service Orchestration Layer)                    │
│  ProjectService | RunService | ReportService | KnowledgeService   │
│  DocumentService | ScenarioService | AnalysisService              │
├───────────────────────────────────────────────────────────────────┤
│  第3层: 领域层 (Domain Layer)                                      │
│  Project | RunRecord | KnowledgeBase | TestCase | Defect          │
│  BusinessRule | UIStandard | PermissionRule | EvidenceChain       │
├───────────────────────────────────────────────────────────────────┤
│  第4层: 基础设施接口层 (Infrastructure Interface Layer)              │
│  Repository (Interface) | AIService (Interface) | OCRService      │
│  ExecutorClient (Interface) | FileService (Interface)             │
├───────────────────────────────────────────────────────────────────┤
│  第5层: 基础设施实现层 (Infrastructure Implementation Layer)         │
│  SQLAlchemy Repo | LiteLLM Client | PaddleOCR | S3FileService     │
│  MidsceneClient | PlaywrightDriver | CeleryTaskQueue              │
├───────────────────────────────────────────────────────────────────┤
│  第6层: 执行器层 (Executor Layer) - 独立部署的服务                   │
│  Midscene Web Executor | Midscene Android Executor | iOS Executor │  
└───────────────────────────────────────────────────────────────────┘
```

### 3.2 层间依赖规则

```
严格的单向依赖：
┌─────────┐     ┌──────────────┐     ┌───────────┐
│ 接口层   │────▶│  业务编排层   │────▶│  领域层    │
└─────────┘     └──────────────┘     └─────┬─────┘
                                            │
                              ┌─────────────┴─────────────┐
                              │                           │
                              ▼                           ▼
                    ┌──────────────────┐     ┌───────────────────┐
                    │ 基础设施接口层     │◀────│ 业务编排层         │
                    │ (Interface)      │     │ (通过 DI 注入)     │
                    └────────┬─────────┘     └───────────────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ 基础设施实现层     │
                    └──────────────────┘

依赖规则:
1. 接口层 → 业务编排层（调用）
2. 业务编排层 → 领域层（使用实体）
3. 业务编排层 → 基础设施接口层（通过接口依赖）
4. 基础设施实现层 → 基础设施接口层（实现接口）
5. 执行器层 → 基础设施接口层（通过 RPC/消息）
6. 严禁：下层依赖上层（如领域层依赖接口层）
7. 严禁：基础设施实现层之间直接依赖
```

### 3.3 各层详细设计

#### 第1层: 接口层

```
职责: 协议适配、参数校验、鉴权、响应格式统一
技术: FastAPI + Pydantic + FastMCP + Click

核心组件:

1.1 REST API Controller
    │
    ├── ProjectController
    │   POST   /api/v1/projects
    │   GET    /api/v1/projects
    │   GET    /api/v1/projects/{id}
    │   PUT    /api/v1/projects/{id}
    │   DELETE /api/v1/projects/{id}
    │
    ├── DocumentController
    │   POST   /api/v1/projects/{id}/documents
    │   GET    /api/v1/projects/{id}/documents
    │   POST   /api/v1/projects/{id}/documents/parse
    │
    ├── KnowledgeController
    │   GET    /api/v1/projects/{id}/knowledge
    │   PUT    /api/v1/projects/{id}/knowledge/rules/{rule_id}
    │   POST   /api/v1/projects/{id}/knowledge/verify
    │
    ├── ScenarioController
    │   POST   /api/v1/projects/{id}/scenarios/generate
    │   GET    /api/v1/projects/{id}/scenarios
    │   PUT    /api/v1/scenarios/{id}
    │
    ├── RunController
    │   POST   /api/v1/projects/{id}/runs
    │   GET    /api/v1/runs/{id}
    │   POST   /api/v1/runs/{id}/cancel
    │   GET    /api/v1/runs/{id}/progress
    │
    ├── ReportController
    │   GET    /api/v1/runs/{id}/report
    │   GET    /api/v1/runs/{id}/report/{format}
    │
    └── DefectController
        GET    /api/v1/runs/{id}/defects
        GET    /api/v1/defects/{id}
        GET    /api/v1/defects/{id}/evidence

1.2 MCP Server (FastMCP)
    │
    ├── tools/
    │   ├── get_defect(defect_id, format) -> DefectData
    │   ├── list_defects(run_id, severity) -> DefectSummary[]
    │   ├── get_run_report(run_id) -> Report
    │   └── create_run(project_id, platforms) -> RunID
    │
    └── resources/
        ├── defect://{defect_id}
        └── report://{run_id}

1.3 CLI (Click)
    │
    ├── autotest project create/list/get/delete
    ├── autotest doc parse/status
    ├── autotest run start/cancel/status
    ├── autotest report get/export
    └── autotest defect get/list
```

#### 第2层: 业务编排层

```
职责: 业务流程编排、事务协调、领域事件发布
技术: FastAPI Depends + 依赖注入

核心服务:

ProjectService
├── create_project(name, platforms, entries, docs) -> Project
├── update_config(project_id, changes) -> Project
├── delete_project(project_id) -> void
├── list_projects(filter) -> Project[]
└── get_project(project_id) -> Project

DocumentService
├── parse_documents(project_id, doc_refs) -> ExtractionResult
├── retry_parse(document_id) -> ExtractionResult
├── get_parse_status(project_id) -> ParseStatus
└── compare_document_versions(old_kb_id, new_kb) -> DiffReport

KnowledgeService
├── create_knowledge_base(project_id, extraction) -> KnowledgeBase
├── get_knowledge_base(project_id) -> KnowledgeBase
├── update_rule(kb_id, rule_id, update) -> BusinessRule
├── confirm_conflict(kb_id, conflict_id, resolution) -> Conflict
├── compare_versions(v1, v2) -> DiffReport
└── incremental_update(project_id) -> KnowledgeBase

ScenarioService
├── generate_scenarios(project_id, platforms) -> TestScenario[]
├── preview_scenarios(project_id) -> ScenarioMatrix
├── revise_scenario(scenario_id, changes) -> TestScenario
├── export_scenario_matrix(project_id) -> ScenarioExport
└── measure_coverage(project_id, scenarios) -> CoverageReport

RunService
├── create_run(project_id, platforms, scope) -> RunRecord
├── cancel_run(run_id) -> void
├── get_run_progress(run_id) -> RunProgress
├── retry_run(run_id, case_ids) -> RunRecord
└── get_run_history(project_id) -> RunRecord[]

AnalysisService
├── collect_multi_dimension_data(step_data) -> RawDataPackage
├── build_evidence_chain(raw_data) -> EvidenceChain[]
├── synthesize_conclusion(chains, rules) -> SynthesisConclusion
└── output_diagnostic_report(conclusion) -> DiagnosticReport

ReportService
├── generate_report(run_id, format) -> TestReport
├── generate_executive_summary(run_id) -> Markdown
├── generate_structured_defect_data(defects) -> JSON
└── export_report(run_id, format, path) -> FilePath
```

#### 第3层: 领域层

```
职责: 核心业务实体、值对象、领域事件
技术: Pydantic BaseModel + dataclasses

核心实体:
├── Project
│   ├── id: str
│   ├── name: str
│   ├── platforms: list[Platform]
│   ├── entries: list[PlatformEntry]
│   ├── document_refs: list[DocumentRef]
│   ├── status: ProjectStatus
│   ├── config: ProjectConfig
│   ├── created_at: datetime
│   └── updated_at: datetime
│
├── DocumentRef
│   ├── id: str
│   ├── url: str
│   ├── type: DocumentType (prd/ui_spec/api_doc)
│   ├── version: str
│   └── parse_status: ParseStatus
│
├── KnowledgeBase
│   ├── id: str
│   ├── project_id: str
│   ├── version: int
│   ├── rules: list[BusinessRule]
│   ├── ui_standards: list[UIStandard]
│   ├── permission_rules: list[PermissionRule]
│   ├── business_lines: list[BusinessLine]
│   ├── conflicts: list[Conflict]
│   └── quality_score: QualityScore
│
├── TestScenario
│   ├── id: str
│   ├── project_id: str
│   ├── business_line: str
│   ├── role: str
│   ├── type: ScenarioType (positive/boundary/abnormal/permission)
│   ├── cases: list[TestCase]
│   └── coverage: CoverageInfo
│
├── TestCase
│   ├── id: str
│   ├── scenario_id: str
│   ├── name: str
│   ├── description: str
│   ├── preconditions: list[str]
│   ├── steps: list[TestStep]
│   ├── expected: ExpectedResult
│   └── tags: list[str]
│
├── RunRecord
│   ├── id: str
│   ├── project_id: str
│   ├── status: RunStatus
│   ├── platforms: list[Platform]
│   ├── executions: list[StepExecutionRecord]
│   ├── defects: list[Defect]
│   └── summary: RunSummary
│
├── StepExecutionRecord
│   ├── step_index: int
│   ├── action: str
│   ├── platform: str
│   ├── status: str
│   ├── screenshots: ScreenshotSet
│   ├── console_snapshot: ConsoleSnapshot
│   ├── network_snapshot: NetworkSnapshot
│   ├── page_state: PageState
│   ├── verifications: Verifications
│   └── cross_dimension_report: CrossDimensionReport
│
├── Defect
│   ├── id: str
│   ├── run_id: str
│   ├── type: DefectType
│   ├── severity: SeverityLevel
│   ├── evidence_chains: list[EvidenceChain]
│   ├── synthesis: SynthesisConclusion
│   └── fix_suggestion: FixSuggestion
│
├── EvidenceChain
│   ├── root_trigger: AnomalyEvent
│   ├── propagation: list[PropagationStep]
│   └── chain_summary: str
│
└── BusinessRule
    ├── id: str
    ├── kb_id: str
    ├── category: str (flow/rule/permission/ui)
    ├── content: str
    ├── source_doc: str
    ├── confidence: float
    └── status: str (confirmed/candidate/conflicted)
```

#### 第4层: 基础设施接口层

```
职责: 定义外部服务接口（契约），供业务编排层依赖
技术: Python ABC / Protocol

核心接口:
├── Repository Interfaces
│   ├── ProjectRepository(ABC)
│   ├── KnowledgeBaseRepository(ABC)
│   ├── ScenarioRepository(ABC)
│   ├── RunRepository(ABC)
│   ├── DefectRepository(ABC)
│   └── DocumentRepository(ABC)
│
├── AIService(ABC)
│   ├── async def extract_rules(doc_content, strategy) -> ExtractionResult
│   ├── async def analyze_root_cause(evidence) -> RootCauseAnalysis
│   ├── async def generate_fix_suggestion(defect) -> FixSuggestion
│   ├── async def judge_causal_relation(event_a, event_b) -> bool
│   └── async def extract_business_chains(rules) -> BusinessChain[]
│
├── OCRService(ABC)
│   ├── async def recognize_text(image_base64) -> OCRResult
│   ├── async def recognize_components(image_base64) -> Component[]
│   └── async def compare_screenshot(actual, expected) -> DiffResult
│
├── ExecutorClient(ABC) - 统一执行器接口
│   ├── async def execute_step(step) -> StepResult
│   ├── async def get_page_state() -> PageState
│   ├── async def get_console_logs() -> ConsoleLog[]
│   ├── async def get_network_requests() -> NetworkEntry[]
│   └── async def take_screenshot() -> str
│
├── FileService(ABC)
│   ├── async def upload(file_data, path) -> str
│   ├── async def download(path) -> bytes
│   └── async def delete(path) -> void
│
└── TaskQueueService(ABC)
    ├── async def enqueue(task_type, payload) -> str
    ├── async def get_status(task_id) -> TaskStatus
    └── async def cancel(task_id) -> void
```

#### 第5层: 基础设施实现层

```
职责: 基础设施接口的具体实现
技术: SQLAlchemy | LiteLLM | PaddleOCR | boto3 | Celery

实现清单:
├── Repository Implementations
│   ├── PostgresProjectRepository(SQLAlchemy)
│   ├── PostgresKnowledgeBaseRepository(SQLAlchemy)
│   ├── PostgresScenarioRepository(SQLAlchemy)
│   └── PostgresRunRepository(SQLAlchemy)
│
├── AIService Implementation
│   └── LiteLLMAIService
│       ├── Provider: OpenAI / Claude / GLM (可配置)
│       ├── 多策略并行提取（通用/结构化/追问/反向）
│       └── 多角色 Prompt 模板
│
├── OCRService Implementation
│   ├── PaddleOCRService (本地 OCR)
│   └── MidsceneOCRService (Midscene 内置 OCR)
│
├── ExecutorClient Implementation
│   ├── MidsceneWebClient (通过 HTTP/REST 调用 Midscene Node 服务)
│   ├── MidsceneAndroidClient (通过 ADB + Midscene.android)
│   └── MidsceneiOSClient (通过 WDA + Midscene.ios)
│       └── 统一接口: execute_step / get_page_state / get_console_logs / ...
│
├── FileService Implementation
│   └── S3FileService (阿里云 OSS / MinIO)
│
└── TaskQueueService Implementation
    └── CeleryTaskQueueService (Redis Broker)
```

#### 第6层: 执行器层

```
职责: 实际执行测试步骤，运行在独立进程中
技术: Node.js + Midscene.js + Playwright

三个执行器:

Web Executor (Midscene.web + Playwright):
├── 启动 Chromium 浏览器
├── 导航到目标 URL
├── AI 视觉定位元素（截图→AI→坐标）
├── 执行点击/输入/滚动等操作
├── 拦截网络请求（Playwright route）
├── 采集控制台日志（page.on('console')）
└── 截图（操作前后）

Android Executor (Midscene.android + ADB):
├── ADB 连接设备/模拟器
├── 启动/管理 Activity
├── AI 视觉定位（截图→AI→坐标）
├── 执行点击/输入
├── 采集 logcat 日志
├── ANR 检测
└── 截图

iOS Executor (WDA + Midscene.ios):
├── WebDriverAgent 连接设备
├── 启动/管理 App
├── AI 视觉定位
├── 执行点击/输入
├── 采集 syslog
├── Crash 检测
└── 截图
```

---

## 4. 业务域架构映射

```
业务域                接口层        业务编排层        领域层       基础设施层      执行器层
──────────────────────────────────────────────────────────────────────────────────────
项目管理域            Controller    ProjectService    Project      Repo            -
文档解析域            Controller    DocumentService   Document     AI Service     -
知识库域              Controller    KnowledgeService  Knowledge    AI + Repo      -
场景生成域            Controller    ScenarioService   Scenario     AI + Repo      -
执行调度域            Controller    RunService        RunRecord    Repo + Queue   -
平台执行域            -             -                 -           ExecutorClient Executor
四维校验域            -             -                 Verification OCR+Console+API -
综合分析域            -             AnalysisService   Evidence     AI Service     -
缺陷分析域            -             (AnalysisService) Defect       AI Service     -
报告域               Controller     ReportService     Report       File Service   -
参考数据接口域        MCP Server    -                 Defect       Repo           -

数据流方向：
  用户请求 → 接口层 → 业务编排层 → 领域层 → 基础设施接口层 → 基础设施实现层
                                                                      ↓
  用户响应 ← 接口层 ← 业务编排层 ← 领域层 ← 基础设施接口层 ← 基础设施实现层
                                                                      ↓
                                                              执行器层 (独立进程)
```

---

## 5. 技术选型与决策

### 5.1 核心技术栈

| 层级 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 接口层 | FastAPI | ≥0.110 | REST API 框架 |
| 接口层 | FastMCP | ≥0.4 | MCP Server |
| 接口层 | Click | ≥8.1 | CLI 工具 |
| 接口层 | WebSocket | FastAPI 原生 | 实时进度推送 |
| 业务编排层 | FastAPI Depends | - | 依赖注入 |
| 领域层 | Pydantic | ≥2.5 | 数据模型/校验 |
| 业务编排层 | SQLAlchemy | ≥2.0 | ORM |
| 基础设施层 | LiteLLM | ≥1.40 | 多模型 AI 网关 |
| 基础设施层 | Celery | ≥5.3 | 分布式任务队列 |
| 基础设施层 | Redis | ≥7.0 | 缓存/消息代理 |
| 基础设施层 | PaddleOCR | - | 本地 OCR |
| 基础设施层 | boto3 / oss2 | - | 文件存储 |
| 执行器层 | Midscene.js | ≥1.0 | AI 驱动测试 |
| 执行器层 | Playwright | ≥1.40 | 浏览器自动化 |
| 数据库 | PostgreSQL | ≥15 | 主数据库 |
| 容器化 | Docker / Compose | - | 部署 |
| AI 模型 | GPT-4o / Claude-3.5 / GLM-4 | - | 业务提取/分析 |

### 5.2 技术选型理由

| 决策 | 选择 | 备选 | 理由 |
|------|------|------|------|
| API 框架 | FastAPI | Flask/Django | 原生异步、Pydantic 校验、自动 OpenAPI |
| ORM | SQLAlchemy 2.0 | Django ORM/Peewee | 异步支持、成熟生态、独立于框架 |
| AI 网关 | LiteLLM | 直接 API | 统一接口、多模型切换、成本追踪 |
| 任务队列 | Celery | Arq/Hue | 成熟度、监控生态、Beat 调度 |
| 测试引擎 | Midscene.js | 纯 Playwright | AI 视觉定位、免维护选择器 |
| 领域模型 | Pydantic | dataclasses | 序列化、校验、OpenAPI 生成 |
| 数据库 | PostgreSQL | MySQL | JSONB、全文本搜索、扩展性 |

---

## 6. 关键架构决策 (ADRs)

### ADR-001: AI 提取的业务规则多层校验

```
状态: 已接受
上下文: AI 从文档提取业务规则具有概率性，单次调用可能产生幻觉或遗漏
决策: 采用多策略并行提取 + 交叉验证 + 冲突消解 Pipeline
  - 4 种提取策略同时运行
  - Embedding 相似度去重
  - 置信度打分（策略匹配数 × AI 自评分）
  - 冲突自动检测 + 人工裁决
后果:
  - 正面: 业务规则准确率从 ~70% 提升至 ~95%
  - 负面: Token 消耗增 3-4 倍，提取耗时增 2-3 倍
  - 缓解: 并行调用 4 策略，首次解析慢，增量更新只处理变更
```

### ADR-002: 六层架构的分层策略

```
状态: 已接受
上下文: 需要支持多执行器（Web/Android/iOS）和 AI 能力演进
决策: 采用严格的六层架构
  - 业务编排层不直接依赖基础设施实现，只依赖接口
  - 执行器层作为独立服务部署，通过 RPC 通信
  - 领域层0外部依赖（纯 Pydantic 模型）
后果:
  - 正面: 每层可独立演进、测试、部署
  - 正面: 新增平台只需实现 ExecutorClient 接口
  - 负面: 开发初期需要定义大量接口抽象
  - 缓解: 使用 Protocol 而非 ABC，降低接口定义成本
```

### ADR-003: 综合分析引擎的因果发现策略

```
状态: 已接受
上下文: 多维度校验需要从多个异常信号中还原 Bug 全貌
决策: 规则引擎 + LLM 混合判断
  - 规则引擎处理已知因果模式（api_error→console_error）
  - LLM 处理规则引擎无法判断的边缘场景
  - 时间轴对齐作为因果判断的前提条件
后果:
  - 正面: 大部分常见因果链由规则引擎快速判断（<10ms）
  - 正面: LLM 提供边缘场景的判断能力
  - 负面: LLM 判断引入延迟和成本
  - 缓解: 静态规则覆盖 80% 场景，LLM 只处理 20% 边缘情况
```

### ADR-004: 执行器与服务端的通信方式

```
状态: 已接受
上下文: 执行器（Node.js）和 Python 服务端需要进行双向通信
决策: HTTP REST + WebSocket + 共享文件
  - 服务端→执行器: HTTP POST (create task)
  - 执行器→服务端: WebSocket (实时进度)
  - 截图/日志: 共享文件系统 + URL 引用
后果:
  - 正面: 实现简单，执行器层零额外依赖
  - 正面: 支持不同语言（Node.js 执行器，Python 服务端）
  - 负面: 网络不稳定时重试逻辑复杂
  - 缓解: Celery 任务队列 + 自动重试 3 次
```

---

## 7. 质量属性设计

### 7.1 性能设计

```yaml
性能目标:
  API 响应时间:
    - 常规查询: <200ms (P95)
    - 项目配置: <500ms (P95)
    - 报告生成: <5s (含大量截图)
    - 极端: 平台限制 30s

  执行器并发:
    - 单机并发: 4-8 个浏览器实例
    - 集群扩展: 水平扩展执行器节点
    - 任务队列缓冲: Celery + Redis

  AI 调用优化:
    - 多策略并行调用（不是串行）
    - LLM 响应缓存（相同文档内容命中缓存）
    - Token 预算控制（每步分析 ≤ 8K tokens）
    - 模型分级: 简单任务用小模型，复杂分析用大模型

  数据库优化:
    - JSONB 存储灵活字段（截图/日志）
    - 分区表: 按项目 ID 分区
    - 归档: 执行记录 > 30 天移入归档表
```

### 7.2 可用性设计

```yaml
可用性目标: 99.5%（每月停机 ≤ 3.6 小时）

容错策略:
  ├── 执行器容错
  │   ├── 步骤执行失败 → 重试 3 次（指数退避）
  │   ├── 浏览器崩溃 → 自动重启 → 继续执行
  │   └── 网络波动 → 等待 30s → 重试
  │
  ├── AI 服务容错
  │   ├── 模型调用失败 → 切换到备用模型
  │   ├── Token 超限 → 分段重试
  │   └── 超时 → 降级为基本分析（跳过 LLM 判断）
  │
  ├── 任务队列容错
  │   ├── Celery worker 宕机 → 自动重新调度
  │   ├── Redis 宕机 → 启动本地 Fallback 队列（限关键任务）
  │   └── 任务超时 → 标记失败 + 记录上下文
  │
  └── 数据库容错
      ├── 主从复制
      ├── 自动备份（每日）
      └── 查询超时保护（语句级 timeout）
```

### 7.3 可扩展性设计

```yaml
水平扩展点:
  ├── 执行器层: 无状态，可任意扩展
  │   ├── Docker 容器池
  │   └── Kubernetes HPA（基于队列长度）
  │
  ├── AI 服务: 无状态 HTTP 服务
  │   ├── 多实例负载均衡
  │   └── 请求队列缓冲
  │
  └── API 服务: 无状态，水平扩展
      └── 会话外置到 Redis

垂直扩展点:
  ├── PostgreSQL: 连接池 (PgBouncer)
  ├── Redis: Cluster 模式（分片）
  └── 执行器: 单机多实例（多浏览器进程）

扩展新增平台:
  只需实现 ExecutorClient 接口 → 注册到 ExecutorRegistry → 即可集成
  新增一个平台 = 实现 5 个方法 + 配置连接信息
```

### 7.4 安全性设计

```yaml
安全层次:
  传输安全:
    - 所有 API 强制 HTTPS
    - MCP Server 走 TLS

  认证授权:
    - API Key / JWT 认证
    - 项目级别隔离（用户只能访问自己的项目）
    - API 请求/响应日志（审计）

  数据安全:
    - 截图自动脱敏（模糊识别到的敏感信息）
    - API 请求 body 中的 Token/密码自动替换
    - 日志中的敏感信息过滤

  执行安全:
    - 浏览器沙箱隔离
    - 执行器容器资源限制（CPU/内存）
    - 禁止执行器访问内部网络
```

---

## 8. 部署架构

参见 `docs/部署方案.md` 详细部署方案。

```
简化部署视图:

┌─────────────────────────────────────────────┐
│  Docker Compose / Kubernetes Cluster         │
│                                              │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐   │
│  │ API 服务  │  │ MCP 服务 │  │ Web UI    │   │
│  │ (Python)  │  │ (Python) │  │ (Nginx)   │   │
│  └─────┬────┘  └─────┬────┘  └───────────┘   │
│        │              │                       │
│  ┌─────┴────────────────┴──────────┐          │
│  │         PostgreSQL (主)          │          │
│  └──────────────────────────────┬──┘          │
│                                 │             │
│  ┌──────────────────────────────┴──┐          │
│  │         PostgreSQL (从)          │          │
│  └─────────────────────────────────┘          │
│                                              │
│  ┌──────────┐  ┌────────────────────────┐    │
│  │  Redis   │  │  Celery Worker Pool    │    │
│  └──────────┘  └───────────┬────────────┘    │
│                            │                  │
│              ┌─────────────┼─────────────┐   │
│              ▼             ▼             ▼   │
│  ┌──────────────┐ ┌──────────────┐ ┌────────┐│
│  │ Web 执行器   │ │Android 执行器│ │iOS执行 ││
│  │ (Node.js)    │ │ (Node.js)    │ │(Node)  ││
│  └──────────────┘ └──────────────┘ └────────┘│
└──────────────────────────────────────────────┘
```

---

## 9. 演进架构

### Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5

```
Phase 1 (MVP): 核心打底
  ├── 项目管理 + 文档解析 + 知识库
  ├── Web 执行器
  ├── CLI 工具
  └── 基础 UI

Phase 2: 四维校验
  ├── UI / Console / API / 业务 校验管线
  ├── 单维度独立校验
  └── 结构化输出 JSON

Phase 3: 缺陷分析 AI
  ├── AI 根因分析
  ├── 修复建议生成
  ├── MCP 参考数据接口
  └── 综合分析引擎

Phase 4: 多平台
  ├── Android 执行器
  ├── iOS 执行器
  └── 跨平台对比分析

Phase 5: 参考数据深化
  ├── 截图标注增强
  ├── 日志结构化
  ├── 代码引用链接
  └── 项目结构理解

架构演进原则:
  - 每个 Phase 都是可用增量
  - 接口先行，实现后补
  - 向下兼容：旧版数据格式在新版中可读
  - 不欠技术债：每个 Phase 合入前必须通过质量门禁
```

---

# 11. 多项目隔离设计

## 11.1 隔离原则

```yaml
AutoTest 支持多项目（Multi-Project），不是多租户（Multi-Tenant）。
这意味着：
  - 同一部署实例内可以创建多个隔离的项目
  - 每个项目有独立的配置、文档、知识库、场景、执行历史
  - 项目之间数据完全隔离（只能通过明确的数据迁移操作交换）
  - 所有 API 调用都基于 project_id 路由

隔离边界:
  数据层: project_id 作为所有业务表的外键
  业务层: Service 方法都接收 project_id 参数
  接口层: 所有 URL 路径都包含 /projects/{project_id}
  文件层: 文件按 project_id 分目录存储
```

## 11.2 数据隔离实现

```sql
-- 所有业务表都通过 project_id 隔离
-- 查询时强制带 project_id 条件
SELECT * FROM business_rules 
WHERE kb_id IN (SELECT id FROM knowledge_bases WHERE project_id = :project_id);

-- 严禁不带 project_id 的跨项目查询
-- 仓储层实现中，所有查询方法第一个参数都是 project_id
```

## 11.3 项目间操作控制

```yaml
允许的跨项目操作:
  - 场景模板导入（从项目 A 导出模板，导入项目 B）
  - 执行器资源共享（同一执行器节点服务多个项目）
  - 对比报告（比较两个项目的质量指标）

禁止的跨项目操作:
  - 直接访问其他项目的知识库
  - 一个项目的执行影响另一个项目的数据
  - 跨项目引用文档或场景

项目配额（可配置）:
  单个项目的最大文档数: 50
  单个项目的最大用例数: 500
  单个项目的并发执行数: 5
  项目总数上限: 100
```

---

# 12. 可观测性架构

## 12.1 三大支柱设计

```yaml
可观测性 = Metrics + Tracing + Logging

Metrics (Prometheus):
  ┌────────────────────────┬──────────────────────┐
  │ 指标                    │ 类型                  │
  ├────────────────────────┼──────────────────────┤
  │ api_requests_total     │ Counter (method, path, status) │
  │ api_request_duration_ms│ Histogram (method, path)      │
  │ ai_calls_total         │ Counter (model, operation)    │
  │ ai_call_duration_ms    │ Histogram (model, operation)  │
  │ ai_token_usage_total   │ Counter (model, type)         │
  │ executor_steps_total   │ Counter (platform, status)    │
  │ executor_step_duration │ Histogram (platform)          │
  │ run_queue_depth        │ Gauge (platform)              │
  │ run_duration_seconds   │ Histogram                     │
  │ defect_found_total     │ Counter (severity, type)      │
  │ kb_quality_score       │ Gauge (project)               │
  │ db_connection_pool_size│ Gauge                         │
  │ celery_queue_depth     │ Gauge (queue)                 │
  └────────────────────────┴──────────────────────┘

Tracing (OpenTelemetry):
  采集点:
    ├── HTTP 请求（入口 + 出口）
    ├── Celery 任务（创建 → 执行 → 完成）
    ├── AI 调用（请求 → 响应）
    ├── 数据库查询（SQL + 耗时）
    ├── 执行器步骤（发送 → 执行 → 回调）
    └── 外部服务调用（文件存储、OCR）

  采样策略:
    ├── API 请求: 10%（固定采样）
    ├── 错误请求: 100%（全采）
    ├── AI 调用: 100%（全采，方便成本追踪）
    └── 执行器步骤: 5%（大量数据，抽样即可）

Logging (结构化 JSON):
  格式:
    {"timestamp":"...","level":"INFO","module":"project_service",
     "action":"create_project","request_id":"req_xxx",
     "duration_ms":45,"project_id":"proj_xxx"}

  强制字段:
    - timestamp: ISO 8601
    - level: ERROR/WARNING/INFO/DEBUG
    - module: 模块名
    - action: 操作名
    - request_id: 请求追踪 ID

  日志级别:
    ERROR:   系统无法自动恢复的错误
    WARNING: 不影响主流程但需要注意的问题
    INFO:    核心业务节点
    DEBUG:   调试信息（生产环境默认关闭）
```

## 12.2 健康检查端点

```http
GET /health
{
  "status": "ok",
  "version": "1.0.0",
  "checks": {
    "database": {"status": "ok", "latency_ms": 2},
    "redis": {"status": "ok", "latency_ms": 1},
    "ai_service": {"status": "ok", "model": "gpt-4o"},
    "executor_web": {"status": "ok", "connected_nodes": 3},
    "disk_usage": {"status": "ok", "percent": 62}
  },
  "uptime_seconds": 86400
}
```

## 12.3 告警规则

```yaml
P1 告警（即时响应）:
  - API 错误率 > 5%（5 分钟窗口）
  - 数据库连接池耗尽
  - AI 服务连续失败 > 10 次
  - 执行器节点全部离线

P2 告警（工作时间响应）:
  - API P95 延迟 > 3s
  - AI Token 日消耗超预算 50%
  - 任务队列积压 > 100
  - 磁盘使用率 > 85%

P3 告警（周报处理）:
  - 测试误报率 > 10%
  - AI 提取召回率 < 80%
  - 慢查询数增加
```

---

# 13. 重试/降级/熔断策略

## 13.1 统一重试策略

```python
class RetryConfig:
    """统一重试配置"""
    max_retries: int = 3
    base_delay_s: float = 1.0
    max_delay_s: float = 30.0
    backoff_factor: float = 2.0  # 指数退避
    jitter: bool = True          # 随机抖动避免惊群
    retryable_exceptions: tuple = (
        TimeoutError,
        ConnectionError,
        AIServiceError,
        ExecutorConnectionError,
    )


async def with_retry(
    func: Callable,
    config: RetryConfig = RetryConfig(),
    context: dict = None
) -> Any:
    """统一重试装饰器"""
    last_exception = None
    for attempt in range(config.max_retries + 1):
        try:
            return await func()
        except config.retryable_exceptions as e:
            last_exception = e
            if attempt < config.max_retries:
                delay = min(
                    config.base_delay_s * (config.backoff_factor ** attempt),
                    config.max_delay_s
                )
                if config.jitter:
                    delay *= random.uniform(0.8, 1.2)
                logger.warning(
                    f"Retry attempt {attempt + 1}/{config.max_retries}",
                    extra={"context": context, "delay_s": delay}
                )
                await asyncio.sleep(delay)
    raise last_exception
```

## 13.2 按模块的重试配置

```yaml
模块专用重试配置:
  AI 服务调用:
    最大重试: 3
    退避: 2x (1s, 2s, 4s)
    可重试: TimeoutError, RateLimitError
    不可重试: InvalidRequestError, AuthenticationError
    降级: 第 2 次重试起使用备用模型

  执行器通信:
    最大重试: 3
    退避: 3x (3s, 9s, 27s)
    可重试: ConnectionError, TimeoutError
    不可重试: 400 Bad Request（参数问题）
    降级: 第 3 次重试失败后标记任务为 failed

  数据库操作:
    最大重试: 2
    退避: 1x（即不等待，立即重试）
    可重试: DeadlockError, ConnectionLost
    不可重试: IntegrityError, ProgrammingError

  文件存储:
    最大重试: 3
    退避: 2x (1s, 2s, 4s)
    可重试: ConnectionError, TimeoutError
    降级: 切换到本地临时存储
```

## 13.3 熔断器设计

```python
class CircuitBreaker:
    """熔断器 - 防止级联故障"""
    
    states = ("closed", "open", "half_open")
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,      # 5 次失败后开启
        recovery_timeout_s: float = 30,  # 30 秒后尝试半开
        half_open_max_requests: int = 3, # 半开状态最多 3 个请求
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout_s
        self.half_open_max = half_open_max_requests
        
        self.state = "closed"
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_requests = 0
    
    async def call(self, func, fallback=None):
        """调用受保护函数"""
        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half_open"
                logger.info(f"CircuitBreaker {self.name}: closed → half_open")
            else:
                return await fallback() if fallback else self._default_fallback()
        
        try:
            result = await func()
            # 成功 → 重置
            if self.state == "half_open":
                self.state = "closed"
                logger.info(f"CircuitBreaker {self.name}: half_open → closed")
            self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.error(f"CircuitBreaker {self.name}: closed → open ({self.failure_count} failures)")
            return await fallback() if fallback else self._default_fallback()

# 熔断器实例
circuit_breakers = {
    "ai_extraction": CircuitBreaker("ai_extraction", failure_threshold=3, recovery_timeout_s=60),
    "ai_analysis": CircuitBreaker("ai_analysis", failure_threshold=5, recovery_timeout_s=30),
    "executor_web": CircuitBreaker("executor_web", failure_threshold=3, recovery_timeout_s=120),
    "executor_android": CircuitBreaker("executor_android", failure_threshold=3, recovery_timeout_s=120),
}
```

## 13.4 降级策略

```yaml
分级降级策略:
  Level 0 (正常运行):
    全部功能可用

  Level 1 (轻度降级 - 单 AI 服务不可用):
    ├── AI 提取 → 切换到备用模型
    ├── AI 分析 → 跳过 LLM 判断，只使用规则引擎
    └── AI 修复建议 → 不生成（标记为"暂不可用"）

  Level 2 (中度降级 - 执行器故障):
    ├── Web 执行器宕机 → 队列等待，自动切换到可用节点
    ├── Android 执行器宕机 → 跳过 Android 用例
    └── 截图服务不可用 → 继续执行但不采集截图

  Level 3 (重度降级 - 数据库不可用):
    ├── 只读模式（API 支持 GET，拒绝 POST/PUT/DELETE）
    ├── 正在执行的测试继续（结果暂存本地）
    └── 新执行请求排队

降级自动触发:
  - AI 服务连续失败 3 次 → Level 1
  - 执行器节点全部离线 → Level 2
  - 数据库主库不可用 → Level 3（10 秒内未自动切换）
```

---

# 14. 配置管理架构

## 14.1 配置分层

```yaml
配置来源（优先级从高到低）:
  1. 环境变量                     # 运行时注入，敏感信息
  2. 运行时配置中心 (system_configs)  # 运行时动态修改，无需重启
  3. ConfigMap (K8s)              # 部署配置
  4. .env 文件                     # 本地开发
  5. 代码内默认值 (config.py)       # 兜底

配置分类:
  ┌──────────────────────┬────────────────┬──────────┐
  │ 配置项               │ 存储位置        │ 是否支持  │
  │                      │                │ 运行时重载 │
  ├──────────────────────┼────────────────┼──────────┤
  │ DATABASE_URL         │ 环境变量         │ ❌      │
  │ LITELLM_API_KEY      │ 环境变量/Secret  │ ❌      │
  │ EXTRACTION_MODEL     │ 环境变量/Config  │ ✅      │
  │ executor.timeout     │ system_configs  │ ✅      │
  │ retry.max_retries    │ system_configs  │ ✅      │
  │ storage.retention    │ system_configs  │ ✅      │
  │ ai.token_budget      │ system_configs  │ ✅      │
  └──────────────────────┴────────────────┴──────────┘

运行时配置表 (system_configs):
  key: str PRIMARY KEY
  value: JSONB
  description: str
  updated_at: TIMESTAMPTZ

  配置变更自动传播:
    1. 用户更新 system_configs 表
    2. 服务检测到变更（定时轮询 / Redis PubSub 通知）
    3. 服务重新加载配置
    4. 无需重启进程
```

## 14.2 配置加载实现

```python
class DynamicConfig:
    """支持运行时热加载的配置管理器"""
    
    def __init__(self, redis_client):
        self._configs = {}
        self._redis = redis_client
        self._pubsub = redis_client.pubsub()
        self._pubsub.subscribe("config_changes")
    
    async def get(self, key: str, default=None):
        """获取配置（优先从缓存读取）"""
        if key in self._configs:
            return self._configs[key]
        return await self._load_from_db(key) or default
    
    async def watch_changes(self):
        """监听配置变更"""
        async for message in self._pubsub.listen():
            if message["type"] == "message":
                key = message["data"]
                # 清除缓存，下次获取时重新加载
                self._configs.pop(key, None)
                logger.info(f"Config reloaded: {key}")
```

---

# 15. Feature Flag 架构

## 15.1 Flag 分类

```yaml
Feature Flag 命名规范: {domain}.{feature_name}

分类:
  发布控制（Release Toggles）:
    ├── executor.android.enabled        # Android 执行器开关
    ├── executor.ios.enabled            # iOS 执行器开关
    ├── analysis.llm_fallback           # LLM 因果判断兜底
    └── report.html_generation          # HTML 报告生成

  实验性功能（Experiment Toggles）:
    ├── extraction.strategy_v2          # 新版提取策略
    ├── analysis.evidence_chain_v2      # 新版证据链算法
    └── executor.web.parallel_steps     # 并行步骤执行

  操作控制（Ops Toggles）:
    ├── system.readonly_mode            # 只读模式
    ├── system.maintenance_window       # 维护窗口
    └── ai.cost_control                 # AI 成本控制

Flag 存储:
  system_configs 表（与配置管理复用）
  key = "feature.{flag_name}"
  value = {"enabled": true/false, "rules": "..."}
```

## 15.2 Flag 生命周期

```yaml
生命周期阶段:
  1. 开发中 (dev):
     默认关闭，开发者手动启用
     用于功能开发阶段的调试

  2. 内测 (alpha):
     默认关闭，可通过环境变量/ConfigMap 启用
     用于内部团队验证

  3. 公测 (beta):
     按项目/用户比例启用（10% → 50% → 100%）
     用于生产环境灰度验证

  4. 全量 (GA):
     默认开启
     代码中保留 Flag 检查（6 个月后清理）

  5. 废弃 (deprecated):
     移除 Flag 代码
     从配置中清理

清理策略:
  GA 后 6 个月必须清理 Flag 代码
  清理时移除 if/else 分支，只保留启用路径
  设置为 GA 时自动创建清理 Issue
```

---

# 16. API Rate Limiting 架构

## 16.1 设计原则

```yaml
Rate Limiting 是 API 网关层（Nginx/Kong）和应用层（FastAPI 中间件）的联合职责。

网关层（Nginx）:
  - 全局速率限制（所有请求）
  - 基于 IP 的黑/白名单
  - DDoS 防护

应用层（FastAPI 中间件）:
  - 基于 API Key 的精细限流
  - 按接口分类的不同限流规则
  - 限流状态透传到响应头

实现方式: 令牌桶算法（Token Bucket），Redis 作为分布式计数器存储。
详细限流规则表见 `docs/API接口规范.md` §11 Rate Limiting 策略。

熔断与限流的关系:
  限流（Rate Limiting）: 客户端请求过多时主动拒绝，保护服务端。
  熔断（Circuit Breaker）: 外部服务故障时主动降级，防止级联故障。
  两者互补，同时作用于 API 层。
```

---

# 17. 数据流与 Sequence Diagrams

## 16.1 端到端数据流

```
用户                    AutoTest                         AI 服务          执行器
 │                        │                                │               │
 │ POST /projects         │                                │               │
 │───────────────────────▶│                                │               │
 │                        │ 创建项目 + 初始知识库              │               │
 │                        │                                │               │
 │ POST /documents/parse  │                                │               │
 │───────────────────────▶│                                │               │
 │                        │ ─── fetch_document() ────────▶│               │
 │                        │◀──── raw_content ────────────│               │
 │                        │                                │               │
 │                        │ ─── 4-strategy extract() ───▶│               │
 │                        │◀── rules + conflicts ───────│               │
 │                        │                                │               │
 │                        │ 构建知识库 v1                    │               │
 │◀──── kb_ready ─────────│                                │               │
 │                        │                                │               │
 │ POST /scenarios/gen    │                                │               │
 │───────────────────────▶│                                │               │
 │                        │ 读取 kb → 构建业务链 → 生成场景   │               │
 │◀──── scenarios ───────│                                │               │
 │                        │                                │               │
 │ POST /runs             │                                │               │
 │───────────────────────▶│                                │               │
 │                        │ ── 创建 run + enqueue tasks ──▶│               │
 │◀──── run_id ──────────│                                │               │
 │                        │                                │               │
 │                        │                     ── execute_step() ─────▶│
 │                        │                     ◀── step_result ────────│
 │                        │                     （每步循环）              │
 │                        │                                │               │
 │                        │ ── cross_dimension_analysis() ─▶│              │
 │                        │ ◀── defect ──────────────────│               │
 │                        │                                │               │
 │ WebSocket: progress    │                                │               │
 │◀──────────────────────│                                │               │
 │                        │                                │               │
 │ GET /runs/{id}/report  │                                │               │
 │───────────────────────▶│                                │               │
 │◀──── report ──────────│                                │               │
 │                        │                                │               │
 │ Claude/MCP: get_defect│                                │               │
 │◀──── structured_data ─│                                │               │
```

## 16.2 关键 Sequence: 综合分析

```
StepExecutionRecord
    │
    ▼
CrossDimensionAnalyzer
    │
    ├── 1. _align_timeline()
    │      │
    │      ├── console.error @ T1 → 添加事件
    │      ├── api.end @ T2 → 添加事件
    │      └── screenshot @ T3 → 添加事件
    │
    ├── 2. _detect_anomalies()
    │      │
    │      ├── verify_ui_dimension() → 有异常? 加入 anomalies[]
    │      ├── verify_console_dimension() → 有异常? 加入 anomalies[]
    │      ├── verify_api_dimension() → 有异常? 加入 anomalies[]
    │      └── 无异常 → 直接返回 pass
    │
    ├── 3. _discover_causal_chains()
    │      │
    │      ├── 按时间排序异常事件
    │      ├── for each event_a:
    │      │   ├── for each event_b (发生在后):
    │      │   │   ├── 规则引擎判断因果?
    │      │   │   │   ├── api_error→console_error: 检查 URL + 时间窗口
    │      │   │   │   ├── console_error→ui_broken: 检查 Uncaught
    │      │   │   │   └── api_cascade: 检查 401 批量
    │      │   │   │
    │      │   │   └── LLM 兜底判断 (if config.use_llm_fallback)
    │      │   │       └── llm_judge.judge(event_a, event_b) → YES/NO
    │      │   │
    │      │   └── 有关联 → 加入证据链
    │      │
    │      └── 返回 chains[]
    │
    └── 4. _build_synthesis()
           │
           ├── bug_count = len(chains)
           ├── summary = "N 个 Bug, M 个表象"
           └── 返回 CrossDimensionReport
```

## 16.3 关键 Sequence: 执行器通信

```
RunService                          ExecutorClient                    Web Executor
    │                                      │                              │
    │ create_run()                          │                              │
    │                                      │                              │
    │ 保存 run记录 + 创建 run_cases         │                              │
    │                                      │                              │
    │ enqueue Celery task                   │                              │
    │ ──────────────────────────────────▶   │                              │
    │                                      │                              │
    │                           execute_platform_cases()                    │
    │                                      │                              │
    │                                      │ POST /executor/run           │
    │                                      │ ──────────────────────────▶  │
    │                                      │                              │ 启动浏览器
    │                                      │                              │
    │                                      │                              │ for each step:
    │                                      │ POST /executor/step          │
    │                                      │ ──────────────────────────▶  │
    │                                      │                              │
    │                                      │                              │ 1. Midscene AI 定位
    │                                      │                              │ 2. 执行操作（点击/输入）
    │                                      │                              │ 3. 采集数据（截图/日志/网络）
    │                                      │                              │
    │                                      │ ◀── StepExecutionRecord ─────│
    │                                      │                              │
    │ 保存 step_record                      │                              │
    │ 推送 WebSocket 进度                    │                              │
    │                                      │                              │
    │ 综合分析 → 发现缺陷                     │                              │
    │                                      │                              │
    │ 保存缺陷数据                            │                              │
    │                                      │                              │
    │                          ... 循环直到所有步骤完成 ...                  │
    │                                      │                              │
    │ 执行下一个用例（如果有多用例）            │                              │
    │                                      │                              │
    │                           run completed                              │
    │                                      │                              │
    │ 生成报告                               │                              │
    │ 推送 run_completed                     │                              │
```

---

## 附录

### A. 架构验证 Checklist（扩展版）

```
□ 分层依赖方向正确（上层→下层，无循环依赖）
□ 领域层无外部框架依赖
□ 基础设施接口定义完整（ABC/Protocol）
□ 每个业务域有明确的服务归属
□ 执行器层可独立部署和扩展
□ 错误处理覆盖所有外部调用
□ 敏感数据处理有脱敏策略
□ API 响应格式统一
□ 异步边界明确（哪些用 Celery，哪些同步）
□ 配置外部化（环境变量/配置中心）
□ 多项目数据隔离已实现（所有查询带 project_id）
□ 重试/降级/熔断策略已实现
□ Feature Flag 机制可用
□ 可观测性指标采集点已配置
□ 熔断器覆盖所有外部服务调用
```

### B. 核心依赖图

```
┌─────────────────────────────┐
│  FastAPI + Pydantic          │
│  (接口层 + 业务编排层 + 领域层) │
└──────────┬──────────────────┘
           │ depends on
           ▼
┌─────────────────────────────┐
│  SQLAlchemy 2.0 (异步)       │
│  LiteLLM (AI 网关)           │
│  Celery + Redis (任务队列)    │
│  Midscene SDK (执行器通信)    │
│  Playwright (Web驱动)        │
│  OpenTelemetry (可观测性)     │
│  Prometheus (指标)           │
└─────────────────────────────┘
```

### C. 关键设计决策索引

```yaml
决策索引（ADRs + 本文档设计决策）:
  ADR-001: 多策略并行提取规则 (§架构文档 6.1)
  ADR-002: 六层架构分层策略 (§架构文档 6.2)
  ADR-003: 综合分析引擎因果发现策略 (§架构文档 6.3)
  ADR-004: 执行器通信方式 (§架构文档 6.4)
  
  D-005: 多项目隔离（基于 project_id 的数据隔离）
  D-006: 可观测性（Prometheus + OTel + 结构化日志）
  D-007: 熔断器保护所有外部服务
  D-008: 运行时配置热加载（system_configs + Redis PubSub）
  D-009: Feature Flag 驱动的分阶段发布
  D-010: 降级分级（Level 0-3）
```

---

> **本文档是 SDD (Specification-Driven Development) 的架构规约**
> 所有实现必须遵循本文档定义的分层、接口和约束
