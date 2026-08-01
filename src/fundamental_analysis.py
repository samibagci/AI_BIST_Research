from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from numbers import Real
from pathlib import Path

import yfinance as yf


PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.download_bist_prices import normalize_bist_symbol


DEFAULT_REPORT_DIRECTORY = Path("reports")

VALUATION_WEIGHT = 0.25
PROFITABILITY_WEIGHT = 0.30
GROWTH_WEIGHT = 0.25
FINANCIAL_HEALTH_WEIGHT = 0.20


SCORED_METRICS = [
    "trailing_pe",
    "forward_pe",
    "price_to_book",
    "return_on_equity",
    "profit_margin",
    "operating_margin",
    "revenue_growth",
    "earnings_growth",
    "debt_to_equity",
    "current_ratio",
    "quick_ratio",
]


def safe_number(
    value: object,
) -> float | None:
    if isinstance(value, bool):
        return None

    if not isinstance(value, Real):
        return None

    numeric_value = float(value)

    if not math.isfinite(numeric_value):
        return None

    return numeric_value


def safe_text(
    value: object,
) -> str | None:
    if not isinstance(value, str):
        return None

    cleaned_value = value.strip()

    if not cleaned_value:
        return None

    return cleaned_value


def fetch_company_info(
    symbol: str,
) -> dict[str, object]:
    yahoo_symbol = normalize_bist_symbol(symbol)

    ticker = yf.Ticker(yahoo_symbol)
    company_info = ticker.get_info()

    if not isinstance(company_info, dict):
        raise ValueError(
            f"{yahoo_symbol} için şirket bilgisi alınamadı."
        )

    if not company_info:
        raise ValueError(
            f"{yahoo_symbol} için şirket bilgisi bulunamadı."
        )

    return company_info


def extract_company_metadata(
    company_info: dict[str, object],
) -> dict[str, object]:
    return {
        "name": (
            safe_text(company_info.get("longName"))
            or safe_text(company_info.get("shortName"))
        ),
        "sector": safe_text(
            company_info.get("sector")
        ),
        "industry": safe_text(
            company_info.get("industry")
        ),
        "country": safe_text(
            company_info.get("country")
        ),
        "currency": safe_text(
            company_info.get("currency")
        ),
        "website": safe_text(
            company_info.get("website")
        ),
    }


def extract_fundamental_metrics(
    company_info: dict[str, object],
) -> dict[str, float | None]:
    return {
        "market_cap": safe_number(
            company_info.get("marketCap")
        ),
        "enterprise_value": safe_number(
            company_info.get("enterpriseValue")
        ),
        "trailing_pe": safe_number(
            company_info.get("trailingPE")
        ),
        "forward_pe": safe_number(
            company_info.get("forwardPE")
        ),
        "price_to_book": safe_number(
            company_info.get("priceToBook")
        ),
        "enterprise_to_ebitda": safe_number(
            company_info.get("enterpriseToEbitda")
        ),
        "return_on_equity": safe_number(
            company_info.get("returnOnEquity")
        ),
        "return_on_assets": safe_number(
            company_info.get("returnOnAssets")
        ),
        "profit_margin": safe_number(
            company_info.get("profitMargins")
        ),
        "operating_margin": safe_number(
            company_info.get("operatingMargins")
        ),
        "gross_margin": safe_number(
            company_info.get("grossMargins")
        ),
        "revenue_growth": safe_number(
            company_info.get("revenueGrowth")
        ),
        "earnings_growth": safe_number(
            company_info.get("earningsGrowth")
        ),
        "earnings_quarterly_growth": safe_number(
            company_info.get(
                "earningsQuarterlyGrowth"
            )
        ),
        "debt_to_equity": safe_number(
            company_info.get("debtToEquity")
        ),
        "current_ratio": safe_number(
            company_info.get("currentRatio")
        ),
        "quick_ratio": safe_number(
            company_info.get("quickRatio")
        ),
        "dividend_yield": safe_number(
            company_info.get("dividendYield")
        ),
        "payout_ratio": safe_number(
            company_info.get("payoutRatio")
        ),
        "beta": safe_number(
            company_info.get("beta")
        ),
        "total_revenue": safe_number(
            company_info.get("totalRevenue")
        ),
        "ebitda": safe_number(
            company_info.get("ebitda")
        ),
        "total_cash": safe_number(
            company_info.get("totalCash")
        ),
        "total_debt": safe_number(
            company_info.get("totalDebt")
        ),
        "free_cashflow": safe_number(
            company_info.get("freeCashflow")
        ),
        "operating_cashflow": safe_number(
            company_info.get("operatingCashflow")
        ),
    }


