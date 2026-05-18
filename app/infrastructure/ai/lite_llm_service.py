"""LiteLLM AI service - gracefully degrades to rule-based when no API key configured."""
import hashlib
import json
import re

from app.config import settings
from app.interfaces.ai_service import AIService
from app.lib.logger import get_logger

logger = get_logger(__name__)


class LiteLLMAIService(AIService):
    """AI service that uses LiteLLM when API key is available.
    
    When LITELLM_API_KEY is empty, falls back to rule-based analysis.
    This ensures the system works WITHOUT any external API key.
    """

    def __init__(self):
        self.extraction_model = settings.extraction_model
        self.analysis_model = settings.analysis_model
        self.api_key = settings.litellm_api_key
        self.api_base = getattr(settings, 'litellm_api_base', None) or None
        self._cache = {}
        self._llm_available = bool(self.api_key)
        if not self._llm_available:
            logger.info("No LITELLM_API_KEY configured - using rule-based analysis (zero external cost)")

    def _resolve_model(self, model: str) -> str:
        if model and "/" not in model:
            base = self.api_base or ""
            if "deepseek" in base or "openai" in base.lower():
                return f"openai/{model}"
        return model

    def _check_llm(self):
        if not self._llm_available:
            raise RuntimeError("LLM unavailable - no API key configured")

    async def _call_llm(self, model, system, user, use_cache=True):
        self._check_llm()
        import litellm
        resolved = self._resolve_model(model)
        prompt_text = system + user
        key = hashlib.sha256(f"{resolved}:{prompt_text}".encode()).hexdigest()
        if use_cache and key in self._cache:
            return self._cache[key]
        logger.info("LLM call: model=%s resolved=%s len=%d", model, resolved, len(prompt_text))
        try:
            kwargs = dict(
                model=resolved, api_key=self.api_key,
                messages=[{"role":"system","content":system},{"role":"user","content":user}],
                temperature=0.1, max_tokens=4096,
            )
            if self.api_base:
                kwargs["api_base"] = self.api_base
            resp = await litellm.acompletion(**kwargs)
            result = resp.choices[0].message.content.strip()
            if use_cache:
                self._cache[key] = result
            return result
        except Exception as e:
            logger.error("LLM failed: model=%s error=%s", resolved, e)
            raise

    COT_ANALYSIS_PROMPT = """你是一个 UI 自动测试分析引擎。请按步骤推理，不要直接下结论。

## 当前操作
{action}

## 采集数据
[OCR] 截图文字: {ocr_text}
[OCR] 文本块: {ocr_elements}
[DOM] 可见文本: {dom_texts}
[DOM] 告警: {alerts}
[Console] 错误: {console_errors}
[Console] 警告: {console_warnings}
[Network] 请求: {network_requests}

## 分步推理

### 步骤 1: API 层检查（最可靠信号）
- 是否有 4xx/5xx 状态码？
- 是否有请求超时(>5s)？
- → 如果 API 失败，这通常是根因

### 步骤 2: Console 层检查
- 是否有 JS Error/Uncaught Exception？
- 如果有，发生在 API 之前还是之后？
- → API 失败后的 Console 错误 = 级联效应
- → 无 API 失败的 Console 错误 = 前端 Bug

### 步骤 3: UI 层检查
- OCR 和 DOM 文本是否包含错误关键词？
- 页面是否白屏/加载中/空白？
- 告警弹窗是否出现？
- → 与 API/Console 交叉验证

### 步骤 4: 业务层检查
- 当前页面是否符合操作预期？
- URL 是否变化？
- 关键元素是否存在？

### 步骤 5: 综合判断
- 哪个维度是 ROOT CAUSE？
- 哪些是 CASCADING EFFECT？
- 整体结论是什么？

## 输出格式（纯 JSON）
{{"dimensions":{{"ui":{{"status":"pass|fail|uncertain","issues":[],"confidence":0.0}},"console":{{"status":"pass|fail|uncertain","issues":[],"confidence":0.0}},"api":{{"status":"pass|fail|uncertain","issues":[],"confidence":0.0}},"business":{{"status":"pass|fail|uncertain","issues":[],"confidence":0.0}}}},"root_cause":"最可能的根因","fix_suggestion":"如何修复","summary":"一句话总结","reasoning":["推理步骤1","推理步骤2"]}}"""

    async def analyze_merged(self, step_signals: dict) -> dict:
        """CoT-enhanced analysis: OCR + DOM + console + network → step-by-step → Defect.

        Uses chain-of-thought reasoning for better accuracy.
        Falls back to basic analysis on failure.
        """
        if not step_signals.get("ocr_text", "").strip():
            step_signals["ocr_text"] = "（OCR 未识别到文字）"

        # Try CoT analysis first
        for attempt in range(2):
            try:
                fields = {
                    "action": step_signals.get("action", "unknown"),
                    "ocr_text": step_signals.get("ocr_text", "")[:2000],
                    "ocr_elements": (step_signals.get("ocr_elements", "") or "")[:1000],
                    "dom_texts": (step_signals.get("dom_texts", "") or "")[:2000],
                    "alerts": (step_signals.get("alerts", "") or "")[:500],
                    "console_errors": (step_signals.get("console_errors", "") or "")[:2000],
                    "console_warnings": (step_signals.get("console_warnings", "") or "")[:1000],
                    "network_requests": (step_signals.get("network_requests", "") or "")[:3000],
                }
                prompt = self.COT_ANALYSIS_PROMPT.format(**fields)
                result = await self._call_llm(self.analysis_model, "", prompt, use_cache=(attempt == 0))
                match = re.search(r'\{.*\}', result, re.DOTALL)
                if match:
                    parsed = json.loads(match.group())
                    if "dimensions" in parsed:
                        return parsed
            except Exception as e:
                logger.warning("CoT analysis attempt %d failed: %s", attempt + 1, e)

        # Fallback: simple analysis
        return self._simple_analysis(step_signals)

    def _simple_analysis(self, signals: dict) -> dict:
        """Rule-based fallback when LLM is unavailable or fails."""
        issues = {"ui": [], "console": [], "api": [], "business": []}
        error_kws = ["系统错误", "网络错误", "404", "500", "error", "出错了"]

        ocr = (signals.get("ocr_text", "") or "").lower()
        dom = (signals.get("dom_texts", "") or "").lower()
        combined = ocr + dom
        for kw in error_kws:
            if kw.lower() in combined:
                issues["ui"].append(f"检测到错误关键词: {kw}")
        if issues["ui"]:
            issues["ui"] = issues["ui"][:3]

        try:
            ce = json.loads(signals.get("console_errors", "[]") or "[]")
            if ce:
                issues["console"] = [e.get("message", str(e))[:100] for e in ce[:3]]
        except Exception:
            pass

        try:
            nr = json.loads(signals.get("network_requests", "[]") or "[]")
            failed = [r for r in nr if isinstance(r, dict) and r.get("status", 0) >= 400]
            if failed:
                issues["api"] = [f"{r.get('method','?')} {r.get('url','?')} → {r.get('status')}" for r in failed[:3]]
        except Exception:
            pass

        dims = {}
        for dim, iss in issues.items():
            if iss:
                dims[dim] = {"status": "fail", "issues": iss, "confidence": 0.7}
            else:
                dims[dim] = {"status": "pass", "issues": [], "confidence": 0.8}

        has_any = any(iss for iss in issues.values())
        return {
            "dimensions": dims,
            "root_cause": issues["api"][0] if issues["api"] else (issues["console"][0] if issues["console"] else ""),
            "fix_suggestion": "检查 " + ", ".join(k for k, v in issues.items() if v) if has_any else "",
            "summary": f"发现 {sum(len(v) for v in issues.values())} 个问题" if has_any else "全部正常",
            "reasoning": [f"{dim}: {iss[0]}" for dim, iss in issues.items() if iss],
        }

    # ─── Rule-based fallbacks used when no API key ─────────────────────

    def _rule_extract(self, content: str, strategy: str) -> dict:
        """Zero-cost keyword-based extraction."""
        lines = content.split("\n")
        rules = []
        flow_keywords = ["登录", "注册", "下单", "支付", "搜索", "查看", "编辑", "删除", "创建", "提交"]
        permission_keywords = ["管理员", "普通用户", "VIP", "权限", "角色"]
        for line in lines[:50]:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            category = "rule"
            if any(k in line for k in flow_keywords):
                category = "flow"
            elif any(k in line for k in permission_keywords):
                category = "permission"
            rules.append({"category": category, "content": line[:200]})
        return {"rules": rules[:20], "strategies_used": [strategy], "engine": "rule-based"}

    def _rule_root_cause(self, evidence: dict) -> dict:
        errors = evidence.get("console_errors", [])
        api_statuses = evidence.get("api_statuses", [])
        cause = "No clear root cause detected (rule-based analysis)"
        confidence = "low"
        if any(e for e in errors):
            cause = f"Console error detected: {errors[0].get('message','')[:100]}"
            confidence = "medium"
        if any(a.get("status", 0) >= 500 for a in api_statuses):
            cause = f"API 5xx error: {api_statuses[0].get('url','')} returned {api_statuses[0].get('status')}"
            confidence = "high"
        return {"root_cause": cause, "confidence": confidence,
                "evidence": errors[:2], "engine": "rule-based"}

    def _rule_fix_suggestion(self, defect_data: dict) -> dict:
        return {"target": "unknown", "description": "AI fix suggestion requires API key",
                "code_snippet": "", "engine": "rule-based"}

    def _rule_causal_judge(self, event_a: dict, event_b: dict) -> bool:
        dim_a = event_a.get("dimension", "")
        dim_b = event_b.get("dimension", "")
        causal_map = {
            ("api", "console"): True,
            ("api", "ui"): True,
            ("console", "ui"): True,
            ("api", "api"): True,
        }
        return causal_map.get((dim_a, dim_b), False)

    # ─── Public API ───────────────────────────────────────────────────

    async def extract_rules(self, content: str, strategy: str = "general") -> dict:
        if not self._llm_available:
            return self._rule_extract(content, strategy)
        try:
            tmpl = self._get_prompt(strategy)
            result = await self._call_llm(self.extraction_model, tmpl["system"],
                                          tmpl["user"].format(content=content[:8000]))
            match = re.search(r'\{.*\}', result, re.DOTALL)
            return json.loads(match.group()) if match else {"rules": []}
        except Exception as e:
            logger.warning("LLM extract failed, fallback to rule: %s", e)
            return self._rule_extract(content, strategy)

    def _get_prompt(self, strategy):
        prompts = {
            "general": {"system": "Extract business rules as JSON: {\"rules\":[{\"category\":\"flow|permission|ui\",\"content\":\"...\"}]}", "user": "{content}"},
            "structured": {"system": "Extract strictly: {\"rules\":[{\"category\":\"...\",\"content\":\"...\"}]}", "user": "{content}"},
        }
        return prompts.get(strategy, prompts["general"])

    async def analyze_root_cause(self, evidence: dict) -> dict:
        if not self._llm_available:
            return self._rule_root_cause(evidence)
        try:
            prompt = """Analyze root cause. Output JSON: {"root_cause":"...","confidence":"high|medium|low","evidence":[...]}"""
            result = await self._call_llm(self.analysis_model, prompt,
                                          json.dumps(evidence, indent=2)[:6000])
            match = re.search(r'\{.*\}', result, re.DOTALL)
            return json.loads(match.group()) if match else {"root_cause": "parsing error"}
        except Exception as e:
            logger.warning("LLM root cause failed, fallback: %s", e)
            return self._rule_root_cause(evidence)

    async def generate_fix_suggestion(self, defect_data: dict) -> dict:
        if not self._llm_available:
            return self._rule_fix_suggestion(defect_data)
        try:
            prompt = """Generate fix suggestion. Output JSON: {"target":"frontend|backend","file_hint":"...","description":"...","code_snippet":"..."}"""
            result = await self._call_llm(self.analysis_model, prompt,
                                          json.dumps(defect_data, indent=2)[:6000])
            match = re.search(r'\{.*\}', result, re.DOTALL)
            return json.loads(match.group()) if match else {"description": "parsing error"}
        except Exception as e:
            logger.warning("LLM fix failed, fallback: %s", e)
            return self._rule_fix_suggestion(defect_data)

    async def judge_causal_relation(self, event_a: dict, event_b: dict) -> bool:
        if not self._llm_available:
            return self._rule_causal_judge(event_a, event_b)
        try:
            prompt = f"Did event A cause B? A:{event_a} B:{event_b}. Answer YES or NO."
            result = await self._call_llm(self.analysis_model, "You are a fault analyst.", prompt)
            return "YES" in result.upper()
        except Exception:
            return self._rule_causal_judge(event_a, event_b)
