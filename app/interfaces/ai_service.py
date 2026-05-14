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
