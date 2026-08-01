from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import src.run_fundamental_batch_analysis as module
from src.run_fundamental_batch_analysis import (
    build_markdown_report,
    extract_data_confidence,
    extract_fundamental_score,
    extract_label,
    run_fundamental_batch_analysis,
    save_json_summary,
    save_markdown_summary,
)


def create_analysis_result(
    symbol: str = "THYAO",
    fundamental_score: float = 65.5,
    data_confidence: float = 90.91,
    label: str = "OLUMLU",
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "fundamental_score": fundamental_score,
        "data_confidence": data_confidence,
        "label": label,
        "company": {
            "name": f"{symbol} Şirketi",
            "sector": "Industrials",
        },
    }


def create_batch_summary() -> dict[str, object]:
    return {
        "generated_at": "2026-08-01T10:00:00+00:00",
        "requested_count": 3,
        "processed_count": 3,
        "success_count": 2,
        "failure_count": 1,
        "results": [
            {
                "rank": 1,
                "symbol": "ASELS",
                "company_name": "ASELS Şirketi",
                "sector": "Technology",
                "fundamental_score": 72.5,
                "data_confidence": 90.91,
                "label": "OLUMLU",
                "json_output": "reports/ASELS.json",
                "markdown_output": "reports/ASELS.md",
            },
            {
                "rank": 2,
                "symbol": "THYAO",
                "company_name": "THYAO Şirketi",
                "sector": "Industrials",
                "fundamental_score": 58.93,
                "data_confidence": 90.91,
                "label": "NÖTR",
                "json_output": "reports/THYAO.json",
                "markdown_output": "reports/THYAO.md",
            },
        ],
        "errors": [
            {
                "symbol": "HATALI",
                "error": "Şirket bilgisi bulunamadı.",
            }
        ],
    }


def test_extract_fundamental_score() -> None:
    result = create_analysis_result(
        fundamental_score=65.567,
    )

    assert extract_fundamental_score(result) == 65.57


@pytest.mark.parametrize(
    "value",
    [
        None,
        "65",
        True,
        False,
    ],
)
def test_extract_fundamental_score_rejects_invalid_values(
    value: object,
) -> None:
    with pytest.raises(
        ValueError,
        match="Temel analiz puanı bulunamadı",
    ):
        extract_fundamental_score(
            {
                "fundamental_score": value,
            }
        )


def test_extract_data_confidence() -> None:
    result = create_analysis_result(
        data_confidence=90.919,
    )

    assert extract_data_confidence(result) == 90.92
    assert extract_data_confidence({}) == 0.0
    assert (
        extract_data_confidence(
            {"data_confidence": True}
        )
        == 0.0
    )


def test_extract_label() -> None:
    assert (
        extract_label({"label": " OLUMLU "})
        == "OLUMLU"
    )
    assert extract_label({}) == "BELİRSİZ"
    assert extract_label({"label": ""}) == "BELİRSİZ"
    assert extract_label({"label": 10}) == "BELİRSİZ"


