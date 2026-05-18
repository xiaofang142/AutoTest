"""Business chain builder: LLM-driven extraction of business lines, functions, and process flows.

Three-tier extraction strategy:
  Level 0 (LLM, best): AI extracts business lines, functions, workflows from documents
  Level 1 (Keywords, medium): Rule-based page/flow extraction from parsed rules
  Level 2 (Template, fallback): Pre-built industry templates when no input available

Output: business_chains = [{name, business_line, function, steps, roles}] 
  → generate_test_chains() → TestScenario[] (4 path types × roles)
"""
import json
import re
from typing import Optional

from app.domain.models.discovery import DiscoveredElement
from app.domain.models.knowledge import BusinessRule
from app.domain.models.scenario import TestCase, TestScenario, TestStep
from app.interfaces.ai_service import AIService
from app.lib.id_generator import generate_id
from app.lib.logger import get_logger

logger = get_logger(__name__)

# ── Pre-built industry templates for zero-LLM fallback ──────────────
INDUSTRY_TEMPLATES: dict[str, list[dict]] = {
    "generic": [
        {
            "name": "用户身份管理",
            "business_line": "用户管理",
            "function": "账号生命周期",
            "steps": [
                {"action": "打开登录页面", "page": "登录页", "expected": "页面加载成功"},
                {"action": "输入账号密码", "page": "登录页", "expected": "输入正常"},
                {"action": "点击登录", "page": "登录页", "expected": "登录成功跳转首页"},
            ],
            "roles": ["管理员", "普通用户"],
        },
        {
            "name": "基础内容浏览",
            "business_line": "内容管理",
            "function": "内容展示",
            "steps": [
                {"action": "打开首页", "page": "首页", "expected": "首页加载完成"},
                {"action": "浏览列表", "page": "列表页", "expected": "列表数据展示"},
                {"action": "查看详情", "page": "详情页", "expected": "详情信息完整"},
            ],
            "roles": ["访客", "普通用户"],
        },
    ],
    "ecommerce": [
        {
            "name": "商品浏览搜索",
            "business_line": "商品管理",
            "function": "商品检索",
            "steps": [
                {"action": "打开商城首页", "page": "首页", "expected": "首页加载"},
                {"action": "搜索商品", "page": "搜索页", "expected": "搜索结果展示"},
                {"action": "查看商品详情", "page": "详情页", "expected": "详情信息完整"},
            ],
            "roles": ["访客", "普通用户"],
        },
        {
            "name": "购物车管理",
            "business_line": "交易管理",
            "function": "购物车",
            "steps": [
                {"action": "加入购物车", "page": "商品详情", "expected": "加入成功"},
                {"action": "查看购物车", "page": "购物车", "expected": "商品列表展示"},
                {"action": "修改数量", "page": "购物车", "expected": "数量更新"},
                {"action": "删除商品", "page": "购物车", "expected": "商品移除"},
            ],
            "roles": ["普通用户"],
        },
        {
            "name": "下单支付",
            "business_line": "交易管理",
            "function": "订单流程",
            "steps": [
                {"action": "提交订单", "page": "订单确认页", "expected": "订单创建成功"},
                {"action": "选择支付方式", "page": "支付页", "expected": "支付方式可选"},
                {"action": "完成支付", "page": "支付页", "expected": "支付成功"},
                {"action": "查看订单状态", "page": "订单详情", "expected": "状态更新"},
            ],
            "roles": ["普通用户"],
        },
        {
            "name": "订单管理",
            "business_line": "交易管理",
            "function": "订单管理",
            "steps": [
                {"action": "查看订单列表", "page": "订单列表", "expected": "列表加载"},
                {"action": "查看订单详情", "page": "订单详情", "expected": "详情展示"},
                {"action": "取消订单", "page": "订单详情", "expected": "取消成功"},
            ],
            "roles": ["管理员", "普通用户"],
        },
    ],
    "admin": [
        {
            "name": "用户管理",
            "business_line": "系统管理",
            "function": "用户管理",
            "steps": [
                {"action": "查看用户列表", "page": "用户管理", "expected": "列表加载"},
                {"action": "创建用户", "page": "用户管理", "expected": "创建成功"},
                {"action": "编辑用户", "page": "用户管理", "expected": "编辑成功"},
                {"action": "删除用户", "page": "用户管理", "expected": "删除成功"},
            ],
            "roles": ["管理员"],
        },
        {
            "name": "角色权限管理",
            "business_line": "系统管理",
            "function": "权限管理",
            "steps": [
                {"action": "查看角色列表", "page": "权限管理", "expected": "列表加载"},
                {"action": "分配角色权限", "page": "权限管理", "expected": "分配成功"},
            ],
            "roles": ["管理员"],
        },
        {
            "name": "系统配置",
            "business_line": "系统管理",
            "function": "系统配置",
            "steps": [
                {"action": "查看系统设置", "page": "设置页", "expected": "设置加载"},
                {"action": "修改配置", "page": "设置页", "expected": "保存成功"},
            ],
            "roles": ["管理员"],
        },
    ],
}


