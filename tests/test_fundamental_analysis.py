from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

import src.fundamental_analysis as module
from src.fundamental_analysis import (
    build_fundamental_result,
    build_markdown_report,
    calculate_component_scores,
    calculate_data_confidence,
    calculate_fundamental_score,
    extract_company_metadata,
    extract_fundamental_metrics,
    fetch_company_info,
    format_number,
    format_percentage,
    fundamental_score_label,
    run_fundamental_analysis,
    safe_number,
    safe_text,
    save_json_result,
    save_markdown_report,
    score_current_ratio,
    score_debt_to_equity,
    score_growth,
    score_margin,
    score_pe,
    score_price_to_book,
    score_quick_ratio,
    score_return_on_equity,
)


def create_company_info() -> dict[str, object]:
    return {
        "longName": "Türk Hava Yolları A.O.",
        "shortName": "THYAO",
        "sector": "Industrials",
        "industry": "Airlines",
        "country": "Türkiye",
        "currency": "TRY",
        "website": "https://www.turkishairlines.com",
        "marketCap": 450_000_000_000,
        "enterpriseValue": 500_000_000_000,
        "trailingPE": 10.0,
        "forwardPE": 9.0,
        "priceToBook": 1.5,
        "enterpriseToEbitda": 5.5,
        "returnOnEquity": 0.22,
        "returnOnAssets": 0.08,
        "profitMargins": 0.12,
        "operatingMargins": 0.18,
        "grossMargins": 0.30,
        "revenueGrowth": 0.15,
        "earningsGrowth": 0.25,
        "earningsQuarterlyGrowth": 0.20,
        "debtToEquity": 40.0,
        "currentRatio": 1.8,
        "quickRatio": 1.2,
        "dividendYield": 0.025,
        "payoutRatio": 0.30,
        "beta": 1.15,
        "totalRevenue": 700_000_000_000,
        "ebitda": 120_000_000_000,
        "totalCash": 100_000_000_000,
        "totalDebt": 150_000_000_000,
        "freeCashflow": 45_000_000_000,
        "operatingCashflow": 90_000_000_000,
    }


def test_safe_number_accepts_real_numbers() -> None:
    assert safe_number(10) == 10.0
    assert safe_number(3.25) == 3.25


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


def test_safe_text_cleans_text() -> None:
    assert safe_text("  THYAO  ") == "THYAO"
    assert safe_text("") is None
    assert safe_text("   ") is None
    assert safe_text(123) is None


def test_extract_company_metadata() -> None:
    metadata = extract_company_metadata(
        create_company_info()
    )

    assert metadata["name"] == "Türk Hava Yolları A.O."
    assert metadata["sector"] == "Industrials"
    assert metadata["industry"] == "Airlines"
    assert metadata["currency"] == "TRY"


def test_extract_company_metadata_uses_short_name() -> None:
    company_info = create_company_info()
    company_info["longName"] = None

    metadata = extract_company_metadata(company_info)

    assert metadata["name"] == "THYAO"


