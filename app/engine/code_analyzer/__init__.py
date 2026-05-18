"""Framework-agnostic project code analyzer.

Scans any project directory (Vue/React/Uniapp/Express/FastAPI/etc.),
extracts routes, page elements, API endpoints, and documentation.
Output is fed to LLM for business structure extraction.

No AST parsing — pure file scanning + regex. Works with ANY framework.
"""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.lib.logger import get_logger

logger = get_logger(__name__)

# Files/directories to skip
SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "dist", "build", ".next", ".nuxt"}
SKIP_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".woff", ".woff2", ".ttf", ".eot", ".map"}


@dataclass
class RouteInfo:
    path: str
    file: str = ""
    component: str = ""
    method: str = "GET"


@dataclass
class PageElement:
    tag: str = ""
    text: str = ""
    placeholder: str = ""
    selector_hint: str = ""


@dataclass
class PageInfo:
    route: str
    file: str
    elements: list[PageElement] = field(default_factory=list)


@dataclass
class ApiInfo:
    method: str
    path: str
    file: str = ""


@dataclass
class DocInfo:
    title: str
    content: str
    file: str = ""


@dataclass
class ProjectInfo:
    framework: str  # vue | react | uniapp | nuxt | next | express | fastapi | unknown
    routes: list[RouteInfo] = field(default_factory=list)
    pages: list[PageInfo] = field(default_factory=list)
    apis: list[ApiInfo] = field(default_factory=list)
    docs: list[DocInfo] = field(default_factory=list)
    project_path: str = ""


# ── Framework detection ─────────────────────────────────────────────

FRAMEWORK_SIGNATURES = [
    ("vue", "vue-router"),
    ("react", "react-router"),
    ("react", "react-router-dom"),
    ("uniapp", "@dcloudio/uni-app"),
    ("uniapp", "uni-app"),
    ("nuxt", "nuxt"),
    ("next", "next"),
    ("fastapi", "fastapi"),
    ("express", "express"),
]


def detect_framework(pkg: dict) -> str:
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    for fw, sig in FRAMEWORK_SIGNATURES:
        if sig in deps:
            return fw
    # Check for uniapp by pages.json
    return "unknown"


# ── Route extraction ────────────────────────────────────────────────

def extract_routes_from_vue_router(content: str) -> list[RouteInfo]:
    routes = []
    # Match vue-router3 patterns: { path: '/login', component: Login }
    # Also match vue-router4 patterns with dynamic import
    for m in re.finditer(r"path\s*:\s*['\"]([^'\"]+)['\"][^}]*?(?:import\(['\"]?([^'\"\)]+)['\"]?\)|component\s*:\s*(\w+))", content):
        path = m.group(1)
        component = m.group(2) or m.group(3) or ""
        routes.append(RouteInfo(path=path, component=component))
    # Fallback: path-only matching for simpler configs
    if not routes:
        for m in re.finditer(r"path\s*:\s*['\"]([^'\"]+)['\"]", content):
            routes.append(RouteInfo(path=m.group(1)))
    return routes


def extract_routes_from_react(content: str) -> list[RouteInfo]:
    routes = []
    # Match <Route path="/login" ...>
    for m in re.finditer(r"path=['\"](\/[^'\"]*)['\"]", content):
        routes.append(RouteInfo(path=m.group(1)))
    return routes


def extract_routes_from_uniapp(content: str) -> list[RouteInfo]:
    routes = []
    try:
        data = json.loads(content)
        for page in data.get("pages", []):
            p = page.get("path", "")
            if p:
                routes.append(RouteInfo(path="/" + p))
    except json.JSONDecodeError:
        pass
    return routes


def extract_routes_from_express(content: str) -> list[RouteInfo]:
    routes = []
    for m in re.finditer(r"(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]+)['\"]", content):
        routes.append(RouteInfo(path=m.group(2), method=m.group(1).upper()))
    return routes


def extract_routes_from_fastapi(content: str) -> list[RouteInfo]:
    routes = []
    for m in re.finditer(r"@\w+\.(?:router|app)\.(?:get|post|put|delete|patch)\s*\([\s\S]*?['\"]([^'\"]+)['\"]", content):
        routes.append(RouteInfo(path=m.group(1)))
    return routes


# ── Page element extraction ─────────────────────────────────────────

