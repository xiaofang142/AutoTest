from abc import ABC, abstractmethod


class AIService(ABC):
    @abstractmethod
    async def extract_rules(self, content: str, strategy: str = "general") -> dict:
        ...

    @abstractmethod
    async def analyze_root_cause(self, evidence: dict) -> dict:
        ...

    @abstractmethod
    async def generate_fix_suggestion(self, defect_data: dict) -> dict:
        ...

    @abstractmethod
    async def judge_causal_relation(self, event_a: dict, event_b: dict) -> bool:
        ...

    @abstractmethod
    async def analyze_merged(self, step_signals: dict) -> dict:
        """Merge multi-signal analysis: OCR + DOM + console + network → LLM.

        Args:
            step_signals: dict with keys:
                - ocr_text: str — PaddleOCR 提取的截图文字
                - ocr_elements: str — OCR 文本块列表的字符串表示
                - dom_texts: str — DOM 可见文本（换行分隔）
                - alerts: str — 页面告警元素列表的字符串表示
                - console_errors: str — 控制台错误的 JSON 表示
                - console_warnings: str — 控制台警告的 JSON 表示
                - network_requests: str — 网络请求的 JSON 表示
                - action: str — 执行的操作描述

        Returns:
            dict with keys:
                - dimensions: dict — 4 维度分析结果
                - root_cause: str
                - fix_suggestion: str
                - summary: str
        """
        ...
