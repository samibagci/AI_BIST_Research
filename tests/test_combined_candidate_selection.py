from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

import src.combined_candidate_selection as module
from src.combined_candidate_selection import (
    build_markdown_report,
    format_score,
    load_combined_summary,
    prepare_combined_results,
    safe_number,
    save_json_result,
    save_markdown_report,
    select_combined_candidates,
)


def create_combined_summary() -> dict[str, object]:
    return {
        "generated_at": "2026-08-01T12:00:00+00:00",
        "weights": {
            "technical": 0.55,
            "fundamental": 0.45,
        },
        "results": [
            {
                "rank": 1,
                "symbol": "ASELS",
                "company_name": "Aselsan",
                "sector": "Technology",
                "technical_score": 78.0,
                "fundamental_score": 72.0,
                "combined_score": 75.3,
                "fundamental_data_confidence": 90.91,
            },
            {
                "rank": 2,
                "symbol": "TUPRS",
                "company_name": "Tüpraş",
                "sector": "Energy",
                "technical_score": 65.0,
                "fundamental_score": 72.08,
                "combined_score": 68.19,
                "fundamental_data_confidence": 90.91,
            },
            {
                "rank": 3,
                "symbol": "KCHOL",
                "company_name": "Koç Holding",
                "sector": "Financial Services",
                "technical_score": 55.0,
                "fundamental_score": 62.0,
                "combined_score": 58.15,
                "fundamental_data_confidence": 81.82,
            },
            {
                "rank": 4,
                "symbol": "THYAO",
                "company_name": "Türk Hava Yolları",
                "sector": "Industrials",
                "technical_score": 45.0,
                "fundamental_score": 58.93,
                "combined_score": 51.27,
                "fundamental_data_confidence": 90.91,
            },
            {
                "rank": 5,
                "symbol": "SISE",
                "company_name": "Şişecam",
                "sector": "Basic Materials",
                "technical_score": 40.0,
                "fundamental_score": 48.0,
                "combined_score": 43.6,
                "fundamental_data_confidence": 72.73,
            },
        ],
    }


def test_safe_number_accepts_real_numbers() -> None:
    assert safe_number(10) == 10.0
    assert safe_number(4.25) == 4.25


@pytest.mark.parametrize(
    "value",
    [
        True,
        False,
        "10",
        None,
        math.inf,
        -math.inf,
        math.nan,
    ],
)
def test_safe_number_rejects_invalid_values(
    value: object,
) -> None:
    assert safe_number(value) is None


