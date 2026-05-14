from app.config import settings
from app.services.project_service import ProjectService
from app.services.document_service import DocumentService
from app.services.knowledge_service import KnowledgeService
from app.services.scenario_service import ScenarioService
from app.services.run_service import RunService
from app.services.report_service import ReportService
from app.services.analysis_service import CrossDimensionAnalyzer

from app.interfaces.repositories.project_repo import ProjectRepository
from app.interfaces.repositories.document_repo import DocumentRepository
from app.interfaces.repositories.knowledge_repo import KnowledgeBaseRepository
from app.interfaces.repositories.scenario_repo import ScenarioRepository
from app.interfaces.repositories.run_repo import RunRepository
from app.interfaces.repositories.defect_repo import DefectRepository


_project_service: ProjectService | None = None
_document_service: DocumentService | None = None
_knowledge_service: KnowledgeService | None = None
_scenario_service: ScenarioService | None = None
_run_service: RunService | None = None
_report_service: ReportService | None = None
_analyzer: CrossDimensionAnalyzer | None = None


def init_services(
    project_repo: ProjectRepository,
    document_repo: DocumentRepository,
    kb_repo: KnowledgeBaseRepository,
    scenario_repo: ScenarioRepository,
    run_repo: RunRepository,
    defect_repo: DefectRepository,
) -> None:
    global _project_service, _document_service, _knowledge_service
    global _scenario_service, _run_service, _report_service, _analyzer

    _project_service = ProjectService(project_repo)
    _document_service = DocumentService(document_repo, ai_service=None)
    _knowledge_service = KnowledgeService(kb_repo)
    _scenario_service = ScenarioService(scenario_repo)
    _run_service = RunService(run_repo, scenario_repo)
    _report_service = ReportService(run_repo, defect_repo)
    _analyzer = CrossDimensionAnalyzer(defect_repo, ai_service=None)


def get_project_service() -> ProjectService:
    assert _project_service is not None, "Services not initialized"
    return _project_service


def get_document_service() -> DocumentService:
    assert _document_service is not None, "Services not initialized"
    return _document_service


def get_knowledge_service() -> KnowledgeService:
    assert _knowledge_service is not None, "Services not initialized"
    return _knowledge_service


def get_scenario_service() -> ScenarioService:
    assert _scenario_service is not None, "Services not initialized"
    return _scenario_service


def get_run_service() -> RunService:
    assert _run_service is not None, "Services not initialized"
    return _run_service


def get_report_service() -> ReportService:
    assert _report_service is not None, "Services not initialized"
    return _report_service


def get_analyzer() -> CrossDimensionAnalyzer:
    assert _analyzer is not None, "Services not initialized"
    return _analyzer
