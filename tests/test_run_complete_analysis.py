from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import src.run_complete_analysis as module
from src.run_complete_analysis import (
    run_complete_analysis,
)


def create_technical_summary() -> dict[str, object]:
    return {
        "generated_at": "2026-08-01T10:00:00+00:00",
        "success_count": 3,
        "failure_count": 0,
        "results": [
            {
                "rank": 1,
                "symbol": "ASELS",
                "technical_score": 75.0,
            },
            {
                "rank": 2,
                "symbol": "TUPRS",
                "technical_score": 65.0,
            },
            {
                "rank": 3,
                "symbol": "THYAO",
                "technical_score": 50.0,
            },
        ],
        "errors": [],
    }


def create_technical_result() -> dict[str, object]:
    return {
        "batch_summary": create_technical_summary(),
        "candidate_selection": {
            "candidate_count": 3,
            "strong_candidate_count": 2,
            "candidates": [],
        },
        "outputs": {
            "batch_json": (
                "reports/bist_batch_analysis.json"
            ),
            "batch_markdown": (
                "reports/bist_batch_analysis.md"
            ),
            "candidate_json": (
                "reports/bist_candidates.json"
            ),
            "candidate_markdown": (
                "reports/bist_candidates.md"
            ),
        },
    }


def create_fundamental_summary() -> dict[str, object]:
    return {
        "generated_at": "2026-08-01T11:00:00+00:00",
        "success_count": 3,
        "failure_count": 0,
        "results": [
            {
                "rank": 1,
                "symbol": "TUPRS",
                "fundamental_score": 72.0,
                "data_confidence": 90.91,
            },
            {
                "rank": 2,
                "symbol": "ASELS",
                "fundamental_score": 68.0,
                "data_confidence": 81.82,
            },
            {
                "rank": 3,
                "symbol": "THYAO",
                "fundamental_score": 58.0,
                "data_confidence": 90.91,
            },
        ],
        "errors": [],
    }


def create_combined_summary(
    combined_count: int = 3,
) -> dict[str, object]:
    results: list[dict[str, object]] = []

    if combined_count > 0:
        results = [
            {
                "rank": 1,
                "symbol": "ASELS",
                "technical_score": 75.0,
                "fundamental_score": 68.0,
                "combined_score": 71.85,
                "label": "OLUMLU",
            }
        ]

    return {
        "generated_at": "2026-08-01T12:00:00+00:00",
        "combined_count": combined_count,
        "unmatched_count": 0,
        "results": results,
        "unmatched": [],
    }


def create_final_candidate_selection() -> dict[str, object]:
    return {
        "generated_at": "2026-08-01T12:30:00+00:00",
        "candidate_count": 2,
        "strong_candidate_count": 1,
        "candidates": [
            {
                "rank": 1,
                "symbol": "ASELS",
                "combined_score": 71.85,
                "label": "GÜÇLÜ NİHAİ ADAY",
            },
            {
                "rank": 2,
                "symbol": "TUPRS",
                "combined_score": 68.15,
                "label": "NİHAİ ADAY",
            },
        ],
        "excluded": [],
    }


def create_complete_result(
    combined_count: int = 3,
) -> dict[str, object]:
    return {
        "technical_analysis": (
            create_technical_result()
        ),
        "fundamental_analysis": (
            create_fundamental_summary()
        ),
        "combined_analysis": (
            create_combined_summary(
                combined_count=combined_count
            )
        ),
        "final_candidate_selection": (
            create_final_candidate_selection()
        ),
        "outputs": {
            "technical_batch_json": (
                "reports/bist_batch_analysis.json"
            ),
            "technical_batch_markdown": (
                "reports/bist_batch_analysis.md"
            ),
            "technical_candidates_json": (
                "reports/bist_candidates.json"
            ),
            "technical_candidates_markdown": (
                "reports/bist_candidates.md"
            ),
            "fundamental_json": (
                "reports/"
                "bist_fundamental_batch_analysis.json"
            ),
            "fundamental_markdown": (
                "reports/"
                "bist_fundamental_batch_analysis.md"
            ),
            "combined_json": (
                "reports/bist_combined_analysis.json"
            ),
            "combined_markdown": (
                "reports/bist_combined_analysis.md"
            ),
            "final_candidates_json": (
                "reports/bist_combined_candidates.json"
            ),
            "final_candidates_markdown": (
                "reports/bist_combined_candidates.md"
            ),
        },
    }