def score_pe(
    value: float | None,
) -> float | None:
    if value is None:
        return None

    if value <= 0:
        return 10.0

    if value <= 8:
        return 100.0

    if value <= 12:
        return 90.0

    if value <= 16:
        return 80.0

    if value <= 22:
        return 65.0

    if value <= 30:
        return 50.0

    if value <= 40:
        return 30.0

    return 15.0


def score_price_to_book(
    value: float | None,
) -> float | None:
    if value is None:
        return None

    if value <= 0:
        return 10.0

    if value <= 1:
        return 100.0

    if value <= 2:
        return 85.0

    if value <= 3:
        return 70.0

    if value <= 5:
        return 50.0

    if value <= 8:
        return 30.0

    return 15.0


def score_return_on_equity(
    value: float | None,
) -> float | None:
    if value is None:
        return None

    if value < 0:
        return 10.0

    if value >= 0.30:
        return 100.0

    if value >= 0.20:
        return 90.0

    if value >= 0.15:
        return 80.0

    if value >= 0.10:
        return 65.0

    if value >= 0.05:
        return 45.0

    return 25.0


def score_margin(
    value: float | None,
) -> float | None:
    if value is None:
        return None

    if value < 0:
        return 10.0

    if value >= 0.25:
        return 100.0

    if value >= 0.15:
        return 85.0

    if value >= 0.10:
        return 70.0

    if value >= 0.05:
        return 55.0

    if value > 0:
        return 35.0

    return 20.0


def score_growth(
    value: float | None,
) -> float | None:
    if value is None:
        return None

    if value >= 0.30:
        return 100.0

    if value >= 0.20:
        return 90.0

    if value >= 0.10:
        return 75.0

    if value >= 0.05:
        return 65.0

    if value >= 0:
        return 50.0

    if value >= -0.10:
        return 35.0

    if value >= -0.25:
        return 20.0

    return 10.0


def score_debt_to_equity(
    value: float | None,
) -> float | None:
    if value is None:
        return None

    if value < 0:
        return 10.0

    if value <= 30:
        return 100.0

    if value <= 60:
        return 85.0

    if value <= 100:
        return 70.0

    if value <= 150:
        return 50.0

    if value <= 250:
        return 30.0

    return 15.0


def score_current_ratio(
    value: float | None,
) -> float | None:
    if value is None:
        return None

    if value >= 2:
        return 100.0

    if value >= 1.5:
        return 85.0

    if value >= 1:
        return 65.0

    if value >= 0.75:
        return 40.0

    return 20.0


def score_quick_ratio(
    value: float | None,
) -> float | None:
    if value is None:
        return None

    if value >= 1.5:
        return 100.0

    if value >= 1:
        return 85.0

    if value >= 0.75:
        return 65.0

    if value >= 0.5:
        return 40.0

    return 20.0


def average_scores(
    scores: list[float | None],
) -> float:
    available_scores = [
        float(score)
        for score in scores
        if score is not None
    ]

    if not available_scores:
        return 0.0

    return round(
        sum(available_scores)
        / len(available_scores),
        2,
    )


