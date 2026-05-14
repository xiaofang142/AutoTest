"""Cross-dimensional analysis engine: UI + Console + API + Business verification with AI root cause analysis."""
import json
from typing import Optional
from app.domain.models.run import StepExecutionRecord, VerificationResult, Verifications
from app.domain.models.defect import Defect, EvidenceChain, SynthesisConclusion, FixSuggestion
from app.interfaces.repositories.defect_repo import DefectRepository
from app.interfaces.ai_service import AIService
from app.lib.id_generator import generate_id
from app.lib.logger import get_logger

logger = get_logger(__name__)


class CrossDimensionAnalyzer:
    """Analyzes step execution data across 4 dimensions and produces evidence chains."""

    def __init__(self, defect_repo: Optional[DefectRepository] = None,
                 ai_service: Optional[AIService] = None):
        self._defect_repo = defect_repo
        self._ai = ai_service

    async def analyze(self, step: StepExecutionRecord) -> Optional[Defect]:
        anomalies = self._detect_anomalies(step)
        if not anomalies:
            return None

        chains = await self._build_evidence_chains(anomalies, step)
        ai_analysis = {}
        fix_suggestion = None
        if self._ai and chains:
            evidence_pkg = self._build_evidence_package(step, anomalies, chains)
            try:
                ai_analysis = await self._ai.analyze_root_cause(evidence_pkg)
                if ai_analysis.get("root_cause"):
                    fix_data = await self._ai.generate_fix_suggestion({
                        "evidence": evidence_pkg,
                        "root_cause": ai_analysis,
                    })
                    if fix_data.get("description"):
                        fix_suggestion = FixSuggestion(**fix_data)
            except Exception as e:
                logger.error(f"AI analysis failed: {e}")

        defect = Defect(
            id=generate_id("defect"),
            run_id=step.run_id,
            step_record_id=step.id,
            severity=self._determine_severity(anomalies),
            title=self._generate_title(anomalies, chains),
            step_context={"action": step.action, "platform": step.platform,
                          "step_index": step.step_index, "case_id": step.case_id},
            screenshots=step.screenshots,
            console_logs={
                "errors": [e.model_dump() for e in step.console_snapshot.errors],
                "warnings": [e.model_dump() for e in step.console_snapshot.warnings],
            } if step.console_snapshot else {},
            api_calls=[r.model_dump() for r in step.network_snapshot.requests],
            page_state=step.page_state.model_dump() if step.page_state else {},
            ai_analysis=ai_analysis,
            fix_suggestion=fix_suggestion,
            cross_dimension_analysis={
                "anomaly_count": len(anomalies),
                "chain_count": len(chains),
            },
            evidence_chains=chains,
            synthesis=SynthesisConclusion(
                bug_count=len(chains),
                evidence_chains=chains,
                summary=self._synthesize(anomalies, chains),
            ),
        )
        if self._defect_repo:
            defect = await self._defect_repo.create(defect)
            logger.info(f"Defect recorded: {defect.id} sev={defect.severity} chains={len(chains)}")
        return defect

    # ── 4-Dimensional Verification ──────────────────────────────────────

    def verify_ui(self, step: StepExecutionRecord) -> VerificationResult:
        """Check UI rendering: error text, blank page, missing components."""
        issues = []
        error_keywords = ["系统错误", "网络错误", "404", "500", "error", "failed", "出错了", "请稍后重试"]
        for alert in (step.page_state.active_alerts or []):
            for kw in error_keywords:
                if kw.lower() in alert.lower():
                    issues.append({"severity": "error", "detail": f"Error alert: {alert}"})
                    break
        if not step.screenshots.get("after") and not step.screenshots.get("before"):
            issues.append({"severity": "warning", "detail": "No screenshot captured"})
        status = "failed" if any(i["severity"] == "error" for i in issues) else "pass"
        return VerificationResult(status=status, dimension="ui", issues=issues,
                                  confidence=0.9 if not issues else 0.95)

    def verify_console(self, step: StepExecutionRecord) -> VerificationResult:
        """Check console logs for JS errors and warnings."""
        issues = []
        for err in (step.console_snapshot.errors or []):
            issues.append({"severity": "error", "detail": err.message, "source": err.source})
        for warn in (step.console_snapshot.warnings or []):
            issues.append({"severity": "warning", "detail": warn.message})
        status = "failed" if any(i["severity"] == "error" for i in issues) else \
                 "uncertain" if any(i["severity"] == "warning" for i in issues) else "pass"
        return VerificationResult(status=status, dimension="console", issues=issues, confidence=0.98)

    def verify_api(self, step: StepExecutionRecord) -> VerificationResult:
        """Check API responses for 4xx/5xx errors and timeouts."""
        issues = []
        for req in (step.network_snapshot.requests or []):
            if req.status >= 400:
                issues.append({"severity": "error" if req.status >= 500 else "warning",
                               "detail": f"{req.method} {req.url} -> {req.status}"})
            if req.timing and req.timing.get("duration_ms", 0) > 5000:
                issues.append({"severity": "warning", "detail": f"Slow: {req.url} ({req.timing.get('duration_ms')}ms)"})
        status = "failed" if any(i["severity"] == "error" for i in issues) else \
                 "uncertain" if issues else "pass"
        return VerificationResult(status=status, dimension="api", issues=issues, confidence=0.95)

    def verify_business(self, step: StepExecutionRecord, expected: Optional[dict] = None) -> VerificationResult:
        """Check business results: URL, visible text, page title match expectations."""
        issues = []
        if expected:
            if expected.get("url_contains") and expected["url_contains"] not in (step.page_state.current_url or ""):
                issues.append({"severity": "error", "detail": f"URL mismatch: expected '{expected['url_contains']}' in '{step.page_state.current_url}'"})
            if expected.get("visible_text"):
                texts = step.page_state.visible_text_elements or []
                if not any(expected["visible_text"] in t for t in texts):
                    issues.append({"severity": "warning", "detail": f"Expected text '{expected['visible_text']}' not found"})
        status = "failed" if issues and any(i["severity"] == "error" for i in issues) else \
                 "uncertain" if issues else "pass"
        return VerificationResult(status=status, dimension="business", issues=issues, confidence=0.85)

    # ── Internal ─────────────────────────────────────────────────────────

    def _detect_anomalies(self, step: StepExecutionRecord) -> list[dict]:
        anomalies = []
        for dim_name, verify_fn in [("ui", self.verify_ui), ("console", self.verify_console),
                                     ("api", self.verify_api), ("business", self.verify_business)]:
            try:
                result = verify_fn(step)
                if result.status != "pass":
                    anomalies.append({"dimension": dim_name, "issues": result.issues,
                                      "confidence": result.confidence})
            except Exception as e:
                logger.error(f"Verify {dim_name} failed: {e}")
        return anomalies

    async def _build_evidence_chains(self, anomalies: list[dict],
                                      step: StepExecutionRecord) -> list[EvidenceChain]:
        if not anomalies:
            return []
        # Sort by confidence (most reliable dimension first)
        sorted_anomalies = sorted(anomalies, key=lambda a: -a["confidence"])
        chain = EvidenceChain(
            chain_id=generate_id("chain"),
            root_trigger={"dimension": sorted_anomalies[0]["dimension"],
                          "event": str(sorted_anomalies[0]["issues"][:1])},
            propagation=[{"step": i, "dimension": a["dimension"],
                          "event": str(a["issues"][:1])}
                         for i, a in enumerate(sorted_anomalies)],
            chain_type=" -> ".join(a["dimension"] for a in sorted_anomalies),
            chain_summary=f"{len(sorted_anomalies)} dimensions affected",
        )
        # If AI available, try to improve chain with causal analysis
        if self._ai and len(sorted_anomalies) >= 2:
            for i in range(len(sorted_anomalies) - 1):
                try:
                    has_causal = await self._ai.judge_causal_relation(
                        sorted_anomalies[i], sorted_anomalies[i + 1])
                    if has_causal:
                        chain.propagation[i]["relation"] = "causal"
                except Exception:
                    pass
        return [chain]

    def _determine_severity(self, anomalies: list[dict]) -> str:
        dims = {a["dimension"] for a in anomalies}
        if "api" in dims: return "high"
        if "ui" in dims and "console" in dims: return "high"
        if "console" in dims: return "medium"
        return "low"

    def _generate_title(self, anomalies: list[dict], chains: list[EvidenceChain]) -> str:
        if chains and chains[0].chain_summary:
            cause = chains[0].root_trigger.get("dimension", "unknown")
            return f"Defect originating from {cause} affecting {len(anomalies)} dimension(s)"
        return f"Anomaly in {', '.join(a['dimension'] for a in anomalies)}"

    def _synthesize(self, anomalies: list[dict], chains: list[EvidenceChain]) -> str:
        return f"{len(chains)} defect chain(s) from {len(anomalies)} anomaly signal(s)"

    def _build_evidence_package(self, step: StepExecutionRecord,
                                 anomalies: list[dict],
                                 chains: list[EvidenceChain]) -> dict:
        return {
            "anomalies": anomalies,
            "chains": [c.model_dump() for c in chains],
            "console_errors": [e.model_dump() for e in step.console_snapshot.errors],
            "api_statuses": [{"url": r.url, "status": r.status}
                            for r in step.network_snapshot.requests],
            "page_url": step.page_state.current_url,
            "page_alerts": step.page_state.active_alerts,
        }
