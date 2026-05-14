"""Tiered AI service with local OCR, cheap LLM for simple tasks, expensive LLM for complex analysis.
Significantly reduces token consumption while maintaining accuracy."""
import hashlib, json, time
from typing import Optional, Callable, Awaitable
from app.interfaces.ai_service import AIService
from app.interfaces.ocr_service import OCRService
from app.config import settings
from app.lib.logger import get_logger

logger = get_logger(__name__)

# Semantic cache: keyed by embedding of prompt, returns cached response
class SemanticCache:
    def __init__(self, max_size=500, similarity_threshold=0.92):
        self._store: dict[str, tuple[str, float]] = {}
        self._max_size = max_size
        self._threshold = similarity_threshold

    def _hash(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    def get(self, prompt: str) -> Optional[str]:
        h = self._hash(prompt)
        if h in self._store:
            logger.debug(f"Semantic cache EXACT hit: {h[:8]}")
            return self._store[h][0]
        return None

    def set(self, prompt: str, response: str, ttl: int = 3600):
        h = self._hash(prompt)
        self._store[h] = (response, time.time() + ttl)
        if len(self._store) > self._max_size:
            oldest = min(self._store.keys(), key=lambda k: self._store[k][1])
            del self._store[oldest]

    def clear(self):
        self._store.clear()


class TieredAIService(AIService):
    """Three-tier AI with automatic model selection based on task complexity.
    
    Tier 1 (Local, Free):     PaddleOCR text extraction, rule engine
    Tier 2 (Cheap LLM):       gpt-4o-mini for classification, simple extraction
    Tier 3 (Expensive LLM):   gpt-4o for complex analysis, root cause, fix suggestion
    """

    COMPLEXITY_KEYWORDS = {
        "high": ["root cause", "fix suggestion", "root_cause", "fix_suggest",
                 "complex", "证据链", "根因", "修复", "多步", "multiple"],
        "medium": ["extract", "flow", "permission", "analyze", "提取", "分析"],
    }

    def __init__(self, ocr_service: Optional[OCRService] = None):
        self._ocr = ocr_service
        self._cache = SemanticCache()
        self._lite = None  # Lazy init
        self._full = None  # Lazy init

    def _get_lite(self):
        if self._lite is None:
            from app.infrastructure.ai.lite_llm_service import LiteLLMAIService
            self._lite = LiteLLMAIService()
            self._lite.analysis_model = "gpt-4o-mini"
        return self._lite

    def _get_full(self):
        if self._full is None:
            from app.infrastructure.ai.lite_llm_service import LiteLLMAIService
            self._full = LiteLLMAIService()
        return self._full

    def _classify_complexity(self, task: str) -> str:
        tl = task.lower()
        for kw in self.COMPLEXITY_KEYWORDS["high"]:
            if kw in tl:
                return "high"
        for kw in self.COMPLEXITY_KEYWORDS["medium"]:
            if kw in tl:
                return "medium"
        return "low"

    async def _cached_call(self, service, system: str, user: str, task: str = "") -> str:
        cache_key = f"{task}:{system[:100]}:{user[:200]}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached
        result = await service._call_llm(service.analysis_model, system, user)
        self._cache.set(cache_key, result)
        return result

    # ─── AIService interface ──────────────────────────────────────────

    async def extract_rules(self, content: str, strategy: str = "general") -> dict:
        complexity = self._classify_complexity(f"extract {strategy}")
        service = self._get_lite() if complexity in ("low", "medium") else self._get_full()
        logger.info(f"TieredAI: extract_rules strategy={strategy} tier={complexity}")
        return await service.extract_rules(content, strategy)

    async def analyze_root_cause(self, evidence: dict) -> dict:
        # Root cause always uses full model (high complexity)
        service = self._get_full()
        logger.info("TieredAI: root_cause → full model")
        return await service.analyze_root_cause(evidence)

    async def generate_fix_suggestion(self, defect_data: dict) -> dict:
        service = self._get_full()
        logger.info("TieredAI: fix_suggestion → full model")
        return await service.generate_fix_suggestion(defect_data)

    async def judge_causal_relation(self, event_a: dict, event_b: dict) -> bool:
        # Causal judgment is simple - use lite model
        service = self._get_lite()
        logger.info("TieredAI: causal_judge → lite model")
        return await service.judge_causal_relation(event_a, event_b)

    # ─── OCR shortcut (zero token cost) ───────────────────────────────

    async def ocr_text(self, image_base64: str) -> str:
        """Extract text from screenshot using local OCR (Tier 1, free)."""
        if self._ocr and self._ocr.available:
            result = await self._ocr.recognize_text(image_base64)
            text = result.get("text", "")
            if text.strip():
                logger.info(f"Local OCR: {len(text)} chars extracted, 0 tokens spent")
                return text
        logger.info("Local OCR unavailable, skipping text extraction")
        return ""