def calculate_component_scores(
    metrics: dict[str, float | None],
) -> dict[str, float]:
    valuation_score = average_scores(
        [
            score_pe(metrics["trailing_pe"]),
            score_pe(metrics["forward_pe"]),
            score_price_to_book(
                metrics["price_to_book"]
            ),
        ]
    )

    profitability_score = average_scores(
        [
            score_return_on_equity(
                metrics["return_on_equity"]
            ),
            score_margin(
                metrics["profit_margin"]
            ),
            score_margin(
                metrics["operating_margin"]
            ),
        ]
    )

    growth_score = average_scores(
        [
            score_growth(
                metrics["revenue_growth"]
            ),
            score_growth(
                metrics["earnings_growth"]
            ),
        ]
    )

    financial_health_score = average_scores(
        [
            score_debt_to_equity(
                metrics["debt_to_equity"]
            ),
            score_current_ratio(
                metrics["current_ratio"]
            ),
            score_quick_ratio(
                metrics["quick_ratio"]
            ),
        ]
    )

    return {
        "valuation_score": valuation_score,
        "profitability_score": profitability_score,
        "growth_score": growth_score,
        "financial_health_score": (
            financial_health_score
        ),
    }


def calculate_data_confidence(
    metrics: dict[str, float | None],
) -> float:
    available_count = sum(
        1
        for metric_name in SCORED_METRICS
        if metrics.get(metric_name) is not None
    )

    return round(
        available_count
        / len(SCORED_METRICS)
        * 100,
        2,
    )


def calculate_fundamental_score(
    component_scores: dict[str, float],
    data_confidence: float,
) -> float:
    raw_score = (
        component_scores["valuation_score"]
        * VALUATION_WEIGHT
        + component_scores["profitability_score"]
        * PROFITABILITY_WEIGHT
        + component_scores["growth_score"]
        * GROWTH_WEIGHT
        + component_scores[
            "financial_health_score"
        ]
        * FINANCIAL_HEALTH_WEIGHT
    )

    confidence_multiplier = (
        0.70
        + 0.30
        * data_confidence
        / 100
    )

    return round(
        raw_score * confidence_multiplier,
        2,
    )


def fundamental_score_label(
    score: float,
) -> str:
    if score >= 75:
        return "GÜÇLÜ"

    if score >= 60:
        return "OLUMLU"

    if score >= 45:
        return "NÖTR"

    if score >= 30:
        return "ZAYIF"

    return "ÇOK ZAYIF"


def build_notes(
    metrics: dict[str, float | None],
    data_confidence: float,
) -> list[str]:
    notes: list[str] = []

    missing_metrics = [
        metric_name
        for metric_name in SCORED_METRICS
        if metrics.get(metric_name) is None
    ]

    if missing_metrics:
        notes.append(
            "Eksik puanlama verileri: "
            + ", ".join(missing_metrics)
        )

    if data_confidence < 60:
        notes.append(
            "Veri güveni düşük olduğu için temel puan "
            "dikkatli değerlendirilmelidir."
        )

    notes.append(
        "Oranların anlamı sektörlere göre değişebilir; "
        "şirketler kendi sektörleriyle karşılaştırılmalıdır."
    )

    notes.append(
        "Bu sonuç yalnızca temel finansal göstergelere "
        "dayalı araştırma çıktısıdır."
    )

    return notes


def build_fundamental_result(
    symbol: str,
    company_info: dict[str, object],
) -> dict[str, object]:
    yahoo_symbol = normalize_bist_symbol(symbol)
    base_symbol = yahoo_symbol.removesuffix(".IS")

    company_metadata = extract_company_metadata(
        company_info
    )

    metrics = extract_fundamental_metrics(
        company_info
    )

    component_scores = calculate_component_scores(
        metrics
    )

    data_confidence = calculate_data_confidence(
        metrics
    )

    fundamental_score = calculate_fundamental_score(
        component_scores=component_scores,
        data_confidence=data_confidence,
    )

    return {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "symbol": base_symbol,
        "yahoo_symbol": yahoo_symbol,
        "company": company_metadata,
        "metrics": metrics,
        "component_scores": component_scores,
        "fundamental_score": fundamental_score,
        "data_confidence": data_confidence,
        "label": fundamental_score_label(
            fundamental_score
        ),
        "notes": build_notes(
            metrics=metrics,
            data_confidence=data_confidence,
        ),
    }


def run_fundamental_analysis(
    symbol: str,
) -> dict[str, object]:
    company_info = fetch_company_info(symbol)

    return build_fundamental_result(
        symbol=symbol,
        company_info=company_info,
    )


