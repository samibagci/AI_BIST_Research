from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import src.candidate_selection as module
from src.candidate_selection import (
    build_markdown_report,
    load_batch_summary,
    prepare_scored_results,
    save_json_result,
    save_markdown_report,
    select_candidates,
    validate_selection_settings,
)


def create_batch_summary() -> dict[str, object]:
    return {
        "generated_at": "2026-07-31T12:00:00+00:00",
        "period": "1y",
        "results": [
            {
                "symbol": "ASELS",
                "technical_score": 75.5,
            },
            {
                "symbol": "TUPRS",
                "technical_score": 64.2,
            },
            {
                "symbol": "KCHOL",
                "technical_score": 58.4,
            },
            {
                "symbol": "THYAO",
                "technical_score": 49.9,
            },
            {
                "symbol": "SISE",
                "technical_score": 42.0,
            },
        ],
    }


def test_load_batch_summary_reads_json(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "batch.json"
    expected_summary = create_batch_summary()

    input_path.write_text(
        json.dumps(expected_summary),
        encoding="utf-8",
    )

    result = load_batch_summary(input_path)

    assert result == expected_summary


def test_load_batch_summary_rejects_missing_file(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "missing.json"

    with pytest.raises(
        FileNotFoundError,
        match="Toplu analiz dosyası bulunamadı",
    ):
        load_batch_summary(input_path)


def test_load_batch_summary_rejects_invalid_json(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "invalid.json"

    input_path.write_text(
        "{geçersiz json",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="geçerli JSON değil",
    ):
        load_batch_summary(input_path)


@pytest.mark.parametrize(
    (
        "max_candidates",
        "max_strong_candidates",
        "candidate_threshold",
        "strong_threshold",
    ),
    [
        (0, 0, 50.0, 60.0),
        (5, -1, 50.0, 60.0),
        (3, 4, 50.0, 60.0),
        (5, 3, -1.0, 60.0),
        (5, 3, 50.0, 101.0),
        (5, 3, 70.0, 60.0),
    ],
)
def test_validate_selection_settings_rejects_invalid_values(
    max_candidates: int,
    max_strong_candidates: int,
    candidate_threshold: float,
    strong_threshold: float,
) -> None:
    with pytest.raises(ValueError):
        validate_selection_settings(
            max_candidates=max_candidates,
            max_strong_candidates=max_strong_candidates,
            candidate_threshold=candidate_threshold,
            strong_threshold=strong_threshold,
        )


def test_prepare_scored_results_cleans_and_sorts() -> None:
    batch_summary: dict[str, object] = {
        "results": [
            {
                "symbol": " thyao ",
                "technical_score": 55.123,
            },
            {
                "symbol": "ASELS",
                "technical_score": 72.8,
            },
            {
                "symbol": "THYAO",
                "technical_score": 90.0,
            },
            {
                "symbol": "",
                "technical_score": 50.0,
            },
            {
                "symbol": "HATALI",
                "technical_score": "60",
            },
            {
                "symbol": "BOOL",
                "technical_score": True,
            },
            {
                "symbol": "YUKSEK",
                "technical_score": 120.0,
            },
        ]
    }

    results = prepare_scored_results(batch_summary)

    assert results == [
        {
            "symbol": "ASELS",
            "technical_score": 72.8,
        },
        {
            "symbol": "THYAO",
            "technical_score": 55.12,
        },
    ]


def test_prepare_scored_results_rejects_missing_results() -> None:
    with pytest.raises(
        ValueError,
        match="sonuç listesi bulunamadı",
    ):
        prepare_scored_results({})


def test_select_candidates_applies_thresholds() -> None:
    result = select_candidates(
        batch_summary=create_batch_summary(),
    )

    candidates = result["candidates"]
    excluded = result["excluded"]

    assert result["candidate_count"] == 3
    assert result["strong_candidate_count"] == 2

    assert isinstance(candidates, list)

    assert [
        candidate["symbol"]
        for candidate in candidates
    ] == [
        "ASELS",
        "TUPRS",
        "KCHOL",
    ]

    assert candidates[0]["label"] == "GÜÇLÜ ADAY"
    assert candidates[1]["label"] == "GÜÇLÜ ADAY"
    assert candidates[2]["label"] == "ADAY"

    assert isinstance(excluded, list)

    assert [
        item["symbol"]
        for item in excluded
    ] == [
        "THYAO",
        "SISE",
    ]


def test_select_candidates_respects_candidate_limits() -> None:
    batch_summary: dict[str, object] = {
        "period": "1y",
        "results": [
            {
                "symbol": "A",
                "technical_score": 90.0,
            },
            {
                "symbol": "B",
                "technical_score": 80.0,
            },
            {
                "symbol": "C",
                "technical_score": 70.0,
            },
            {
                "symbol": "D",
                "technical_score": 65.0,
            },
        ],
    }

    result = select_candidates(
        batch_summary=batch_summary,
        max_candidates=3,
        max_strong_candidates=2,
        candidate_threshold=50.0,
        strong_threshold=60.0,
    )

    candidates = result["candidates"]
    excluded = result["excluded"]

    assert result["candidate_count"] == 3
    assert result["strong_candidate_count"] == 2

    assert isinstance(candidates, list)
    assert candidates[2]["label"] == "ADAY"

    assert isinstance(excluded, list)
    assert excluded[0]["symbol"] == "D"
    assert (
        excluded[0]["reason"]
        == "Maksimum aday sayısına ulaşıldı."
    )


def test_build_markdown_report_contains_candidates() -> None:
    selection_result = select_candidates(
        batch_summary=create_batch_summary(),
    )

    markdown = build_markdown_report(
        selection_result
    )

    assert "# BIST Teknik Aday Seçim Raporu" in markdown
    assert "| 1 | ASELS | 75.50 | GÜÇLÜ ADAY |" in markdown
    assert "| 2 | TUPRS | 64.20 | GÜÇLÜ ADAY |" in markdown
    assert "| 3 | KCHOL | 58.40 | ADAY |" in markdown
    assert "**THYAO** (49.90)" in markdown
    assert "yatırım tavsiyesi değildir" in markdown


def test_save_result_files(
    tmp_path: Path,
) -> None:
    selection_result = select_candidates(
        batch_summary=create_batch_summary(),
    )

    json_path = tmp_path / "reports" / "candidates.json"
    markdown_path = tmp_path / "reports" / "candidates.md"

    save_json_result(
        selection_result=selection_result,
        output_path=json_path,
    )

    save_markdown_report(
        markdown_report="# Adaylar\n",
        output_path=markdown_path,
    )

    assert json_path.exists()
    assert markdown_path.exists()

    saved_result = json.loads(
        json_path.read_text(encoding="utf-8")
    )

    assert (
        saved_result["candidate_count"]
        == selection_result["candidate_count"]
    )

    assert (
        markdown_path.read_text(encoding="utf-8")
        == "# Adaylar\n"
    )


def test_main_completes_candidate_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_path = tmp_path / "batch.json"
    json_output_path = tmp_path / "candidates.json"
    report_output_path = tmp_path / "candidates.md"

    input_path.write_text(
        json.dumps(create_batch_summary()),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "candidate_selection.py",
            "--input",
            str(input_path),
            "--json-output",
            str(json_output_path),
            "--report-output",
            str(report_output_path),
        ],
    )

    exit_code = module.main()
    terminal_output = capsys.readouterr().out

    assert exit_code == 0
    assert json_output_path.exists()
    assert report_output_path.exists()

    assert "BAŞARILI" in terminal_output
    assert "Seçilen aday: 3" in terminal_output
    assert "Güçlü aday: 2" in terminal_output


def test_main_returns_error_for_invalid_settings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_path = tmp_path / "batch.json"

    input_path.write_text(
        json.dumps(create_batch_summary()),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "candidate_selection.py",
            "--input",
            str(input_path),
            "--max-candidates",
            "2",
            "--max-strong-candidates",
            "3",
        ],
    )

    exit_code = module.main()
    terminal_output = capsys.readouterr().out

    assert exit_code == 1
    assert "HATA" in terminal_output
    assert (
        "Güçlü aday sayısı toplam aday sayısını aşamaz"
        in terminal_output
    )