from app.domain.models.run import StepExecutionRecord, ConsoleSnapshot, NetworkSnapshot, PageState, Verifications, VerificationResult
from app.domain.models.scenario import TestStep
from app.interfaces.executor_client import ExecutorClient
from app.lib.logger import get_logger

logger = get_logger(__name__)


class MockExecutorClient(ExecutorClient):
    """Mock executor for development/testing without real browser."""

    @property
    def mode(self) -> str:
        return "mock"

    async def ping(self) -> bool:
        return False

    async def execute_step(self, step: TestStep, context: dict | None = None) -> StepExecutionRecord:
        logger.info(f"Mock execute: step={step.index} action={step.action}")
        return StepExecutionRecord(
            id=f"mock_{step.index}", run_id=(context or {}).get("run_id", ""),
            case_id=(context or {}).get("case_id", ""), step_index=step.index,
            action=step.action, platform="web", status="passed", duration_ms=100,
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
        return {"url": "https://example.com/mock"}