def format_number(
    value: object,
    decimal_places: int = 2,
) -> str:
    numeric_value = safe_number(value)

    if numeric_value is None:
        return "Veri yok"

    return f"{numeric_value:,.{decimal_places}f}"


def format_percentage(
    value: object,
) -> str:
    numeric_value = safe_number(value)

    if numeric_value is None:
        return "Veri yok"

    return f"{numeric_value * 100:.2f}%"


def build_markdown_report(
    analysis_result: dict[str, object],
) -> str:
    symbol = analysis_result["symbol"]
    generated_at = analysis_result["generated_at"]
    company = analysis_result["company"]
    metrics = analysis_result["metrics"]
    component_scores = analysis_result[
        "component_scores"
    ]
    fundamental_score = analysis_result[
        "fundamental_score"
    ]
    data_confidence = analysis_result[
        "data_confidence"
    ]
    label = analysis_result["label"]
    notes = analysis_result["notes"]

    if not isinstance(company, dict):
        raise ValueError(
            "Şirket bilgileri kullanılamıyor."
        )

    if not isinstance(metrics, dict):
        raise ValueError(
            "Temel analiz metrikleri kullanılamıyor."
        )

    if not isinstance(component_scores, dict):
        raise ValueError(
            "Temel analiz bileşenleri kullanılamıyor."
        )

    lines = [
        f"# {symbol} Temel Analiz Raporu",
        "",
        f"- Oluşturulma zamanı: {generated_at}",
        (
            "- Şirket: "
            f"{company.get('name') or 'Veri yok'}"
        ),
        (
            "- Sektör: "
            f"{company.get('sector') or 'Veri yok'}"
        ),
        (
            "- Endüstri: "
            f"{company.get('industry') or 'Veri yok'}"
        ),
        (
            "- Para birimi: "
            f"{company.get('currency') or 'Veri yok'}"
        ),
        "",
        "## Genel Sonuç",
        "",
        (
            f"- Temel puan: "
            f"**{float(fundamental_score):.2f} / 100**"
        ),
        f"- Değerlendirme: **{label}**",
        (
            f"- Veri güveni: "
            f"**{float(data_confidence):.2f}%**"
        ),
        "",
        "## Bileşen Puanları",
        "",
        "| Bileşen | Puan | Ağırlık |",
        "|---|---:|---:|",
        (
            "| Değerleme "
            f"| {float(component_scores['valuation_score']):.2f} "
            f"| {VALUATION_WEIGHT * 100:.0f}% |"
        ),
        (
            "| Kârlılık "
            f"| {float(component_scores['profitability_score']):.2f} "
            f"| {PROFITABILITY_WEIGHT * 100:.0f}% |"
        ),
        (
            "| Büyüme "
            f"| {float(component_scores['growth_score']):.2f} "
            f"| {GROWTH_WEIGHT * 100:.0f}% |"
        ),
        (
            "| Finansal sağlık "
            f"| {float(component_scores['financial_health_score']):.2f} "
            f"| {FINANCIAL_HEALTH_WEIGHT * 100:.0f}% |"
        ),
        "",
        "## Değerleme Göstergeleri",
        "",
        "| Gösterge | Değer |",
        "|---|---:|",
        (
            "| F/K "
            f"| {format_number(metrics.get('trailing_pe'))} |"
        ),
        (
            "| İleri F/K "
            f"| {format_number(metrics.get('forward_pe'))} |"
        ),
        (
            "| Piyasa değeri / Defter değeri "
            f"| {format_number(metrics.get('price_to_book'))} |"
        ),
        (
            "| Firma değeri / FAVÖK "
            f"| {format_number(metrics.get('enterprise_to_ebitda'))} |"
        ),
        "",
        "## Kârlılık ve Büyüme",
        "",
        "| Gösterge | Değer |",
        "|---|---:|",
        (
            "| Özsermaye kârlılığı "
            f"| {format_percentage(metrics.get('return_on_equity'))} |"
        ),
        (
            "| Net kâr marjı "
            f"| {format_percentage(metrics.get('profit_margin'))} |"
        ),
        (
            "| Faaliyet kâr marjı "
            f"| {format_percentage(metrics.get('operating_margin'))} |"
        ),
        (
            "| Gelir büyümesi "
            f"| {format_percentage(metrics.get('revenue_growth'))} |"
        ),
        (
            "| Kâr büyümesi "
            f"| {format_percentage(metrics.get('earnings_growth'))} |"
        ),
        "",
        "## Finansal Sağlık",
        "",
        "| Gösterge | Değer |",
        "|---|---:|",
        (
            "| Borç / Özsermaye "
            f"| {format_number(metrics.get('debt_to_equity'))} |"
        ),
        (
            "| Cari oran "
            f"| {format_number(metrics.get('current_ratio'))} |"
        ),
        (
            "| Likidite oranı "
            f"| {format_number(metrics.get('quick_ratio'))} |"
        ),
        (
            "| Serbest nakit akışı "
            f"| {format_number(metrics.get('free_cashflow'), 0)} |"
        ),
        "",
        "## Diğer Göstergeler",
        "",
        "| Gösterge | Değer |",
        "|---|---:|",
        (
            "| Piyasa değeri "
            f"| {format_number(metrics.get('market_cap'), 0)} |"
        ),
        (
            "| Toplam gelir "
            f"| {format_number(metrics.get('total_revenue'), 0)} |"
        ),
        (
            "| FAVÖK "
            f"| {format_number(metrics.get('ebitda'), 0)} |"
        ),
        (
            "| Temettü verimi "
            f"| {format_percentage(metrics.get('dividend_yield'))} |"
        ),
        (
            "| Beta "
            f"| {format_number(metrics.get('beta'))} |"
        ),
        "",
        "## Notlar",
        "",
    ]

    if isinstance(notes, list):
        for note in notes:
            lines.append(f"- {note}")

    lines.extend(
        [
            "",
            (
                "> Bu rapor araştırma amacıyla "
                "oluşturulmuştur ve yatırım tavsiyesi değildir."
            ),
            "",
        ]
    )

    return "\n".join(lines)


