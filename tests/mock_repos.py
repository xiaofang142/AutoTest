"""Shared in-memory repository implementations for tests and dev.

Replaces the inline _Mem*Repo classes previously in app/dependencies.py.
All test files should import from here instead of defining their own.
"""
from app.interfaces.repositories.defect_repo import DefectRepository
from app.interfaces.repositories.document_repo import DocumentRepository
from app.interfaces.repositories.knowledge_repo import KnowledgeBaseRepository
from app.interfaces.repositories.project_repo import ProjectRepository
from app.interfaces.repositories.run_repo import RunRepository
from app.interfaces.repositories.scenario_repo import ScenarioRepository


class MemProjectRepo(ProjectRepository):
    def __init__(self): self._s = {}
    async def create(self, p): self._s[p.id] = p; return p
    async def get_by_id(self, i): return self._s.get(i)
    async def update(self, p): self._s[p.id] = p; return p
    async def delete(self, i): self._s.pop(i, None)
    async def list_projects(self, st=None):
        r = list(self._s.values())
        if st: r = [p for p in r if p.status == st]
        return r


class MemDocRepo(DocumentRepository):
    def __init__(self): self._s = {}
    async def create(self, d): self._s[d.id] = d; return d
    async def get_by_id(self, i): return self._s.get(i)
    async def get_by_project(self, p): return [d for d in self._s.values() if d.project_id == p]
    async def update(self, d): self._s[d.id] = d; return d
    async def delete(self, i): self._s.pop(i, None)
    async def save_raw(self, r): return r
    async def get_raw(self, _): return None


class MemKBRepo(KnowledgeBaseRepository):
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


class MemScenarioRepo(ScenarioRepository):
    def __init__(self): self._s = {}; self._c = {}
    async def create_scenario(self, s): self._s[s.id] = s; return s
    async def get_by_project(self, p): return [s for s in self._s.values() if s.project_id == p]
    async def get_by_id(self, i): return self._s.get(i)
    async def update_scenario(self, s): self._s[s.id] = s; return s
    async def create_case(self, c): self._c[c.id] = c; return c
    async def get_case(self, i): return self._c.get(i)


class MemRunRepo(RunRepository):
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


class MemDefectRepo(DefectRepository):
    def __init__(self): self._s = {}
    async def create(self, d): self._s[d.id] = d; return d
    async def get_by_id(self, i): return self._s.get(i)
    async def get_by_run(self, i, s=None):
        r = [d for d in self._s.values() if d.run_id == i]
        if s: r = [d for d in r if d.severity == s]
        return r
    async def update(self, d): self._s[d.id] = d; return d
