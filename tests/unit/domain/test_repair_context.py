from app.domain.models.repair_context import RepairContext


class TestRepairContext:
    def test_default_values(self):
        ctx = RepairContext()
        assert ctx.defect_title == ""
        assert ctx.reproduction_steps == []
        assert ctx.console_errors == []
        assert ctx.root_cause_candidates == []

    def test_from_defect_with_evidence(self):
        class MockDefect:
            title = "Login API 500"
            evidence_chains = [
                type("obj", (), {"propagation": ["Step 1: API failed", "Step 2: JS error"]})()
            ]
            console_logs = {"errors": ["TypeError: x undefined"]}
            api_calls = [{"url": "/api/login", "status": 500}]
            ai_analysis = {"root_cause": "Backend validation missing"}
            fix_suggestion = type("obj", (), {"description": "Add input validation"})()

        ctx = RepairContext.from_defect(MockDefect())
        assert ctx.defect_title == "Login API 500"
        assert len(ctx.reproduction_steps) == 2
        assert "API failed" in ctx.reproduction_steps[0]
        assert "Backend" in ctx.root_cause_candidates[0]
        assert "input validation" in ctx.repair_suggestions[0]

    def test_from_defect_empty(self):
        class MockDefect:
            title = "test"
            evidence_chains = []
            console_logs = {}
            api_calls = []
            ai_analysis = {}
            fix_suggestion = None

        ctx = RepairContext.from_defect(MockDefect())
        assert ctx.defect_title == "test"
        assert ctx.reproduction_steps == []
        assert ctx.console_errors == []
        assert ctx.repair_suggestions == []
