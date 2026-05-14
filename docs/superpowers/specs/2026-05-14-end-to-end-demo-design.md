# AutoTest — 全链路端到端 Demo 设计文档

> 版本: 1.0 | 日期: 2026-05-14 | 状态: 草案
> 基于已完成: Midscene 执行器集成 + 四维校验 + AI 综合分析引擎

---

## 1. 概述

### 1.1 目标

实现完整闭环：**输入被测 URL + 需求文档 → 文档解析 + 页面发现 → 按角色×流程生成场景 → Midscene AI 执行 → 四维校验 → 跨步骤因果链 → 根因分析 → 输出结构化修复参考数据**

### 1.2 CLI

```bash
autotest demo --url https://admin.example.com --doc https://docs.example.com/prd.md
```

### 1.3 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--url` | 是 | 被测系统入口 URL |
| `--doc` | 否 | 文档 URL，可多个，自动识别类型 |
| `--role` | 否 | 限定角色，默认全部 |
| `--output` | 否 | 报告输出路径 |
| `--format` | 否 | json / markdown，默认 json |

### 1.4 文档类型自动识别

| URL 特征 | 类型 |
|----------|------|
| prd/requirement/需求 | PRD |
| ui/spec/规范/界面 | UI 规范 |
| api/interface/接口 | API 文档 |
| 交互/flow/ux | 交互设计 |
| 其他 | 通用 |

---

## 2. 模块 1: 双通道 — 文档解析 + 页面发现

### 2.1 文档解析（复用现有管道）

```
Stage 1: 原始采集 → Stage 2: 结构化 → Stage 3: 规则提取
→ Stage 4: 冲突消解 → Stage 5: 知识构建

输出: BusinessRule[] + Role[] + BusinessChain[]
```

### 2.2 页面发现（新增）

```
page_discovery(url):
  1. 导航到 URL，等待 networkidle
  2. 提取:
     - 导航菜单: nav>a, sidebar links, menu items
     - 交互元素: button(文本), a(文本+href), input(placeholder+type), select, textarea
     - 表单: form>所有字段+提交按钮
     - 表格: table>列头+行操作
     - 标题: h1/h2/h3, label, alert/error 区域
     - 页面标题: document.title
  3. 去重结构化: {type, text, selector_hint, is_visible}
     - 按区域分组: header/nav/main/sidebar/footer
  4. 截图 (全页+视口)
  5. 输出: PageDiscoveryResult

保护: 交互元素上限50, 文本上限80, 导航深度最多3层
```

### 2.3 文档-页面对照

```
对比:
  功能流程: 文档路径 vs 页面上存在的导航/按钮
  角色权限: 文档定义 vs 页面菜单可见性
  UI规范: 文档文案 vs 页面元素
  数据定义: 文档字段 vs 页面表单

评级:
  ✅ 一致   ⚠️ 缺失 (文档有页面无)
  ⚡ 多余 (页面有文档无)   ❌ 冲突

输出: ContrastReport
```

---

## 3. 模块 2: 场景生成 — 角色×流程×类型

### 3.1 矩阵

```
流程: 来自文档业务链
角色: 来自文档角色定义
元素: 来自页面发现

组合优先级:
  高: 文档定义的角色×流程 → 必须生成
  中: 页面存在但文档未定义 → 补充生成
  低: 文档有但页面元素不可见 → 标记不可测试

每种 4 类型:
  positive: 正常路径
  boundary: 空输入/超长/极限值
  abnormal: 错误密码/超时/服务端错误
  permission: 越权/未授权

上限: 20 场景, 每场景 10 步, 总计 100 步
```

### 3.2 与现有 ChainBuilder 集成

复用 `chain_builder.py` 的 `generate_test_chains` 和 `_build_scenario`。增强点：步骤 target 使用页面实际元素文本，预期结果来自文档规则。

---

## 4. 模块 3: 执行 + 四维校验

```
for each 场景(role, flow, type):
  for each 步骤:
    1. 导航到起始页 (跨流程时)
    2. capturer.clear()
    3. 操作前截图
    4. Midscene AI 执行 (或 4 级降级)
    5. 等待 800ms
    6. 操作后截图
    7. 采集: console + network + page state
    8. 四维并行校验:
       UI: 错误文案/空白/组件可见
       Console: JS Error/Warning
       API: 4xx/5xx/超时(>5s)
       Business: URL/标题/预期文案
    9. 记录 StepExecutionRecord

步骤状态:
  passed: 全通过
  uncertain: 仅 warning
  failed: error 出现

异常场景规则:
  type=abnormal → 预期失败
    预期失败且实际失败 → ✅
    预期失败但实际成功 → ❌ 缺陷
```

