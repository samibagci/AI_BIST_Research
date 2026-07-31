from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import src.run_full_analysis as module
from src.run_full_analysis import run_full_analysis


def create_batch_summary() -> dict[str, object]:
    return {
        "generated_at": "2026-07-31T12:00:00+00:00",
        "period": "1y",
        "requested_count": 4,
        "processed_count": 4,
        "success_count": 4,
        "failure_count": 0,
        "results": [
            {
                "rank": 1,
                "symbol": "ASELS",
                "technical_score": 75.5,
            },
            {
                "rank": 2,
                "symbol": "TUPRS",
                "technical_score": 64.2,
            },
            {
                "rank": 3,
                "symbol": "KCHOL",
                "technical_score": 58.4,
            },
            {
                "rank": 4,
                "symbol": "THYAO",
                "technical_score": 49.9,
            },
        ],
        "errors": [],
    }


def create_full_result(
    success_count: int = 4,
) -> dict[str, object]:
    return {
        "batch_summary": {
            "success_count": success_count,
            "failure_count": 0,
        },
        "candidate_selection": {
            "candidate_count": 3,
            "strong_candidate_count": 2,
            "candidates": [
                {
                    "rank": 1,
                    "symbol": "ASELS",
                    "technical_score": 75.5,
                    "label": "GÜÇLÜ ADAY",
                }
            ],
        },
        "outputs": {
            "batch_json": "reports/batch.json",
            "batch_markdown": "reports/batch.md",
            "candidate_json": "reports/candidates.json",
            "candidate_markdown": "reports/candidates.md",
        },
    }


def test_run_full_analysis_creates_all_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report_directory = tmp_path / "reports"
    price_directory = tmp_path / "prices"

    monkeypatch.setattr(
        module,
        "run_bist_batch_analysis",
        lambda **kwargs: create_batch_summary(),
    )

    result = run_full_analysis(
        symbols=[
            "THYAO",
            "ASELS",
            "TUPRS",
            "KCHOL",
        ],
        period="1y",
        price_directory=price_directory,
        report_directory=report_directory,
    )

    batch_json_path = (
        report_directory
        / "bist_batch_analysis.json"
    )
    batch_markdown_path = (
        report_directory
        / "bist_batch_analysis.md"
    )
    candidate_json_path = (
        report_directory
        / "bist_candidates.json"
    )
    candidate_markdown_path = (
        report_directory
        / "bist_candidates.md"
    )

    assert batch_json_path.exists()
    assert batch_markdown_path.exists()
    assert candidate_json_path.exists()
    assert candidate_markdown_path.exists()

    selection_result = result["candidate_selection"]

    assert isinstance(selection_result, dict)
    assert selection_result["candidate_count"] == 3
    assert selection_result["strong_candidate_count"] == 2

    saved_candidates = json.loads(
        candidate_json_path.read_text(
            encoding="utf-8"
        )
    )

    assert saved_candidates["candidate_count"] == 3


