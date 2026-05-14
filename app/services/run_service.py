from datetime import datetime
from app.domain.models.run import RunRecord, StepExecutionRecord, RunSummary
from app.domain.models.scenario import TestCase
from app.domain.exceptions import RunNotFoundError, InvalidParameterError
from app.interfaces.repositories.run_repo import RunRepository
from app.interfaces.repositories.scenario_repo import ScenarioRepository
from app.lib.id_generator import generate_id
from app.lib.logger import get_logger

logger = get_logger(__name__)


class RunService:
    def __init__(self, run_repo: RunRepository, scenario_repo: ScenarioRepository):
        self._repo = run_repo
        self._scenario_repo = scenario_repo

    async def create_run(self, project_id: str, platforms: list[str],
                         scenario_ids: list[str] | None = None) -> RunRecord:
        if not platforms:
            raise InvalidParameterError("At least one platform required for run")

        run = RunRecord(
            id=generate_id("run"),
            project_id=project_id,
            platforms=platforms,
        )

        if scenario_ids:
            cases = []
            for sid in scenario_ids:
                scenario = await self._scenario_repo.get_by_id(sid)
                if scenario:
                    cases.extend(scenario.cases)
            run.total_cases = len(cases)

        created = await self._repo.create(run)
        logger.info(f"Run created: {created.id}, cases={run.total_cases}")
        return created

    async def get_run(self, run_id: str) -> RunRecord:
        run = await self._repo.get_by_id(run_id)
        if not run:
            raise RunNotFoundError(run_id)
        return run

    async def get_run_progress(self, run_id: str) -> dict:
        run = await self.get_run(run_id)
        return {
            "run_id": run.id,
            "status": run.status,
            "progress": run.progress,
        }

    async def cancel_run(self, run_id: str) -> None:
        await self._repo.update_status(run_id, "cancelled")
        logger.info(f"Run cancelled: {run_id}")

    async def retry_run(self, run_id: str, case_ids: list[str] | None = None) -> RunRecord:
        original = await self.get_run(run_id)
        new_run = RunRecord(
            id=generate_id("run"),
            project_id=original.project_id,
            name=f"{original.name} (retry)",
            platforms=original.platforms,
        )
        return await self._repo.create(new_run)

    async def save_step(self, step: StepExecutionRecord) -> StepExecutionRecord:
        return await self._repo.save_step(step)
