from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from src.run_pipeline import main, run_pipeline


def test_run_pipeline_creates_all_outputs(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "prices.csv"
    json_output_path = tmp_path / "analysis.json"
    report_output_path = tmp_path / "analysis.md"

    result = run_pipeline(
        input_path=input_path,
        symbol="thyao",
        json_output_path=json_output_path,
        report_output_path=report_output_path,
        generate_sample=True,
        sample_rows=120,
    )

    assert input_path.exists()
    assert json_output_path.exists()
    assert report_output_path.exists()

    assert result["symbol"] == "THYAO"
    assert result["record_count"] == 120
    assert "technical_analysis" in result

    technical_score = result["technical_analysis"][
        "technical_score"
    ]

    assert 0 <= technical_score <= 100


def test_pipeline_json_output_matches_result(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "prices.csv"
    json_output_path = tmp_path / "analysis.json"
    report_output_path = tmp_path / "analysis.md"

    result = run_pipeline(
        input_path=input_path,
        symbol="TEST",
        json_output_path=json_output_path,
        report_output_path=report_output_path,
        generate_sample=True,
        sample_rows=100,
    )

    with json_output_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        saved_result = json.load(file)

    assert saved_result == result


def test_pipeline_markdown_contains_symbol_and_score(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "prices.csv"
    json_output_path = tmp_path / "analysis.json"
    report_output_path = tmp_path / "analysis.md"

    result = run_pipeline(
        input_path=input_path,
        symbol="ASELS",
        json_output_path=json_output_path,
        report_output_path=report_output_path,
        generate_sample=True,
        sample_rows=120,
    )

    report_text = report_output_path.read_text(
        encoding="utf-8",
    )

    technical_score = result["technical_analysis"][
        "technical_score"
    ]

    assert "# ASELS Teknik Analiz Raporu" in report_text
    assert f"{technical_score:.2f} / 100" in report_text


def test_main_completes_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_path = tmp_path / "prices.csv"
    json_output_path = tmp_path / "analysis.json"
    report_output_path = tmp_path / "analysis.md"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_pipeline.py",
            "--input",
            str(input_path),
            "--symbol",
            "THYAO",
            "--json-output",
            str(json_output_path),
            "--report-output",
            str(report_output_path),
            "--generate-sample",
            "--sample-rows",
            "90",
        ],
    )

    exit_code = main()
    terminal_output = capsys.readouterr().out

    assert exit_code == 0
    assert input_path.exists()
    assert json_output_path.exists()
    assert report_output_path.exists()

    assert "BAŞARILI" in terminal_output
    assert "THYAO" in terminal_output
    assert "Teknik puan" in terminal_output


def test_main_returns_error_for_invalid_sample_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_path = tmp_path / "prices.csv"
    json_output_path = tmp_path / "analysis.json"
    report_output_path = tmp_path / "analysis.md"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_pipeline.py",
            "--input",
            str(input_path),
            "--json-output",
            str(json_output_path),
            "--report-output",
            str(report_output_path),
            "--generate-sample",
            "--sample-rows",
            "20",
        ],
    )

    exit_code = main()
    terminal_output = capsys.readouterr().out

    assert exit_code == 1
    assert "HATA" in terminal_output
    assert not json_output_path.exists()
    assert not report_output_path.exists()