"""GLM-4V OCR service - gracefully degrades to empty result when no API key."""
import json
import re

from app.config import settings
from app.interfaces.ocr_service import OCRService
from app.lib.logger import get_logger

logger = get_logger(__name__)

TEXT_PROMPT = """Read all visible text in this screenshot.
Output JSON: {"text":"...","elements":[{"text":"...","bbox":[x1,y1,x2,y2]}]}"""

COMPONENT_PROMPT = """Detect UI components.
Output JSON array: [{"type":"button|input|text|link","text":"...","bbox":[...],"confidence":0.95}]"""


class GLMVOCRService(OCRService):
    def __init__(self):
        self.api_key = settings.litellm_api_key
        self._available = bool(self.api_key)
        if not self._available:
            logger.info("No API key - GLM-4V OCR disabled")

    async def recognize_text(self, image_base64: str) -> dict:
        if not self._available:
            logger.debug("OCR skipped (no API key)")
            return {"text": "", "elements": [], "engine": "disabled"}
        try:
            import httpx
            data = image_base64.split(",", 1)[-1] if image_base64.startswith("data:") else image_base64
            resp = await httpx.AsyncClient(timeout=30).post(
                "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"model": "glm-4v", "messages": [{"role": "user", "content": [
                    {"type": "text", "text": TEXT_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{data}"}},
                ]}], "temperature": 0.1, "max_tokens": 4096},
            )
            content = resp.json()["choices"][0]["message"]["content"]
            match = re.search(r'\{.*\}', content, re.DOTALL)
            return json.loads(match.group()) if match else {"text": content, "elements": []}
        except Exception as e:
            logger.error("GLM-4V OCR failed: %s", e)
            return {"text": "", "elements": [], "error": str(e)}

    async def recognize_components(self, image_base64: str) -> list[dict]:
        return []
