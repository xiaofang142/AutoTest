from abc import ABC, abstractmethod


class OCRService(ABC):
    @abstractmethod
    async def recognize_text(self, image_base64: str) -> dict:
        """Extract text from image. Returns: {"text": "...", "confidence": 0.95, "elements": [{"text": "...", "bbox": [x1,y1,x2,y2]}]}"""
        ...

    @abstractmethod
    async def recognize_components(self, image_base64: str) -> list[dict]:
        """Detect UI components. Returns: [{"type": "button|input|label", "text": "...", "bbox": [x1,y1,x2,y2], "confidence": 0.95}]"""
        ...
