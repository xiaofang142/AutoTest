import hashlib
import json
from app.interfaces.ai_service import AIService
from app.config import settings
from app.lib.logger import get_logger

logger = get_logger(__name__)

EXTRACT_PROMPTS = {
    "general": {
        "system": "You are a senior business analyst. Extract business processes and rules from the product document. Output JSON: {\"business_lines\": [{\"name\": \"...\", \"steps\": [...]}], \"rules\": [{\"category\": \"flow|rule|permission|ui\", \"content\": \"...\", \"page\": \"...\", \"role\": \"...\"}]}",
        "user": "Document content:\n\n{content}",
    },
    "structured": {
        "system": "You are a test architect. Extract testable rules strictly following this JSON schema: {\"rules\": [{\"category\": \"flow|rule|permission|ui\", \"content\": \"...\", \"page\": \"...\", \"role\": \"...\"}]}",
        "user": "Document:\n\n{content}",
    },
}

ROOT_CAUSE_PROMPT = {
    "system": "You are a QA debug expert. Analyze multi-dimensional defect data (console logs, API calls, page state) and find root cause. Output JSON: {\"root_cause\": \"...\", \"confidence\": \"high|medium|low\", \"evidence\": [\"...\"], \"suggestion\": \"...\"}",
    "user": "Defect evidence:\n\n{evidence_json}",
}

FIX_SUGGEST_PROMPT = {
    "system": "You are a senior engineer. Based on defect analysis, generate fix suggestions. Output JSON: {\"target\": \"frontend|backend\", \"file_hint\": \"...\", \"description\": \"...\", \"code_snippet\": \"...\"}",
    "user": "Defect data:\n\n{defect_json}",
}

CAUSAL_JUDGE_PROMPT = {
    "system": "You are a fault analysis expert. Determine if event A caused event B. Answer YES or NO only.",
    "user": "Event A (earlier): {event_a}\nEvent B (later): {event_b}\nDid A cause B?",
}


class LiteLLMAIService(AIService):
    """Real AI service with LiteLLM. Supports OpenAI/Claude/Gemini/GLM via config."""

    def __init__(self):
        self.extraction_model = settings.extraction_model
        self.analysis_model = settings.analysis_model
        self.api_key = settings.litellm_api_key
        self._cache = {}

    def _cache_key(self, model, prompt):
        return hashlib.sha256(f"{model}:{prompt}".encode()).hexdigest()

    async def _call_llm(self, model, system, user, use_cache=True):
        import litellm
        prompt_text = system + user
        key = self._cache_key(model, prompt_text)
        if use_cache and key in self._cache:
            logger.debug(f"AI cache hit")
            return self._cache[key]

        logger.info(f"AI call: model={model}")
        try:
            resp = await litellm.acompletion(
                model=model,
                api_key=self.api_key,
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}],
                temperature=0.1, max_tokens=4096,
            )
            result = resp.choices[0].message.content.strip()
            if use_cache:
                self._cache[key] = result
            return result
        except Exception as e:
            logger.error(f"AI call failed: {e}")
            raise

    async def extract_rules(self, content: str, strategy: str = "general") -> dict:
        import re
        tmpl = EXTRACT_PROMPTS.get(strategy, EXTRACT_PROMPTS["general"])
        try:
            result = await self._call_llm(self.extraction_model, tmpl["system"],
                                          tmpl["user"].format(content=content[:8000]))
            match = re.search(r'\{.*\}', result, re.DOTALL)
            if match:
                parsed = json.loads(match.group())
                logger.info(f"Extracted {len(parsed.get('rules', []))} rules")
                return parsed
            return {"rules": [], "raw": result}
        except Exception as e:
            logger.error(f"Extract failed: {e}")
            return {"rules": [], "error": str(e)}

    async def analyze_root_cause(self, evidence: dict) -> dict:
        import re
        try:
            result = await self._call_llm(self.analysis_model, ROOT_CAUSE_PROMPT["system"],
                                          ROOT_CAUSE_PROMPT["user"].format(
                                              evidence_json=json.dumps(evidence, indent=2)[:6000]))
            match = re.search(r'\{.*\}', result, re.DOTALL)
            return json.loads(match.group()) if match else {"root_cause": "parsing error"}
        except Exception as e:
            logger.error(f"Root cause failed: {e}")
            return {"root_cause": "unavailable"}

    async def generate_fix_suggestion(self, defect_data: dict) -> dict:
        import re
        try:
            result = await self._call_llm(self.analysis_model, FIX_SUGGEST_PROMPT["system"],
                                          FIX_SUGGEST_PROMPT["user"].format(
                                              defect_json=json.dumps(defect_data, indent=2)[:6000]))
            match = re.search(r'\{.*\}', result, re.DOTALL)
            return json.loads(match.group()) if match else {"description": "parsing error"}
        except Exception as e:
            logger.error(f"Fix suggestion failed: {e}")
            return {"description": "unavailable"}

    async def judge_causal_relation(self, event_a: dict, event_b: dict) -> bool:
        try:
            result = await self._call_llm(self.analysis_model, CAUSAL_JUDGE_PROMPT["system"],
                                          CAUSAL_JUDGE_PROMPT["user"].format(
                                              event_a=json.dumps(event_a), event_b=json.dumps(event_b)))
            return "YES" in result.upper()
        except Exception:
            return False