def extract_html_elements(content: str) -> list[PageElement]:
    elements = []
    # Inputs
    for m in re.finditer(r"<(input|textarea|select)([^>]*)>", content):
        attrs = m.group(2)
        el = PageElement(tag=m.group(1))
        ph = re.search(r'placeholder\s*=\s*["\']([^"\']*)["\']', attrs)
        if ph:
            el.placeholder = ph.group(1)
        type_m = re.search(r'type\s*=\s*["\']([^"\']*)["\']', attrs)
        if type_m and type_m.group(1) in ("submit", "button"):
            el.tag = "button"
            el.text = el.placeholder or ""
        elements.append(el)
    # Buttons
    for m in re.finditer(r"<(button|el-button|a-button)([^>]*)>([^<]+)</\1>", content):
        elements.append(PageElement(tag="button", text=m.group(3).strip()))
    # Element Plus / Ant Design buttons
    for m in re.finditer(r"<(el-button|a-button)([^>]*)>([^<]+)</\1>", content):
        elements.append(PageElement(tag="button", text=m.group(3).strip()))
    return elements


# ── File scanning ───────────────────────────────────────────────────

def find_route_files(project_path: Path, framework: str) -> list[Path]:
    patterns = []
    if framework in ("vue", "unknown"):
        patterns.extend(["**/router/**/*.ts", "**/router/**/*.js", "**/router/index.ts", "**/router/index.js",
                         "**/router.ts", "**/router.js"])
    if framework in ("react", "unknown"):
        patterns.extend(["**/routes/**/*.tsx", "**/routes/**/*.jsx", "**/App.tsx", "**/App.jsx"])
    if framework == "uniapp":
        patterns.append("pages.json")
    if framework in ("express",):
        patterns.extend(["**/routes/**/*.js", "**/routes/**/*.ts", "**/*.route.*"])
    if framework in ("fastapi",):
        patterns.extend(["**/routes/**/*.py", "**/api/**/*.py"])

    files = []
    for pat in patterns:
        for f in project_path.glob(pat):
            if not any(skip in str(f) for skip in SKIP_DIRS):
                files.append(f)
    return files[:20]  # limit


def find_page_files(project_path: Path) -> list[Path]:
    exts = ("*.vue", "*.tsx", "*.jsx")
    dirs = ("src/views", "src/pages", "pages", "views", "components",
            "web/src/views", "web/src/pages", "web/src/components")
    files = []
    for d in dirs:
        for ext in exts:
            for f in (project_path / d).glob(f"**/{ext}"):
                if not any(skip in str(f) for skip in SKIP_DIRS):
                    files.append(f)
    return files[:50]


def find_api_files(project_path: Path) -> list[Path]:
    dirs = ("src/api", "src/services", "api", "services")
    exts = ("*.ts", "*.js", "*.py")
    files = []
    for d in dirs:
        for ext in exts:
            for f in (project_path / d).glob(f"**/{ext}"):
                if not any(skip in str(f) for skip in SKIP_DIRS):
                    files.append(f)
    return files[:20]


def find_doc_files(project_path: Path) -> list[Path]:
    files = []
    for f in project_path.rglob("*.md"):
        if not any(skip in str(f) for skip in SKIP_DIRS):
            files.append(f)
    return files[:10]


# ── Main scanner ────────────────────────────────────────────────────

