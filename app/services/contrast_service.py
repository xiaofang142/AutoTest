from dataclasses import dataclass, field
from typing import Optional
import re
from app.domain.models.knowledge import BusinessRule
from app.domain.models.discovery import PageDiscoveryResult, DiscoveredElement
from app.lib.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ContrastItem:
    rule_id: str = ""
    rule_content: str = ""
    dimension: str = ""  # flow/permission/ui/data
    status: str = ""     # matched/missing/extra/conflict
    page_element_text: str = ""
    detail: str = ""


@dataclass
class ContrastReport:
    matched: list[ContrastItem] = field(default_factory=list)
    missing: list[ContrastItem] = field(default_factory=list)
    extra: list[ContrastItem] = field(default_factory=list)
    conflict: list[ContrastItem] = field(default_factory=list)

    @property
    def coverage_rate(self) -> float:
        total = len(self.matched) + len(self.missing)
        return len(self.matched) / total if total > 0 else 0.0


class ContrastService:
    """Contrast verification between document rules and discovered page elements.
    Matching strategy: keyword-based substring matching (non-AI)."""

    def contrast(self, rules: list[BusinessRule], page: PageDiscoveryResult) -> ContrastReport:
        report = ContrastReport()
        page_texts = set()
        page_text_to_elem = {}
        for e in page.elements:
            t = e.text.lower().strip()
            if t:
                page_texts.add(t)
                page_text_to_elem[t] = e

        for rule in rules:
            keywords = self._extract_keywords(rule.content)
            found_keywords = [kw for kw in keywords if any(kw in pt or pt in kw for pt in page_texts)]
            item = ContrastItem(
                rule_id=rule.id,
                rule_content=rule.content[:100],
                dimension=rule.category,
            )
            if found_keywords:
                item.status = "matched"
                item.page_element_text = found_keywords[0]
                item.detail = f"Matched keywords: {', '.join(found_keywords[:3])}"
                report.matched.append(item)
            else:
                item.status = "missing"
                item.detail = f"Document keywords not found on page: {', '.join(keywords[:5])}"
                report.missing.append(item)

        # Detect extra: page elements that don't match any rule
        all_rule_keywords = set()
        for rule in rules:
            all_rule_keywords.update(self._extract_keywords(rule.content))
        for pt, elem in page_text_to_elem.items():
            if not any(kw in pt or pt in kw for kw in all_rule_keywords):
                if elem.type in ('button', 'link', 'nav-item', 'input', 'select'):
                    report.extra.append(ContrastItem(
                        status="extra", page_element_text=pt,
                        dimension="ui",
                        detail=f"Element exists on page but not defined in document: [{elem.type}] {pt[:60]}"
                    ))

        return report

    def _extract_keywords(self, text: str) -> list[str]:
        words = re.split(r'[\s,，。.；;:：()（）【】\[\]{}]', text)
        return list(set(w.strip().lower() for w in words if len(w.strip()) >= 2))[:10]