def test_extract_fundamental_metrics() -> None:
    metrics = extract_fundamental_metrics(
        create_company_info()
    )

    assert metrics["trailing_pe"] == 10.0
    assert metrics["price_to_book"] == 1.5
    assert metrics["return_on_equity"] == 0.22
    assert metrics["revenue_growth"] == 0.15
    assert metrics["debt_to_equity"] == 40.0
    assert metrics["free_cashflow"] == 45_000_000_000.0


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (5.0, 100.0),
        (10.0, 90.0),
        (15.0, 80.0),
        (20.0, 65.0),
        (25.0, 50.0),
        (35.0, 30.0),
        (50.0, 15.0),
        (-2.0, 10.0),
        (None, None),
    ],
)
def test_score_pe(
    value: float | None,
    expected: float | None,
) -> None:
    assert score_pe(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.8, 100.0),
        (1.5, 85.0),
        (2.5, 70.0),
        (4.0, 50.0),
        (7.0, 30.0),
        (10.0, 15.0),
        (-1.0, 10.0),
        (None, None),
    ],
)
def test_score_price_to_book(
    value: float | None,
    expected: float | None,
) -> None:
    assert score_price_to_book(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.35, 100.0),
        (0.22, 90.0),
        (0.16, 80.0),
        (0.12, 65.0),
        (0.07, 45.0),
        (0.02, 25.0),
        (-0.05, 10.0),
        (None, None),
    ],
)
def test_score_return_on_equity(
    value: float | None,
    expected: float | None,
) -> None:
    assert score_return_on_equity(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.30, 100.0),
        (0.18, 85.0),
        (0.12, 70.0),
        (0.07, 55.0),
        (0.02, 35.0),
        (0.0, 20.0),
        (-0.05, 10.0),
        (None, None),
    ],
)
def test_score_margin(
    value: float | None,
    expected: float | None,
) -> None:
    assert score_margin(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.35, 100.0),
        (0.25, 90.0),
        (0.15, 75.0),
        (0.07, 65.0),
        (0.02, 50.0),
        (-0.05, 35.0),
        (-0.20, 20.0),
        (-0.40, 10.0),
        (None, None),
    ],
)
def test_score_growth(
    value: float | None,
    expected: float | None,
) -> None:
    assert score_growth(value) == expected


def test_financial_health_scoring_functions() -> None:
    assert score_debt_to_equity(20.0) == 100.0
    assert score_debt_to_equity(50.0) == 85.0
    assert score_debt_to_equity(90.0) == 70.0
    assert score_debt_to_equity(200.0) == 30.0

    assert score_current_ratio(2.2) == 100.0
    assert score_current_ratio(1.7) == 85.0
    assert score_current_ratio(1.2) == 65.0
    assert score_current_ratio(0.5) == 20.0

    assert score_quick_ratio(1.7) == 100.0
    assert score_quick_ratio(1.2) == 85.0
    assert score_quick_ratio(0.8) == 65.0
    assert score_quick_ratio(0.3) == 20.0


def test_calculate_component_scores() -> None:
    metrics = extract_fundamental_metrics(
        create_company_info()
    )

    scores = calculate_component_scores(metrics)

    assert scores["valuation_score"] == 88.33
    assert scores["profitability_score"] == 81.67
    assert scores["growth_score"] == 82.5
    assert scores["financial_health_score"] == 85.0


def test_calculate_data_confidence_is_full() -> None:
    metrics = extract_fundamental_metrics(
        create_company_info()
    )

    assert calculate_data_confidence(metrics) == 100.0


def test_calculate_data_confidence_with_missing_data() -> None:
    metrics = extract_fundamental_metrics(
        create_company_info()
    )

    metrics["trailing_pe"] = None
    metrics["forward_pe"] = None
    metrics["price_to_book"] = None

    assert calculate_data_confidence(metrics) == 72.73


def test_calculate_fundamental_score() -> None:
    metrics = extract_fundamental_metrics(
        create_company_info()
    )

    component_scores = calculate_component_scores(
        metrics
    )

    score = calculate_fundamental_score(
        component_scores=component_scores,
        data_confidence=100.0,
    )

    assert score == 84.21


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
def test_fundamental_score_label(
    score: float,
    expected: str,
) -> None:
    assert fundamental_score_label(score) == expected


def test_build_fundamental_result() -> None:
    result = build_fundamental_result(
        symbol="thyao",
        company_info=create_company_info(),
    )

    assert result["symbol"] == "THYAO"
    assert result["yahoo_symbol"] == "THYAO.IS"
    assert result["fundamental_score"] == 84.21
    assert result["data_confidence"] == 100.0
    assert result["label"] == "GÜÇLÜ"

    company = result["company"]

    assert isinstance(company, dict)
    assert company["name"] == "Türk Hava Yolları A.O."


