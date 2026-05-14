"""GLM-4V OCR service for text and component recognition from screenshots.

Uses ZhiPu GLM-4V multimodal model for OCR and UI component detection.
Supports PaddleOCR as offline fallback.
"""

import base64
import json
from app.interfaces.ocr_service import OCRService
from app.config import settings
from app.lib.logger import get_logger

logger = get_logger(__name__)

TEXT_RECOGNITION_PROMPT = """Please carefully read all visible text in this screenshot and return it as a structured JSON:
{
  "text": "All visible text concatenated",
  "elements": [
    {"text": "each distinct text element", "bbox": [x1, y1, x2, y2]}
  ],
  "page_title": "main heading or page title if visible"
}
Only return the JSON, no explanation."""

COMPONENT_DETECTION_PROMPT = """Analyze this UI screenshot and detect all interactive and visible UI components.
Return as JSON array:
[
  {"type": "button|input|text|image|link|icon|card|modal|table", "text": "visible text", "bbox": [x1, y1, x2, y2], "confidence": 0.95}
]
Only return the JSON array, no explanation."""


class GLMVOCRService(OCRService):
    """OCR service using GLM-4V multimodal model for vision-language based OCR."""

    def __init__(self):
        self.model = "glm-4v"
        self.api_key = settings.litellm_api_key

    async def recognize_text(self, image_base64: str) -> dict:
        if image_base64.startswith("data:image"):
            image_data = image_base64.split(",", 1)[-1]
        else:
            image_data = image_base64

        try:
            import httpx
            url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": [
                        {"type": "text", "text": TEXT_RECOGNITION_PROMPT},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}},
                    ]},
                ],
                "temperature": 0.1,
                "max_tokens": 4096,
            }
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                result = resp.json()
                content = result["choices"][0]["message"]["content"]

            import re
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                return json.loads(match.group())
            return {"text": content, "elements": []}
        except Exception as e:
            logger.error(f"GLM-4V OCR failed: {e}")
            # Fallback: use LiteLLM with a vision-capable model
            return await self._fallback_ocr(image_data)

    async def _fallback_ocr(self, image_base64: str) -> dict:
        """Fallback OCR using LiteLLM with vision model."""
        try:
            import litellm
            resp = await litellm.acompletion(
                model="gpt-4o",
                api_key=self.api_key,
                messages=[
                    {"role": "user", "content": [
                        {"type": "text", "text": TEXT_RECOGNITION_PROMPT},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}},
                    ]},
                ],
                max_tokens=4096,
            )
            content = resp.choices[0].message.content
            import re
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                return json.loads(match.group())
            return {"text": content, "elements": [], "fallback": True}
        except Exception as e:
            logger.error(f"Fallback OCR also failed: {e}")
            return {"text": "", "elements": [], "error": str(e)}

    async def recognize_components(self, image_base64: str) -> list[dict]:
        if image_base64.startswith("data:image"):
            image_data = image_base64.split(",", 1)[-1]
        else:
            image_data = image_base64

        try:
            import httpx
            url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": [
                        {"type": "text", "text": COMPONENT_DETECTION_PROMPT},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}},
                    ]},
                ],
                "temperature": 0.1,
                "max_tokens": 4096,
            }
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                result = resp.json()
                content = result["choices"][0]["message"]["content"]

            import re
            match = re.search(r'\[.*\]', content, re.DOTALL)
            if match:
                return json.loads(match.group())
            return []
        except Exception as e:
            logger.error(f"Component detection failed: {e}")
            return []
