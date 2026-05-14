"""Business chain builder: extracts page flows from documents, generates test chains with multi-role paths."""
import json, re
from typing import Optional
from app.domain.models.knowledge import BusinessRule, KnowledgeBase
from app.domain.models.discovery import DiscoveredElement
from app.domain.models.scenario import TestScenario, TestCase, TestStep
from app.interfaces.ai_service import AIService
from app.lib.id_generator import generate_id
from app.lib.logger import get_logger

logger = get_logger(__name__)


class ChainBuilder:
    """Builds business chains from rules and generates multi-role test scenarios.
    
    A business chain is a sequence of pages/actions: Login → Dashboard → Product → Order
    Each chain generates 4 test variants per role:
    - positive: happy path
    - boundary: edge cases (empty input, max length, etc.)
    - abnormal: error handling (wrong password, server error, etc.)
    - permission: role-based access control
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

    async def build_chains(self, rules: list[BusinessRule]) -> list[dict]:
        """Build business chain DAGs from extracted rules."""
        pages = self._extract_pages(rules)
        flows = self._extract_flows(rules, pages)
        if not flows and self._ai:
            flows = await self._ai_extract_flows(rules)
        if not flows:
            flows = self._default_flows(pages)
        return flows

    def _extract_pages(self, rules: list[BusinessRule]) -> list[str]:
        pages = set()
        for rule in rules:
            text = rule.content.lower()
            for page_name, keywords in self.PAGE_KEYWORDS.items():
                if any(kw in text for kw in keywords):
                    pages.add(page_name)
        return list(pages) or ["首页", "登录", "用户"]

    def _extract_flows(self, rules: list[BusinessRule], pages: list[str]) -> list[dict]:
        flow_rules = [r for r in rules if r.category == "flow"]
        if not flow_rules:
            return self._default_flows(pages)

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

    def _default_flows(self, pages: list[str]) -> list[dict]:
        if len(pages) >= 2:
            name = f"{pages[0]}→{pages[1]} 流程"
            return [{
                "name": name,
                "steps": [{"action": f"打开{pages[0]}", "page": pages[0], "expected": "页面加载成功"},
                          {"action": f"进入{pages[1]}", "page": pages[1], "expected": "跳转成功"},
                          {"action": f"在{pages[1]}执行操作", "page": pages[1], "expected": "操作成功"}],
                "roles": ["管理员", "普通用户"],
            }]
        return [{
            "name": "基础业务流程",
            "steps": [{"action": "打开页面", "page": pages[0] if pages else "首页", "expected": "页面加载"},
                      {"action": "验证页面渲染", "page": pages[0] if pages else "首页", "expected": "渲染正常"}],
            "roles": ["管理员", "普通用户", "访客"],
        }]

    async def _ai_extract_flows(self, rules: list[BusinessRule]) -> list[dict]:
        if not self._ai:
            return []
        texts = "\n".join(f"- {r.content[:100]}" for r in rules[:5])
        try:
            result = await self._ai.extract_rules(
                f"从以下规则中提取完整的业务流程（页面→操作→跳转），输出JSON格式。\n{texts}",
                "structured",
            )
            return result.get("flows", [])
        except Exception as e:
            logger.error(f"AI flow extraction failed: {e}")
            return []

    def generate_test_chains(
        self,
        business_chains: list[dict],
        page_elements: Optional[list[DiscoveredElement]] = None,
    ) -> list[TestScenario]:
        """For each business chain × role × path type, generate test scenarios."""
        scenarios = []
        for chain in business_chains:
            for role in chain.get("roles", ["普通用户"]):
                for path_type in ["positive", "boundary", "abnormal", "permission"]:
                    scenario = self._build_scenario(chain, role, path_type, page_elements=page_elements)
                    if scenario:
                        scenarios.append(scenario)
        return scenarios

    def _build_scenario(
        self, chain: dict, role: str, path_type: str,
        page_elements: Optional[list[DiscoveredElement]] = None,
    ) -> Optional[TestScenario]:
        steps = chain.get("steps", [])
        if not steps:
            return None

        type_names = {"positive": "正向流程", "boundary": "边界条件", "abnormal": "异常流程", "permission": "权限验证"}
        expected_status = "failure" if path_type == "abnormal" else "success"
        scenario = TestScenario(
            id=generate_id("scenario"),
            project_id="",
            business_line=chain.get("name", "业务流"),
            name=f"{chain.get('name', '业务')} - {type_names.get(path_type, path_type)}",
            type=path_type,
            role=role,
            expected_status=expected_status,
        )

        case = TestCase(id=generate_id("test_case"), scenario_id=scenario.id, project_id="",
                        name=f"{role} {chain.get('name', '')} {type_names.get(path_type, path_type)}")
        case.preconditions = [f"以{role}身份登录系统"]

        for i, step in enumerate(steps):
            action = step.get("action", "操作")
            expected = step.get("expected", "")
            # Adapt action based on path type
            if path_type == "abnormal":
                action = f"{action}（异常场景）"
                expected = "显示错误提示"
            elif path_type == "permission":
                action = f"{action}（验证权限）"
                expected = "有权限则成功，无权限则拒绝"
            elif path_type == "boundary":
                action = f"{action}（边界值验证）"
                expected = "边界值处理正确"

            # Use real element text as target when page elements are available
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

    def _find_closest_element(
        self, action: str, page: str, elements: list[DiscoveredElement],
    ) -> str:
        """Match step action/page description to the closest discovered element text."""
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
