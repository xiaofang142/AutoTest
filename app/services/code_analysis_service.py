"""桥接 code_analyzer 到任务管线: 扫描源码目录→增强理解→生成更精准蓝图"""
import os
from app.engine.code_analyzer import scan_project, build_llm_prompt, ProjectInfo
from app.domain.models.task import UnderstandingResult, TestBlueprint, BlueprintStep
from app.lib.logger import get_logger

logger = get_logger(__name__)


class CodeAnalysisService:
    """分析项目源码目录, 提取路由/组件/API端点, 用于增强测试理解阶段"""

    @staticmethod
    async def analyze_codebase(code_dir: str) -> dict:
        if not code_dir:
            return {"error": "目录未指定", "routes": [], "pages": [], "apis": []}
        abs_path = os.path.abspath(os.path.expanduser(code_dir))
        if not os.path.isdir(abs_path):
            logger.warning("Code directory not found: %s", abs_path)
            return {"error": "目录不存在", "routes": [], "pages": [], "apis": []}
        try:
            info = scan_project(abs_path)
            prompt = build_llm_prompt(info)
            return {
                "framework": info.framework,
                "routes": [{"path": r.path, "file": r.file} for r in info.routes],
                "pages": [{"route": p.route, "file": p.file,
                           "elements": [{"tag": e.tag, "text": e.text[:50]}
                                       for e in p.elements[:10]]}
                         for p in info.pages[:20]],
                "apis": [{"method": a.method, "path": a.path} for a in info.apis],
                "docs": [{"file": d.file} for d in info.docs],
                "llm_prompt": prompt,
                "page_count": len(info.pages),
                "api_count": len(info.apis),
                "route_count": len(info.routes),
            }
        except Exception as e:
            logger.error("Code analysis failed: %s", e)
            return {"error": str(e), "routes": [], "pages": [], "apis": []}

    @staticmethod
    def enhance_understanding(code_info: dict, understanding: UnderstandingResult) -> UnderstandingResult:
        """用代码分析结果增强理解阶段的产出"""
        if not code_info or code_info.get("error"):
            return understanding
        key_flows = list(understanding.key_flows)
        risk_points = list(understanding.risk_points)
        routes = code_info.get("routes", [])
        apis = code_info.get("apis", [])
        pages = code_info.get("pages", [])
        if routes:
            flows = [f"路由: {r['path']} ({r.get('file','')})" for r in routes[:5]]
            key_flows.extend(flows)
        if apis:
            for a in apis[:5]:
                risk_points.append(f"API {a['method']} {a['path']}")
        if pages:
            for p in pages[:3]:
                for el in p.get("elements", [])[:3]:
                    if el.get("tag") in ("button", "input", "a"):
                        risk_points.append(f"元素 {el['tag']}={el['text']} 于 {p['route']}")
        understanding.key_flows = key_flows
        understanding.risk_points = risk_points
        understanding.completeness = min(1.0, understanding.completeness + 0.2)
        return understanding

    @staticmethod
    def generate_blueprint_steps(code_info: dict, url: str) -> list[BlueprintStep]:
        """生成测试步骤: navigate每个路由 → 点击该页面的按钮"""
        steps = []
        if not code_info or code_info.get("error"):
            return steps
        routes = code_info.get("routes", [])
        pages = code_info.get("pages", [])
        step_idx = 0

        # 构建 file_name -> page 的映射
        page_map = {}
        for p in pages:
            fname = p.get("file", "").replace("\\", "/").split("/")[-1].replace(".vue", "").lower()
            page_map[fname] = p

        # 导航到首页
        steps.append(BlueprintStep(
            index=step_idx, action="navigate", target=url,
            assert_ui=True, assert_console=True, assert_api=True,
        ))
        step_idx += 1

        # 导航到每个静态路由 + 点击该路由上页面独有的按钮
        for route_info in routes[:10]:
            path = route_info.get("path", "")
            if not path or path == "/" or ":" in path:
                continue
            full_url = url.rstrip("/") + path
            steps.append(BlueprintStep(index=step_idx, action="navigate", target=full_url, assert_ui=True))
            step_idx += 1
            # 根据路由路径匹配页面文件 (模糊匹配: 路径段 in 文件名 or 文件名 in 路径段)
            route_name = path.strip("/").split("/")[-1] if path.strip("/") else "dashboard"
            route_page = {}
            for fname, p in page_map.items():
                if route_name in fname or fname in route_name:
                    route_page = p
                    break
            for el in route_page.get("elements", [])[:2]:
                if el.get("tag") == "button" and el.get("text"):
                    steps.append(BlueprintStep(index=step_idx, action="click", target=el["text"], assert_ui=True))
                    step_idx += 1

        return steps