LLM_EXTRACT_PROMPT = """你是一个资深的测试架构师。根据以下产品需求文档内容，提取完整的测试业务体系。

要求：
1. 识别所有 **业务线**（business_line）：系统有哪些大的业务领域
2. 每个业务线下识别 **功能线**（function）：该业务线包含哪些子功能
3. 每个功能线下识别 **流程线**（flow）：该功能的核心操作流程（步骤序列）
4. 每个流程的步骤标注：操作描述(action)、所在页面(page)、预期结果(expected)
5. 识别系统中有哪些 **角色**（roles）

格式要求：
- 输出严格的 JSON，不要包含 markdown 代码块标记
- 每个流程线 3-8 个步骤
- 步骤描述要具体可执行（如"点击登录按钮"而不是"执行登录"）
- 如果文档信息不足，根据你的行业知识合理推断缺失的环节（在 source 字段标注 "derived"）

输出 JSON Schema:
{
  "business_lines": [
    {
      "name": "业务线名称（如：用户管理）",
      "functions": [
        {
          "name": "功能名称（如：用户注册）",
          "flows": [
            {
              "name": "流程名称（如：注册流程）",
              "steps": [
                {"action": "具体操作", "page": "所在页面", "expected": "预期结果"},
                {"action": "...", "page": "...", "expected": "..."}
              ]
            }
          ]
        }
      ]
    }
  ],
  "roles": ["角色1", "角色2"],
  "industry_type": "电商/金融/教育/SaaS/其他"
}

文档内容：
"""


