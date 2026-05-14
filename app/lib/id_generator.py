import secrets

PREFIXES = {
    "project": "proj",
    "document": "doc",
    "knowledge": "kb",
    "rule": "rule",
    "scenario": "sce",
    "test_case": "tc",
    "run": "run",
    "step": "step",
    "defect": "def",
    "conflict": "conf",
    "file": "file",
    "task": "task",
}


def generate_id(entity_type: str) -> str:
    prefix = PREFIXES.get(entity_type, "gen")
    random_part = secrets.token_hex(6)
    return f"{prefix}_{random_part}"
