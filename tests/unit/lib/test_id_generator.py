from app.lib.id_generator import generate_id


class TestIdGenerator:
    def test_project_id_prefix(self):
        pid = generate_id("project")
        assert pid.startswith("proj_")
        assert len(pid) == 4 + 1 + 12

    def test_document_id_prefix(self):
        did = generate_id("document")
        assert did.startswith("doc_")

    def test_defect_id_prefix(self):
        did = generate_id("defect")
        assert did.startswith("def_")

    def test_run_id_prefix(self):
        rid = generate_id("run")
        assert rid.startswith("run_")

    def test_uniqueness(self):
        ids = {generate_id("project") for _ in range(100)}
        assert len(ids) == 100
