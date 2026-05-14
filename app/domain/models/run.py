from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, model_validator


class ConsoleLogEntry(BaseModel):
    level: str = "error"
    message: str
    source: str = ""
    stack: str = ""
    timestamp: str = ""


class ConsoleSnapshot(BaseModel):
    errors: list[ConsoleLogEntry] = []
    warnings: list[ConsoleLogEntry] = []


class NetworkEntry(BaseModel):
    method: str = "GET"
    url: str
    status: int = 0
    request: dict = {}
    response: Optional[dict] = None
    timing: Optional[dict] = None


class NetworkSnapshot(BaseModel):
    requests: list[NetworkEntry] = []
    failed: list[NetworkEntry] = []


class PageState(BaseModel):
    current_url: str = ""
    visible_text_elements: list[str] = []
    active_alerts: list[str] = []


class VerificationResult(BaseModel):
    status: str = "pass"
    dimension: str = ""
    issues: list[dict] = []
    confidence: float = 1.0
    detail: str = ""


class Verifications(BaseModel):
    ui: VerificationResult = VerificationResult(dimension="ui")
    console: VerificationResult = VerificationResult(dimension="console")
    api: VerificationResult = VerificationResult(dimension="api")
    business: VerificationResult = VerificationResult(dimension="business")


class StepExecutionRecord(BaseModel):
    id: str = ""
    run_id: str = ""
    case_id: str = ""
    step_index: int = 0
    action: str = ""
    platform: str = "web"
    status: str = "passed"
    duration_ms: int = 0
    screenshots: dict = {}
    console_snapshot: ConsoleSnapshot = ConsoleSnapshot()
    network_snapshot: NetworkSnapshot = NetworkSnapshot()
    page_state: PageState = PageState()
    verifications: Verifications = Verifications()
    cross_dimension_report: dict = {}
    error: Optional[str] = None
    retry_count: int = 0
    created_at: datetime = Field(default_factory=datetime.now)


class RunSummary(BaseModel):
    total_cases: int = 0
    passed: int = 0
    failed: int = 0
    uncertain: int = 0
    pass_rate: float = 0.0

    @model_validator(mode='after')
    def _compute_pass_rate(self):
        """Auto-compute pass_rate, excluding uncertain steps from the denominator."""
        total = self.total_cases - self.uncertain if self.uncertain > 0 else self.total_cases
        if self.total_cases > 0 and total > 0:
            self.pass_rate = round(self.passed / total, 4)
        return self


class RunRecord(BaseModel):
    id: str = ""
    project_id: str
    name: str = ""
    status: str = "queued"
    platforms: list[str] = ["web"]
    progress: dict = {}
    summary: RunSummary = RunSummary()
    total_cases: int = 0
    passed_count: int = 0
    failed_count: int = 0
    uncertain_count: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