def test_fetch_company_info(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_symbols: list[str] = []

    class FakeTicker:
        def __init__(self, symbol: str) -> None:
            captured_symbols.append(symbol)

        def get_info(self) -> dict[str, object]:
            return create_company_info()

    monkeypatch.setattr(
        module.yf,
        "Ticker",
        FakeTicker,
    )

    result = fetch_company_info("THYAO")

    assert captured_symbols == ["THYAO.IS"]
    assert result["longName"] == "Türk Hava Yolları A.O."


def test_fetch_company_info_rejects_empty_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeTicker:
        def __init__(self, symbol: str) -> None:
            self.symbol = symbol

        def get_info(self) -> dict[str, object]:
            return {}

    monkeypatch.setattr(
        module.yf,
        "Ticker",
        FakeTicker,
    )

    with pytest.raises(
        ValueError,
        match="şirket bilgisi bulunamadı",
    ):
        fetch_company_info("THYAO")


def test_run_fundamental_analysis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        module,
        "fetch_company_info",
        lambda symbol: create_company_info(),
    )

    result = run_fundamental_analysis("THYAO")

    assert result["symbol"] == "THYAO"
    assert result["fundamental_score"] == 84.21


def test_format_functions() -> None:
    assert format_number(1234.567) == "1,234.57"
    assert format_number(1234.567, 0) == "1,235"
    assert format_number(None) == "Veri yok"

    assert format_percentage(0.125) == "12.50%"
    assert format_percentage(None) == "Veri yok"


def test_build_markdown_report() -> None:
    result = build_fundamental_result(
        symbol="THYAO",
        company_info=create_company_info(),
    )

    markdown = build_markdown_report(result)

    assert "# THYAO Temel Analiz Raporu" in markdown
    assert "Türk Hava Yolları A.O." in markdown
    assert "**84.21 / 100**" in markdown
    assert "Değerlendirme: **GÜÇLÜ**" in markdown
    assert "| F/K | 10.00 |" in markdown
    assert "| Özsermaye kârlılığı | 22.00% |" in markdown
    assert "yatırım tavsiyesi değildir" in markdown


def test_save_analysis_files(
    tmp_path: Path,
) -> None:
    result = build_fundamental_result(
        symbol="THYAO",
        company_info=create_company_info(),
    )

    json_path = tmp_path / "reports" / "result.json"
    markdown_path = tmp_path / "reports" / "result.md"

    save_json_result(
        analysis_result=result,
        output_path=json_path,
    )

    save_markdown_report(
        markdown_report="# Temel Analiz\n",
        output_path=markdown_path,
    )

    assert json_path.exists()
    assert markdown_path.exists()

    saved_result = json.loads(
        json_path.read_text(encoding="utf-8")
    )

    assert saved_result["symbol"] == "THYAO"
    assert saved_result["fundamental_score"] == 84.21

    assert (
        markdown_path.read_text(encoding="utf-8")
        == "# Temel Analiz\n"
    )


def test_main_completes_fundamental_analysis(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    json_path = tmp_path / "fundamental.json"
    markdown_path = tmp_path / "fundamental.md"

    analysis_result = build_fundamental_result(
        symbol="THYAO",
        company_info=create_company_info(),
    )

    monkeypatch.setattr(
        module,
        "run_fundamental_analysis",
        lambda symbol: analysis_result,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "fundamental_analysis.py",
            "THYAO",
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
    assert "Hisse: THYAO" in terminal_output
    assert "Temel puan: 84.21" in terminal_output
    assert "Veri güveni: 100.0%" in terminal_output


def test_main_returns_error_for_invalid_symbol(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "fundamental_analysis.py",
            "THY AO",
        ],
    )

    exit_code = module.main()
    terminal_output = capsys.readouterr().out

    assert exit_code == 1
    assert "HATA" in terminal_output
    assert "Geçersiz hisse kodu" in terminal_output