def test_run_fundamental_batch_analysis_sorts_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scores = {
        "THYAO": 58.93,
        "ASELS": 72.5,
        "TUPRS": 64.2,
    }

    def fake_analysis(
        symbol: str,
    ) -> dict[str, object]:
        return create_analysis_result(
            symbol=symbol,
            fundamental_score=scores[symbol],
        )

    monkeypatch.setattr(
        module,
        "run_fundamental_analysis",
        fake_analysis,
    )

    monkeypatch.setattr(
        module,
        "build_company_report",
        lambda result: f"# {result['symbol']} Raporu\n",
    )

    summary = run_fundamental_batch_analysis(
        symbols=[
            "THYAO",
            "ASELS",
            "TUPRS",
            "THYAO.IS",
        ],
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

    assert (
        tmp_path
        / "reports"
        / "THYAO_fundamental_analysis.json"
    ).exists()

    assert (
        tmp_path
        / "reports"
        / "THYAO_fundamental_analysis.md"
    ).exists()


def test_run_fundamental_batch_analysis_records_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_analysis(
        symbol: str,
    ) -> dict[str, object]:
        if symbol == "HATALI":
            raise ValueError(
                "Şirket bilgisi bulunamadı."
            )

        return create_analysis_result(
            symbol=symbol,
        )

    monkeypatch.setattr(
        module,
        "run_fundamental_analysis",
        fake_analysis,
    )

    monkeypatch.setattr(
        module,
        "build_company_report",
        lambda result: "# Rapor\n",
    )

    summary = run_fundamental_batch_analysis(
        symbols=["THYAO", "HATALI"],
        report_directory=tmp_path / "reports",
    )

    errors = summary["errors"]

    assert summary["success_count"] == 1
    assert summary["failure_count"] == 1

    assert isinstance(errors, list)
    assert errors[0]["symbol"] == "HATALI"
    assert (
        errors[0]["error"]
        == "Şirket bilgisi bulunamadı."
    )


def test_run_fundamental_batch_analysis_rejects_empty_list() -> None:
    with pytest.raises(
        ValueError,
        match="En az bir hisse kodu",
    ):
        run_fundamental_batch_analysis([])


def test_build_markdown_report_contains_ranking() -> None:
    markdown = build_markdown_report(
        create_batch_summary()
    )

    assert "# BIST Toplu Temel Analiz Raporu" in markdown
    assert "| 1 | ASELS | ASELS Şirketi" in markdown
    assert "| 72.50 | 90.91% | OLUMLU |" in markdown
    assert "| 2 | THYAO | THYAO Şirketi" in markdown
    assert "**HATALI**: Şirket bilgisi bulunamadı." in markdown
    assert "yatırım tavsiyesi değildir" in markdown


def test_save_summary_files(
    tmp_path: Path,
) -> None:
    summary = create_batch_summary()

    json_path = tmp_path / "reports" / "summary.json"
    markdown_path = tmp_path / "reports" / "summary.md"

    save_json_summary(
        summary=summary,
        output_path=json_path,
    )

    save_markdown_summary(
        markdown_report="# Temel Analiz\n",
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
        == "# Temel Analiz\n"
    )


def test_main_completes_batch_analysis(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    json_path = tmp_path / "batch.json"
    markdown_path = tmp_path / "batch.md"
    summary = create_batch_summary()

    monkeypatch.setattr(
        module,
        "run_fundamental_batch_analysis",
        lambda **kwargs: summary,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_fundamental_batch_analysis.py",
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
    assert "Başarısız analiz: 1" in terminal_output
    assert (
        "En yüksek temel puan: ASELS - 72.5"
        in terminal_output
    )


def test_main_uses_watchlist_when_symbols_are_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    watchlist_path = tmp_path / "watchlist.txt"
    json_path = tmp_path / "batch.json"
    markdown_path = tmp_path / "batch.md"

    watchlist_path.write_text(
        "THYAO\nASELS\nTUPRS\n",
        encoding="utf-8",
    )

    captured_arguments: dict[str, object] = {}

    def fake_batch_analysis(
        **kwargs: object,
    ) -> dict[str, object]:
        captured_arguments.update(kwargs)

        summary = create_batch_summary()
        summary["failure_count"] = 0
        return summary

    monkeypatch.setattr(
        module,
        "run_fundamental_batch_analysis",
        fake_batch_analysis,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_fundamental_batch_analysis.py",
            "--watchlist",
            str(watchlist_path),
            "--json-output",
            str(json_path),
            "--report-output",
            str(markdown_path),
        ],
    )

    exit_code = module.main()

    assert exit_code == 0
    assert captured_arguments["symbols"] == [
        "THYAO",
        "ASELS",
        "TUPRS",
    ]


def test_main_returns_error_when_all_analyses_fail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    summary: dict[str, object] = {
        "generated_at": "2026-08-01T10:00:00+00:00",
        "requested_count": 1,
        "processed_count": 1,
        "success_count": 0,
        "failure_count": 1,
        "results": [],
        "errors": [
            {
                "symbol": "HATALI",
                "error": "Şirket bilgisi bulunamadı.",
            }
        ],
    }

    monkeypatch.setattr(
        module,
        "run_fundamental_batch_analysis",
        lambda **kwargs: summary,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_fundamental_batch_analysis.py",
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
    assert (
        "Hiçbir şirketin temel analizi tamamlanamadı"
        in terminal_output
    )