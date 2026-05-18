from app.domain.exceptions import ScenarioNotFoundError
from app.domain.models.knowledge import BusinessRule
from app.domain.models.scenario import CoverageInfo, TestCase, TestScenario, TestStep
from app.interfaces.ai_service import AIService
from app.interfaces.repositories.knowledge_repo import KnowledgeBaseRepository
from app.interfaces.repositories.scenario_repo import ScenarioRepository
from app.lib.id_generator import generate_id
from app.lib.logger import get_logger

logger = get_logger(__name__)


class ScenarioService:
    def __init__(self, scenario_repo: ScenarioRepository,
                 kb_repo: KnowledgeBaseRepository | None = None,
                 ai_service: AIService | None = None):
        self._repo = scenario_repo
        self._kb_repo = kb_repo
        self._ai = ai_service

    async def generate_scenarios(self, project_id: str,
                                  platforms: list[str] | None = None) -> list[TestScenario]:
        platforms = platforms or ["web"]
        rules = []
        if self._kb_repo:
            kb = await self._kb_repo.get_by_project(project_id)
            if kb:
                rules = await self._kb_repo.get_rules(kb.id)
        if not rules and self._ai:
            rules = await self._ai_extract_rules(project_id)
        if not rules:
            return await self._generate_default_scenarios(project_id, platforms)

        scenarios = []
        for cat in ["flow", "permission", "ui"]:
            cat_rules = [r for r in rules if r.category == cat]
            if cat_rules:
                scenarios.append(await self._build_scenario(
                    project_id, { "flow": "业务流程", "permission": "权限验证", "ui": "UI规范" }[cat],
                    { "flow": "positive", "permission": "permission", "ui": "boundary" }[cat],
                    cat_rules, platforms))

        if not scenarios:
            return await self._generate_default_scenarios(project_id, platforms)
        for s in scenarios:
            try:
                await self._repo.create_scenario(s)
            except Exception as e:
                logger.error("Save scenario failed: %s", e)
        logger.info("Generated %s scenarios for %s", len(scenarios), project_id)
        return scenarios

    async def _build_scenario(self, project_id, name, stype, rules, platforms):
        s = TestScenario(id=generate_id("scenario"), project_id=project_id,
            business_line=name, name=f"{name}-{stype}", type=stype,
            platforms=platforms, role="user")
        case = TestCase(id=generate_id("test_case"), scenario_id=s.id,
            project_id=project_id, name=f"{name}主流程", steps=[])
        for i, r in enumerate(rules[:5]):
            case.steps.append(TestStep(index=i+1, action=r.content[:80], target=r.content[:80],
                verifications=["ui","api","console"]))
        if not case.steps:
            case.steps.append(TestStep(index=1, action="verify", target=name))
        s.cases = [case]
        s.coverage = CoverageInfo(rule_coverage=min(1.0, len(rules)/10), grade="B")
        return s

    async def _ai_extract_rules(self, project_id):
        try:
            result = await self._ai.extract_rules(f"Project {project_id}", "general")
            raw = result.get("rules", [])
            return [BusinessRule(id=generate_id("rule"), kb_id="",
                content=r.get("content",""), category=r.get("category","rule")) for r in raw]
        except Exception as e:
            logger.error("AI extract failed: %s", e)
            return []

    async def _generate_default_scenarios(self, project_id, platforms):
        s = TestScenario(id=generate_id("scenario"), project_id=project_id,
            business_line="默认", name="页面基础功能验证", type="positive",
            platforms=platforms, role="user",
            cases=[TestCase(id=generate_id("test_case"), scenario_id="",
                project_id=project_id, name="页面加载验证",
                steps=[TestStep(index=1, action="打开页面", target="首页",
                    verifications=["ui","console"])])])
        try:
            await self._repo.create_scenario(s)
        except Exception:
            pass
        return [s]

    async def get_scenarios(self, project_id):
        return await self._repo.get_by_project(project_id)

    async def get_scenario(self, scenario_id):
        s = await self._repo.get_by_id(scenario_id)
        if not s:
            raise ScenarioNotFoundError(scenario_id)
        return s

    async def update_scenario(self, scenario_id, updates):
        s = await self.get_scenario(scenario_id)
        for k, v in updates.items():
            if hasattr(s, k): setattr(s, k, v)
        return await self._repo.update_scenario(s)

    async def generate_with_chain(self, project_id: str, rules: list,
                                    platforms: list[str] | None = None) -> list[TestScenario]:
        """Generate scenarios using ChainBuilder for multi-role business chains."""
        from app.engine.chain_builder import ChainBuilder
        builder = ChainBuilder(self._ai)
        chains = await builder.build_chains(rules)
        scenarios = builder.generate_test_chains(chains)

        for s in scenarios:
            s.project_id = project_id
            s.platforms = platforms or ["web"]
            try:
                await self._repo.create_scenario(s)
            except Exception as e:
                logger.error("Save scenario failed: %s", e)
        logger.info("ChainBuilder: %s scenarios from %s chains", len(scenarios), len(chains))
        return scenarios