def test_run_full_analysis_passes_batch_arguments(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_arguments: dict[str, object] = {}

    def fake_batch_analysis(
        **kwargs: object,
    ) -> dict[str, object]:
        captured_arguments.update(kwargs)
        return create_batch_summary()

    monkeypatch.setattr(
        module,
        "run_bist_batch_analysis",
        fake_batch_analysis,
    )

    run_full_analysis(
        symbols=["THYAO", "ASELS"],
        period="6mo",
        price_directory=tmp_path / "prices",
        report_directory=tmp_path / "reports",
        max_candidates=2,
        max_strong_candidates=1,
        candidate_threshold=55.0,
        strong_threshold=70.0,
    )

    assert captured_arguments["symbols"] == [
        "THYAO",
        "ASELS",
    ]
    assert captured_arguments["period"] == "6mo"
    assert (
        captured_arguments["price_directory"]
        == tmp_path / "prices"
    )
    assert (
        captured_arguments["report_directory"]
        == tmp_path / "reports"
    )


def test_run_full_analysis_uses_custom_output_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch_json_path = tmp_path / "custom_batch.json"
    batch_report_path = tmp_path / "custom_batch.md"
    candidate_json_path = (
        tmp_path / "custom_candidates.json"
    )
    candidate_report_path = (
        tmp_path / "custom_candidates.md"
    )

    monkeypatch.setattr(
        module,
        "run_bist_batch_analysis",
        lambda **kwargs: create_batch_summary(),
    )

    result = run_full_analysis(
        symbols=["THYAO"],
        batch_json_path=batch_json_path,
        batch_report_path=batch_report_path,
        candidate_json_path=candidate_json_path,
        candidate_report_path=candidate_report_path,
    )

    assert batch_json_path.exists()
    assert batch_report_path.exists()
    assert candidate_json_path.exists()
    assert candidate_report_path.exists()

    outputs = result["outputs"]

    assert isinstance(outputs, dict)
    assert outputs["batch_json"] == str(
        batch_json_path
    )
    assert outputs["candidate_markdown"] == str(
        candidate_report_path
    )


def test_main_uses_explicit_symbols(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured_arguments: dict[str, object] = {}

    def fake_full_analysis(
        **kwargs: object,
    ) -> dict[str, object]:
        captured_arguments.update(kwargs)
        return create_full_result()

    monkeypatch.setattr(
        module,
        "run_full_analysis",
        fake_full_analysis,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_full_analysis.py",
            "THYAO",
            "ASELS",
            "--period",
            "6mo",
            "--report-directory",
            str(tmp_path / "reports"),
        ],
    )

    exit_code = module.main()
    terminal_output = capsys.readouterr().out

    assert exit_code == 0
    assert captured_arguments["symbols"] == [
        "THYAO",
        "ASELS",
    ]
    assert captured_arguments["period"] == "6mo"

    assert "BAŞARILI" in terminal_output
    assert "Başarılı analiz: 4" in terminal_output
    assert "Seçilen aday: 3" in terminal_output
    assert "Güçlü aday: 2" in terminal_output
    assert "En yüksek aday: ASELS - 75.5" in terminal_output


def test_main_uses_watchlist_when_symbols_are_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    watchlist_path = tmp_path / "watchlist.txt"

    watchlist_path.write_text(
        "THYAO\nASELS\nTUPRS\n",
        encoding="utf-8",
    )

    captured_arguments: dict[str, object] = {}

    def fake_full_analysis(
        **kwargs: object,
    ) -> dict[str, object]:
        captured_arguments.update(kwargs)
        return create_full_result()

    monkeypatch.setattr(
        module,
        "run_full_analysis",
        fake_full_analysis,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_full_analysis.py",
            "--watchlist",
            str(watchlist_path),
        ],
    )

    exit_code = module.main()

    assert exit_code == 0
    assert captured_arguments["symbols"] == [
        "THYAO",
        "ASELS",
        "TUPRS",
    ]


def test_main_returns_error_when_no_analysis_succeeds(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        module,
        "run_full_analysis",
        lambda **kwargs: create_full_result(
            success_count=0
        ),
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_full_analysis.py",
            "HATALI",
        ],
    )

    exit_code = module.main()
    terminal_output = capsys.readouterr().out

    assert exit_code == 1
    assert (
        "Hiçbir hisse analiz edilemedi"
        in terminal_output
    )


def test_main_returns_error_for_missing_watchlist(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_full_analysis.py",
            "--watchlist",
            str(tmp_path / "missing.txt"),
        ],
    )

    exit_code = module.main()
    terminal_output = capsys.readouterr().out

    assert exit_code == 1
    assert "HATA" in terminal_output
    assert "İzleme listesi bulunamadı" in terminal_output


def test_main_returns_error_when_analysis_fails(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_full_analysis(
        **kwargs: object,
    ) -> dict[str, object]:
        raise ValueError("Analiz başarısız oldu.")

    monkeypatch.setattr(
        module,
        "run_full_analysis",
        fake_full_analysis,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_full_analysis.py",
            "THYAO",
        ],
    )

    exit_code = module.main()
    terminal_output = capsys.readouterr().out

    assert exit_code == 1
    assert "HATA: Analiz başarısız oldu." in terminal_output