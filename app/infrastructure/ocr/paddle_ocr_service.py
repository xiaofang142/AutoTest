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
            logger.warning("PaddleOCR init failed: %s", e)

    @property
    def available(self) -> bool:
        return self._available

    async def recognize_text(self, image_base64: str) -> dict:
        if not self._available or self._ocr is None:
            logger.debug("PaddleOCR unavailable")
            return {"text": "", "elements": [], "engine": "unavailable"}

        import base64

        import cv2
        import numpy as np
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
            logger.error("PaddleOCR failed: %s", e)
            return {"text": "", "elements": [], "error": str(e)}

    async def recognize_components(self, image_base64: str) -> list[dict]:
        """Detect UI components from screenshot using OCR text + position heuristics.

        Uses PaddleOCR text detection results and infers component type
        from text content and bounding box position/size.
        """
        ocr_data = await self.recognize_text(image_base64)
        elements = ocr_data.get("elements", [])
        if not elements:
            return []

        img_h = max(e["bbox"][3] for e in elements) if elements else 768
        img_w = max(e["bbox"][2] for e in elements) if elements else 1024

        components: list[dict] = []
        button_keywords = ["提交", "确认", "取消", "登录", "注册", "保存", "删除", "编辑",
                           "新增", "查询", "搜索", "返回", "下一步", "完成", "确定",
                           "submit", "confirm", "login", "save", "delete", "search",
                           "cancel", "ok", "yes", "next", "done"]

        for el in elements:
            text = el.get("text", "").strip()
            bbox = el.get("bbox", [0, 0, 0, 0])
            conf = el.get("confidence", 0.5)
            x1, y1, x2, y2 = bbox
            w, h = x2 - x1, y2 - y1
            area_ratio = (w * h) / (img_w * img_h) if img_w * img_h > 0 else 0

            inferred_type = "text"
            # Large block → likely section heading
            if area_ratio > 0.15:
                inferred_type = "heading"
            # Short text in button-like keyword → button
            elif any(kw in text for kw in button_keywords):
                inferred_type = "button"
            # Input-placeholder-like text
            elif any(kw in text for kw in ["请输入", "请选择", "输入", "搜索", "placeholder",
                                            "please enter", "select", "search"]):
                inferred_type = "input"
            # Centered text in large area → link or nav
            elif w > img_w * 0.3 and h < img_h * 0.05:
                inferred_type = "nav_link"

            components.append({
                "type": inferred_type,
                "text": text,
                "bbox": bbox,
                "confidence": round(conf, 3),
            })

        return components
