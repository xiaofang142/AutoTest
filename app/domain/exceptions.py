class DomainError(Exception):
    def __init__(self, message: str, code: str = "DOMAIN_ERROR"):
        self.code = code
        super().__init__(message)


class ProjectNotFoundError(DomainError):
    def __init__(self, project_id: str):
        super().__init__(f"Project not found: {project_id}", "PROJECT_NOT_FOUND")


class DocumentNotFoundError(DomainError):
    def __init__(self, document_id: str):
        super().__init__(f"Document not found: {document_id}", "DOCUMENT_NOT_FOUND")


class KnowledgeBaseNotFoundError(DomainError):
    def __init__(self, kb_id: str):
        super().__init__(f"Knowledge base not found: {kb_id}", "KB_NOT_FOUND")


class ScenarioNotFoundError(DomainError):
    def __init__(self, scenario_id: str):
        super().__init__(f"Scenario not found: {scenario_id}", "SCENARIO_NOT_FOUND")


class RunNotFoundError(DomainError):
    def __init__(self, run_id: str):
        super().__init__(f"Run not found: {run_id}", "RUN_NOT_FOUND")


class DefectNotFoundError(DomainError):
    def __init__(self, defect_id: str):
        super().__init__(f"Defect not found: {defect_id}", "DEFECT_NOT_FOUND")


class InvalidParameterError(DomainError):
    def __init__(self, message: str):
        super().__init__(message, "INVALID_PARAMETER")


class OperationNotAllowedError(DomainError):
    def __init__(self, message: str):
        super().__init__(message, "OPERATION_NOT_ALLOWED")


class DocumentParseError(DomainError):
    def __init__(self, document_id: str, reason: str = ""):
        super().__init__(
            f"Document parse failed: {document_id} - {reason}",
            "DOCUMENT_PARSE_FAILED",
        )
