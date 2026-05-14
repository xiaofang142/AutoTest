from app.domain.models.run import StepExecutionRecord, ConsoleSnapshot, NetworkSnapshot, PageState, Verifications, VerificationResult
from app.domain.models.scenario import TestStep
from app.interfaces.executor_client import ExecutorClient
from app.config import settings
from app.lib.logger import get_logger

logger = get_logger(__name__)


class MockExecutorClient(ExecutorClient):
    async def execute_step(self, step: TestStep, context: dict | None = None) -> StepExecutionRecord:
        logger.info(f"Mock execute_step: step={step.index} action={step.action}")
        return StepExecutionRecord(
            id=f"mock_step_{step.index}",
            run_id=(context or {}).get("run_id", ""),
            case_id=(context or {}).get("case_id", ""),
            step_index=step.index,
            action=step.action,
            platform="web",
            status="passed",
            duration_ms=150,
            page_state=PageState(current_url="https://example.com/mock"),
            verifications=Verifications(
                ui=VerificationResult(status="pass", dimension="ui", confidence=0.9),
                console=VerificationResult(status="pass", dimension="console", confidence=0.95),
                api=VerificationResult(status="pass", dimension="api", confidence=0.9),
                business=VerificationResult(status="uncertain", dimension="business", confidence=0.5),
            ),
        )

    async def take_screenshot(self) -> str:
        return "data:image/png;base64,mock"

    async def get_page_state(self) -> dict:
        return {"url": "https://example.com/mock", "visible_texts": ["mock"]}


def create_executor_client() -> ExecutorClient:
    if settings.executor_mode == "mock":
        return MockExecutorClient()
    return MockExecutorClient()