def configure_successful_mocks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        module,
        "run_full_analysis",
        lambda **kwargs: create_technical_result(),
    )

    monkeypatch.setattr(
        module,
        "run_fundamental_batch_analysis",
        lambda **kwargs: create_fundamental_summary(),
    )

    monkeypatch.setattr(
        module,
        "build_fundamental_report",
        lambda summary: "# Temel Analiz\n",
    )

    monkeypatch.setattr(
        module,
        "combine_analysis_summaries",
        lambda **kwargs: create_combined_summary(),
    )

    monkeypatch.setattr(
        module,
        "build_combined_report",
        lambda summary: "# Birleşik Analiz\n",
    )

    monkeypatch.setattr(
        module,
        "select_combined_candidates",
        lambda **kwargs: (
            create_final_candidate_selection()
        ),
    )

    monkeypatch.setattr(
        module,
        "build_final_candidate_report",
        lambda result: "# Nihai Adaylar\n",
    )


def test_run_complete_analysis_creates_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report_directory = tmp_path / "reports"
    price_directory = tmp_path / "prices"

    configure_successful_mocks(monkeypatch)

    result = run_complete_analysis(
        symbols=[
            "THYAO",
            "ASELS",
            "TUPRS",
        ],
        price_directory=price_directory,
        report_directory=report_directory,
    )

    fundamental_json_path = (
        report_directory
        / "bist_fundamental_batch_analysis.json"
    )
    fundamental_markdown_path = (
        report_directory
        / "bist_fundamental_batch_analysis.md"
    )
    combined_json_path = (
        report_directory
        / "bist_combined_analysis.json"
    )
    combined_markdown_path = (
        report_directory
        / "bist_combined_analysis.md"
    )
    final_candidate_json_path = (
        report_directory
        / "bist_combined_candidates.json"
    )
    final_candidate_markdown_path = (
        report_directory
        / "bist_combined_candidates.md"
    )

    assert fundamental_json_path.exists()
    assert fundamental_markdown_path.exists()
    assert combined_json_path.exists()
    assert combined_markdown_path.exists()
    assert final_candidate_json_path.exists()
    assert final_candidate_markdown_path.exists()

    saved_final_candidates = json.loads(
        final_candidate_json_path.read_text(
            encoding="utf-8"
        )
    )

    assert (
        saved_final_candidates["candidate_count"]
        == 2
    )
    assert (
        saved_final_candidates[
            "strong_candidate_count"
        ]
        == 1
    )

    outputs = result["outputs"]

    assert isinstance(outputs, dict)
    assert outputs["final_candidates_json"] == str(
        final_candidate_json_path
    )


