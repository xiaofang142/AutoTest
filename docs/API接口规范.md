# AutoTest — API 接口规范 (API Specification)

> 版本: 2.0
> 日期: 2026-05-15
> 状态: 生效 (代码已落地)
> 本文定位: 定义 AutoTest 的 REST API、MCP 接口、WebSocket 推送与错误码规范
> 关联文档: [REQUIREMENTS.md](./REQUIREMENTS.md) | [ARCHITECTURE.md](./ARCHITECTURE.md) |
>          [自动测试任务模型设计.md](./自动测试任务模型设计.md) | [自动缺陷归因与AI交付设计.md](./自动缺陷归因与AI交付设计.md)

---

## 修订历史

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|----------|
| 1.0 | 2026-05-14 | AutoTest 架构组 | 初始 API 设计 |

---

## 目录

1. [通用规范](#1-通用规范)
2. [项目管理 API](#2-项目管理-api)
3. [文档管理 API](#3-文档管理-api)
4. [知识库 API](#4-知识库-api)
5. [场景管理 API](#5-场景管理-api)
6. [执行管理 API](#6-执行管理-api)
7. [报告与缺陷 API](#7-报告与缺陷-api)
8. [MCP 接口协议](#8-mcp-接口协议)
9. [WebSocket 实时推送](#9-websocket-实时推送)
10. [错误码定义](#10-错误码定义)

---

## 1. 通用规范

### 1.1 基础信息

| 属性 | 值 |
|------|------|
| Base URL | `/api/v1` |
| 协议 | HTTPS |
| 数据格式 | JSON (Content-Type: `application/json`) |
| 字符编码 | UTF-8 |
| 时间格式 | ISO 8601 (`2026-05-14T14:30:00Z`) |
| ID 格式 | `task_xxx` / `proj_xxx` / `doc_xxx` / `run_xxx` / `def_xxx` (类别前缀 + 12 位随机字符串) |

### 1.2 通用响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": { ... },
  "request_id": "req_abc123",
  "timestamp": "2026-05-14T14:30:00Z"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 业务状态码，0 表示成功 |
| message | str | 状态描述 |
| data | any | 业务数据（具体见各接口定义） |
| request_id | str | 请求追踪 ID |
| timestamp | str | 响应时间戳 |

### 1.3 分页请求

```http
GET /api/v1/resources?page=1&page_size=20&sort=-created_at
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | int | 1 | 页码 |
| page_size | int | 20 | 每页条数 (max 100) |
| sort | str | -created_at | 排序字段，前缀 `-` 表示降序 |

### 1.4 分页响应

```json
{
  "code": 0,
  "data": {
    "items": [...],
    "total": 156,
    "page": 1,
    "page_size": 20,
    "total_pages": 8
  }
}
```

### 1.5 错误响应

```json
{
  "code": 40001,
  "message": "项目不存在",
  "data": {
    "error_code": "PROJECT_NOT_FOUND",
    "detail": "project_id=proj_abc123 不存在",
    "suggestion": "请检查 project_id 是否正确"
  },
  "request_id": "req_abc123"
}
```

### 1.6 认证方式

```http
Authorization: Bearer <api_key_or_jwt>
```

认证方式：
- API Key: `AT-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` (32 位十六进制)
- JWT: 标准 JWT Token（适用于 Web UI 用户会话）
- MCP 接口使用相同 API Key 认证

### 1.7 公共状态码

| 状态码 | 含义 |
|--------|------|
| 0 | 成功 |
| 40000 | 参数错误 |
| 40001 | 资源不存在 |
| 40002 | 资源冲突（已存在） |
| 40003 | 操作不允许 |
| 40100 | 未认证 |
| 40101 | API Key 无效 |
| 40300 | 无权限 |
| 42900 | 请求频率限制 |
| 50000 | 服务器内部错误 |
| 50001 | AI 服务调用失败 |
| 50002 | 执行器通信失败 |
| 50003 | OCR 服务不可用 |
| 50400 | 上游服务超时 |

### 1.8 VNext 顶层对象与推荐主线

本规范兼容现有项目驱动接口，但从产品主线看，推荐的顶层对象已经调整为以下接口资源视角:

- `TestTask`
- `EnvironmentCheck`
- `UnderstandingResult`
- `TestBlueprint`
- `ExecutionRun`
- `Defect`
- `RepairContext`
- `DeliveryPackage`

这些对象的业务语义由 [自动测试任务模型设计.md](./自动测试任务模型设计.md) 和 [自动缺陷归因与AI交付设计.md](./自动缺陷归因与AI交付设计.md) 定义。

本规范只负责说明它们在接口层如何暴露，而不是重复定义完整业务模型。

### 1.9 任务状态

推荐统一使用以下任务状态:

- `draft`
- `prechecking`
- `understanding`
- `planning`
- `running`
- `analyzing`
- `completed`
- `completed_with_defects`
- `blocked`
- `cancelled`
- `error`

### 1.10 推荐的任务驱动接口

建议新增并逐步作为主线使用:

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/tasks` | 创建自动测试任务 |
| `GET` | `/api/v1/tasks` | 获取任务列表 |
| `GET` | `/api/v1/tasks/{task_id}` | 获取任务详情 |
| `POST` | `/api/v1/tasks/{task_id}/start` | 启动任务 |
| `POST` | `/api/v1/tasks/{task_id}/cancel` | 取消任务 |
| `GET` | `/api/v1/tasks/{task_id}/timeline` | 获取任务阶段时间线 |
| `GET` | `/api/v1/tasks/{task_id}/delivery` | 获取任务交付包 |
| `GET` | `/api/v1/tasks/{task_id}/defects` | 获取任务缺陷列表 |
| `GET` | `/api/v1/tasks/{task_id}/repair-context` | 获取任务级修复上下文 |

---

## 2. 项目管理 API

### 2.1 创建项目

```http
POST /api/v1/projects
```

**请求体:**

```json
{
  "name": "电商后台 V2.0 回归测试",
  "description": "电商后台管理系统的全量回归测试",
  "platforms": ["web", "android"],
  "entries": [
    {
      "platform": "web",
      "url": "https://admin.example.com",
      "viewport": {"width": 1920, "height": 1080}
    }
  ],
  "document_refs": [
    {
      "url": "https://xxx.feishu.cn/wiki/prd",
      "type": "prd",
      "description": "电商后台 PRD v2.1"
    }
  ]
}
```

**响应体:**

```json
{
  "code": 0,
  "data": {
    "project": {
      "id": "proj_abc123def456",
      "name": "电商后台 V2.0 回归测试",
      "status": "created",
      "platforms": ["web", "android"],
      "created_at": "2026-05-14T14:30:00Z",
      "document_count": 2
    }
  }
}
```

### 2.2 获取项目列表

```http
GET /api/v1/projects?status=active&page=1&page_size=20
```

**查询参数:**

| 参数 | 类型 | 说明 |
|------|------|------|
| status | str | 过滤状态: created/parsing/ready/running/completed/archived |
| q | str | 搜索关键字（匹配名称和描述） |

**响应数据:**

```json
{
  "items": [
    {
      "id": "proj_abc123",
      "name": "电商后台 V2.0 回归测试",
      "status": "ready",
      "platforms": ["web", "android"],
      "document_count": 3,
      "scenario_count": 45,
      "last_run_at": "2026-05-14T14:30:00Z",
      "created_at": "2026-05-13T10:00:00Z"
    }
  ],
  "total": 8,
  "page": 1,
  "page_size": 20
}
```

### 2.3 获取项目详情

```http
GET /api/v1/projects/{project_id}
```

**响应数据:**

```json
{
  "code": 0,
  "data": {
    "id": "proj_abc123",
    "name": "电商后台 V2.0 回归测试",
    "description": "电商后台管理系统的全量回归测试",
    "status": "ready",
    "platforms": ["web", "android"],
    "entries": [
      {
        "platform": "web",
        "url": "https://admin.example.com",
        "viewport": {"width": 1920, "height": 1080}
      }
    ],
    "document_refs": [
      {
        "id": "doc_001",
        "url": "https://xxx.feishu.cn/wiki/prd",
        "type": "prd",
        "status": "parsed",
        "rules_count": 45
      }
    ],
    "knowledge_base": {
      "id": "kb_001",
      "version": 3,
      "quality_score": "A",
      "rules_count": 87,
      "conflicts_count": 0
    },
    "statistics": {
      "total_scenarios": 45,
      "total_runs": 12,
      "last_run_at": "2026-05-14T14:30:00Z",
      "defect_count": 3
    },
    "created_at": "2026-05-13T10:00:00Z",
    "updated_at": "2026-05-14T14:30:00Z"
  }
}
```

### 2.4 更新项目

```http
PUT /api/v1/projects/{project_id}
```

**请求体:**

```json
{
  "name": "电商后台 V2.1 回归测试",
  "description": "更新描述",
  "platforms": ["web", "android", "ios"],
  "entries": [
    {
      "platform": "web",
      "url": "https://admin.example.com",
      "viewport": {"width": 1920, "height": 1080}
    },
    {
      "platform": "android",
      "app_package": "com.example.admin",
      "app_activity": ".MainActivity"
    }
  ]
}
```

### 2.5 删除项目

```http
DELETE /api/v1/projects/{project_id}
```

**响应:** 204 No Content

---

## 3. 文档管理 API

### 3.1 添加文档

```http
POST /api/v1/projects/{project_id}/documents
```

**请求体:**

```json
{
  "url": "https://xxx.feishu.cn/wiki/ui_spec",
  "type": "ui_spec",
  "description": "UI 设计规范 v1.3"
}
```

**响应:** 返回文档引用

### 3.2 文档列表

```http
GET /api/v1/projects/{project_id}/documents
```

**响应数据:**

```json
{
  "items": [
    {
      "id": "doc_001",
      "url": "https://xxx.feishu.cn/wiki/prd",
      "type": "prd",
      "status": "parsed",
      "description": "电商后台 PRD v2.1",
      "version": "2.1",
      "rules_count": 45,
      "error_message": null,
      "created_at": "2026-05-13T10:00:00Z",
      "parsed_at": "2026-05-13T10:05:00Z"
    }
  ]
}
```

### 3.3 解析文档

```http
POST /api/v1/projects/{project_id}/documents/parse
```

**请求体:**

```json
{
  "document_ids": ["doc_001", "doc_002"],
  "strategies": ["general", "structured", "multi_round", "reverse"]
}
```

**响应:**

```json
{
  "code": 0,
  "data": {
    "task_id": "parse_task_001",
    "status": "processing",
    "estimated_time_seconds": 120
  }
}
```

### 3.4 获取解析状态

```http
GET /api/v1/projects/{project_id}/documents/parse/status
```

**响应数据:**

```json
{
  "code": 0,
  "data": {
    "overall_status": "completed",
    "documents": [
      {
        "document_id": "doc_001",
        "status": "completed",
        "progress": 1.0,
        "rules_found": 45,
        "conflicts_found": 1
      },
      {
        "document_id": "doc_002",
        "status": "failed",
        "progress": 0.3,
        "error": "文档内容超出 Token 限制",
        "suggestion": "尝试分段解析或减少文档范围"
      }
    ]
  }
}
```

---

## 4. 知识库 API

### 4.1 获取知识库

```http
GET /api/v1/projects/{project_id}/knowledge
```

**查询参数:**

| 参数 | 类型 | 说明 |
|------|------|------|
| version | int | 指定版本号，默认最新 |

**响应数据:**

```json
{
  "code": 0,
  "data": {
    "id": "kb_001",
    "project_id": "proj_abc123",
    "version": 1,
    "quality_score": {
      "overall": "A",
      "rule_coverage": 0.91,
      "confidence": 0.88,
      "human_reviewed": false
    },
    "statistics": {
      "total_rules": 87,
      "confirmed_rules": 72,
      "candidate_rules": 12,
      "conflicted_rules": 3,
      "ui_standards": 15,
      "business_lines": 4
    },
    "conflicts": [
      {
        "id": "conflict_001",
        "type": "contradiction",
        "description": "验证码有效期冲突: 60s vs 5min",
        "source_a": {"document": "prd", "text": "验证码 60 秒有效"},
        "source_b": {"document": "api_spec", "text": "验证码 5 分钟有效"},
        "status": "pending",
        "suggested_action": "与产品经理确认验证码有效期的正确值"
      }
    ]
  }
}
```

### 4.2 获取规则列表

```http
GET /api/v1/projects/{project_id}/knowledge/rules
```

**查询参数:**

| 参数 | 类型 | 说明 |
|------|------|------|
| category | str | 过滤: flow/rule/permission/ui |
| status | str | 过滤: confirmed/candidate/conflicted |
| confidence_min | float | 最低置信度过滤 |

### 4.3 更新规则

```http
PUT /api/v1/projects/{project_id}/knowledge/rules/{rule_id}
```

**请求体:**

```json
{
  "content": "验证码 60 秒有效（与产品经理确认）",
  "confidence": 0.95,
  "status": "confirmed",
  "notes": "2026-05-14 经与张三确认，验证码有效期统一为 60 秒"
}
```

### 4.4 消解冲突

```http
POST /api/v1/projects/{project_id}/knowledge/conflicts/{conflict_id}/resolve
```

**请求体:**

```json
{
  "resolution": "accept_a",
  "note": "与 PM 确认，PRD 的 60 秒为准"
}
```

### 4.5 知识库版本历史

```http
GET /api/v1/projects/{project_id}/knowledge/versions
```

### 4.6 人工确认知识库

```http
POST /api/v1/projects/{project_id}/knowledge/verify
```

**请求体:**

```json
{
  "confirmed_rules": ["rule_001", "rule_002"],
  "rejected_rules": ["rule_003"],
  "modified_rules": [
    {
      "rule_id": "rule_004",
      "content": "修改后的规则内容"
    }
  ],
  "notes": "首次确认，整体准确率良好，修正了 1 条规则"
}
```

---

## 5. 场景管理 API

### 5.1 生成测试场景

```http
POST /api/v1/projects/{project_id}/scenarios/generate
```

**请求体:**

```json
{
  "platforms": ["web", "android"],
  "types": ["positive", "boundary", "abnormal", "permission"],
  "business_lines": ["user_login", "order_flow", "product_management"],
  "coverage_threshold": 0.85
}
```

**响应:**

```json
{
  "code": 0,
  "data": {
    "task_id": "scenario_gen_001",
    "status": "processing",
    "estimated_time_seconds": 60
  }
}
```

### 5.2 获取场景列表

```http
GET /api/v1/projects/{project_id}/scenarios
```

**查询参数:**

| 参数 | 类型 | 说明 |
|------|------|------|
| business_line | str | 业务线过滤 |
| type | str | 场景类型过滤 |
| platform | str | 平台过滤 |

**响应数据:**

```json
{
  "items": [
    {
      "id": "scenario_001",
      "project_id": "proj_abc123",
      "business_line": "user_login",
      "name": "用户登录 - 正向流程",
      "type": "positive",
      "platform": "web",
      "role": "普通用户",
      "case_count": 3,
      "coverage": {
        "rule_coverage": 0.92,
        "page_coverage": 1.0
      },
      "status": "ready"
    }
  ],
  "summary": {
    "total": 12,
    "positive": 4,
    "boundary": 3,
    "abnormal": 3,
    "permission": 2,
    "coverage_report": {
      "rule_coverage": 0.91,
      "page_coverage": 0.88,
      "role_coverage": 0.90,
      "grade": "A"
    }
  }
}
```

### 5.3 获取场景详情

```http
GET /api/v1/scenarios/{scenario_id}
```

**响应数据:**

```json
{
  "code": 0,
  "data": {
    "id": "scenario_001",
    "project_id": "proj_abc123",
    "business_line": "user_login",
    "name": "用户登录 - 正向流程",
    "type": "positive",
    "platform": "web",
    "role": "普通用户",
    "description": "验证普通用户可以正常登录系统",
    "preconditions": [
      "已注册有效的用户账号",
      "浏览器已打开登录页面"
    ],
    "cases": [
      {
        "id": "tc_001",
        "name": "正常登录 - 用户名密码正确",
        "steps": [
          {
            "index": 1,
            "action": "输入用户名",
            "target": "用户名输入框",
            "value": "admin@example.com",
            "verifications": ["ui", "console"]
          },
          {
            "index": 2,
            "action": "输入密码",
            "target": "密码输入框",
            "value": "********",
            "verifications": ["ui", "console"]
          },
          {
            "index": 3,
            "action": "点击登录按钮",
            "target": "登录按钮",
            "verifications": ["ui", "api", "console", "business"],
            "expected": {
              "api": {"status": 200, "path": "/api/v1/auth/login"},
              "business": {"url_contains": "/dashboard", "visible_text": "欢迎回来"}
            }
          }
        ],
        "expected_results": {
          "business": "登录成功后跳转到仪表盘页面",
          "ui": "仪表盘完整渲染，显示用户信息",
          "api": "登录 API 返回 200 + token",
          "console": "无 Error 日志"
        }
      }
    ]
  }
}
```

### 5.4 修订场景

```http
PUT /api/v1/scenarios/{scenario_id}
```

**请求体:** 场景的部分或全部字段

### 5.5 导出场景矩阵

```http
GET /api/v1/projects/{project_id}/scenarios/export?format=json
```

**查询参数:**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| format | str | json | json / csv / markdown |

---

## 6. 执行管理 API

### 6.1 创建执行计划

```http
POST /api/v1/projects/{project_id}/runs
```

**请求体:**

```json
{
  "name": "全量回归 2026-05-14",
  "platforms": ["web", "android"],
  "scenario_ids": ["scenario_001", "scenario_002"],
  "scope": "all",
  "concurrency": {
    "web": 4,
    "android": 2
  },
  "retry_config": {
    "max_retries": 3,
    "retry_delay_seconds": 10
  },
  "notify": {
    "on_complete": true,
    "webhook_url": "https://hooks.example.com/autotest"
  }
}
```

**响应:**

```json
{
  "code": 0,
  "data": {
    "run_id": "run_001",
    "status": "queued",
    "total_cases": 45,
    "created_at": "2026-05-14T14:30:00Z"
  }
}
```

### 6.2 获取执行详情

```http
GET /api/v1/runs/{run_id}
```

**响应数据:**

```json
{
  "code": 0,
  "data": {
    "id": "run_001",
    "project_id": "proj_abc123",
    "name": "全量回归 2026-05-14",
    "status": "running",
    "platforms": ["web", "android"],
    "progress": {
      "total": 45,
      "completed": 23,
      "passed": 20,
      "failed": 2,
      "uncertain": 1,
      "percent": 51.1
    },
    "platform_progress": {
      "web": {"total": 25, "completed": 15, "passed": 14, "failed": 1},
      "android": {"total": 20, "completed": 8, "passed": 6, "failed": 1}
    },
    "current_step": {
      "case_id": "tc_015",
      "step_index": 3,
      "action": "点击提交订单"
    },
    "started_at": "2026-05-14T14:30:00Z",
    "estimated_end_at": "2026-05-14T15:00:00Z"
  }
}
```

### 6.3 获取执行进度（轻量）

```http
GET /api/v1/runs/{run_id}/progress
```

**响应数据:**

```json
{
  "code": 0,
  "data": {
    "run_id": "run_001",
    "status": "running",
    "progress": {
      "total": 45,
      "completed": 23,
      "passed": 20,
      "failed": 2,
      "uncertain": 1,
      "percent": 51.1
    },
    "current_step": {
      "case_id": "tc_015",
      "step_index": 3,
      "action": "点击提交订单"
    }
  }
}
```

### 6.4 取消执行

```http
POST /api/v1/runs/{run_id}/cancel
```

### 6.5 重试执行

```http
POST /api/v1/runs/{run_id}/retry
```

**请求体:**

```json
{
  "case_ids": ["tc_003", "tc_008"],
  "platforms": ["web"]
}
```

### 6.6 执行历史列表

```http
GET /api/v1/projects/{project_id}/runs
```

---

## 7. 报告与缺陷 API

### 7.1 获取执行报告

```http
GET /api/v1/runs/{run_id}/report
```

**查询参数:**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| format | str | summary | summary / full / html / json_compact |

**响应数据 (format=summary):**

```json
{
  "code": 0,
  "data": {
    "run_id": "run_001",
    "project_name": "电商后台 V2.0 回归测试",
    "executed_at": "2026-05-14T14:30:00Z",
    "duration_seconds": 845,
    "summary": {
      "total_cases": 45,
      "passed": 38,
      "failed": 4,
      "uncertain": 3,
      "pass_rate": 0.84
    },
    "platforms": {
      "web": {"total": 25, "passed": 22, "failed": 2, "uncertain": 1},
      "android": {"total": 20, "passed": 16, "failed": 2, "uncertain": 2}
    },
    "defects": [
      {
        "id": "def_001",
        "severity": "high",
        "type": "api_error",
        "title": "创建订单 API 返回 500",
        "business_line": "order_flow",
        "evidence_count": 3
      },
      {
        "id": "def_002",
        "severity": "medium",
        "type": "ui_mismatch",
        "title": "订单列表页数据为空时未显示空状态",
        "business_line": "order_flow"
      }
    ],
    "recommendation": "建议修复 4 个失败用例中的 P0/P1 缺陷后重新验证"
  }
}
```

### 7.2 获取缺陷详情

```http
GET /api/v1/defects/{defect_id}
```

**查询参数:**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| format | str | full | full / compact（compact 不含截图 base64）|

**响应数据:** 见需求文档 §3.2 结构化缺陷数据 Schema

### 7.3 获取缺陷证据详情

```http
GET /api/v1/defects/{defect_id}/evidence
```

获取缺陷的完整证据链（含截图 base64、控制台日志、API 调用、页面状态快照）。设计参考需求文档 §3.2。

**查询参数:**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| format | str | full | full（含截图 base64） / compact（不含截图，适合 AI 处理） |

**响应:** 完整的证据链数据（`EvidenceChain[]`），数据结构参考 [详细设计说明书.md](./详细设计说明书.md) 中与缺陷事件、证据链相关的定义。

### 7.4 缺陷列表

```http
GET /api/v1/runs/{run_id}/defects
```

**查询参数:**

| 参数 | 类型 | 说明 |
|------|------|------|
| severity | str | 过滤: high/medium/low/suggestion |
| type | str | 过滤: api_error/console_error/ui_mismatch/biz_error |

### 7.4 导出报告

```http
GET /api/v1/runs/{run_id}/report/export?format=html
```

**查询参数:**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| format | str | html | html / json / pdf |

**响应:** 文件下载

---

## 8. MCP 接口协议

### 8.1 MCP Server 端点

```
Host: mcp.autotest.local
Auth: Authorization: Bearer <api_key>
```

### 8.2 MCP 工具定义

#### get_defect

```json
{
  "name": "get_defect",
  "description": "获取缺陷的完整参考数据，供 AI 开发工具消费",
  "input_schema": {
    "type": "object",
    "properties": {
      "defect_id": {"type": "string", "description": "缺陷 ID"},
      "format": {
        "type": "string",
        "enum": ["full", "compact"],
        "description": "full=含截图base64, compact=不含截图(适合AI处理)"
      }
    },
    "required": ["defect_id"]
  },
  "output": {
    "type": "object",
    "properties": {
      "defect": {"type": "object"},
      "reproduction_steps": {"type": "array"},
      "evidence": {"type": "object"},
      "ai_reference": {"type": "object"}
    }
  }
}
```

#### list_defects

```json
{
  "name": "list_defects",
  "description": "列出执行记录中的所有缺陷（摘要信息）",
  "input_schema": {
    "type": "object",
    "properties": {
      "run_id": {"type": "string", "description": "执行记录 ID"},
      "severity": {
        "type": "string",
        "enum": ["high", "medium", "low", "suggestion"],
        "description": "按严重程度过滤（可选）"
      }
    },
    "required": ["run_id"]
  }
}
```

#### create_run

```json
{
  "name": "create_run",
  "description": "创建并启动一次测试执行",
  "input_schema": {
    "type": "object",
    "properties": {
      "project_id": {"type": "string"},
      "platforms": {"type": "array", "items": {"type": "string"}},
      "scenario_ids": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["project_id"]
  }
}
```

### 8.3 MCP Resource 定义

```
defect://{defect_id}           # 缺陷完整数据（JSON）
report://{run_id}              # 执行报告（JSON）
run://{run_id}/progress        # 执行进度（JSON）
```

---

## 9. WebSocket 实时推送

### 9.1 连接

```http
WebSocket /api/v1/ws/runs/{run_id}
```

### 9.2 推送消息格式

```json
{
  "type": "run_progress",
  "data": {
    "run_id": "run_001",
    "progress": {"total": 45, "completed": 23, "percent": 51.1},
    "current_step": {
      "case_id": "tc_015",
      "step_index": 3,
      "action": "点击提交订单",
      "platform": "web"
    }
  },
  "timestamp": "2026-05-14T14:30:00Z"
}
```

### 9.3 消息类型

| 类型 | 说明 |
|------|------|
| `run_progress` | 执行进度更新（每步完成推送） |
| `step_completed` | 单步执行完成（含初步校验结果） |
| `defect_found` | 发现缺陷时推送 |
| `run_completed` | 执行完成 |
| `run_error` | 执行异常 |

---

## 10. 错误码定义

| 错误码 | 名称 | 说明 |
|--------|------|------|
| **通用错误 (40000-40099)** | | |
| 40000 | INVALID_PARAMETER | 请求参数校验失败 |
| 40001 | RESOURCE_NOT_FOUND | 资源不存在 |
| 40002 | RESOURCE_CONFLICT | 资源冲突（重复创建） |
| 40003 | OPERATION_NOT_ALLOWED | 当前状态下不允许此操作 |
| **认证错误 (40100-40199)** | | |
| 40100 | UNAUTHORIZED | 未提供认证信息 |
| 40101 | INVALID_API_KEY | API Key 无效 |
| 40102 | TOKEN_EXPIRED | Token 已过期 |
| **权限错误 (40300-40399)** | | |
| 40300 | PERMISSION_DENIED | 无权限 |
| **限流错误 (42900-42999)** | | |
| 42900 | RATE_LIMITED | 请求频率超限 |
| **业务错误 (41000-41999)** | | |
| 41001 | DOCUMENT_PARSE_FAILED | 文档解析失败 |
| 41002 | KNOWLEDGE_BUILD_FAILED | 知识库构建失败 |
| 41003 | SCENARIO_GENERATION_FAILED | 场景生成失败 |
| 41004 | RUN_EXECUTION_FAILED | 执行失败 |
| **基础设施错误 (50000-50099)** | | |
| 50000 | INTERNAL_ERROR | 服务器内部错误 |
| 50001 | AI_SERVICE_ERROR | AI 服务调用失败 |
| 50002 | EXECUTOR_CONNECTION_ERROR | 执行器连接失败 |
| 50003 | OCR_SERVICE_ERROR | OCR 服务不可用 |
| 50004 | FILE_STORAGE_ERROR | 文件存储错误 |
| **超时错误 (50400-50499)** | | |
| 50400 | UPSTREAM_TIMEOUT | 上游服务超时 |
| 50401 | AI_SERVICE_TIMEOUT | AI 服务响应超时 |
| 50402 | EXECUTOR_TIMEOUT | 执行器超时 |

---

## 11. Rate Limiting 策略

### 11.1 限流规则

```yaml
限流算法: 令牌桶 (Token Bucket)

默认限制（按 API Key）:
  ┌──────────────────────┬──────────┬──────────┬──────────┐
  │ 接口分类              │ 速率      │ 突发     │ 窗口      │
  ├──────────────────────┼──────────┼──────────┼──────────┤
  │ 查询类 (GET)          │ 100/s    │ 200      │ 1s       │
  │ 写操作 (POST/PUT)     │ 20/s     │ 50       │ 1s       │
  │ 批量操作               │ 5/s      │ 10       │ 1s       │
  │ 文件上传               │ 2/s      │ 5        │ 1s       │
  │ 执行操作 (run)         │ 1/s      │ 3        │ 1s       │
  │ 文档解析               │ 1/10s    │ 2        │ 10s      │
  │ MCP 查询               │ 50/s     │ 100      │ 1s       │
  └──────────────────────┴──────────┴──────────┴──────────┘

限流响应:
  HTTP 429 Too Many Requests
  {
    "code": 42900,
    "message": "请求频率超限",
    "data": {
      "retry_after_ms": 500,
      "limit": 100,
      "remaining": 0,
      "reset_at": "2026-05-14T14:30:01Z"
    }
  }

响应头:
  X-RateLimit-Limit: 100
  X-RateLimit-Remaining: 45
  X-RateLimit-Reset: 1715673001
```

### 11.2 限流实现要点

```yaml
实现方式:
  - Redis + 令牌桶算法
  - 每个 API Key 独立的限流计数器
  - 限流规则可配置（system_configs 表）
  - 限流触发时记录 WARNING 日志

特殊豁免:
  - WebSocket 连接不受限流约束
  - 健康检查端点 /health 不受限流约束
  - MCP 接口使用独立的限流规则
```

---

## 12. Webhook 回调系统

### 12.1 Webhook 注册

```http
POST /api/v1/webhooks
```

**请求体:**

```json
{
  "url": "https://hooks.example.com/autotest",
  "events": ["run.completed", "defect.found"],
  "secret": "whsec_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "description": "发送到内部通知系统",
  "active": true
}
```

**响应:** Webhook 订阅信息（含 `webhook_id`）

### 12.2 Webhook 事件清单

```yaml
支持的事件类型:
  run.completed:      执行完成（含汇总数据）
  run.failed:         执行失败
  run.cancelled:      执行被取消
  defect.found:       发现新缺陷
  defect.severity_high: 发现 P0/P1 缺陷
  document.parsed:    文档解析完成
  knowledge.updated:  知识库更新
  scenario.generated: 场景生成完成
```

### 12.3 Webhook 回调格式

```json
{
  "event_id": "evt_abc123",
  "event_type": "defect.found",
  "timestamp": "2026-05-14T14:30:00Z",
  "payload": {
    "defect_id": "def_001",
    "run_id": "run_001",
    "project_id": "proj_abc123",
    "severity": "high",
    "title": "创建订单 API 返回 500",
    "summary": "...",
    "detail_url": "https://autotest.example.com/defects/def_001"
  }
}
```

### 12.4 回调可靠性

```yaml
投递保证:
  - 至少一次投递 (at-least-once)
  - 失败重试: 指数退避（5s, 25s, 125s, 625s）
  - 最大重试: 5 次
  - 全部失败后: 标记为 failed，在 Webhook 日志中可查

签名:
  - 使用 HMAC-SHA256 签名
  - Header: X-AutoTest-Signature
  - 签名内容: {timestamp}.{body_json}
  - 接收方应验证签名

Webhook 状态:
  active:     正常接收
  disabled:   手动禁用
  failing:    连续失败（自动标记）
```

---

## 13. 批量操作规范

### 13.1 批量读取

```http
GET /api/v1/batch/projects
```

**请求参数:**

```json
{
  "ids": ["proj_001", "proj_002", "proj_003"]
}
```

**响应:**

```json
{
  "code": 0,
  "data": {
    "proj_001": { "...project data..." },
    "proj_002": { "...project data..." },
    "proj_003": null  /* 不存在的 ID 返回 null */
  }
}
```

### 13.2 批量写入

```http
POST /api/v1/batch/runs/{run_id}/retry
```

**请求体:**

```json
{
  "operations": [
    {"case_id": "tc_001", "platform": "web"},
    {"case_id": "tc_003", "platform": "android"}
  ]
}
```

**响应:**

```json
{
  "code": 0,
  "data": {
    "results": [
      {"case_id": "tc_001", "platform": "web", "status": "accepted"},
      {"case_id": "tc_003", "platform": "android", "status": "accepted"}
    ],
    "failed_count": 0
  }
}
```

### 13.3 批量操作限制

```yaml
批量操作约束:
  - 单次批量操作 ≤ 100 条
  - 批量操作计入 API 限流配额（5/s）
  - 批量操作中单条失败不影响其他条
  - 批量操作返回每个条目的独立结果
```

---

## 14. 文件上传规范

### 14.1 上传端点

```http
POST /api/v1/files/upload
```

**请求格式:** `multipart/form-data`

| 字段 | 类型 | 说明 |
|------|------|------|
| file | File | 文件内容 |
| category | str | 文件分类: screenshot | doc | log | attachment |
| project_id | str | 关联项目（可选） |

**响应:**

```json
{
  "code": 0,
  "data": {
    "file_id": "file_abc123",
    "url": "https://storage.autotest.example.com/proj_abc/screenshots/abc123.png",
    "size_bytes": 245760,
    "mime_type": "image/png",
    "content_hash": "sha256-xxxxx",
    "created_at": "2026-05-14T14:30:00Z"
  }
}
```

### 14.2 文件限制

```yaml
上传限制:
  单文件大小上限: 50MB
  截图文件上限: 10MB
  文档文件上限: 20MB
  日志文件上限: 50MB
  
  支持格式:
    - 图片: png, jpg, webp
    - 文档: md, pdf, html
    - 日志: txt, log, json
  
  存储路径规则:
    {bucket}/{project_id}/{category}/{file_id}.{ext}
    
  保留策略:
    截图: 30 天（活跃）/ 1 年（归档）
    日志: 7 天（活跃）/ 30 天（归档）
```

### 14.3 文件访问

```http
GET /api/v1/files/{file_id}
```

**响应:** 文件内容（Content-Type 自动识别）

```yaml
认证:
  - 文件访问需要 API Key 认证
  - 临时访问链接（用于嵌入报告）:
    GET /api/v1/files/{file_id}/download?token={temp_token}&expires=300
  - 临时 Token 有效期: 5 分钟
```

---

## 附录: API 变更管理

```
API 版本策略:
  - URL 路径版本: /api/v1/, /api/v2/
  - 向后兼容: v1 接口在 v2 发布后仍保持至少 6 个月可用
  - 弃用通知: 弃用前至少提前 30 天在响应头中加入 Deprecation 标记

响应头:
  X-API-Version: 1.0
  X-API-Deprecated: true (弃用后添加)
  X-API-Deprecation-Date: 2026-12-31
```

---

> **本文档是 SDD (Specification-Driven Development) 的 API 规约**
> 所有客户端/服务端实现必须遵循本文定义的端点、格式和状态码
