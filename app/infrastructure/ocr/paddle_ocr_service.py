"""Local PaddleOCR service for zero-token text extraction from screenshots."""
import base64, json, re, os, tempfile
from typing import Optional
from app.interfaces.ocr_service import OCRService
from app.lib.logger import get_logger

logger = get_logger(__name__)


class PaddleOCRService(OCRService):
    """Local PaddleOCR - zero token cost for text extraction.
    
    Falls back to GLM-4V if PaddleOCR is not installed.
    """

    def __init__(self):
        self._ocr = None
        self._available = False
        self._init_ocr()

    def _init_ocr(self):
        try:
            from paddleocr import PaddleOCR
            self._ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
            self._available = True
            logger.info("PaddleOCR initialized - local OCR available")
        except ImportError:
            logger.warning("PaddleOCR not installed, will use GLM-4V fallback")
        except Exception as e:
            logger.warning(f"PaddleOCR init failed: {e}")

    @property
    def available(self) -> bool:
        return self._available

    async def recognize_text(self, image_base64: str) -> dict:
        if image_base64.startswith("data:image"):
            image_data = image_base64.split(",", 1)[-1]
        else:
            image_data = image_base64

        if not self._available:
            return await self._fallback_ocr(image_data)

        try:
            import cv2
            import numpy as np

            img_bytes = base64.b64decode(image_data)
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            result = self._ocr.ocr(img, cls=True)
            elements = []
            full_text = []
            for line in result[0] if result and result[0] else []:
                bbox, (text, confidence) = line
                elements.append({
                    "text": text,
                    "confidence": round(confidence, 3),
                    "bbox": [int(bbox[0][0]), int(bbox[0][1]), int(bbox[2][0]), int(bbox[2][1])],
                })
                full_text.append(text)

            logger.info(f"PaddleOCR: {len(elements)} elements, confidence={sum(e['confidence'] for e in elements)/max(len(elements),1):.2f}")
            return {
                "text": "\n".join(full_text),
                "elements": elements,
                "engine": "paddleocr",
            }
        except Exception as e:
            logger.error(f"PaddleOCR failed: {e}")
            return await self._fallback_ocr(image_data)

    async def recognize_components(self, image_base64: str) -> list[dict]:
        text_result = await self.recognize_text(image_base64)
        elements = text_result.get("elements", [])
        components = []
        for e in elements[:30]:
            components.append({
                "type": "text",
                "text": e["text"],
                "bbox": e["bbox"],
                "confidence": e["confidence"],
            })
        return components

    async def _fallback_ocr(self, image_data: str) -> dict:
        logger.info("Falling back to GLM-4V OCR")
        try:
            from app.infrastructure.ocr.glm_ocr_service import GLMVOCRService
            glm = GLMVOCRService()
            return await glm.recognize_text(image_data)
        except Exception as e:
            logger.error(f"Fallback OCR failed: {e}")
            return {"text": "", "elements": [], "error": str(e), "engine": "fallback_failed"}
