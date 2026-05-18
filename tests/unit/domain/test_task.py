import pytest
from app.domain.models.task import (
    TestTask, TaskInput, TaskStatus, TaskMode, TaskGoal, TaskDepth,
    AutoLevel, EnvironmentCheck, UnderstandingResult, TestBlueprint,
    BlueprintStep, DeliveryPackage, TaskStateMachine,
)


class TestTestTaskCreation:
    def test_created_with_draft_status(self):
        task = TestTask(name="test smoke", input=TaskInput(target_url="https://example.com"))
        assert task.status == TaskStatus.DRAFT
        assert task.name == "test smoke"
        assert task.input.target_url == "https://example.com"
        assert task.mode == TaskMode.QUICK
        assert task.auto_level == AutoLevel.A0

    def test_all_fields_have_defaults(self):
        task = TestTask(name="minimal")
        assert task.id == ""
        assert task.description == ""
        assert task.project_id == ""
        assert task.blocked_reason == ""
        assert task.error_summary == ""
        assert task.defect_count == 0
        assert task.delivery_ready is False

    def test_with_document_driven_mode(self):
        task = TestTask(name="doc driven", mode=TaskMode.DOCUMENT_DRIVEN,
                        input=TaskInput(target_url="https://x.com", documents=["doc_001"]))
        assert task.mode == TaskMode.DOCUMENT_DRIVEN
        assert len(task.input.documents) == 1


class TestTaskStateMachine:
    def test_valid_transition(self):
        assert TaskStateMachine.can_transition(TaskStatus.DRAFT, TaskStatus.PRECHECKING)
        assert TaskStateMachine.can_transition(TaskStatus.PRECHECKING, TaskStatus.UNDERSTANDING)
        assert TaskStateMachine.can_transition(TaskStatus.UNDERSTANDING, TaskStatus.PLANNING)
        assert TaskStateMachine.can_transition(TaskStatus.PLANNING, TaskStatus.RUNNING)
        assert TaskStateMachine.can_transition(TaskStatus.RUNNING, TaskStatus.ANALYZING)
        assert TaskStateMachine.can_transition(TaskStatus.ANALYZING, TaskStatus.COMPLETED)
        assert TaskStateMachine.can_transition(TaskStatus.ANALYZING, TaskStatus.COMPLETED_WITH_DEFECTS)

    def test_invalid_transition_returns_false(self):
        assert not TaskStateMachine.can_transition(TaskStatus.DRAFT, TaskStatus.COMPLETED)
        assert not TaskStateMachine.can_transition(TaskStatus.DRAFT, TaskStatus.RUNNING)
        assert not TaskStateMachine.can_transition(TaskStatus.COMPLETED, TaskStatus.RUNNING)
        assert not TaskStateMachine.can_transition(TaskStatus.CANCELLED, TaskStatus.DRAFT)

    def test_blocked_can_retry(self):
        assert TaskStateMachine.can_transition(TaskStatus.BLOCKED, TaskStatus.DRAFT)

    def test_error_can_retry(self):
        assert TaskStateMachine.can_transition(TaskStatus.ERROR, TaskStatus.DRAFT)

    def test_terminal_states(self):
        assert TaskStateMachine.is_terminal(TaskStatus.COMPLETED)
        assert TaskStateMachine.is_terminal(TaskStatus.COMPLETED_WITH_DEFECTS)
        assert TaskStateMachine.is_terminal(TaskStatus.CANCELLED)
        assert not TaskStateMachine.is_terminal(TaskStatus.RUNNING)
        assert not TaskStateMachine.is_terminal(TaskStatus.DRAFT)

    def test_allowed_actions(self):
        assert "start" in TaskStateMachine.allowed_actions(TaskStatus.DRAFT)
        assert "cancel" in TaskStateMachine.allowed_actions(TaskStatus.RUNNING)
        assert "view_defects" in TaskStateMachine.allowed_actions(TaskStatus.COMPLETED_WITH_DEFECTS)


class TestSubModels:
    def test_environment_check_defaults(self):
        check = EnvironmentCheck()
        assert check.executor_online is False
        assert check.summary == ""

    def test_understanding_result_defaults(self):
        result = UnderstandingResult()
        assert result.completeness == 0.0
        assert result.key_flows == []

    def test_blueprint_step_with_assertions(self):
        step = BlueprintStep(index=1, action="click", target="登录按钮", assert_api=True)
        assert step.action == "click"
        assert step.assert_api is True
        assert step.assert_business is False

    def test_delivery_package_has_all_views(self):
        pkg = DeliveryPackage()
        assert pkg.tester_view.summary == ""
        assert pkg.ai_assistant_view.repair_suggestion == ""


class TestTaskModeEnum:
    def test_all_modes(self):
        assert TaskMode.QUICK.value == "quick"
        assert TaskMode.DOCUMENT_DRIVEN.value == "document_driven"
        assert TaskMode.MIXED.value == "mixed"

    def test_auto_levels_ordered(self):
        levels = [AutoLevel.A0, AutoLevel.A1, AutoLevel.A2, AutoLevel.A3, AutoLevel.A4, AutoLevel.A5]
        assert len(levels) == 6