class ChainBuilder:
    """Builds business chains from documents using LLM, keywords, or templates.

    Three-tier strategy:
    1. LLM: extract_business_structure() — full AI extraction
    2. Keywords: _keyword_extract() — rule-based from parsed rules
    3. Templates: INDUSTRY_TEMPLATES — when no input available
    """

    PAGE_KEYWORDS = {
        "登录": ["login", "signin", "登录", "登陆", "认证", "auth"],
        "注册": ["register", "signup", "注册", "登记"],
        "首页": ["home", "dashboard", "首页", "仪表盘", "工作台"],
        "商品": ["product", "goods", "商品", "产品"],
        "订单": ["order", "orders", "订单", "交易"],
        "购物车": ["cart", "shopping", "购物车", "购物"],
        "支付": ["pay", "payment", "checkout", "支付", "结算"],
        "用户": ["user", "profile", "用户", "个人", "账户"],
        "设置": ["setting", "config", "设置", "配置"],
        "管理": ["admin", "manage", "管理", "后台"],
    }

    ROLE_ACTIONS = {
        "管理员": ["查看", "创建", "编辑", "删除", "导出"],
        "普通用户": ["查看", "创建", "编辑"],
        "访客": ["查看"],
    }

    def __init__(self, ai_service: Optional[AIService] = None):
        self._ai = ai_service

    # ────────────────────────────────────────────────────────────────
    # Public API
    # ────────────────────────────────────────────────────────────────

    async def build_chains(self, rules: list[BusinessRule], raw_document: str = "") -> list[dict]:
        """Build business chains from rules or raw document text.

        Priority: raw_document (LLM) > rules (keywords) > templates
        """
        # Level 0: LLM extraction from raw document
        if self._ai and raw_document:
            chains = await self._ai_extract_business_structure(raw_document)
            if chains:
                logger.info("ChainBuilder: LLM extracted %s chains from document", len(chains))
                return chains

        # Level 0b: LLM from rules (less context but still better than keywords)
        if self._ai and rules:
            texts = "\n".join(f"- [{r.category}] {r.content[:200]}" for r in rules[:15])
            chains = await self._ai_extract_business_structure(texts)
            if chains:
                logger.info("ChainBuilder: LLM extracted %s chains from rules", len(chains))
                return chains

        # Level 1: Keyword-based extraction from rules
        if rules:
            pages = self._keyword_extract_pages(rules)
            chains = self._keyword_extract_flows(rules, pages)
            if chains:
                logger.info("ChainBuilder: Keyword extracted %s chains", len(chains))
                return chains

        # Level 2: Detect industry type from URL/text and use templates
        industry = self._detect_industry(rules, raw_document)
        templates = INDUSTRY_TEMPLATES.get(industry, INDUSTRY_TEMPLATES["generic"])
        logger.info("ChainBuilder: Using %s templates (%s chains)", industry, len(templates))
        return templates

    async def extract_from_url(self, url: str) -> list[dict]:
        """Build chains by analyzing a URL with LLM (zero-doc mode)."""
        if not self._ai:
            return INDUSTRY_TEMPLATES["generic"]

        prompt = f"""分析以下网站URL，推断这个系统的业务功能。
URL: {url}

请根据URL路径和可能的业务场景，推断：
1. 这个系统是什么类型的（电商/管理后台/社交/SaaS/其他）
2. 可能包含哪些业务线和功能
3. 核心业务流程是什么

输出与 extract_business_structure 相同格式的 JSON。"""
        try:
            result = await self._ai.extract_rules(prompt, "structured")
            raw = result if isinstance(result, dict) else json.loads(result.get("result", "{}"))
            return self._flatten_llm_output(raw)
        except Exception as e:
            logger.error("URL extraction failed: %s", e)
            return INDUSTRY_TEMPLATES["generic"]

    def generate_test_chains(
        self,
        business_chains: list[dict],
        page_elements: Optional[list[DiscoveredElement]] = None,
    ) -> list[TestScenario]:
        """For each business chain × role × path type, generate test scenarios."""
        scenarios = []
        for chain in business_chains:
            roles = chain.get("roles", ["普通用户"])
            for role in roles:
                for path_type in ["positive", "boundary", "abnormal", "permission"]:
                    scenario = self._build_scenario(chain, role, path_type, page_elements=page_elements)
                    if scenario:
                        scenarios.append(scenario)
        return scenarios

    # ────────────────────────────────────────────────────────────────
    # Level 0: LLM extraction
    # ────────────────────────────────────────────────────────────────

    async def _ai_extract_business_structure(self, text: str) -> list[dict]:
        """Use LLM to extract business lines, functions, and flows from document text."""
        if not self._ai:
            return []

        try:
            result = await self._ai.extract_rules(
                LLM_EXTRACT_PROMPT + text[:12000],
                "structured",
            )
            parsed = result if isinstance(result, dict) else {}
            return self._flatten_llm_output(parsed)
        except Exception as e:
            logger.error("LLM business structure extraction failed: %s", e)
            return []

    def _flatten_llm_output(self, data: dict) -> list[dict]:
        """Flatten LLM's hierarchical output (business_line → function → flow) into chain list."""
        chains = []
        raw_roles = data.get("roles", [])

        for bl in data.get("business_lines", []):
            bl_name = bl.get("name", "")

            for func in bl.get("functions", []):
                func_name = func.get("name", "")

                for flow in func.get("flows", []):
                    flow_name = flow.get("name", "")
                    steps = flow.get("steps", [])

                    if not steps:
                        continue

                    # Merge all known roles
                    roles = list(raw_roles) if raw_roles else ["管理员", "普通用户"]
                    # Source tracking
                    source = flow.get("source", "extracted")

                    chains.append({
                        "name": f"{bl_name} - {func_name} - {flow_name}" if bl_name and func_name else
                                f"{bl_name} - {flow_name}" if bl_name else flow_name,
                        "business_line": bl_name,
                        "function": func_name,
                        "steps": steps,
                        "roles": roles,
                        "source": source,
                    })

        return chains

    # ────────────────────────────────────────────────────────────────
    # Level 1: Keyword-based extraction (fallback)
    # ────────────────────────────────────────────────────────────────

    def _keyword_extract_pages(self, rules: list[BusinessRule]) -> list[str]:
        pages = set()
        for rule in rules:
            text = rule.content.lower()
            for page_name, keywords in self.PAGE_KEYWORDS.items():
                if any(kw in text for kw in keywords):
                    pages.add(page_name)
        return list(pages) or ["首页", "登录", "用户"]

    def _keyword_extract_flows(self, rules: list[BusinessRule], pages: list[str]) -> list[dict]:
        flow_rules = [r for r in rules if r.category == "flow"]
        if not flow_rules:
            return self._keyword_default_flows(pages)

        flows = []
        for rule in flow_rules[:10]:
            text = rule.content
            chain = self._parse_flow_text(text, pages)
            if chain:
                flows.append(chain)
        return flows

    def _parse_flow_text(self, text: str, pages: list[str]) -> Optional[dict]:
        steps = []
        parts = re.split(r'[，,。.；;]', text)
        for part in parts[:10]:
            part = part.strip()
            if not part:
                continue
            found_page = "操作"
            for p in pages:
                if p in part:
                    found_page = p
                    break
            steps.append({
                "action": part[:60],
                "page": found_page,
                "expected": "操作成功" if "失败" not in part else "错误提示",
            })
        if len(steps) < 2:
            return None
        name = steps[0]["action"][:20] + "流程" if steps else "业务流"
        return {"name": name, "steps": steps, "roles": ["管理员", "普通用户"]}

    def _keyword_default_flows(self, pages: list[str]) -> list[dict]:
        if len(pages) >= 2:
            name = f"{pages[0]}→{pages[1]} 流程"
            return [{
                "name": name,
                "steps": [
                    {"action": f"打开{pages[0]}", "page": pages[0], "expected": "页面加载成功"},
                    {"action": f"进入{pages[1]}", "page": pages[1], "expected": "跳转成功"},
                    {"action": f"在{pages[1]}执行操作", "page": pages[1], "expected": "操作成功"},
                ],
                "roles": ["管理员", "普通用户"],
            }]
        return [{
            "name": "基础业务流程",
            "steps": [
                {"action": "打开页面", "page": pages[0] if pages else "首页", "expected": "页面加载"},
                {"action": "验证页面渲染", "page": pages[0] if pages else "首页", "expected": "渲染正常"},
            ],
            "roles": ["管理员", "普通用户", "访客"],
        }]

    def _detect_industry(self, rules: list[BusinessRule], text: str) -> str:
        """Detect likely industry from available text."""
        combined = text.lower()
        for r in rules:
            combined += " " + r.content.lower()

        if any(kw in combined for kw in ["商品", "订单", "购物车", "支付", "product", "order", "cart"]):
            return "ecommerce"
        if any(kw in combined for kw in ["管理员", "权限", "角色", "设置", "配置", "admin", "role"]):
            return "admin"
        if any(kw in combined for kw in ["课程", "视频", "学习", "考试", "course", "lesson"]):
            return "education"
        return "generic"

    # ────────────────────────────────────────────────────────────────
    # Scenario builder (shared across all tiers)
    # ────────────────────────────────────────────────────────────────

    def _build_scenario(
        self, chain: dict, role: str, path_type: str,
        page_elements: Optional[list[DiscoveredElement]] = None,
    ) -> Optional[TestScenario]:
        steps = chain.get("steps", [])
        if not steps:
            return None

        type_names = {"positive": "正向流程", "boundary": "边界条件", "abnormal": "异常流程", "permission": "权限验证"}
        expected_status = "failure" if path_type == "abnormal" else "success"

        chain_name = chain.get("name", "业务流")
        bl_name = chain.get("business_line", "")
        source = chain.get("source", "extracted")

        scenario = TestScenario(
            id=generate_id("scenario"),
            project_id="",
            business_line=bl_name or chain_name,
            name=f"{chain_name} - {type_names.get(path_type, path_type)}",
            type=path_type,
            role=role,
            expected_status=expected_status,
        )

        case_name = f"{role} {chain_name} {type_names.get(path_type, path_type)}"
        case = TestCase(id=generate_id("test_case"), scenario_id=scenario.id, project_id="", name=case_name)
        case.preconditions = [f"以{role}身份登录系统"]

        for i, step in enumerate(steps):
            action = step.get("action", "操作")
            expected = step.get("expected", "")

            if path_type == "abnormal":
                action = f"{action}（异常场景）"
                expected = "显示错误提示"
            elif path_type == "permission":
                action = f"{action}（验证权限）"
                expected = "有权限则成功，无权限则拒绝"
            elif path_type == "boundary":
                action = f"{action}（边界值验证）"
                expected = "边界值处理正确"

            if page_elements:
                target = self._find_closest_element(action, step.get("page", ""), page_elements)
            else:
                target = step.get("page", "")

            case.steps.append(TestStep(
                index=i + 1, action=action,
                target=target,
                value="",
                verifications=["ui", "console", "api"],
                expected={"business": expected},
            ))

        scenario.cases = [case]
        return scenario

    def _find_closest_element(self, action: str, page: str, elements: list[DiscoveredElement]) -> str:
        query = (action + " " + page).lower()
        query_tokens = [w for w in re.split(r'[\s,，。.；;:：()（）【】\[\]{}-]', query) if len(w) >= 2]
        best_match = page
        best_score = 0
        for elem in elements:
            text = (elem.text or "").lower().strip()
            if not text:
                continue
            score = sum(1 for tok in query_tokens if tok in text)
            if score > best_score:
                best_score = score
                best_match = elem.text
        return best_match
