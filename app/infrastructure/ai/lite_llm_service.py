from app.interfaces.ai_service import AIService
from app.lib.logger import get_logger

logger = get_logger(__name__)


class LiteLLMAIService(AIService):
    async def extract_rules(self, content: str, strategy: str = "general") -> dict:
        logger.info(f"AI extract_rules called: strategy={strategy}, content_length={len(content)}")
        return {"rules": [], "strategies_used": [strategy]}

    async def analyze_root_cause(self, evidence: dict) -> dict:
        logger.info("AI analyze_root_cause called")
        return {"root_cause": "Analysis pending", "confidence": "low"}

    async def generate_fix_suggestion(self, defect_data: dict) -> dict:
        logger.info("AI generate_fix_suggestion called")
        return {"description": "Fix suggestion pending", "target": "unknown"}

    async def judge_causal_relation(self, event_a: dict, event_b: dict) -> bool:
        return False
