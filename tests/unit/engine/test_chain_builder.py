"""Tests for ChainBuilder: LLM-driven + keyword + template three-tier extraction and scenario generation."""
import pytest

from app.domain.models.knowledge import BusinessRule
from app.engine.chain_builder import ChainBuilder


@pytest.fixture
def builder():
    return ChainBuilder(ai_service=None)


class TestKeywordExtractPages:
    def test_extracts_from_rules(self, builder):
        rules = [
            BusinessRule(id="r1", kb_id="kb_1", category="flow", content="用户登录后进入首页"),
            BusinessRule(id="r2", kb_id="kb_1", category="flow", content="在商品页加入购物车"),
        ]
        pages = builder._keyword_extract_pages(rules)
        assert "登录" in pages
        assert "商品" in pages

    def test_default_when_no_match(self, builder):
        rules = [BusinessRule(id="r1", kb_id="kb_1", category="other", content="no match")]
        pages = builder._keyword_extract_pages(rules)
        assert len(pages) >= 1
        assert "首页" in pages


class TestKeywordExtractFlows:
    def test_flow_rules_parsed(self, builder):
        rules = [BusinessRule(id="r1", kb_id="kb_1", category="flow", content="用户登录，然后查看订单")]
        flows = builder._keyword_extract_flows(rules, ["登录", "订单"])
        assert len(flows) > 0

    def test_default_flows_when_no_flow_rules(self, builder):
        rules = [BusinessRule(id="r1", kb_id="kb_1", category="ui", content="Button is blue")]
        flows = builder._keyword_extract_flows(rules, ["首页"])
        assert len(flows) > 0


class TestKeywordDefaultFlows:
    def test_multi_page_flow(self, builder):
        flows = builder._keyword_default_flows(["登录", "首页"])
        assert len(flows) == 1
        assert len(flows[0]["steps"]) >= 2

    def test_single_page_flow(self, builder):
        flows = builder._keyword_default_flows(["首页"])
        assert len(flows) == 1


class TestTemplateFallback:
    @pytest.mark.asyncio
    async def test_empty_rules_uses_generic_templates(self, builder):
        chains = await builder.build_chains([])
        assert len(chains) >= 1
        chain_names = [c["name"] for c in chains]
        assert any("用户" in n for n in chain_names)

    @pytest.mark.asyncio
    async def test_ecommerce_keywords_trigger_templates(self, builder):
        rules = [BusinessRule(id="r1", kb_id="kb_1", category="flow", content="用户下单购买商品并支付")]
        chains = await builder.build_chains(rules)
        assert len(chains) >= 2


class TestLLMOutputFlatten:
    def test_flatten_basic(self, builder):
        data = {
            "business_lines": [{
                "name": "用户管理",
                "functions": [{
                    "name": "注册功能",
                    "flows": [{
                        "name": "注册流程",
                        "steps": [{"action": "打开注册页", "page": "注册", "expected": "页面加载"}],
                    }],
                }],
            }],
            "roles": ["管理员", "普通用户"],
        }
        chains = builder._flatten_llm_output(data)
        assert len(chains) == 1
        assert chains[0]["business_line"] == "用户管理"
        assert chains[0]["function"] == "注册功能"
        assert len(chains[0]["steps"]) == 1

    def test_flatten_empty(self, builder):
        assert builder._flatten_llm_output({}) == []

    def test_flatten_multi_function(self, builder):
        data = {
            "business_lines": [{
                "name": "商品管理",
                "functions": [
                    {"name": "商品上架", "flows": [{"name": "上架流程", "steps": [{"action": "填写信息", "page": "上架页", "expected": "成功"}]}]},
                    {"name": "商品编辑", "flows": [{"name": "编辑流程", "steps": [{"action": "修改价格", "page": "编辑页", "expected": "成功"}]}]},
                ],
            }],
            "roles": ["管理员"],
        }
        chains = builder._flatten_llm_output(data)
        assert len(chains) == 2
        assert chains[0]["function"] == "商品上架"
        assert chains[1]["function"] == "商品编辑"


class TestGenerateTestChains:
    def test_generates_scenarios(self, builder):
        chains = [{
            "name": "登录流程", "business_line": "用户管理",
            "steps": [{"action": "打开登录页", "page": "登录", "expected": "页面加载"},
                      {"action": "输入凭据", "page": "登录", "expected": "登录成功"}],
            "roles": ["管理员", "普通用户"],
        }]
        scenarios = builder.generate_test_chains(chains)
        assert len(scenarios) == 8

    def test_all_path_types_present(self, builder):
        chains = [{"name": "测试流程", "steps": [{"action": "操作", "page": "首页", "expected": "成功"}], "roles": ["普通用户"]}]
        types = {s.type for s in builder.generate_test_chains(chains)}
        assert types == {"positive", "boundary", "abnormal", "permission"}


class TestBuildScenario:
    def test_positive_path(self, builder):
        s = builder._build_scenario({"name": "测试", "steps": [{"action": "打开", "page": "首页", "expected": "成功"}]}, "普通用户", "positive")
        assert s.type == "positive" and s.expected_status == "success"

    def test_abnormal_path(self, builder):
        s = builder._build_scenario({"name": "测试", "steps": [{"action": "操作", "page": "首页"}]}, "普通用户", "abnormal")
        assert s.expected_status == "failure" and "异常" in s.cases[0].steps[0].action

    def test_permission_path(self, builder):
        s = builder._build_scenario({"name": "管理", "steps": [{"action": "删除", "page": "管理"}]}, "访客", "permission")
        assert "权限" in s.cases[0].steps[0].action

    def test_boundary_path(self, builder):
        s = builder._build_scenario({"name": "表单", "steps": [{"action": "输入", "page": "设置"}]}, "普通用户", "boundary")
        assert "边界" in s.cases[0].steps[0].action

    def test_business_line_preserved(self, builder):
        chain = {"name": "注册", "business_line": "用户管理", "function": "账号", "steps": [{"action": "填写", "page": "注册页", "expected": "成功"}]}
        assert builder._build_scenario(chain, "普通用户", "positive").business_line == "用户管理"


class TestBuildChains:
    @pytest.mark.asyncio
    async def test_build_from_keyword_rules(self, builder):
        rules = [BusinessRule(id="r1", kb_id="kb_1", category="flow", content="用户登录后进入首页查看订单")]
        chains = await builder.build_chains(rules)
        assert len(chains) > 0

    @pytest.mark.asyncio
    async def test_no_llm_raw_document_falls_through(self, builder):
        chains = await builder.build_chains([], raw_document="电商平台用户手册")
        assert len(chains) >= 1

    @pytest.mark.asyncio
    async def test_industry_detection(self, builder):
        assert builder._detect_industry([BusinessRule(id="r", kb_id="k", category="f", content="管理员设置角色权限")], "") == "admin"
        assert builder._detect_industry([BusinessRule(id="r", kb_id="k", category="f", content="用户下单购买商品")], "") == "ecommerce"
        assert builder._detect_industry([], "") == "generic"
