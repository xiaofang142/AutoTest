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
_initialized = False


class _MemProjectRepo(ProjectRepository):
    def __init__(self): self._s = {}
    async def create(self, p): self._s[p.id] = p; return p
    async def get_by_id(self, i): return self._s.get(i)
    async def update(self, p): self._s[p.id] = p; return p
    async def delete(self, i): self._s.pop(i, None)
    async def list_projects(self, st=None):
        r = list(self._s.values())
        if st: r = [p for p in r if p.status == st]
        return r

class _MemDocRepo(DocumentRepository):
    def __init__(self): self._s = {}
    async def create(self, d): self._s[d.id] = d; return d
    async def get_by_id(self, i): return self._s.get(i)
    async def get_by_project(self, p): return [d for d in self._s.values() if d.project_id == p]
    async def update(self, d): self._s[d.id] = d; return d
    async def delete(self, i): self._s.pop(i, None)
    async def save_raw(self, r): return r
    async def get_raw(self, _): return None

class _MemKBRepo(KnowledgeBaseRepository):
    def __init__(self): self._k = {}; self._r = {}; self._c = {}
    async def create(self, k): self._k[k.id] = k; return k
    async def get_by_project(self, p):
        for k in self._k.values():
            if k.project_id == p: return k
        return None
    async def get_by_id(self, i): return self._k.get(i)
    async def update(self, k): self._k[k.id] = k; return k
    async def get_rules(self, k, cat=None):
        r = list(self._r.values())
        if cat: r = [x for x in r if x.category == cat]
        return r
    async def create_rule(self, r): self._r[r.id] = r; return r
    async def update_rule(self, r): self._r[r.id] = r; return r
    async def get_conflicts(self, _): return list(self._c.values())
    async def resolve_conflict(self, c): self._c[c.id] = c; return c

class _MemScenarioRepo(ScenarioRepository):
    def __init__(self): self._s = {}; self._c = {}
    async def create_scenario(self, s): self._s[s.id] = s; return s
    async def get_by_project(self, p): return [s for s in self._s.values() if s.project_id == p]
    async def get_by_id(self, i): return self._s.get(i)
    async def update_scenario(self, s): self._s[s.id] = s; return s
    async def create_case(self, c): self._c[c.id] = c; return c
    async def get_case(self, i): return self._c.get(i)

class _MemRunRepo(RunRepository):
    def __init__(self): self._r = {}; self._t = {}
    async def create(self, r): self._r[r.id] = r; return r
    async def get_by_id(self, i): return self._r.get(i)
    async def get_by_project(self, p): return [r for r in self._r.values() if r.project_id == p]
    async def update_status(self, i, s):
        if i in self._r: self._r[i].status = s
    async def update_progress(self, i, p):
        if i in self._r: self._r[i].progress = p
    async def save_step(self, s): self._t[s.id] = s; return s
    async def get_steps(self, i): return [s for s in self._t.values() if s.run_id == i]

class _MemDefectRepo(DefectRepository):
    def __init__(self): self._s = {}
    async def create(self, d): self._s[d.id] = d; return d
    async def get_by_id(self, i): return self._s.get(i)
    async def get_by_run(self, i, s=None):
        r = [d for d in self._s.values() if d.run_id == i]
        if s: r = [d for d in r if d.severity == s]
        return r
    async def update(self, d): self._s[d.id] = d; return d


def _create_ai():
    from app.config import settings
    if settings.litellm_api_key:
        from app.infrastructure.ai.lite_llm_service import LiteLLMAIService
        return LiteLLMAIService()
    from app.lib.logger import get_logger
    get_logger('deps').info('No LITELLM_API_KEY - AI features disabled, using rule-based analysis')
    return None


def init_services(project_repo=None, document_repo=None, kb_repo=None,
                  scenario_repo=None, run_repo=None, defect_repo=None):
    global _project_service, _document_service, _knowledge_service
    global _scenario_service, _run_service, _report_service, _analyzer, _initialized

    pr = project_repo or _MemProjectRepo()
    dr = document_repo or _MemDocRepo()
    kr = kb_repo or _MemKBRepo()
    sr = scenario_repo or _MemScenarioRepo()
    rr = run_repo or _MemRunRepo()
    dfr = defect_repo or _MemDefectRepo()

    _project_service = ProjectService(pr)
    _document_service = DocumentService(dr)
    _knowledge_service = KnowledgeService(kr)
    _scenario_service = ScenarioService(sr, kb_repo=kr, ai_service=_create_ai())
    _run_service = RunService(rr, sr)
    _report_service = ReportService(rr, dfr)
    _analyzer = CrossDimensionAnalyzer(dfr, ai_service=_create_ai())
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
    from app.infrastructure.ai.lite_llm_service import LiteLLMAIService
    if _analyzer._ai is None:
        _analyzer._ai = LiteLLMAIService()
    return _analyzer

def get_defect_repo():
    _ensure()
    return _analyzer._defect_repo
