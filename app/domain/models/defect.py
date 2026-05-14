from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class EvidenceChain(BaseModel):
    chain_id: str = ""
    root_trigger: dict = {}
    propagation: list[dict] = []
    chain_type: str = ""
    chain_summary: str = ""


class SynthesisConclusion(BaseModel):
    bug_count: int = 0
    evidence_chains: list[EvidenceChain] = []
    summary: str = ""


class FixSuggestion(BaseModel):
    target: str = ""
    file_hint: str = ""
    description: str = ""
    code_snippet: str = ""
    estimated_effort: str = ""


class Defect(BaseModel):
    id: str = ""
    run_id: str
    step_record_id: str = ""
    type: str = "api_error"
    severity: str = "medium"
    title: str = ""
    step_context: dict = {}
    screenshots: dict = {}
    console_logs: dict = {}
    api_calls: list[dict] = []
    page_state: dict = {}
    ai_analysis: dict = {}
    fix_suggestion: Optional[FixSuggestion] = None
    cross_dimension_analysis: dict = {}
    evidence_chains: list[EvidenceChain] = []
    synthesis: Optional[SynthesisConclusion] = None
    is_false_positive: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
