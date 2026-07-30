from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "analysis.schema.json"
SAMPLE_PATH = PROJECT_ROOT / "examples" / "sample_analysis.json"


def load_json(file_path: Path) -> dict:
    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def test_sample_analysis_matches_schema() -> None:
    schema = load_json(SCHEMA_PATH)
    sample_data = load_json(SAMPLE_PATH)

    validator = Draft202012Validator(
        schema=schema,
        format_checker=FormatChecker(),
    )

    errors = list(validator.iter_errors(sample_data))

    assert errors == [], "\n".join(
        f"{list(error.absolute_path)}: {error.message}"
        for error in errors
    )
