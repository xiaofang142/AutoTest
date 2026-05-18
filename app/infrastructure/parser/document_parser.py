"""Multi-stage document parser with chunking, classification, and flow extraction."""
import json
import re

from app.lib.logger import get_logger

logger = get_logger(__name__)

STAGE2_PROMPTS = {
    "flow": """Extract complete business flows from this section.
Output JSON: {"flows": [{"name":"...","steps":[{"step":1,"action":"...","page":"...","expected":"..."}],"roles":["..."]}]}""",
    "permission": """Extract role-permission rules.
Output JSON: {"permissions":[{"role":"...","resource":"...","action":"create|read|update|delete","allowed":true}]}""",
    "ui": """Extract UI component specs.
Output JSON: {"components":[{"type":"button|input|table|card","text":"...","properties":{}}]}""",
    "api": """Extract API endpoint specs.
Output JSON: {"endpoints":[{"method":"GET|POST","path":"...","params":[],"responses":{}}]}""",
}

CLASSIFY_KEYWORDS = {
    "flow": ["流程","步骤","操作","导航","跳转","点击","输入","flow","step","navigate"],
    "permission": ["权限","角色","admin","user","role","permission","访问","auth"],
    "ui": ["ui","界面","样式","颜色","字体","按钮","组件","布局","component","style","color"],
    "api": ["api","接口","endpoint","请求","响应","http","/api","rest"],
}


class DocumentParser:
    def __init__(self, ai_service=None):
        self._ai = ai_service

    async def parse(self, raw_markdown: str) -> dict:
        raw_markdown = raw_markdown[:50000]
        chapters = self._chunk_by_headings(raw_markdown) or self._fallback_chunk(raw_markdown)
        chapters = await self._classify(chapters)
        extracted = {}
        for ct in ["flow", "permission", "ui", "api"]:
            ct_chapters = [c for c in chapters if c.get("type") == ct]
            if ct_chapters:
                extracted[ct] = await self._extract_type(ct, ct_chapters)
        return {"chapters": chapters, "extracted": extracted, "chapter_count": len(chapters)}

    def _chunk_by_headings(self, md: str) -> list[dict]:
        matches = list(re.finditer(r'^(#{1,6})\s+(.+)$', md, re.MULTILINE))
        if len(matches) < 2:
            return []
        chapters = []
        for i, m in enumerate(matches):
            end = matches[i+1].start() if i+1 < len(matches) else len(md)
            chapters.append({
                "heading": m.group(2).strip(),
                "level": len(m.group(1)),
                "content": md[m.end():end].strip()[:3000],
            })
        return chapters

    def _fallback_chunk(self, md: str) -> list[dict]:
        return [{"heading": f"Section {i+1}", "level": 1, "content": p.strip()[:2000]}
                for i, p in enumerate(md.split("\n\n")[:20]) if p.strip()]

    async def _classify(self, chapters: list[dict]) -> list[dict]:
        if self._ai:
            try:
                text = json.dumps([{"h":c["heading"], "p":c["content"][:150]} for c in chapters])
                result = await self._ai.extract_rules(f"Classify by type:\n{text}", "general")
                types = result.get("rules", [])
                for i, c in enumerate(chapters):
                    c["type"] = types[i].get("category", self._kw_classify(c)) if i < len(types) else self._kw_classify(c)
                return chapters
            except Exception:
                pass
        for c in chapters:
            c["type"] = self._kw_classify(c)
        return chapters

    def _kw_classify(self, c: dict) -> str:
        t = (c.get("heading","") + " " + c.get("content","")).lower()
        for ct, kws in CLASSIFY_KEYWORDS.items():
            if any(k in t for k in kws):
                return ct
        return "other"

    async def _extract_type(self, ctype: str, chapters: list[dict]) -> list[dict]:
        if not self._ai:
            return []
        combined = "\n\n".join(f"## {c['heading']}\n{c['content']}" for c in chapters)
        try:
            result = await self._ai.extract_rules(
                f"{STAGE2_PROMPTS[ctype]}\n\n{combined[:6000]}", "structured")
            return result.get(ctype + ("s" if ctype in ("flow","endpoint") else ""), [])
        except Exception as e:
            logger.error("Extract %s failed: %s", ctype, e)
            return []