def test_load_combined_summary_reads_json(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "combined.json"
    expected_summary = create_combined_summary()

    input_path.write_text(
        json.dumps(expected_summary),
        encoding="utf-8",
    )

    result = load_combined_summary(input_path)

    assert result == expected_summary


def test_load_combined_summary_rejects_missing_file(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "missing.json"

    with pytest.raises(
        FileNotFoundError,
        match="Birleşik analiz dosyası bulunamadı",
    ):
        load_combined_summary(input_path)


def test_load_combined_summary_rejects_invalid_json(
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
        load_combined_summary(input_path)


def test_load_combined_summary_rejects_non_object_json(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "list.json"

    input_path.write_text(
        json.dumps([1, 2, 3]),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="JSON nesnesi olmalıdır",
    ):
        load_combined_summary(input_path)


def test_prepare_combined_results_cleans_and_sorts() -> None:
    summary: dict[str, object] = {
        "results": [
            {
                "symbol": " thyao.is ",
                "technical_score": 45.123,
                "fundamental_score": 58.934,
                "combined_score": 51.276,
                "fundamental_data_confidence": 90.919,
            },
            {
                "symbol": "ASELS",
                "technical_score": 78.0,
                "fundamental_score": 72.0,
                "combined_score": 75.3,
                "fundamental_data_confidence": 81.82,
            },
            {
                "symbol": "THYAO",
                "combined_score": 90.0,
            },
            {
                "symbol": "",
                "combined_score": 60.0,
            },
            {
                "symbol": "HATALI",
                "combined_score": "70",
            },
            {
                "symbol": "BOOL",
                "combined_score": True,
            },
            {
                "symbol": "YUKSEK",
                "combined_score": 120.0,
            },
        ]
    }

    results = prepare_combined_results(summary)

    assert [
        result["symbol"]
        for result in results
    ] == [
        "ASELS",
        "THYAO",
    ]

    assert results[0]["combined_score"] == 75.3
    assert results[1]["combined_score"] == 51.28
    assert results[1]["technical_score"] == 45.12
    assert results[1]["fundamental_score"] == 58.93
    assert (
        results[1]["fundamental_data_confidence"]
        == 90.92
    )


def test_prepare_combined_results_rejects_missing_results() -> None:
    with pytest.raises(
        ValueError,
        match="sonuç listesi bulunamadı",
    ):
        prepare_combined_results({})


def test_select_combined_candidates_applies_thresholds() -> None:
    result = select_combined_candidates(
        combined_summary=create_combined_summary(),
    )

    candidates = result["candidates"]
    excluded = result["excluded"]

    assert result["candidate_count"] == 4
    assert result["strong_candidate_count"] == 2

    assert isinstance(candidates, list)

    assert [
        candidate["symbol"]
        for candidate in candidates
    ] == [
        "ASELS",
        "TUPRS",
        "KCHOL",
        "THYAO",
    ]

    assert (
        candidates[0]["label"]
        == "GÜÇLÜ NİHAİ ADAY"
    )
    assert (
        candidates[1]["label"]
        == "GÜÇLÜ NİHAİ ADAY"
    )
    assert candidates[2]["label"] == "NİHAİ ADAY"
    assert candidates[3]["label"] == "NİHAİ ADAY"

    assert isinstance(excluded, list)
    assert excluded[0]["symbol"] == "SISE"
    assert (
        excluded[0]["reason"]
        == "Birleşik puan aday eşiğinin altında."
    )


def test_select_combined_candidates_respects_limits() -> None:
    result = select_combined_candidates(
        combined_summary=create_combined_summary(),
        max_candidates=3,
        max_strong_candidates=1,
        candidate_threshold=50.0,
        strong_threshold=60.0,
    )

    candidates = result["candidates"]
    excluded = result["excluded"]

    assert result["candidate_count"] == 3
    assert result["strong_candidate_count"] == 1

    assert isinstance(candidates, list)
    assert (
        candidates[0]["label"]
        == "GÜÇLÜ NİHAİ ADAY"
    )
    assert candidates[1]["label"] == "NİHAİ ADAY"

    assert isinstance(excluded, list)

    excluded_map = {
        item["symbol"]: item["reason"]
        for item in excluded
    }

    assert (
        excluded_map["THYAO"]
        == "Maksimum aday sayısına ulaşıldı."
    )
    assert (
        excluded_map["SISE"]
        == "Birleşik puan aday eşiğinin altında."
    )


def test_select_combined_candidates_rejects_invalid_settings() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "Güçlü aday sayısı toplam aday "
            "sayısını aşamaz"
        ),
    ):
        select_combined_candidates(
            combined_summary=create_combined_summary(),
            max_candidates=2,
            max_strong_candidates=3,
        )


def test_format_score() -> None:
    assert format_score(58.934) == "58.93"
    assert format_score(70) == "70.00"
    assert format_score(None) == "Veri yok"
    assert format_score(True) == "Veri yok"


def test_build_markdown_report_contains_candidates() -> None:
    selection_result = select_combined_candidates(
        combined_summary=create_combined_summary(),
    )

    markdown = build_markdown_report(
        selection_result
    )

    assert "# BIST Nihai Aday Seçim Raporu" in markdown
    assert (
        "| 1 | ASELS | 78.00 | 72.00 | 75.30 "
        "| 90.91% | GÜÇLÜ NİHAİ ADAY |"
        in markdown
    )
    assert (
        "| 3 | KCHOL | 55.00 | 62.00 | 58.15 "
        "| 81.82% | NİHAİ ADAY |"
        in markdown
    )
    assert "**SISE** (43.60)" in markdown
    assert "yatırım tavsiyesi değildir" in markdown


def test_save_result_files(
    tmp_path: Path,
) -> None:
    selection_result = select_combined_candidates(
        combined_summary=create_combined_summary(),
    )

    json_path = (
        tmp_path
        / "reports"
        / "combined_candidates.json"
    )

    markdown_path = (
        tmp_path
        / "reports"
        / "combined_candidates.md"
    )

    save_json_result(
        selection_result=selection_result,
        output_path=json_path,
    )

    save_markdown_report(
        markdown_report="# Nihai Adaylar\n",
        output_path=markdown_path,
    )

    assert json_path.exists()
    assert markdown_path.exists()

    saved_result = json.loads(
        json_path.read_text(encoding="utf-8")
    )

    assert saved_result["candidate_count"] == 4
    assert saved_result["strong_candidate_count"] == 2

    assert (
        markdown_path.read_text(encoding="utf-8")
        == "# Nihai Adaylar\n"
    )


def test_main_completes_candidate_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_path = tmp_path / "combined.json"
    json_output_path = tmp_path / "candidates.json"
    report_output_path = tmp_path / "candidates.md"

    input_path.write_text(
        json.dumps(create_combined_summary()),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "combined_candidate_selection.py",
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
    assert "Seçilen nihai aday: 4" in terminal_output
    assert "Güçlü nihai aday: 2" in terminal_output
    assert (
        "En yüksek nihai aday: ASELS - 75.3"
        in terminal_output
    )


def test_main_returns_error_for_invalid_settings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_path = tmp_path / "combined.json"

    input_path.write_text(
        json.dumps(create_combined_summary()),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "combined_candidate_selection.py",
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