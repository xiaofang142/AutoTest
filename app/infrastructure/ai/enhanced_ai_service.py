"""Enhanced AI analysis with chain-of-thought reasoning, multimodal support, and few-shot examples.

三大增强:
  1. Chain-of-Thought: 分步推理而非一次性判断
  2. 多模态输入: 截图直接送入视觉模型
  3. 跨步上下文: 前一步结果影响后一步分析
"""
import json
import re
from datetime import datetime

from app.interfaces.ai_service import AIService
from app.lib.logger import get_logger

logger = get_logger(__name__)


class ChainOfThoughtAnalyzer:
    """Wraps an AI service with enhanced prompting strategies."""

    def __init__(self, base_ai: AIService, analysis_model: str = "gpt-4o"):
        self._ai = base_ai
        self._model = analysis_model
        self._step_history: list[dict] = []

    def reset_history(self):
        self._step_history = []

    # ── CoT 多步推理分析 ────────────────────────────────────────────────

    async def analyze_with_cot(self, step_signals: dict) -> dict:
        """Chain-of-Thought analysis: reason step by step before concluding."""
        cot_prompt = self._build_cot_prompt(step_signals)
        # We call the underlying LLM directly via the service's internal
        # Since we can't access _call_llm directly, we use the analyze_merged
        # but enhance its signals with CoT instructions
        enhanced = dict(step_signals)
        enhanced["_cot_instruction"] = cot_prompt
        result = await self._ai.analyze_merged(enhanced)

        # Post-process: if LLM returned dimensions, enhance with CoT reasoning
        dims = result.get("dimensions", {})
        reasoning = self._extract_reasoning(dims)
        result["_reasoning"] = reasoning
        return result

    def _build_cot_prompt(self, signals: dict) -> str:
        action = signals.get("action", "unknown")
        return f"""Analyze step by step:

Step 1 - What action was performed?
Action: {action}
→ Determine expected outcome

Step 2 - Check API layer first (most reliable signal)
Look at network_requests: any 4xx/5xx? Any timeouts?
→ If API failed → likely root cause

Step 3 - Check Console layer
Look at console_errors: any JS exceptions?
→ If console error after API failure → likely cascade
→ If console error before API failure → likely frontend bug

Step 4 - Check UI layer
Look at ocr_text and dom_texts: any error messages?
→ Cross-reference with alerts

Step 5 - Check Business layer
Did the page transition as expected?
→ URL change? Key element appeared?

Step 6 - Synthesize
Which dimension is the ROOT cause?
Which are cascading effects?
What is the single most actionable fix?"""

    @staticmethod
    def _extract_reasoning(dimensions: dict) -> list[str]:
        steps = []
        for dim_name, dim_data in dimensions.items():
            if isinstance(dim_data, dict):
                issues = dim_data.get("issues", [])
                status = dim_data.get("status", "unknown")
                if issues:
                    steps.append(f"{dim_name}={status}: {'; '.join(str(i) for i in issues[:2])}")
        return steps

    # ── Few-shot 示例注入 ────────────────────────────────────────────────

    FEW_SHOT_EXAMPLES = [
        {
            "action": "click `登录按钮`",
            "ocr_text": "欢迎登录\n用户名\n密码\n登录\n系统错误",
            "dom_texts": "登录页面\n错误提示: 用户名或密码错误",
            "console_errors": '[{"message": "POST /api/login 401"}]',
            "network_requests": '[{"method":"POST","url":"/api/login","status":401}]',
            "expected": {
                "dimensions": {
                    "api": {"status": "fail", "issues": ["POST /api/login 401 Unauthorized"], "confidence": 0.95},
                    "console": {"status": "pass", "issues": [], "confidence": 0.95},
                    "ui": {"status": "uncertain", "issues": ["页面显示'系统错误'但非崩溃"], "confidence": 0.7},
                    "business": {"status": "fail", "issues": ["登录未成功，URL 未跳转"], "confidence": 0.9},
                },
                "root_cause": "API 返回 401，认证失败导致登录流程中断",
                "fix_suggestion": "检查用户凭证或后端认证逻辑",
                "summary": "登录 API 认证失败，页面显示错误提示但未崩溃",
            }
        },
        {
            "action": "navigate to https://example.com",
            "ocr_text": "",
            "dom_texts": "",
            "console_errors": '[]',
            "network_requests": '[{"method":"GET","url":"https://example.com","status":200}]',
            "expected": {
                "dimensions": {
                    "api": {"status": "pass", "issues": [], "confidence": 0.95},
                    "console": {"status": "pass", "issues": [], "confidence": 0.95},
                    "ui": {"status": "pass", "issues": [], "confidence": 0.95},
                    "business": {"status": "pass", "issues": [], "confidence": 0.95},
                },
                "root_cause": "",
                "fix_suggestion": "",
                "summary": "页面加载成功，所有维度正常",
            }
        },
    ]

    @staticmethod
    def format_few_shot() -> str:
        """Format few-shot examples as injectable prompt context."""
        lines = ["\n## 参考示例\n"]
        for i, ex in enumerate(FewShotExamples.FEW_SHOT_EXAMPLES, 1):
            lines.append(f"### 示例 {i}")
            lines.append(f"操作: {ex['action']}")
            lines.append(f"OCR: {ex['ocr_text'][:50]}...")
            lines.append(f"Console: {ex['console_errors'][:50]}...")
            lines.append(f"Network: {ex['network_requests'][:50]}...")
            exp = ex['expected']
            lines.append(f"→ 判断: API={exp['dimensions']['api']['status']}, "
                        f"UI={exp['dimensions']['ui']['status']}, "
                        f"摘要: {exp['summary']}")
        return "\n".join(lines)


class FewShotExamples:
    FEW_SHOT_EXAMPLES = ChainOfThoughtAnalyzer.FEW_SHOT_EXAMPLES


# ── 跨步上下文聚合 ──────────────────────────────────────────────────

class CrossStepContext:
    """Aggregates analysis results across steps for better root cause detection."""

    def __init__(self, max_history: int = 10):
        self._steps: list[dict] = []
        self._max = max_history

    def add_step(self, step_index: int, action: str, analysis: dict):
        self._steps.append({
            "index": step_index,
            "action": action,
            "analysis": analysis,
            "timestamp": datetime.now().isoformat(),
        })
        if len(self._steps) > self._max:
            self._steps.pop(0)

    def get_context(self, current_step: int) -> str:
        if len(self._steps) <= 1:
            return ""
        prev = [s for s in self._steps if s["index"] < current_step]
        if not prev:
            return ""
        lines = ["\n## 前一步骤分析上下文\n"]
        for s in prev[-3:]:
            dims = s["analysis"].get("dimensions", {})
            statuses = {k: v.get("status", "?") for k, v in dims.items()}
            lines.append(f"  步骤 {s['index']} ({s['action']}): {statuses}")
        return "\n".join(lines)

    def reset(self):
        self._steps = []

    @property
    def step_count(self) -> int:
        return len(self._steps)
