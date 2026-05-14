from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TestStep(BaseModel):
    index: int
    action: str
    target: str = ""
    value: str = ""
    verifications: list[str] = Field(default_factory=lambda: ["ui", "console"])
    expected: Optional[dict] = None
    xpath: Optional[str] = None


class ExpectedResult(BaseModel):
    business: str = ""
    ui: str = ""
    api: str = ""
    console: str = ""


class TestCase(BaseModel):
    id: str = ""
    scenario_id: str = ""
    project_id: str = ""
    name: str
    description: str = ""
    steps: list[TestStep] = []
    expected_results: Optional[ExpectedResult] = None
    preconditions: list[str] = []
    tags: list[str] = []
    created_at: datetime = Field(default_factory=datetime.now)


class CoverageInfo(BaseModel):
    rule_coverage: float = 0.0
    page_coverage: float = 0.0
    grade: str = "C"


class TestScenario(BaseModel):
    id: str = ""
    project_id: str
    business_line: str = ""
    name: str
    description: str = ""
    type: str = "positive"
    role: str = ""
    cases: list[TestCase] = []
    coverage: CoverageInfo = CoverageInfo()
    status: str = "draft"
    expected_status: str = "success"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
