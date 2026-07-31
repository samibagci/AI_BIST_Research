from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import src.run_bist_batch_analysis as module
from src.run_bist_batch_analysis import (
    build_markdown_report,
    extract_technical_score,
    parse_symbol_inputs,
    run_bist_batch_analysis,
    save_json_summary,
    save_markdown_summary,
)


def create_analysis_result(
    symbol: str,
    technical_score: float,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "technical_analysis": {
            "technical_score": technical_score,
        },
    }


def test_parse_symbol_inputs_supports_spaces_and_commas() -> None:
    result = parse_symbol_inputs(
        [
            "THYAO, ASELS",
            "TUPRS",
            " KCHOL,SISE ",
        ]
    )

    assert result == [
        "THYAO",
        "ASELS",
        "TUPRS",
        "KCHOL",
        "SISE",
    ]


def test_parse_symbol_inputs_rejects_empty_values() -> None:
    with pytest.raises(
        ValueError,
        match="En az bir hisse kodu",
    ):
        parse_symbol_inputs(["", " , "])


def test_extract_technical_score() -> None:
    result = create_analysis_result(
        symbol="THYAO",
        technical_score=67.456,
    )

    assert extract_technical_score(result) == 67.46


def test_extract_technical_score_rejects_missing_score() -> None:
    with pytest.raises(
        ValueError,
        match="Teknik puan bulunamadı",
    ):
        extract_technical_score(
            {
                "technical_analysis": {},
            }
        )


def test_run_bist_batch_analysis_sorts_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scores = {
        "THYAO": 45.45,
        "ASELS": 72.8,
        "TUPRS": 61.2,
    }

    captured_calls: list[dict[str, object]] = []

    def fake_run_bist_analysis(
        **kwargs: object,
    ) -> dict[str, object]:
        captured_calls.append(kwargs)

        symbol = str(kwargs["symbol"])

        return create_analysis_result(
            symbol=symbol,
            technical_score=scores[symbol],
        )

    monkeypatch.setattr(
        module,
        "run_bist_analysis",
        fake_run_bist_analysis,
    )

    summary = run_bist_batch_analysis(
        symbols=[
            "THYAO",
            "ASELS",
            "TUPRS",
            "THYAO.IS",
        ],
        period="6mo",
        price_directory=tmp_path / "prices",
        report_directory=tmp_path / "reports",
    )

    results = summary["results"]

    assert summary["requested_count"] == 4
    assert summary["processed_count"] == 3
    assert summary["success_count"] == 3
    assert summary["failure_count"] == 0

    assert isinstance(results, list)

    assert [
        result["symbol"]
        for result in results
    ] == [
        "ASELS",
        "TUPRS",
        "THYAO",
    ]

    assert [
        result["rank"]
        for result in results
    ] == [1, 2, 3]

    assert len(captured_calls) == 3
    assert captured_calls[0]["period"] == "6mo"


def test_run_bist_batch_analysis_records_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run_bist_analysis(
        **kwargs: object,
    ) -> dict[str, object]:
        symbol = str(kwargs["symbol"])

        if symbol == "HATALI":
            raise ValueError("Veri bulunamadı.")

        return create_analysis_result(
            symbol=symbol,
            technical_score=55.0,
        )

    monkeypatch.setattr(
        module,
        "run_bist_analysis",
        fake_run_bist_analysis,
    )

    summary = run_bist_batch_analysis(
        symbols=["THYAO", "HATALI"],
        price_directory=tmp_path / "prices",
        report_directory=tmp_path / "reports",
    )

    errors = summary["errors"]

    assert summary["success_count"] == 1
    assert summary["failure_count"] == 1

    assert isinstance(errors, list)
    assert errors[0]["symbol"] == "HATALI"
    assert errors[0]["error"] == "Veri bulunamadı."


def test_build_markdown_report_contains_ranking() -> None:
    summary: dict[str, object] = {
        "generated_at": "2026-07-31T12:00:00+00:00",
        "period": "1y",
        "success_count": 2,
        "failure_count": 1,
        "results": [
            {
                "rank": 1,
                "symbol": "ASELS",
                "technical_score": 72.8,
            },
            {
                "rank": 2,
                "symbol": "THYAO",
                "technical_score": 45.45,
            },
        ],
        "errors": [
            {
                "symbol": "HATALI",
                "error": "Veri bulunamadı.",
            }
        ],
    }

    markdown = build_markdown_report(summary)

    assert "# BIST Toplu Teknik Analiz Raporu" in markdown
    assert "| 1 | ASELS | 72.80 |" in markdown
    assert "| 2 | THYAO | 45.45 |" in markdown
    assert "**HATALI**: Veri bulunamadı." in markdown


def test_save_summary_files(
    tmp_path: Path,
) -> None:
    summary: dict[str, object] = {
        "success_count": 1,
        "results": [],
    }

    json_path = tmp_path / "reports" / "summary.json"
    markdown_path = tmp_path / "reports" / "summary.md"

    save_json_summary(
        summary=summary,
        output_path=json_path,
    )

    save_markdown_summary(
        markdown_report="# Rapor\n",
        output_path=markdown_path,
    )

    assert json_path.exists()
    assert markdown_path.exists()

    saved_summary = json.loads(
        json_path.read_text(encoding="utf-8")
    )

    assert saved_summary == summary
    assert (
        markdown_path.read_text(encoding="utf-8")
        == "# Rapor\n"
    )


def test_main_completes_batch_analysis(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    json_path = tmp_path / "batch.json"
    markdown_path = tmp_path / "batch.md"

    summary: dict[str, object] = {
        "generated_at": "2026-07-31T12:00:00+00:00",
        "period": "1y",
        "requested_count": 2,
        "processed_count": 2,
        "success_count": 2,
        "failure_count": 0,
        "results": [
            {
                "rank": 1,
                "symbol": "ASELS",
                "technical_score": 72.8,
            },
            {
                "rank": 2,
                "symbol": "THYAO",
                "technical_score": 45.45,
            },
        ],
        "errors": [],
    }

    monkeypatch.setattr(
        module,
        "run_bist_batch_analysis",
        lambda **kwargs: summary,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_bist_batch_analysis.py",
            "THYAO",
            "ASELS",
            "--json-output",
            str(json_path),
            "--report-output",
            str(markdown_path),
        ],
    )

    exit_code = module.main()
    terminal_output = capsys.readouterr().out

    assert exit_code == 0
    assert json_path.exists()
    assert markdown_path.exists()

    assert "BAŞARILI" in terminal_output
    assert "Başarılı analiz: 2" in terminal_output
    assert "En yüksek puan: ASELS - 72.8" in terminal_output


def test_main_returns_error_when_all_analyses_fail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    summary: dict[str, object] = {
        "generated_at": "2026-07-31T12:00:00+00:00",
        "period": "1y",
        "requested_count": 1,
        "processed_count": 1,
        "success_count": 0,
        "failure_count": 1,
        "results": [],
        "errors": [
            {
                "symbol": "HATALI",
                "error": "Veri bulunamadı.",
            }
        ],
    }

    monkeypatch.setattr(
        module,
        "run_bist_batch_analysis",
        lambda **kwargs: summary,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_bist_batch_analysis.py",
            "HATALI",
            "--json-output",
            str(tmp_path / "batch.json"),
            "--report-output",
            str(tmp_path / "batch.md"),
        ],
    )

    exit_code = module.main()
    terminal_output = capsys.readouterr().out

    assert exit_code == 1
    assert "Hiçbir hisse analiz edilemedi" in terminal_output