def test_run_complete_analysis_passes_arguments(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_technical: dict[str, object] = {}
    captured_fundamental: dict[str, object] = {}
    captured_combined: dict[str, object] = {}
    captured_final_selection: dict[str, object] = {}

    def fake_full_analysis(
        **kwargs: object,
    ) -> dict[str, object]:
        captured_technical.update(kwargs)
        return create_technical_result()

    def fake_fundamental_analysis(
        **kwargs: object,
    ) -> dict[str, object]:
        captured_fundamental.update(kwargs)
        return create_fundamental_summary()

    def fake_combined_analysis(
        **kwargs: object,
    ) -> dict[str, object]:
        captured_combined.update(kwargs)
        return create_combined_summary()

    def fake_final_selection(
        **kwargs: object,
    ) -> dict[str, object]:
        captured_final_selection.update(kwargs)
        return create_final_candidate_selection()

    monkeypatch.setattr(
        module,
        "run_full_analysis",
        fake_full_analysis,
    )
    monkeypatch.setattr(
        module,
        "run_fundamental_batch_analysis",
        fake_fundamental_analysis,
    )
    monkeypatch.setattr(
        module,
        "combine_analysis_summaries",
        fake_combined_analysis,
    )
    monkeypatch.setattr(
        module,
        "select_combined_candidates",
        fake_final_selection,
    )
    monkeypatch.setattr(
        module,
        "build_fundamental_report",
        lambda summary: "# Temel\n",
    )
    monkeypatch.setattr(
        module,
        "build_combined_report",
        lambda summary: "# Birleşik\n",
    )
    monkeypatch.setattr(
        module,
        "build_final_candidate_report",
        lambda result: "# Nihai Adaylar\n",
    )

    run_complete_analysis(
        symbols=["THYAO", "ASELS"],
        period="6mo",
        price_directory=tmp_path / "prices",
        report_directory=tmp_path / "reports",
        technical_weight=0.60,
        fundamental_weight=0.40,
        max_candidates=4,
        max_strong_candidates=2,
        candidate_threshold=55.0,
        strong_threshold=70.0,
    )

    assert captured_technical["symbols"] == [
        "THYAO",
        "ASELS",
    ]
    assert captured_technical["period"] == "6mo"
    assert captured_technical["max_candidates"] == 4

    assert captured_fundamental["symbols"] == [
        "THYAO",
        "ASELS",
    ]

    assert captured_combined["technical_weight"] == 0.60
    assert (
        captured_combined["fundamental_weight"]
        == 0.40
    )

    assert (
        captured_final_selection["max_candidates"]
        == 4
    )
    assert (
        captured_final_selection[
            "max_strong_candidates"
        ]
        == 2
    )
    assert (
        captured_final_selection[
            "candidate_threshold"
        ]
        == 55.0
    )
    assert (
        captured_final_selection["strong_threshold"]
        == 70.0
    )


def test_run_complete_analysis_uses_custom_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_successful_mocks(monkeypatch)

    fundamental_json_path = (
        tmp_path / "custom_fundamental.json"
    )
    fundamental_report_path = (
        tmp_path / "custom_fundamental.md"
    )
    combined_json_path = (
        tmp_path / "custom_combined.json"
    )
    combined_report_path = (
        tmp_path / "custom_combined.md"
    )
    final_candidate_json_path = (
        tmp_path / "custom_candidates.json"
    )
    final_candidate_report_path = (
        tmp_path / "custom_candidates.md"
    )

    result = run_complete_analysis(
        symbols=["THYAO"],
        report_directory=tmp_path / "reports",
        fundamental_json_path=(
            fundamental_json_path
        ),
        fundamental_report_path=(
            fundamental_report_path
        ),
        combined_json_path=combined_json_path,
        combined_report_path=combined_report_path,
        final_candidate_json_path=(
            final_candidate_json_path
        ),
        final_candidate_report_path=(
            final_candidate_report_path
        ),
    )

    assert fundamental_json_path.exists()
    assert fundamental_report_path.exists()
    assert combined_json_path.exists()
    assert combined_report_path.exists()
    assert final_candidate_json_path.exists()
    assert final_candidate_report_path.exists()

    outputs = result["outputs"]

    assert isinstance(outputs, dict)
    assert outputs["final_candidates_json"] == str(
        final_candidate_json_path
    )
    assert outputs["final_candidates_markdown"] == str(
        final_candidate_report_path
    )


def test_run_complete_analysis_rejects_empty_symbols() -> None:
    with pytest.raises(
        ValueError,
        match="En az bir hisse kodu",
    ):
        run_complete_analysis(symbols=[])


def test_run_complete_analysis_rejects_invalid_technical_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        module,
        "run_full_analysis",
        lambda **kwargs: {},
    )

    with pytest.raises(
        ValueError,
        match="Teknik analiz sonucu kullanılamıyor",
    ):
        run_complete_analysis(
            symbols=["THYAO"],
            report_directory=tmp_path / "reports",
        )


def test_main_uses_explicit_symbols(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured_arguments: dict[str, object] = {}

    def fake_complete_analysis(
        **kwargs: object,
    ) -> dict[str, object]:
        captured_arguments.update(kwargs)
        return create_complete_result()

    monkeypatch.setattr(
        module,
        "run_complete_analysis",
        fake_complete_analysis,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_complete_analysis.py",
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
    assert "Teknik analiz: 3" in terminal_output
    assert "Temel analiz: 3" in terminal_output
    assert "Birleşik analiz: 3" in terminal_output
    assert "Teknik aday: 3" in terminal_output
    assert "Güçlü teknik aday: 2" in terminal_output
    assert "Nihai aday: 2" in terminal_output
    assert "Güçlü nihai aday: 1" in terminal_output

    assert (
        "En yüksek nihai aday: ASELS - 71.85"
        in terminal_output
    )


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

    def fake_complete_analysis(
        **kwargs: object,
    ) -> dict[str, object]:
        captured_arguments.update(kwargs)
        return create_complete_result()

    monkeypatch.setattr(
        module,
        "run_complete_analysis",
        fake_complete_analysis,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_complete_analysis.py",
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


def test_main_returns_error_when_no_result_combines(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        module,
        "run_complete_analysis",
        lambda **kwargs: create_complete_result(
            combined_count=0
        ),
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_complete_analysis.py",
            "THYAO",
        ],
    )

    exit_code = module.main()
    terminal_output = capsys.readouterr().out

    assert exit_code == 1
    assert (
        "Teknik ve temel analiz sonuçları "
        "birleştirilemedi"
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
            "run_complete_analysis.py",
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
    def fake_complete_analysis(
        **kwargs: object,
    ) -> dict[str, object]:
        raise ValueError(
            "Tam analiz başarısız oldu."
        )

    monkeypatch.setattr(
        module,
        "run_complete_analysis",
        fake_complete_analysis,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_complete_analysis.py",
            "THYAO",
        ],
    )

    exit_code = module.main()
    terminal_output = capsys.readouterr().out

    assert exit_code == 1
    assert (
        "HATA: Tam analiz başarısız oldu."
        in terminal_output
    )