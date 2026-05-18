from datetime import datetime
from app.domain.models.project import Project, PlatformEntry
from app.domain.models.task import TestTask, TaskInput, TaskStatus, TaskMode
from app.domain.models.run import RunRecord, RunSummary
from app.domain.models.scenario import TestScenario, TestStep, ScenarioType, TestCase
from app.domain.models.defect import Defect, EvidenceChain
from app.domain.models.knowledge import KnowledgeBase, BusinessRule
from app.lib.id_generator import generate_id


def create_test_project(name: str = "Test Project", platform: str = "web") -> Project:
    return Project(
        id=generate_id("proj"),
        name=name,
        platforms=[platform],
        entries=[PlatformEntry(platform=platform, url=f"https://{name.lower().replace(' ', '-')}.com")],
    )


def create_test_task(url: str = "https://example.com", mode: str = "quick") -> TestTask:
    return TestTask(
        id=generate_id("task"),
        name=f"Test {url}",
        input=TaskInput(target_url=url),
        mode=TaskMode(mode),
    )


def create_test_run(project_id: str, total: int = 5) -> RunRecord:
    return RunRecord(
        id=generate_id("run"),
        project_id=project_id,
        name="Test Run",
        total_cases=total,
        summary=RunSummary(total_cases=total),
    )


def create_test_defect(run_id: str, severity: str = "high", title: str = "Test defect") -> Defect:
    return Defect(
        id=generate_id("defect"),
        run_id=run_id,
        severity=severity,
        title=title,
        evidence_chains=[EvidenceChain(
            chain_id=generate_id("chain"),
            root_trigger={"dimension": "api", "event": "POST /api/test 500"},
            propagation=[{"step": 0, "dimension": "api", "event": "API failed"}, {"step": 1, "dimension": "console", "event": "JS Error"}],
            chain_summary="API failure caused console error",
        )],
    )


def create_test_scenario(project_id: str, name: str = "Test Scenario") -> TestScenario:
    return TestScenario(
        id=generate_id("sce"),
        project_id=project_id,
        name=name,
        cases=[TestCase(
            name="test case",
            steps=[TestStep(index=0, action="navigate", target="url")],
        )],
    )


def create_test_knowledge_base(project_id: str) -> KnowledgeBase:
    kb = KnowledgeBase(
        id=generate_id("kb"),
        project_id=project_id,
        version=1,
    )
    kb.business_rules = [
        BusinessRule(id=generate_id("rule"), kb_id=kb.id, category="flow", content="User can login"),
    ]
    return kb
