from dataclasses import dataclass, field
import httpx
from typing import Optional
from app.domain.models.run import StepExecutionRecord, ConsoleSnapshot, ConsoleLogEntry, NetworkSnapshot, NetworkEntry, PageState, Verifications, VerificationResult
from app.domain.models.scenario import TestStep
from app.interfaces.executor_client import ExecutorClient
from app.config import settings
from app.lib.logger import get_logger

logger = get_logger(__name__)


@dataclass
class NavigateResult:
    success: bool = False
    screenshot: str = ""
    current_url: str = ""


class WebExecutorClient(ExecutorClient):
    def __init__(self, base_url: str = ""):
        self.base_url = base_url or settings.executor_web_url
        self._client = httpx.AsyncClient(timeout=60)

    @property
    def mode(self) -> str:
        return "real"

    async def ping(self) -> bool:
        try:
            resp = await self._client.get(f"{self.base_url}/health", timeout=10)
            return resp.json().get("status") == "ok"
        except Exception:
            return False

    async def navigate(self, url: str, viewport: dict | None = None) -> NavigateResult:
        resp = await self._client.post(f"{self.base_url}/agent/navigate", json={
            "url": url,
        }, timeout=120)
        data = resp.json()
        return NavigateResult(
            success=data.get("success", False),
            screenshot=data.get("screenshot", ""),
            current_url=data.get("url", ""),
        )

    async def create_run(self, run_id: str, entry: dict, cases: list) -> dict:
        executable_cases = []
        for c in cases:
            steps = []
            for s in (getattr(c, 'steps', None) or []):
                steps.append({"index": s.index, "action": s.action, "target": s.target, "value": s.value})
            executable_cases.append({"id": c.id, "name": c.name, "steps": steps})
        resp = await self._client.post(f"{self.base_url}/run/create", json={
            "run_id": run_id, "entry": entry, "cases": executable_cases,
        }, timeout=30)
        return resp.json()

    async def start_run(self, run_id: str) -> dict:
        resp = await self._client.post(f"{self.base_url}/run/{run_id}/start", timeout=10)
        return resp.json()

    async def get_run_progress(self, run_id: str) -> dict:
        resp = await self._client.get(f"{self.base_url}/run/{run_id}/progress", timeout=10)
        return resp.json()

    async def cancel_run(self, run_id: str) -> None:
        await self._client.post(f"{self.base_url}/run/{run_id}/cancel", timeout=10)

    async def execute_step(self, step: TestStep, context: Optional[dict] = None) -> StepExecutionRecord:
        logger.info(f"Executor: {step.action} {step.target}")
        try:
            resp = await self._client.post(f"{self.base_url}/agent/execute", json={
                "action": step.action, "target": step.target, "value": step.value,
            }, timeout=60)
            resp.raise_for_status()
            result = resp.json()
        except Exception as e:
            return StepExecutionRecord(id=f"err_{step.index}", run_id=(context or {}).get("run_id", ""),
                case_id=(context or {}).get("case_id", ""), step_index=step.index,
                action=step.action, status="failed", error=str(e))

        console = result.get("consoleLogs") or {}
        ps = result.get("pageState") or {}
        return StepExecutionRecord(
            id=f"step_{step.index}", run_id=(context or {}).get("run_id", ""),
            case_id=(context or {}).get("case_id", ""), step_index=step.index,
            action=step.action, platform="web",
            status="passed" if result.get("success") else "failed",
            screenshots={"before": result.get("screenshotBefore", ""),
                         "after": result.get("screenshotAfter", "")},
            console_snapshot=ConsoleSnapshot(
                errors=[ConsoleLogEntry(level="error", message=e.get("message","")) for e in console.get("errors",[])],
                warnings=[ConsoleLogEntry(level="warning", message=e.get("message","")) for e in console.get("warnings",[])]),
            network_snapshot=NetworkSnapshot(requests=[], failed=[]),
            page_state=PageState(current_url=ps.get("url",""),
                visible_text_elements=ps.get("visibleTexts",[]),
                active_alerts=ps.get("alerts",[])),
            verifications=Verifications(
                ui=VerificationResult(status="failed" if not result.get("success") else "pass", dimension="ui")),
        )

    async def take_screenshot(self) -> str:
        resp = await self._client.post(f"{self.base_url}/agent/screenshot", timeout=30)
        return resp.json().get("screenshot", "")

    async def get_page_state(self) -> dict:
        return {}