def save_json_result(
    analysis_result: dict[str, object],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            analysis_result,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def save_markdown_report(
    markdown_report: str,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        markdown_report,
        encoding="utf-8",
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Yahoo Finance verileriyle BIST şirketi "
            "temel analizi yapar."
        )
    )

    parser.add_argument(
        "symbol",
        help="BIST hisse kodu. Örnek: THYAO",
    )

    parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
        help="JSON analiz sonucunun yolu.",
    )

    parser.add_argument(
        "--report-output",
        type=Path,
        default=None,
        help="Markdown analiz raporunun yolu.",
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        yahoo_symbol = normalize_bist_symbol(
            arguments.symbol
        )
        base_symbol = yahoo_symbol.removesuffix(".IS")

        json_output_path = arguments.json_output

        if json_output_path is None:
            json_output_path = (
                DEFAULT_REPORT_DIRECTORY
                / f"{base_symbol}_fundamental_analysis.json"
            )

        markdown_output_path = (
            arguments.report_output
        )

        if markdown_output_path is None:
            markdown_output_path = (
                DEFAULT_REPORT_DIRECTORY
                / f"{base_symbol}_fundamental_analysis.md"
            )

        analysis_result = run_fundamental_analysis(
            symbol=base_symbol
        )

        save_json_result(
            analysis_result=analysis_result,
            output_path=json_output_path,
        )

        markdown_report = build_markdown_report(
            analysis_result
        )

        save_markdown_report(
            markdown_report=markdown_report,
            output_path=markdown_output_path,
        )

        print(
            "BAŞARILI: Temel analiz tamamlandı."
        )
        print(f"Hisse: {base_symbol}")
        print(
            "Temel puan: "
            f"{analysis_result['fundamental_score']}"
        )
        print(
            "Veri güveni: "
            f"{analysis_result['data_confidence']}%"
        )
        print(
            f"JSON sonucu: "
            f"{json_output_path.resolve()}"
        )
        print(
            f"Markdown raporu: "
            f"{markdown_output_path.resolve()}"
        )

        return 0

    except Exception as error:
        print(f"HATA: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())