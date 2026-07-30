from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from src.technical_report import (
    build_markdown_report,
    format_number,
    load_analysis,
    main,
    save_report,
    score_label,
)


@pytest.fixture
def sample_analysis() -> dict:
    return {
        "symbol": "TEST",
        "analysis_date": "2026-07-30T16:30:00+03:00",
        "price_date": "2026-07-29T00:00:00",
        "record_count": 180,
        "indicators": {
            "close": 165.25,
            "sma_20": 160.10,
            "ema_20": 161.20,
            "ema_50": 150.40,
            "rsi_14": 61.50,
            "macd": 2.1456,
            "macd_signal": 1.8456,
            "macd_histogram": 0.3000,
            "bollinger_upper": 170.00,
            "bollinger_middle": 160.10,
            "bollinger_lower": 150.20,
            "atr_14": 3.20,
            "adx": 28.50,
            "positive_di": 32.00,
            "negative_di": 18.00,
            "relative_volume_20": 1.35,
        },
        "technical_analysis": {
            "score": 68.70,
            "technical_score": 68.70,
            "trend_score": 82.00,
            "momentum_score": 72.00,
            "volume_score": 68.00,
            "volatility_score": 55.00,
            "confidence_score": 100.00,
            "signals": [
                "Fiyat EMA20 üzerinde.",
                "EMA20, EMA50 üzerinde.",
            ],
            "warnings": [
                "İşlem hacmi sınırlı olabilir.",
            ],
        },
    }


def test_load_analysis_reads_valid_json(
    tmp_path: Path,
    sample_analysis: dict,
) -> None:
    input_path = tmp_path / "analysis.json"

    input_path.write_text(
        json.dumps(sample_analysis),
        encoding="utf-8",
    )

    result = load_analysis(input_path)

    assert result == sample_analysis
    assert result["symbol"] == "TEST"


def test_missing_analysis_file_raises_error(
    tmp_path: Path,
) -> None:
    missing_path = tmp_path / "missing.json"

    with pytest.raises(
        FileNotFoundError,
        match="Teknik analiz dosyası bulunamadı",
    ):
        load_analysis(missing_path)


def test_invalid_json_raises_error(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "invalid.json"

    input_path.write_text(
        "{geçersiz-json",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="geçerli bir JSON değil",
    ):
        load_analysis(input_path)


def test_missing_required_field_raises_error(
    tmp_path: Path,
    sample_analysis: dict,
) -> None:
    input_path = tmp_path / "incomplete.json"

    incomplete_analysis = sample_analysis.copy()
    incomplete_analysis.pop("indicators")

    input_path.write_text(
        json.dumps(incomplete_analysis),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="eksik alanlar var",
    ):
        load_analysis(input_path)


def test_format_number_handles_numeric_values() -> None:
    assert format_number(68.704) == "68.70"
    assert format_number(2.14567, 4) == "2.1457"


def test_format_number_handles_none() -> None:
    assert format_number(None) == "Veri yok"


@pytest.mark.parametrize(
    ("score", "expected_label"),
    [
        (85, "Güçlü pozitif"),
        (70, "Pozitif"),
        (55, "Nötr"),
        (40, "Negatif"),
        (20, "Güçlü negatif"),
    ],
)
def test_score_label(
    score: float,
    expected_label: str,
) -> None:
    assert score_label(score) == expected_label


def test_build_markdown_report_contains_expected_sections(
    sample_analysis: dict,
) -> None:
    report = build_markdown_report(sample_analysis)

    assert "# TEST Teknik Analiz Raporu" in report
    assert "## Analiz bilgileri" in report
    assert "## Teknik değerlendirme" in report
    assert "## Alt puanlar" in report
    assert "## Güncel indikatörler" in report
    assert "## Olumlu ve nötr sinyaller" in report
    assert "## Riskler ve uyarılar" in report
    assert "## Sonuç" in report
    assert "68.70 / 100" in report
    assert "Pozitif" in report


def test_build_markdown_report_contains_signals_and_warnings(
    sample_analysis: dict,
) -> None:
    report = build_markdown_report(sample_analysis)

    assert "Fiyat EMA20 üzerinde." in report
    assert "EMA20, EMA50 üzerinde." in report
    assert "İşlem hacmi sınırlı olabilir." in report


def test_save_report_creates_markdown_file(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "technical_report.md"

    report_text = "# Test Raporu\n"

    save_report(
        report_text=report_text,
        output_path=output_path,
    )

    assert output_path.exists()
    assert output_path.read_text(
        encoding="utf-8",
    ) == report_text


def test_main_creates_markdown_report(
    tmp_path: Path,
    sample_analysis: dict,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_path = tmp_path / "analysis.json"
    output_path = tmp_path / "report.md"

    input_path.write_text(
        json.dumps(sample_analysis),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "technical_report.py",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
        ],
    )

    exit_code = main()
    terminal_output = capsys.readouterr().out

    assert exit_code == 0
    assert output_path.exists()
    assert "BAŞARILI" in terminal_output
    assert "TEST" in terminal_output

    report_content = output_path.read_text(
        encoding="utf-8",
    )

    assert "# TEST Teknik Analiz Raporu" in report_content


def test_main_returns_error_for_missing_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_path = tmp_path / "missing.json"
    output_path = tmp_path / "report.md"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "technical_report.py",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
        ],
    )

    exit_code = main()
    terminal_output = capsys.readouterr().out

    assert exit_code == 1
    assert "HATA" in terminal_output
    assert not output_path.exists()