def scan_project(project_path: str) -> ProjectInfo:
    """Scan a project directory and extract all structural information."""
    path = Path(project_path).resolve()
    if not path.exists():
        logger.error("Project path does not exist: %s", project_path)
        return ProjectInfo(framework="unknown", project_path=project_path)

    # Detect framework - check root and common subdirectories
    pkg = {}
    for pkg_path in [path / "package.json", path / "web" / "package.json",
                     path / "frontend" / "package.json", path / "client" / "package.json"]:
        if pkg_path.exists():
            try:
                pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
                if detect_framework(pkg) != "unknown":
                    break
            except (json.JSONDecodeError, OSError):
                pass
    framework = detect_framework(pkg)

    info = ProjectInfo(framework=framework, project_path=str(path))
    logger.info("Detected framework: %s for %s", framework, project_path)

    # Extract routes
    for rf in find_route_files(path, framework):
        try:
            content = rf.read_text(encoding="utf-8", errors="ignore")
            if framework in ("vue", "nuxt"):
                info.routes.extend(extract_routes_from_vue_router(content))
            elif framework in ("react", "next"):
                info.routes.extend(extract_routes_from_react(content))
            elif framework == "uniapp":
                info.routes.extend(extract_routes_from_uniapp(content))
            elif framework == "express":
                info.routes.extend(extract_routes_from_express(content))
            elif framework == "fastapi":
                info.routes.extend(extract_routes_from_fastapi(content))
            else:
                # Try all parsers
                info.routes.extend(extract_routes_from_vue_router(content))
                info.routes.extend(extract_routes_from_react(content))
        except OSError:
            continue

    # Extract page elements
    for pf in find_page_files(path):
        try:
            content = pf.read_text(encoding="utf-8", errors="ignore")
            elements = extract_html_elements(content)
            rel_path = str(pf.relative_to(path))
            info.pages.append(PageInfo(
                route="",
                file=rel_path,
                elements=elements,
            ))
        except (OSError, ValueError):
            continue

    # Extract APIs
    for af in find_api_files(path):
        try:
            content = af.read_text(encoding="utf-8", errors="ignore")
            if framework == "fastapi":
                for r in extract_routes_from_fastapi(content):
                    info.apis.append(ApiInfo(method=r.method, path=r.path, file=str(af)))
            else:
                for r in extract_routes_from_express(content):
                    info.apis.append(ApiInfo(method=r.method, path=r.path, file=str(af)))
        except OSError:
            continue

    # Extract docs
    for df in find_doc_files(path):
        try:
            content = df.read_text(encoding="utf-8", errors="ignore")[:5000]
            info.docs.append(DocInfo(
                title=df.stem,
                content=content,
                file=str(df.relative_to(path)),
            ))
        except (OSError, ValueError):
            continue

    logger.info("Scanned %s: %d routes, %d pages, %d APIs, %d docs",
                project_path, len(info.routes), len(info.pages), len(info.apis), len(info.docs))
    return info


def build_llm_prompt(info: ProjectInfo, extra_context: str = "") -> str:
    """Build the LLM prompt for business structure extraction from project scan results."""
    parts = [f"项目路径: {info.project_path}", f"检测框架: {info.framework}", ""]

    if info.routes:
        parts.append("## 路由")
        for r in info.routes:
            parts.append(f"  [{r.method}] {r.path}")
        parts.append("")

    if info.pages:
        parts.append("## 页面与组件")
        for p in info.pages[:20]:
            el_text = "; ".join(f"<{e.tag}> '{e.text or e.placeholder}'" for e in p.elements[:5])
            parts.append(f"  {p.file}: {el_text}")
        parts.append("")

    if info.apis:
        parts.append("## API 端点")
        for a in info.apis[:20]:
            parts.append(f"  [{a.method}] {a.path}")
        parts.append("")

    if info.docs:
        parts.append("## 文档")
        for d in info.docs:
            parts.append(f"--- {d.title} ---")
            parts.append(d.content[:2000])
        parts.append("")

    if extra_context:
        parts.append("## 用户补充")
        parts.append(extra_context)
        parts.append("")

    prompt = """你是一个资深测试架构师。基于以下项目分析信息，提取完整的测试业务体系。

要求：
1. 识别所有业务线（business_line）：系统有哪些大的业务领域
2. 每个业务线下识别功能线（function）：该功能的核心操作
3. 每个功能线下识别流程线（flow）：具体操作步骤（3-8步）
4. 识别系统中所有角色（roles）

输出严格的 JSON 格式：
{
  "business_lines": [
    {
      "name": "业务线名称",
      "functions": [
        {
          "name": "功能名称",
          "flows": [
            {
              "name": "流程名称",
              "steps": [
                {"action": "具体操作", "target": "目标元素", "page": "页面路由", "expected": "预期结果"}
              ]
            }
          ]
        }
      ]
    }
  ],
  "roles": ["角色1", "角色2"]
}

项目信息：
"""
    prompt += "\n".join(parts)
    return prompt


async def extract_business_structure(project_path: str, llm_service=None, extra_context: str = "") -> dict:
    """Full pipeline: scan project → build prompt → call LLM → return structured business info."""
    from app.lib.logger import get_logger
    log = get_logger(__name__)

    info = scan_project(project_path)
    prompt = build_llm_prompt(info, extra_context)

    if llm_service:
        try:
            result = await llm_service.extract_rules(prompt, "structured")
            log.info("LLM business extraction completed for %s", project_path)
            return result if isinstance(result, dict) else {"business_lines": [], "roles": []}
        except Exception as e:
            log.error("LLM extraction failed: %s", e)

    # Fallback: return project structure as-is
    return {
        "business_lines": [],
        "roles": ["管理员", "普通用户"],
        "routes": [{"path": r.path, "method": r.method} for r in info.routes],
        "_fallback": True,
    }
