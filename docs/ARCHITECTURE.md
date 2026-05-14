# AutoTest 架构设计文档 (ADD)

> 版本: 2.0 | 基于需求规格说明书 v2.0

---

## 1. 系统架构

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
│              Executor (Node.js + Midscene)              │
│         http://localhost:3100                           │
│                                                         │
│  Playwright + Midscene PageAgent                        │
│  CDP Network + Console Capture                          │
│  Smart Screenshot                                       │
└─────────────────────────────────────────────────────────┘
```

## 2. 核心数据流

### 快速模式 (无文档)
```
用户: 输入 URL
  │
  ▼
POST /projects {name, url}
  │
  ▼
POST /projects/{id}/scenarios/generate → 生成基础场景
  │
  ▼
POST /projects/{id}/runs → 创建执行
  │
  ▼
执行引擎:
  1. 读取项目 entry URL
  2. 通知 Executor 打开浏览器 → 导航到 URL
  3. 对每个测试步骤:
     a. AI 视觉定位元素
     b. 执行操作 (点击/输入)
     c. 截图 → 采集日志 → 采集网络
     d. 四维校验
  4. 汇总报告 + 缺陷
```

### 完整模式 (有文档)
```
用户: 输入 URL + 上传文档 .md
  │
  ▼
POST /projects/{id}/documents/parse
  │
  ▼
DocumentParser: 分块 → 分类(flow/permission/ui/api) → 提取规则 → 存知识库
  │
  ▼
POST /projects/{id}/scenarios/generate → 从规则生成场景
  │
  ▼
... (同快速模式)
```

## 3. 关键技术选型

| 组件 | 技术 | 用途 |
|------|------|------|
| Web 框架 | FastAPI + Uvicorn | REST API |
| AI 视觉引擎 | Midscene.js PageAgent | 视觉元素定位与操作 |
| 浏览器自动化 | Playwright | 浏览器控制 + CDP 数据采集 |
| 前端 | Vue 3 + Element Plus + Vite | 管理界面 |
| AI 服务 | LiteLLM (可选) | 无 key 时规则引擎降级 |
| 存储 | 内存 (默认) | 项目/执行/缺陷数据 |
| CLI | Click | 命令行操作 |

## 4. API 设计

### 项目管理
- `POST /api/v1/projects` — 创建项目
- `GET /api/v1/projects` — 项目列表
- `GET /api/v1/projects/{id}` — 项目详情
- `PUT /api/v1/projects/{id}` — 更新项目
- `DELETE /api/v1/projects/{id}` — 删除项目

### 文档管理
- `POST /api/v1/projects/{id}/documents` — 添加文档
- `GET /api/v1/projects/{id}/documents` — 文档列表
- `POST /api/v1/projects/{id}/documents/parse` — 解析文档

### 场景与执行
- `POST /api/v1/projects/{id}/scenarios/generate` — 生成场景
- `GET /api/v1/projects/{id}/scenarios` — 场景列表
- `POST /api/v1/projects/{id}/runs` — 创建执行
- `GET /api/v1/runs/{id}` — 执行详情
- `GET /api/v1/runs/{id}/progress` — 执行进度
- `POST /api/v1/runs/{id}/cancel` — 取消执行

### 报告与缺陷
- `GET /api/v1/runs/{id}/report` — 执行报告
- `GET /api/v1/runs/{id}/defects` — 缺陷列表
- `GET /api/v1/defects/{id}` — 缺陷详情
- `GET /api/v1/defects/{id}/evidence` — 缺陷证据

### MCP (AI 编程工具接口)
- `get_defect(defect_id)` — 获取缺陷数据
- `list_defects(run_id)` — 缺陷列表
