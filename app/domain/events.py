from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class DomainEvent:
    event_id: str
    event_type: str
    timestamp: datetime = field(default_factory=datetime.now)
    source_module: str = ""
    payload: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source_module,
            "payload": self.payload,
        }


PROJECT_CREATED = "project.created"
PROJECT_CONFIG_CHANGED = "project.config.updated"
PROJECT_DELETED = "project.deleted"
DOCUMENT_ADDED = "document.added"
DOCUMENT_PARSED = "document.parsed"
DOCUMENT_PARSE_FAILED = "document.parse.failed"
ALL_DOCUMENTS_PARSED = "document.all_parsed"
KNOWLEDGE_BASE_CREATED = "kb.created"
KNOWLEDGE_BASE_UPDATED = "kb.updated"
RULE_CONFIRMED = "rule.confirmed"
CONFLICT_RESOLVED = "conflict.resolved"
SCENARIOS_GENERATED = "scenarios.generated"
SCENARIO_GENERATION_FAILED = "scenarios.generation.failed"
RUN_CREATED = "run.created"
RUN_STARTED = "run.started"
STEP_COMPLETED = "step.completed"
DEFECT_FOUND = "defect.found"
RUN_COMPLETED = "run.completed"
RUN_FAILED = "run.failed"
DEFECT_CONFIRMED = "defect.confirmed"
DEFECT_DISMISSED = "defect.dismissed"
