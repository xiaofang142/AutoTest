"""LiteLLM AI service - gracefully degrades to rule-based when no API key configured."""
import json, re, hashlib
from typing import Optional
from app.interfaces.ai_service import AIService
from app.config import settings
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
        self._cache = {}
        self._llm_available = bool(self.api_key)

        if not self._llm_available:
            logger.info("No LITELLM_API_KEY configured - using rule-based analysis (zero external cost)")

    def _check_llm(self):
        if not self._llm_available:
            raise RuntimeError("LLM unavailable - no API key configured")

    async def _call_llm(self, model, system, user, use_cache=True):
        self._check_llm()
        import litellm
        prompt_text = system + user
        key = hashlib.sha256(f"{model}:{prompt_text}".encode()).hexdigest()
        if use_cache and key in self._cache:
            return self._cache[key]
        logger.info(f"LLM call: model={model} len={len(prompt_text)}")
        try:
            resp = await litellm.acompletion(
                model=model, api_key=self.api_key,
                messages=[{"role":"system","content":system},{"role":"user","content":user}],
                temperature=0.1, max_tokens=4096,
            )
            result = resp.choices[0].message.content.strip()
            if use_cache:
                self._cache[key] = result
            return result
        except Exception as e:
            logger.error(f"LLM failed: {e}")
            raise

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
            logger.warning(f"LLM extract failed, fallback to rule: {e}")
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
            logger.warning(f"LLM root cause failed, fallback: {e}")
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
            logger.warning(f"LLM fix failed, fallback: {e}")
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
