"""Aggregate all demo execution data into a structured JSON report."""
from datetime import datetime

from app.domain.models.defect import Defect
from app.domain.models.discovery import PageDiscoveryResult
from app.domain.models.run import StepExecutionRecord
from app.services.contrast_service import ContrastReport


class DemoReportService:
    """Aggregate all demo execution data into a structured JSON report."""

    def build_report(self, target_url: str, doc_urls: list[str],
                     page_discovery: PageDiscoveryResult | None,
                     contrast: ContrastReport | None,
                     steps: list[StepExecutionRecord],
                     defects: list[Defect],
                     duration_seconds: float,
                     no_screenshots: bool = False) -> dict:
        passed = sum(1 for s in steps if s.status == "passed")
        failed = sum(1 for s in steps if s.status == "failed")
        uncertain = sum(1 for s in steps if s.status == "uncertain")

        report = {
            "demo_run": {
                "target_url": target_url,
                "documents": doc_urls,
                "duration_seconds": round(duration_seconds, 1),
                "browser": "Chromium headless",
                "viewport": "1920x1080",
                "timestamp": datetime.now().isoformat(),
            },
            "summary": {
                "total_steps": len(steps),
                "passed": passed, "failed": failed, "uncertain": uncertain,
                "defects_found": len(defects),
            },
            "scenarios": [],
            "defects": [self._defect_to_dict(d, no_screenshots) for d in defects],
        }

        if contrast:
            report["summary"]["coverage"] = {
                "coverage_rate": round(contrast.coverage_rate * 100, 1),
                "matched": len(contrast.matched),
                "missing": len(contrast.missing),
                "extra": len(contrast.extra),
            }

        return report

    def _defect_to_dict(self, d: Defect, no_screenshots: bool) -> dict:
        data = {
            "id": d.id,
            "severity": d.severity,
            "title": d.title,
            "evidence_chain": {
                "trigger": d.evidence_chains[0].root_trigger if d.evidence_chains else {},
                "propagation": d.evidence_chains[0].propagation if d.evidence_chains else [],
                "chain_summary": d.evidence_chains[0].chain_summary if d.evidence_chains else "",
            },
            "console_logs": d.console_logs,
            "api_calls": d.api_calls,
        }
        if not no_screenshots:
            data["screenshots"] = d.screenshots
        if d.ai_analysis:
            data["ai_analysis"] = d.ai_analysis
        if d.fix_suggestion:
            data["fix_suggestion"] = {
                "target": d.fix_suggestion.target,
                "file_hint": d.fix_suggestion.file_hint,
                "description": d.fix_suggestion.description,
            }
        return data