---

## 5. 模块 4: 跨步骤因果链 + AI 分析

### 5.1 因果发现

```
collect_all_anomalies(scenario_steps):
  1. 收集所有步骤异常
  2. 按时间戳全局排序
  3. 规则匹配 (<10ms):
     api_error→console_error: 500ms内, 相同API路径
     api_error→api_error: Token过期→批量401
     console_error→ui_broken: 未捕获异常后组件缺失
  4. LLM 补充 (规则未覆盖):
     - 单条 prompt 带全部异常
     - 返回因果分组
     - 置信度<0.6 → "不确定"
  5. 输出 EvidenceChain[] (可跨步骤)
```

### 5.2 AI 分析 fallback

```
if AI available:
  analyze(defect) → root_cause + fix_suggestion
else:
  规则引擎:
    严重度 = 维度数+类型权重
    标题 = "维度X异常"
    修复建议 = "请检查{触发维度}代码"
```

---

## 6. 模块 5: 结构化输出

### 6.1 报告结构

```json
{
  "demo_run": {
    "target_url": "https://admin.example.com",
    "documents": ["prd.md"],
    "duration_seconds": 45,
    "browser": "Chromium headless",
    "viewport": "1920x1080",
    "timestamp": "2026-05-14T14:30:00Z"
  },
  "summary": {
    "total_scenarios": 6,
    "total_steps": 24,
    "passed": 18, "failed": 4, "uncertain": 2,
    "defects_found": 3,
    "coverage": {"documented_features": 12, "tested_features": 10, "coverage_rate": "83%"}
  },
  "scenarios": [{
    "role": "管理员", "flow": "商品管理", "type": "正向",
    "status": "failed",
    "steps": [{"index": 1, "action": "打开页面", "status": "passed", "duration_ms": 3200}],
    "defects": ["def_001"]
  }],
  "defects": [{
    "id": "def_001",
    "severity": "high",
    "title": "创建商品 API 返回 500",
    "evidence_chain": {
      "trigger": {"dimension": "api", "event": "POST /api/products → 500"},
      "propagation": [
        {"step": 3, "dimension": "api", "event": "缺参"},
        {"step": 3, "dimension": "console", "event": "TypeError"},
        {"step": 3, "dimension": "ui", "event": "错误提示"}
      ],
      "chain_summary": "API缺参→后端500→前端报错→页面错误"
    },
    "screenshots": {"error_state": "data:image/png;base64,..."},
    "console_logs": {"errors": [{"message": "TypeError", "source": "app.js:1"}]},
    "api_calls": [{
      "request": {"method": "POST", "url": "/api/products", "body": {"name": "test"}},
      "response": {"status": 500, "body": "Internal Server Error"}
    }],
    "ai_analysis": {
      "root_cause": "缺少 price 必填字段校验",
      "confidence": "medium",
      "fix_reference": {"file_hint": "ProductController.create()", "description": "添加 @NotNull 校验"}
    }
  }]
}
```

### 6.2 输出格式

```
--format json      → AI 工具消费
--format markdown  → 人类阅读
--output file.json → 写入文件
无 --output        → 标准输出摘要
```

---

## 7. 实现计划

### Phase 1: 页面发现器
- 新建: `app/infrastructure/executor/page_discovery.py`
- 新建: `app/domain/models/discovery.py`

### Phase 2: 对照验证
- 新建: `app/services/contrast_service.py`
- 修改: `app/engine/chain_builder.py` — 页面元素集成

### Phase 3: CLI 命令
- 新建: `scripts/demo.py` — 全流程编排
- 集成: 文档解析 + 页面发现 + 场景生成 + 执行 + 校验 + 分析 + 输出

### Phase 4: 报告 + MCP
- 新建: `app/services/demo_report_service.py`
- 修改: `app/api/mcp/server.py` — 添加 demo 工具

---

## 8. 不在此范围

- Android/iOS 执行器
- 多租户/权限
- CI/CD 集成
- 定时执行
- 性能测试
- 截图 OCR 深度校验
