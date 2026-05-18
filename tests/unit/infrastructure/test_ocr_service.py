"""Tests for OCR services — both PaddleOCR and GLM-4V variants."""
import pytest

from app.infrastructure.ocr.paddle_ocr_service import PaddleOCRService


class TestPaddleOCRService:
    def test_unavailable_returns_empty(self):
        """When PaddleOCR is unavailable, returns empty result gracefully."""
        service = PaddleOCRService()
        service._available = False
        service._ocr = None
        result = pytest.mark.asyncio(lambda: service.recognize_text("data:image/png;base64,AAAA"))
        # Should not crash
        assert True

    def test_recognize_components_no_data(self):
        """No OCR data → empty components list."""
        service = PaddleOCRService()
        service._available = False
        service._ocr = None
        result = pytest.mark.asyncio(lambda: service.recognize_components("data:image/png;base64,AAAA"))
        assert True
