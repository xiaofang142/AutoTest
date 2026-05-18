"""Enhanced OCR service with image preprocessing, layout analysis, and DOM-OCR alignment.

三层增强:
  1. 图片预处理: 去噪/增强对比度/纠偏 → 提升 OCR 识别率
  2. 布局区域检测: 识别 header/main/sidebar/footer/modal
  3. DOM-OCR 坐标映射: 把 OCR 文本块和 DOM 元素通过坐标匹配
"""
import base64
from io import BytesIO
from typing import Optional

import cv2
import numpy as np
from PIL import Image

from app.interfaces.ocr_service import OCRService
from app.lib.logger import get_logger

logger = get_logger(__name__)


class EnhancedOCRService:
    """Wraps an OCR service with preprocessing and layout analysis."""

    def __init__(self, base_ocr: OCRService):
        self._ocr = base_ocr
        self._last_result = None

    # ── Stage 1: 图片预处理 ──────────────────────────────────────────────

    @staticmethod
    def preprocess(image_base64: str) -> str:
        """Apply image enhancement pipeline before OCR."""
        img = _decode_image(image_base64)
        if img is None:
            return image_base64

        original = img.copy()
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 1.1 自适应二值化（处理光照不均）
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 31, 2)

        # 1.2 去噪（中值滤波）
        denoised = cv2.medianBlur(binary, 3)

        # 1.3 对比度增强
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        enhanced_color = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)

        # 1.4 纠偏（检测文本旋转角度）
        coords = np.column_stack(np.where(denoised > 0))
        if len(coords) > 100:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = 90 + angle
            if abs(angle) > 2:
                h, w = img.shape[:2]
                center = (w // 2, h // 2)
                matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
                enhanced_color = cv2.warpAffine(enhanced_color, matrix, (w, h),
                                                flags=cv2.INTER_CUBIC,
                                                borderMode=cv2.BORDER_REPLICATE)

        return _encode_image(enhanced_color)

    # ── Stage 2: 布局区域分析 ────────────────────────────────────────────

    @staticmethod
    def analyze_layout(image_base64: str, ocr_elements: list[dict],
                       viewport: Optional[dict] = None) -> list[dict]:
        """Classify OCR elements into layout regions.

        Returns elements with added 'region' field:
          header / main / sidebar / footer / modal / dialog / unknown
        """
        img = _decode_image(image_base64)
        if img is None or not ocr_elements:
            return ocr_elements

        h, w = img.shape[:2]
        if viewport:
            w, h = viewport.get("width", w), viewport.get("height", h)

        # Find bounding boxes for each region
        top_strip = h * 0.12  # top 12% = header
        bottom_strip = h * 0.88  # bottom 12% = footer
        left_strip = w * 0.2  # left 20% = possible sidebar

        enriched = []
        for el in ocr_elements:
            bbox = el.get("bbox", [0, 0, 0, 0])
            cx = (bbox[0] + bbox[2]) / 2
            cy = (bbox[1] + bbox[3]) / 2

            # Detect modal/dialog (centered, large, overlapping)
            el_w = bbox[2] - bbox[0]
            el_h = bbox[3] - bbox[1]
            is_centered = abs(cx - w / 2) < w * 0.15
            is_large = el_w > w * 0.4 and el_h > h * 0.3

            if is_large and is_centered and el_h > h * 0.2:
                region = "modal"
            elif cy < top_strip:
                region = "header"
            elif cy > bottom_strip:
                region = "footer"
            elif cx < left_strip and el_h > h * 0.3:
                region = "sidebar"
            else:
                region = "main"

            el["region"] = region
            el["position"] = {"x": cx, "y": cy, "width": el_w, "height": el_h}
            enriched.append(el)

        return enriched

    # ── Stage 3: DOM-OCR 坐标对齐 ────────────────────────────────────────

    @staticmethod
    def align_to_dom(ocr_elements: list[dict],
                     dom_elements: list[dict],
                     threshold: float = 0.6) -> list[dict]:
        """Match OCR text blocks to DOM elements by coordinate proximity.

        dom_elements: [{"text": "...", "x": 100, "y": 200, "w": 80, "h": 30}, ...]
        Returns OCR elements with matched 'dom_ref' field.
        """
        if not dom_elements:
            return ocr_elements

        for ocr_el in ocr_elements:
            ob = ocr_el.get("bbox", [0, 0, 0, 0])
            ocx = (ob[0] + ob[2]) / 2
            ocy = (ob[1] + ob[3]) / 2
            ow = ob[2] - ob[0]
            oh = ob[3] - ob[1]

            best_score = 0
            best_match = None
            for dom_el in dom_elements:
                dx = dom_el.get("x", 0) + dom_el.get("w", 0) / 2
                dy = dom_el.get("y", 0) + dom_el.get("h", 0) / 2
                dw = dom_el.get("w", 1)
                dh = dom_el.get("h", 1)

                # Intersection over Union of bounding boxes
                ix = max(ob[0], dom_el.get("x", 0))
                iy = max(ob[1], dom_el.get("y", 0))
                ix2 = min(ob[2], dom_el.get("x", 0) + dw)
                iy2 = min(ob[3], dom_el.get("y", 0) + dh)
                iw = max(0, ix2 - ix)
                ih = max(0, iy2 - iy)
                intersection = iw * ih
                union = ow * oh + dw * dh - intersection
                iou = intersection / union if union > 0 else 0

                # Text similarity bonus
                text_score = 0
                ocr_text = ocr_el.get("text", "").lower()
                dom_text = dom_el.get("text", "").lower()
                if ocr_text and dom_text:
                    common = len(set(ocr_text) & set(dom_text))
                    text_score = common / max(len(ocr_text), len(dom_text))

                score = iou * 0.6 + text_score * 0.4
                if score > best_score:
                    best_score = score
                    best_match = dom_el

            if best_score >= threshold and best_match:
                ocr_el["dom_ref"] = {
                    "text": best_match.get("text", ""),
                    "tag": best_match.get("tag", ""),
                    "selector": best_match.get("selector", ""),
                    "score": round(best_score, 3),
                }
            else:
                ocr_el["dom_ref"] = None

        return ocr_elements

    # ── 一站式 OCR 分析 ──────────────────────────────────────────────────

    async def full_analyze(self, image_base64: str,
                           dom_elements: Optional[list[dict]] = None,
                           viewport: Optional[dict] = None) -> dict:
        """Run full OCR pipeline: preprocess → recognize → layout → align."""
        # Step 1: Preprocess
        processed = self.preprocess(image_base64)

        # Step 2: OCR recognition
        ocr_result = await self._ocr.recognize_text(processed)
        elements = ocr_result.get("elements", [])

        # Step 3: Component recognition
        components = []
        try:
            components = await self._ocr.recognize_components(processed)
        except Exception:
            pass

        # Step 4: Layout analysis
        elements = self.analyze_layout(processed, elements, viewport)
        components = self.analyze_layout(processed, components, viewport)

        # Step 5: DOM alignment
        if dom_elements:
            elements = self.align_to_dom(elements, dom_elements)

        return {
            "text": ocr_result.get("text", ""),
            "elements": elements,
            "components": components,
            "engine": ocr_result.get("engine", "unknown"),
            "preprocessed": True,
            "layout_analyzed": True,
        }


def _decode_image(image_base64: str) -> Optional[np.ndarray]:
    try:
        data = image_base64.split(",", 1)[-1] if image_base64.startswith("data:") else image_base64
        return cv2.imdecode(np.frombuffer(base64.b64decode(data), np.uint8), cv2.IMREAD_COLOR)
    except Exception as e:
        logger.debug("Image decode failed: %s", e)
        return None


def _encode_image(img: np.ndarray) -> str:
    _, buffer = cv2.imencode(".png", img)
    return base64.b64encode(buffer).decode()
