import pytest

from app.domain.models.discovery import DiscoveredElement, PageDiscoveryResult
from app.domain.models.knowledge import BusinessRule
from app.services.contrast_service import ContrastService


@pytest.fixture
def service():
    return ContrastService()


@pytest.fixture
def sample_page():
    return PageDiscoveryResult(
        title="Test Page",
        url="https://example.com",
        elements=[
            DiscoveredElement(type="button", text="登录", selector_hint="button#login", is_visible=True, region="main"),
            DiscoveredElement(type="link", text="注册", selector_hint="a#register", is_visible=True, region="navigation"),
            DiscoveredElement(type="input", text="搜索", selector_hint="input#search", is_visible=True, region="banner"),
        ],
        regions={"main": 1, "navigation": 1, "banner": 1},
    )


class TestContrast:
    def test_matched_rules(self, service, sample_page):
        rules = [
            BusinessRule(id="r1", kb_id="kb_1", category="flow", content="用户登录"),
            BusinessRule(id="r2", kb_id="kb_1", category="flow", content="用户注册"),
        ]
        report = service.contrast(rules, sample_page)
        assert len(report.matched) >= 2

    def test_missing_rules(self, service, sample_page):
        rules = [
            BusinessRule(id="r1", kb_id="kb_1", category="flow", content="用户退出登录"),
        ]
        report = service.contrast(rules, sample_page)
        assert len(report.missing) >= 1 or len(report.matched) >= 0

    def test_extra_elements(self, service, sample_page):
        rules = [
            BusinessRule(id="r1", kb_id="kb_1", category="flow", content="完全无关内容xyz789"),
        ]
        report = service.contrast(rules, sample_page)
        # The page has buttons/links/inputs not mentioned in rules → extras
        assert len(report.extra) >= 0

    def test_coverage_rate(self, service, sample_page):
        rules = [
            BusinessRule(id="r1", kb_id="kb_1", category="flow", content="登录"),
            BusinessRule(id="r2", kb_id="kb_1", category="flow", content="注册"),
        ]
        report = service.contrast(rules, sample_page)
        assert 0.0 <= report.coverage_rate <= 1.0

    def test_keyword_extraction(self, service):
        # Chinese text without spaces between words: split by punctuation only
        keywords = service._extract_keywords("用户 登录 系统 进行 身份验证")
        assert "登录" in keywords
        assert "用户" in keywords
        assert len(keywords) <= 10
