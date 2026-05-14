"""PaddleOCR service - gracefully handles missing paddlepaddle dependency."""
from app.interfaces.ocr_service import OCRService
from app.lib.logger import get_logger

logger = get_logger(__name__)


class PaddleOCRService(OCRService):
    def __init__(self):
        self._ocr = None
        self._available = False
        self._init_ocr()

    def _init_ocr(self):
        try:
            from paddleocr import PaddleOCR
            self._ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
            self._available = True
            logger.info("PaddleOCR ready")
        except ImportError:
            logger.info("PaddleOCR not installed - use GLM-4V or disable OCR")
        except Exception as e:
            logger.warning(f"PaddleOCR init failed: {e}")

    @property
    def available(self) -> bool:
        return self._available

    async def recognize_text(self, image_base64: str) -> dict:
        if not self._available:
            logger.debug("PaddleOCR unavailable")
            return {"text": "", "elements": [], "engine": "unavailable"}

        import base64, cv2, numpy as np
        try:
            data = image_base64.split(",", 1)[-1] if image_base64.startswith("data:") else image_base64
            img = cv2.imdecode(np.frombuffer(base64.b64decode(data), np.uint8), cv2.IMREAD_COLOR)
            result = self._ocr.ocr(img, cls=True)
            elements = []
            texts = []
            for line in (result[0] if result and result[0] else []):
                bbox, (text, conf) = line
                elements.append({"text": text, "confidence": round(conf, 3),
                                 "bbox": [int(bbox[0][0]), int(bbox[0][1]), int(bbox[2][0]), int(bbox[2][1])]})
                texts.append(text)
            return {"text": "\n".join(texts), "elements": elements, "engine": "paddleocr"}
        except Exception as e:
            logger.error(f"PaddleOCR failed: {e}")
            return {"text": "", "elements": [], "error": str(e)}

    async def recognize_components(self, image_base64: str) -> list[dict]:
        return []
