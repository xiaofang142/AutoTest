"""Cross-dimensional analysis engine: UI + Console + API + Business verification with AI root cause analysis."""
import json
from typing import Optional

from app.domain.models.defect import Defect, EvidenceChain, SynthesisConclusion
from app.domain.models.run import StepExecutionRecord, VerificationResult
from app.interfaces.ai_service import AIService
from app.interfaces.ocr_service import OCRService
from app.interfaces.repositories.defect_repo import DefectRepository
from app.lib.id_generator import generate_id
from app.lib.logger import get_logger
from app.services.causal_engine import CausalRuleEngine, LLMCausalJudge

logger = get_logger(__name__)


class CrossDimensionAnalyzer:
    """Analyzes step execution data across 4 dimensions and produces evidence chains."""

    def __init__(self, defect_repo: Optional[DefectRepository] = None,
                 ai_service: Optional[AIService] = None,
                 ocr_service: Optional[OCRService] = None):
        self._defect_repo = defect_repo
        self._ai = ai_service
        self._ocr = ocr_service
        self._causal_engine = CausalRuleEngine()
        self._llm_judge = LLMCausalJudge(ai_service)

    async def analyze(self, step: StepExecutionRecord) -> Optional[Defect]:
        """LLM 合并分析路径：OCR + DOM + console + network → LLM → Defect。

        PaddleOCR（常驻）+ LLM（常驻）始终参与分析。
        """
        screenshot = step.screenshots.get("after") or step.screenshots.get("before")

        # 1. Enhanced OCR: 预处理 + 识别 + 布局分析 + DOM 对齐
        ocr_text = ""
        ocr_elements = []
        ocr_components = []
        if self._ocr and screenshot:
            try:
                from app.infrastructure.ocr.enhanced_ocr_service import EnhancedOCRService
                enhancer = EnhancedOCRService(self._ocr)
                dom_elements = _dom_to_elements(step.page_state)
                viewport = {"width": 1920, "height": 1080}
                ocr_result = await enhancer.full_analyze(screenshot, dom_elements, viewport)
                ocr_text = ocr_result.get("text", "")
                ocr_elements = ocr_result.get("elements", [])
                ocr_components = ocr_result.get("components", [])
            except Exception as e:
                logger.error("Enhanced OCR failed, fallback to basic: %s", e)
                try:
                    ocr_result = await self._ocr.recognize_text(screenshot)
                    ocr_text = ocr_result.get("text", "")
                    ocr_elements = ocr_result.get("elements", [])
                except Exception as e2:
                    logger.error("Basic OCR also failed: %s", e2)

        # 2. 收集所有信号
        signals = {
            "ocr_text": ocr_text,
            "ocr_elements": str([e.get("text", "") for e in ocr_elements[:10]]),
            "dom_texts": "\n".join(step.page_state.visible_text_elements or []),
            "alerts": str(step.page_state.active_alerts or []),
            "console_errors": json.dumps(
                [e.model_dump() for e in step.console_snapshot.errors], ensure_ascii=False),
            "console_warnings": json.dumps(
                [e.model_dump() for e in step.console_snapshot.warnings], ensure_ascii=False),
            "network_requests": json.dumps(
                [{"method": r.method, "url": r.url, "status": r.status}
                 for r in step.network_snapshot.requests], ensure_ascii=False),
            "action": f"{step.action} (step {step.step_index})",
        }

        # 3. LLM 合并分析
        analysis = {}
        if self._ai:
            try:
                analysis = await self._ai.analyze_merged(signals)
            except Exception as e:
                logger.error("LLM merged analysis failed: %s", e)

        # 4. 存入 step 记录
        step.llm_analysis = {
            "ocr_text": ocr_text[:1000],
            "ocr_elements": ocr_elements[:20],
            "signals": {k: v[:200] if isinstance(v, str) else v for k, v in signals.items()},
            "llm_response": analysis,
        }

        # 5. 检查是否有缺陷 (优先LLM, 降级到规则引擎)
        analysis_dims = analysis.get("dimensions", {})
        has_llm_result = bool(analysis_dims)
        if has_llm_result:
            anomalies = []
            for dim_name in ("ui", "console", "api", "business"):
                dim = analysis_dims.get(dim_name, {})
                if dim.get("status") in ("fail", "uncertain"):
                    anomalies.append({
                        "dimension": dim_name,
                        "issues": dim.get("issues", []),
                        "confidence": dim.get("confidence", 0.7),
                    })
        else:
            anomalies = self._detect_anomalies(step)

        if not anomalies:
            return None

        # 6. 构造 Defect
        chains = await self._build_evidence_chains(anomalies, step)
        defect = Defect(
            id=generate_id("defect"),
            run_id=step.run_id,
            step_record_id=step.id,
            severity=self._determine_severity(anomalies),
            title=analysis.get("summary", "Defect detected by LLM analysis"),
            step_context={"action": step.action, "platform": step.platform,
                          "step_index": step.step_index, "case_id": step.case_id},
            screenshots=step.screenshots,
            console_logs={
                "errors": [e.model_dump() for e in step.console_snapshot.errors],
                "warnings": [e.model_dump() for e in step.console_snapshot.warnings],
            } if step.console_snapshot else {},
            api_calls=[r.model_dump() for r in step.network_snapshot.requests],
            page_state=step.page_state.model_dump() if step.page_state else {},
            ai_analysis=analysis,
            cross_dimension_analysis={
                "anomaly_count": len(anomalies),
                "chain_count": len(chains),
            },
            evidence_chains=chains,
            synthesis=SynthesisConclusion(
                bug_count=len(chains),
                evidence_chains=chains,
                summary=analysis.get("summary", "LLM analysis completed"),
            ),
        )
        if self._defect_repo:
            defect = await self._defect_repo.create(defect)
            logger.info("Defect recorded: %s sev=%s chains=%d", defect.id, defect.severity, len(chains))
        return defect

    # ── 4-Dimensional Verification ──────────────────────────────────────

    def verify_ui(self, step: StepExecutionRecord) -> VerificationResult:
        """Check UI rendering: error text alerts from DOM.

        Note: OCR-based text detection is now handled in the LLM merge
        analysis path (analyze() method). This method is a utility for
        the rule-based fallback path.
        """
        issues = []
        error_keywords = ["系统错误", "网络错误", "404", "500", "error", "failed", "出错了", "请稍后重试"]

        for alert in (step.page_state.active_alerts or []):
            for kw in error_keywords:
                if kw.lower() in alert.lower():
                    issues.append({"severity": "error", "detail": f"Error alert: {alert}"})
                    break

        has_screenshot = bool(step.screenshots.get("after") or step.screenshots.get("before"))
        if not has_screenshot:
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
                logger.error("Verify %s failed: %s", dim_name, e)
        return anomalies

    async def _build_evidence_chains(self, anomalies: list[dict],
                                      step: StepExecutionRecord) -> list[EvidenceChain]:
        if not anomalies:
            return []

        from datetime import datetime as _dt

        def _to_causal_event(anomaly: dict, index: int) -> dict:
            dim = anomaly["dimension"]
            dim_type_map = {
                "ui": "ui_broken",
                "console": "console_error",
                "api": "api_error",
                "business": "ui_broken",
            }
            return {
                "dimension": dim,
                "type": dim_type_map.get(dim, "ui_broken"),
                "timestamp": _dt.utcnow().isoformat(),
                "data": {
                    "issues": anomaly.get("issues", []),
                    "confidence": anomaly.get("confidence", 0.7),
                    "url": step.page_state.current_url if step.page_state else "",
                    "message": str(anomaly.get("issues", [])[:1]),
                    "visible_texts": step.page_state.visible_text_elements or [],
                    "status": next(
                        (r.status for r in (step.network_snapshot.requests or [])
                         if r.status >= 400), None
                    ),
                },
            }

        events = [_to_causal_event(a, i) for i, a in enumerate(anomalies)]

        causal_pairs: list[tuple[int, int]] = []
        for i in range(len(events)):
            for j in range(i + 1, len(events)):
                if self._causal_engine.is_causally_related(events[i], events[j]):
                    causal_pairs.append((i, j))

        if causal_pairs:
            root_idx = causal_pairs[0][0]
            root = anomalies[root_idx]
            root_trigger = {
                "dimension": root["dimension"],
                "event": str(root.get("issues", [])[:1]),
                "source": "rule_engine",
            }
            propagation = []
            for src, dst in causal_pairs:
                dst_anomaly = anomalies[dst]
                propagation.append({
                    "step": dst,
                    "dimension": dst_anomaly["dimension"],
                    "event": str(dst_anomaly.get("issues", [])[:1]),
                    "relation": "causal",
                    "source": "rule_engine",
                })
            chain_type = " -> ".join(
                anomalies[idx]["dimension"] for idx in [root_idx] + [d for _, d in causal_pairs]
            )
            chain_summary = f"{len(causal_pairs)} causal link(s) across {len(set(c for pair in causal_pairs for c in pair))} dimensions"
        else:
            sorted_anomalies = sorted(anomalies, key=lambda a: -a["confidence"])
            root = sorted_anomalies[0]
            root_trigger = {
                "dimension": root["dimension"],
                "event": str(root.get("issues", [])[:1]),
            }
            propagation = [
                {"step": i, "dimension": a["dimension"],
                 "event": str(a.get("issues", [])[:1])}
                for i, a in enumerate(sorted_anomalies)
            ]
            chain_type = " -> ".join(a["dimension"] for a in sorted_anomalies)
            chain_summary = f"{len(sorted_anomalies)} dimensions affected (sorted by confidence)"

        chain = EvidenceChain(
            chain_id=generate_id("chain"),
            root_trigger=root_trigger,
            propagation=propagation,
            chain_type=chain_type,
            chain_summary=chain_summary,
        )

        if self._ai and len(anomalies) >= 2:
            for i in range(len(events)):
                for j in range(i + 1, len(events)):
                    already_causal = any(
                        (i, j) == (s, d) for s, d in causal_pairs
                    )
                    if already_causal:
                        continue
                    try:
                        if await self._llm_judge.judge(events[i], events[j]):
                            chain.propagation.append({
                                "step": j,
                                "dimension": anomalies[j]["dimension"],
                                "event": str(anomalies[j].get("issues", [])[:1]),
                                "relation": "causal",
                                "source": "llm",
                            })
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

def _dom_to_elements(page_state) -> list[dict]:
    """Convert PageState visible texts to DOM element candidates for OCR alignment."""
    if not page_state:
        return []
    elements = []
    for i, text in enumerate(page_state.visible_text_elements or []):
        elements.append({
            "text": text,
            "x": 0, "y": i * 30, "w": 200, "h": 20,
            "tag": "text",
            "selector": f"text-{i}",
        })
    return elements


def _build_evidence_package(step: StepExecutionRecord,
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
