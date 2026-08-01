from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

import src.combined_scoring as module
from src.combined_scoring import (
    build_markdown_report,
    combine_analysis_summaries,
    combined_score_label,
    extract_score_map,
    load_json_object,
    normalize_symbol,
    safe_number,
    save_json_result,
    save_markdown_report,
    validate_weights,
)


def create_technical_summary() -> dict[str, object]:
    return {
        "generated_at": "2026-08-01T10:00:00+00:00",
        "results": [
            {
                "rank": 1,
                "symbol": "ASELS",
                "technical_score": 80.0,
            },
            {
                "rank": 2,
                "symbol": "TUPRS",
                "technical_score": 65.0,
            },
            {
                "rank": 3,
                "symbol": "THYAO",
                "technical_score": 45.0,
            },
            {
                "rank": 4,
                "symbol": "SISE",
                "technical_score": 40.0,
            },
        ],
    }


def create_fundamental_summary() -> dict[str, object]:
    return {
        "generated_at": "2026-08-01T11:00:00+00:00",
        "results": [
            {
                "rank": 1,
                "symbol": "TUPRS",
                "company_name": "Tüpraş",
                "sector": "Energy",
                "fundamental_score": 75.0,
                "data_confidence": 90.91,
            },
            {
                "rank": 2,
                "symbol": "ASELS",
                "company_name": "Aselsan",
                "sector": "Technology",
                "fundamental_score": 70.0,
                "data_confidence": 81.82,
            },
            {
                "rank": 3,
                "symbol": "THYAO",
                "company_name": "Türk Hava Yolları",
                "sector": "Industrials",
                "fundamental_score": 60.0,
                "data_confidence": 90.91,
            },
            {
                "rank": 4,
                "symbol": "KCHOL",
                "company_name": "Koç Holding",
                "sector": "Financial Services",
                "fundamental_score": 55.0,
                "data_confidence": 72.73,
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


def test_load_json_object_reads_file(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "analysis.json"
    expected_data = create_technical_summary()

    input_path.write_text(
        json.dumps(expected_data),
        encoding="utf-8",
    )

    result = load_json_object(
        input_path=input_path,
        description="Teknik analiz dosyası",
    )

    assert result == expected_data


def test_load_json_object_rejects_missing_file(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "missing.json"

    with pytest.raises(
        FileNotFoundError,
        match="Teknik analiz dosyası bulunamadı",
    ):
        load_json_object(
            input_path=input_path,
            description="Teknik analiz dosyası",
        )


def test_load_json_object_rejects_invalid_json(
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
        load_json_object(
            input_path=input_path,
            description="Analiz dosyası",
        )


def test_load_json_object_rejects_non_object_json(
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
        load_json_object(
            input_path=input_path,
            description="Analiz dosyası",
        )


def test_validate_weights_accepts_valid_values() -> None:
    validate_weights(
        technical_weight=0.55,
        fundamental_weight=0.45,
    )


@pytest.mark.parametrize(
    ("technical_weight", "fundamental_weight"),
    [
        (-0.10, 1.10),
        (1.10, -0.10),
        (0.50, 0.40),
        (0.70, 0.50),
    ],
)
def test_validate_weights_rejects_invalid_values(
    technical_weight: float,
    fundamental_weight: float,
) -> None:
    with pytest.raises(ValueError):
        validate_weights(
            technical_weight=technical_weight,
            fundamental_weight=fundamental_weight,
        )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("THYAO", "THYAO"),
        (" thyao ", "THYAO"),
        ("ASELS.IS", "ASELS"),
        (" asels.is ", "ASELS"),
        ("", None),
        ("   ", None),
        (None, None),
        (123, None),
    ],
)
def test_normalize_symbol(
    value: object,
    expected: str | None,
) -> None:
    assert normalize_symbol(value) == expected


def test_extract_score_map_cleans_results() -> None:
    summary: dict[str, object] = {
        "results": [
            {
                "symbol": " thyao.is ",
                "technical_score": 55.456,
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
                "technical_score": 60.0,
            },
            {
                "symbol": "HATALI",
                "technical_score": "70",
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

    score_map = extract_score_map(
        summary=summary,
        score_field="technical_score",
    )

    assert set(score_map) == {
        "THYAO",
        "ASELS",
    }

    assert (
        score_map["THYAO"]["technical_score"]
        == 55.46
    )

    assert (
        score_map["ASELS"]["technical_score"]
        == 72.8
    )


def test_extract_score_map_rejects_missing_results() -> None:
    with pytest.raises(
        ValueError,
        match="Analiz sonuç listesi bulunamadı",
    ):
        extract_score_map(
            summary={},
            score_field="technical_score",
        )


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (80.0, "GÜÇLÜ"),
        (65.0, "OLUMLU"),
        (50.0, "NÖTR"),
        (35.0, "ZAYIF"),
        (20.0, "ÇOK ZAYIF"),
    ],
)
def test_combined_score_label(
    score: float,
    expected: str,
) -> None:
    assert combined_score_label(score) == expected


def test_combine_analysis_summaries_calculates_scores() -> None:
    combined_summary = combine_analysis_summaries(
        technical_summary=create_technical_summary(),
        fundamental_summary=create_fundamental_summary(),
    )

    results = combined_summary["results"]

    assert combined_summary["technical_count"] == 4
    assert combined_summary["fundamental_count"] == 4
    assert combined_summary["combined_count"] == 3
    assert combined_summary["unmatched_count"] == 2

    assert isinstance(results, list)

    assert [
        result["symbol"]
        for result in results
    ] == [
        "ASELS",
        "TUPRS",
        "THYAO",
    ]

    assert results[0]["combined_score"] == 75.5
    assert results[1]["combined_score"] == 69.5
    assert results[2]["combined_score"] == 51.75

    assert results[0]["rank"] == 1
    assert results[0]["label"] == "GÜÇLÜ"
    assert results[1]["label"] == "OLUMLU"
    assert results[2]["label"] == "NÖTR"


def test_combine_analysis_summaries_records_unmatched() -> None:
    combined_summary = combine_analysis_summaries(
        technical_summary=create_technical_summary(),
        fundamental_summary=create_fundamental_summary(),
    )

    unmatched = combined_summary["unmatched"]

    assert isinstance(unmatched, list)

    assert {
        (
            result["symbol"],
            result["reason"],
        )
        for result in unmatched
    } == {
        (
            "SISE",
            "Temel analiz sonucu bulunamadı.",
        ),
        (
            "KCHOL",
            "Teknik analiz sonucu bulunamadı.",
        ),
    }


def test_combine_analysis_uses_custom_weights() -> None:
    technical_summary: dict[str, object] = {
        "results": [
            {
                "symbol": "THYAO",
                "technical_score": 80.0,
            }
        ]
    }

    fundamental_summary: dict[str, object] = {
        "results": [
            {
                "symbol": "THYAO",
                "fundamental_score": 60.0,
                "data_confidence": 90.0,
            }
        ]
    }

    result = combine_analysis_summaries(
        technical_summary=technical_summary,
        fundamental_summary=fundamental_summary,
        technical_weight=0.70,
        fundamental_weight=0.30,
    )

    results = result["results"]

    assert isinstance(results, list)
    assert results[0]["combined_score"] == 74.0


def test_build_markdown_report_contains_ranking() -> None:
    combined_summary = combine_analysis_summaries(
        technical_summary=create_technical_summary(),
        fundamental_summary=create_fundamental_summary(),
    )

    markdown = build_markdown_report(
        combined_summary
    )

    assert "# BIST Birleşik Analiz Raporu" in markdown
    assert "| 1 | ASELS | 80.00 | 70.00 | 75.50" in markdown
    assert "| 2 | TUPRS | 65.00 | 75.00 | 69.50" in markdown
    assert "**SISE**: Temel analiz sonucu bulunamadı." in markdown
    assert "**KCHOL**: Teknik analiz sonucu bulunamadı." in markdown
    assert "yatırım tavsiyesi değildir" in markdown


def test_save_result_files(
    tmp_path: Path,
) -> None:
    combined_summary = combine_analysis_summaries(
        technical_summary=create_technical_summary(),
        fundamental_summary=create_fundamental_summary(),
    )

    json_path = tmp_path / "reports" / "combined.json"
    markdown_path = tmp_path / "reports" / "combined.md"

    save_json_result(
        combined_summary=combined_summary,
        output_path=json_path,
    )

    save_markdown_report(
        markdown_report="# Birleşik Analiz\n",
        output_path=markdown_path,
    )

    assert json_path.exists()
    assert markdown_path.exists()

    saved_result = json.loads(
        json_path.read_text(encoding="utf-8")
    )

    assert saved_result["combined_count"] == 3

    assert (
        markdown_path.read_text(encoding="utf-8")
        == "# Birleşik Analiz\n"
    )


def test_main_completes_combined_analysis(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    technical_path = tmp_path / "technical.json"
    fundamental_path = tmp_path / "fundamental.json"
    json_output_path = tmp_path / "combined.json"
    report_output_path = tmp_path / "combined.md"

    technical_path.write_text(
        json.dumps(create_technical_summary()),
        encoding="utf-8",
    )

    fundamental_path.write_text(
        json.dumps(create_fundamental_summary()),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "combined_scoring.py",
            "--technical-input",
            str(technical_path),
            "--fundamental-input",
            str(fundamental_path),
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
    assert "Birleştirilen hisse: 3" in terminal_output
    assert "Eşleşmeyen hisse: 2" in terminal_output
    assert (
        "En yüksek birleşik puan: ASELS - 75.5"
        in terminal_output
    )


def test_main_returns_error_when_no_results_match(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    technical_path = tmp_path / "technical.json"
    fundamental_path = tmp_path / "fundamental.json"

    technical_path.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "symbol": "THYAO",
                        "technical_score": 60.0,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    fundamental_path.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "symbol": "ASELS",
                        "fundamental_score": 70.0,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "combined_scoring.py",
            "--technical-input",
            str(technical_path),
            "--fundamental-input",
            str(fundamental_path),
            "--json-output",
            str(tmp_path / "combined.json"),
            "--report-output",
            str(tmp_path / "combined.md"),
        ],
    )

    exit_code = module.main()
    terminal_output = capsys.readouterr().out

    assert exit_code == 1
    assert (
        "Teknik ve temel analiz sonuçları birleştirilemedi"
        in terminal_output
    )


def test_main_returns_error_for_invalid_weights(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    technical_path = tmp_path / "technical.json"
    fundamental_path = tmp_path / "fundamental.json"

    technical_path.write_text(
        json.dumps(create_technical_summary()),
        encoding="utf-8",
    )

    fundamental_path.write_text(
        json.dumps(create_fundamental_summary()),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "combined_scoring.py",
            "--technical-input",
            str(technical_path),
            "--fundamental-input",
            str(fundamental_path),
            "--technical-weight",
            "0.70",
            "--fundamental-weight",
            "0.40",
        ],
    )

    exit_code = module.main()
    terminal_output = capsys.readouterr().out

    assert exit_code == 1
    assert "HATA" in terminal_output
    assert (
        "ağırlıklarının toplamı 1 olmalıdır"
        in terminal_output
    )