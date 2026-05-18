from datetime import datetime
from pydantic import BaseModel, Field


class RepairContext(BaseModel):
    defect_title: str = ""
    task_background: str = ""
    business_goal: str = ""
    reproduction_steps: list[str] = Field(default_factory=list)
    actual_behavior: str = ""
    expected_result: str = ""
    console_errors: list[str] = Field(default_factory=list)
    network_anomalies: list[dict] = Field(default_factory=list)
    root_cause_candidates: list[str] = Field(default_factory=list)
    root_cause_confidence: float = 0.0
    repair_suggestions: list[str] = Field(default_factory=list)
    regression_entries: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def from_defect(cls, defect) -> "RepairContext":
        return cls(
            defect_title=defect.title,
            reproduction_steps=[
                str(p) for chain in (defect.evidence_chains or [])
                for p in (chain.propagation or [])
            ],
            console_errors=[
                str(e) for e in (defect.console_logs or {}).get("errors", [])
            ],
            network_anomalies=[
                {"url": a.get("url"), "status": a.get("status")}
                for a in (defect.api_calls or [])
            ],
            root_cause_candidates=[defect.ai_analysis.get("root_cause", "")]
            if defect.ai_analysis else [],
            repair_suggestions=[defect.fix_suggestion.description]
            if defect.fix_suggestion else [],
        )
