import pytest
from app.services.code_analysis_service import CodeAnalysisService
from app.domain.models.task import UnderstandingResult, TestBlueprint, TaskInput


class TestCodeAnalysisService:
    @pytest.mark.asyncio
    async def test_missing_dir_returns_error(self):
        result = await CodeAnalysisService.analyze_codebase("/nonexistent/path")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_empty_dir_returns_error(self):
        result = await CodeAnalysisService.analyze_codebase("")
        assert "error" in result

    def test_enhance_understanding_empty(self):
        understanding = UnderstandingResult(completeness=0.6)
        result = CodeAnalysisService.enhance_understanding({}, understanding)
        assert result.completeness == 0.6

    def test_enhance_understanding_with_error(self):
        understanding = UnderstandingResult(completeness=0.5)
        result = CodeAnalysisService.enhance_understanding({"error": "fail"}, understanding)
        assert result.completeness == 0.5

    def test_enhance_understanding_adds_flows(self):
        understanding = UnderstandingResult(completeness=0.5)
        code_info = {"routes": [{"path": "/login", "file": "pages/Login.vue"}],
                     "apis": [{"method": "POST", "path": "/api/login"}]}
        result = CodeAnalysisService.enhance_understanding(code_info, understanding)
        assert result.completeness == 0.7
        assert len(result.key_flows) > 0
        assert len(result.risk_points) > 0

    def test_generate_blueprint_steps_empty(self):
        steps = CodeAnalysisService.generate_blueprint_steps({}, "https://x.com")
        assert steps == []

    def test_generate_blueprint_steps_with_error(self):
        steps = CodeAnalysisService.generate_blueprint_steps({"error": "fail"}, "https://x.com")
        assert steps == []
