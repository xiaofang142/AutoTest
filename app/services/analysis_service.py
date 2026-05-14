from app.domain.models.run import StepExecutionRecord
from app.domain.models.defect import Defect, EvidenceChain, SynthesisConclusion, FixSuggestion
from app.interfaces.repositories.defect_repo import DefectRepository
from app.interfaces.ai_service import AIService
from app.lib.id_generator import generate_id
from app.lib.logger import get_logger

logger = get_logger(__name__)


class CrossDimensionAnalyzer:
    """Analyzes step execution data across UI, console, API, and business dimensions."""

    def __init__(self, defect_repo: DefectRepository, ai_service: AIService | None = None):
        self._defect_repo = defect_repo
        self._ai = ai_service

    async def analyze(self, step: StepExecutionRecord) -> Defect | None:
        anomalies = self._detect_anomalies(step)
        if not anomalies:
            return None

        chains = self._build_evidence_chains(anomalies)
        defect = Defect(
            id=generate_id("defect"),
            run_id=step.run_id,
            step_record_id=step.id,
            severity=self._determine_severity(anomalies),
            title=self._generate_title(anomalies),
            evidence_chains=chains,
            synthesis=SynthesisConclusion(
                bug_count=len(chains),
                evidence_chains=chains,
                summary=f"{len(chains)} defect(s) found across {len(anomalies)} dimension(s)",
            ),
        )
        created = await self._defect_repo.create(defect)
        logger.info(f"Defect found: {created.id} severity={created.severity}")
        return created

    def _detect_anomalies(self, step: StepExecutionRecord) -> list[dict]:
        anomalies = []
        for dim in ["ui", "console", "api", "business"]:
            v = getattr(step.verifications, dim, None)
            if v and v.status == "failed":
                anomalies.append({"dimension": dim, "issues": v.issues, "confidence": v.confidence})
        return anomalies

    def _build_evidence_chains(self, anomalies: list[dict]) -> list[EvidenceChain]:
        if not anomalies:
            return []
        chain = EvidenceChain(
            chain_id="chain_001",
            root_trigger={"dimension": anomalies[0]["dimension"], "event": str(anomalies[0]["issues"][:1])},
            propagation=[{"step": i, "dimension": a["dimension"]} for i, a in enumerate(anomalies)],
        )
        return [chain]

    def _determine_severity(self, anomalies: list[dict]) -> str:
        for a in anomalies:
            if a["dimension"] == "api":
                return "high"
        return "medium"

    def _generate_title(self, anomalies: list[dict]) -> str:
        dims = [a["dimension"] for a in anomalies]
        return f"Anomaly detected in {', '.join(dims)}"
