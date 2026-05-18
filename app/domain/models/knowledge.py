from datetime import datetime, timezone

from pydantic import BaseModel, Field


class BusinessRule(BaseModel):
    id: str = ""
    kb_id: str
    category: str = "rule"
    content: str
    source_doc_id: str = ""
    source_strategy: str = ""
    confidence: float = 0.0
    status: str = "candidate"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UIStandard(BaseModel):
    id: str = ""
    kb_id: str
    component_type: str = ""
    property: str = ""
    expected_value: str = ""
    confidence: float = 0.0


class PermissionRule(BaseModel):
    id: str = ""
    kb_id: str
    role: str
    resource: str
    action: str
    allowed: bool = True


class BusinessLine(BaseModel):
    id: str = ""
    kb_id: str
    name: str
    description: str = ""
    completeness: float = 0.0


class Conflict(BaseModel):
    id: str = ""
    kb_id: str
    conflict_type: str = "contradiction"
    description: str = ""
    status: str = "pending"
    resolution: str = ""
    suggested_action: str = ""


class QualityScore(BaseModel):
    overall: str = "C"
    rule_coverage: float = 0.0
    confidence: float = 0.0
    human_reviewed: bool = False


class KnowledgeBase(BaseModel):
    id: str = ""
    project_id: str
    version: int = 1
    quality_grade: str = "C"
    quality_score: QualityScore = QualityScore()
    total_rules: int = 0
    confirmed_rules: int = 0
    conflicts_count: int = 0
    human_reviewed: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
