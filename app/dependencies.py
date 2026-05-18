from app.services.analysis_service import CrossDimensionAnalyzer
from app.services.document_service import DocumentService
from app.services.knowledge_service import KnowledgeService
from app.services.project_service import ProjectService
from app.services.report_service import ReportService
from app.services.run_service import RunService
from app.services.scenario_service import ScenarioService
from app.interfaces.repositories.task_repo import TaskRepository
from app.interfaces.repositories.run_repo import RunRepository
from app.infrastructure.persistence.task_repo import InMemoryTaskRepository
from tests.mock_repos import (
    MemDefectRepo,
    MemDocRepo,
    MemKBRepo,
    MemProjectRepo,
    MemRunRepo,
    MemScenarioRepo,
)

_ai_instance = None
_project_service: ProjectService | None = None
_document_service: DocumentService | None = None
_knowledge_service: KnowledgeService | None = None
_scenario_service: ScenarioService | None = None
_run_service: RunService | None = None
_report_service: ReportService | None = None
_analyzer: CrossDimensionAnalyzer | None = None
_task_repo: TaskRepository | None = None
_run_repo_singleton = None
_initialized = False


def _create_ai():
    global _ai_instance
    if _ai_instance is not None:
        return _ai_instance
    from app.config import settings
    if settings.litellm_api_key:
        from app.infrastructure.ai.lite_llm_service import LiteLLMAIService
        _ai_instance = LiteLLMAIService()
    else:
        from app.lib.logger import get_logger
        get_logger('deps').info('No LITELLM_API_KEY - AI features disabled, using rule-based analysis')
        _ai_instance = None
    return _ai_instance


def init_services(project_repo=None, document_repo=None, kb_repo=None,
                  scenario_repo=None, run_repo=None, defect_repo=None):
    global _project_service, _document_service, _knowledge_service
    global _scenario_service, _run_service, _report_service, _analyzer, _initialized, _task_repo, _run_repo_singleton

    pr = project_repo or MemProjectRepo()
    dr = document_repo or MemDocRepo()
    kr = kb_repo or MemKBRepo()
    sr = scenario_repo or MemScenarioRepo()
    rr = run_repo or MemRunRepo()
    dfr = defect_repo or MemDefectRepo()

    if _task_repo is None:
        _task_repo = InMemoryTaskRepository()
    global _run_repo_singleton
    _run_repo_singleton = rr

    ai = _create_ai()
    _project_service = ProjectService(pr)
    _document_service = DocumentService(dr, kb_repo=kr, ai_service=ai)
    _knowledge_service = KnowledgeService(kr)
    _scenario_service = ScenarioService(sr, kb_repo=kr, ai_service=ai)
    _run_service = RunService(rr, sr)
    _report_service = ReportService(rr, dfr)
    _analyzer = CrossDimensionAnalyzer(dfr, ai_service=ai)
    _initialized = True


def _ensure():
    if not _initialized: init_services()

def get_project_service(): _ensure(); return _project_service
def get_document_service(): _ensure(); return _document_service
def get_knowledge_service(): _ensure(); return _knowledge_service
def get_scenario_service(): _ensure(); return _scenario_service
def get_run_service(): _ensure(); return _run_service
def get_report_service(): _ensure(); return _report_service
def get_analyzer():
    _ensure()
    return _analyzer

def get_defect_repo():
    _ensure()
    return _analyzer._defect_repo if _analyzer else None

def get_task_repo() -> TaskRepository:
    _ensure()
    return _task_repo

def get_run_repo() -> RunRepository:
    _ensure()
    return _run_repo_singleton

def get_ai_status() -> dict:
    _ensure()
    from app.config import settings
    has_key = bool(settings.litellm_api_key)
    return {
        "engine": "litellm" if has_key else "rule-based",
        "configured": has_key,
        "status": "connected" if has_key else "ready (rule-based fallback)",
    }
