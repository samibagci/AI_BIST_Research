from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from numbers import Real
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_TECHNICAL_INPUT_PATH = Path(
    "reports/bist_batch_analysis.json"
)
DEFAULT_FUNDAMENTAL_INPUT_PATH = Path(
    "reports/bist_fundamental_batch_analysis.json"
)
DEFAULT_JSON_OUTPUT_PATH = Path(
    "reports/bist_combined_analysis.json"
)
DEFAULT_MARKDOWN_OUTPUT_PATH = Path(
    "reports/bist_combined_analysis.md"
)

DEFAULT_TECHNICAL_WEIGHT = 0.55
DEFAULT_FUNDAMENTAL_WEIGHT = 0.45


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


def load_json_object(
    input_path: Path,
    description: str,
) -> dict[str, object]:
    if not input_path.exists():
        raise FileNotFoundError(
            f"{description} bulunamadı: {input_path}"
        )

    try:
        loaded_data = json.loads(
            input_path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as error:
        raise ValueError(
            f"{description} geçerli JSON değil."
        ) from error

    if not isinstance(loaded_data, dict):
        raise ValueError(
            f"{description} JSON nesnesi olmalıdır."
        )

    return loaded_data


def validate_weights(
    technical_weight: float,
    fundamental_weight: float,
) -> None:
    if technical_weight < 0:
        raise ValueError(
            "Teknik analiz ağırlığı negatif olamaz."
        )

    if fundamental_weight < 0:
        raise ValueError(
            "Temel analiz ağırlığı negatif olamaz."
        )

    total_weight = (
        technical_weight
        + fundamental_weight
    )

    if not math.isclose(
        total_weight,
        1.0,
        rel_tol=1e-9,
        abs_tol=1e-9,
    ):
        raise ValueError(
            "Teknik ve temel analiz ağırlıklarının "
            "toplamı 1 olmalıdır."
        )


def normalize_symbol(
    value: object,
) -> str | None:
    if not isinstance(value, str):
        return None

    normalized_symbol = value.strip().upper()

    if not normalized_symbol:
        return None

    if normalized_symbol.endswith(".IS"):
        normalized_symbol = normalized_symbol[:-3]

    if not normalized_symbol:
        return None

    return normalized_symbol


def extract_score_map(
    summary: dict[str, object],
    score_field: str,
) -> dict[str, dict[str, object]]:
    raw_results = summary.get("results")

    if not isinstance(raw_results, list):
        raise ValueError(
            "Analiz sonuç listesi bulunamadı."
        )

    score_map: dict[str, dict[str, object]] = {}

    for raw_result in raw_results:
        if not isinstance(raw_result, dict):
            continue

        symbol = normalize_symbol(
            raw_result.get("symbol")
        )

        score = safe_number(
            raw_result.get(score_field)
        )

        if symbol is None or score is None:
            continue

        if not 0 <= score <= 100:
            continue

        if symbol in score_map:
            continue

        score_map[symbol] = {
            **raw_result,
            "symbol": symbol,
            score_field: round(score, 2),
        }

    return score_map


def combined_score_label(
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


def combine_analysis_summaries(
    technical_summary: dict[str, object],
    fundamental_summary: dict[str, object],
    technical_weight: float = (
        DEFAULT_TECHNICAL_WEIGHT
    ),
    fundamental_weight: float = (
        DEFAULT_FUNDAMENTAL_WEIGHT
    ),
) -> dict[str, object]:
    validate_weights(
        technical_weight=technical_weight,
        fundamental_weight=fundamental_weight,
    )

    technical_results = extract_score_map(
        summary=technical_summary,
        score_field="technical_score",
    )

    fundamental_results = extract_score_map(
        summary=fundamental_summary,
        score_field="fundamental_score",
    )

    technical_symbols = set(
        technical_results
    )
    fundamental_symbols = set(
        fundamental_results
    )

    common_symbols = (
        technical_symbols
        & fundamental_symbols
    )

    combined_results: list[dict[str, object]] = []

    for symbol in common_symbols:
        technical_result = technical_results[
            symbol
        ]
        fundamental_result = fundamental_results[
            symbol
        ]

        technical_score = float(
            technical_result["technical_score"]
        )

        fundamental_score = float(
            fundamental_result["fundamental_score"]
        )

        combined_score = round(
            technical_score
            * technical_weight
            + fundamental_score
            * fundamental_weight,
            2,
        )

        data_confidence = safe_number(
            fundamental_result.get(
                "data_confidence"
            )
        )

        company_name = fundamental_result.get(
            "company_name"
        )
        sector = fundamental_result.get("sector")

        combined_results.append(
            {
                "rank": 0,
                "symbol": symbol,
                "company_name": (
                    company_name
                    if isinstance(company_name, str)
                    else None
                ),
                "sector": (
                    sector
                    if isinstance(sector, str)
                    else None
                ),
                "technical_score": technical_score,
                "fundamental_score": fundamental_score,
                "combined_score": combined_score,
                "technical_weight": (
                    technical_weight
                ),
                "fundamental_weight": (
                    fundamental_weight
                ),
                "fundamental_data_confidence": (
                    round(data_confidence, 2)
                    if data_confidence is not None
                    else 0.0
                ),
                "label": combined_score_label(
                    combined_score
                ),
                "technical_rank": (
                    technical_result.get("rank")
                ),
                "fundamental_rank": (
                    fundamental_result.get("rank")
                ),
            }
        )

    combined_results.sort(
        key=lambda item: float(
            item["combined_score"]
        ),
        reverse=True,
    )

    for rank, result in enumerate(
        combined_results,
        start=1,
    ):
        result["rank"] = rank

    unmatched_results: list[
        dict[str, str]
    ] = []

    only_technical = (
        technical_symbols
        - fundamental_symbols
    )

    for symbol in sorted(only_technical):
        unmatched_results.append(
            {
                "symbol": symbol,
                "reason": (
                    "Temel analiz sonucu bulunamadı."
                ),
            }
        )

    only_fundamental = (
        fundamental_symbols
        - technical_symbols
    )

    for symbol in sorted(only_fundamental):
        unmatched_results.append(
            {
                "symbol": symbol,
                "reason": (
                    "Teknik analiz sonucu bulunamadı."
                ),
            }
        )

    return {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "technical_source_generated_at": (
            technical_summary.get(
                "generated_at"
            )
        ),
        "fundamental_source_generated_at": (
            fundamental_summary.get(
                "generated_at"
            )
        ),
        "weights": {
            "technical": technical_weight,
            "fundamental": fundamental_weight,
        },
        "technical_count": len(
            technical_results
        ),
        "fundamental_count": len(
            fundamental_results
        ),
        "combined_count": len(
            combined_results
        ),
        "unmatched_count": len(
            unmatched_results
        ),
        "results": combined_results,
        "unmatched": unmatched_results,
    }


def build_markdown_report(
    combined_summary: dict[str, object],
) -> str:
    generated_at = combined_summary[
        "generated_at"
    ]
    weights = combined_summary["weights"]
    combined_count = combined_summary[
        "combined_count"
    ]
    unmatched_count = combined_summary[
        "unmatched_count"
    ]
    results = combined_summary["results"]
    unmatched_results = combined_summary[
        "unmatched"
    ]

    if not isinstance(weights, dict):
        raise ValueError(
            "Birleşik puan ağırlıkları bulunamadı."
        )

    technical_weight = float(
        weights["technical"]
    )
    fundamental_weight = float(
        weights["fundamental"]
    )

    lines = [
        "# BIST Birleşik Analiz Raporu",
        "",
        f"- Oluşturulma zamanı: {generated_at}",
        f"- Birleştirilen hisse: {combined_count}",
        f"- Eşleşmeyen hisse: {unmatched_count}",
        (
            "- Teknik analiz ağırlığı: "
            f"{technical_weight * 100:.0f}%"
        ),
        (
            "- Temel analiz ağırlığı: "
            f"{fundamental_weight * 100:.0f}%"
        ),
        "",
        "## Birleşik Puan Sıralaması",
        "",
    ]

    if isinstance(results, list) and results:
        lines.extend(
            [
                (
                    "| Sıra | Hisse | Teknik puan "
                    "| Temel puan | Birleşik puan "
                    "| Veri güveni | Sonuç |"
                ),
                "|---:|---|---:|---:|---:|---:|---|",
            ]
        )

        for result in results:
            if not isinstance(result, dict):
                continue

            lines.append(
                f"| {result['rank']} "
                f"| {result['symbol']} "
                f"| {float(result['technical_score']):.2f} "
                f"| {float(result['fundamental_score']):.2f} "
                f"| {float(result['combined_score']):.2f} "
                f"| {float(result['fundamental_data_confidence']):.2f}% "
                f"| {result['label']} |"
            )
    else:
        lines.append(
            "Birleştirilebilen analiz sonucu bulunamadı."
        )

    lines.extend(
        [
            "",
            "## Eşleşmeyen Sonuçlar",
            "",
        ]
    )

    if (
        isinstance(unmatched_results, list)
        and unmatched_results
    ):
        for unmatched_result in unmatched_results:
            if not isinstance(
                unmatched_result,
                dict,
            ):
                continue

            lines.append(
                f"- **{unmatched_result['symbol']}**: "
                f"{unmatched_result['reason']}"
            )
    else:
        lines.append(
            "Eşleşmeyen analiz sonucu bulunmuyor."
        )

    lines.extend(
        [
            "",
            (
                "> Birleşik puan; teknik analiz puanının "
                f"%{technical_weight * 100:.0f}'i ile temel "
                "analiz puanının "
                f"%{fundamental_weight * 100:.0f}'inin "
                "birleşimidir."
            ),
            (
                "> Bu rapor araştırma amacıyla "
                "oluşturulmuştur ve yatırım tavsiyesi değildir."
            ),
            "",
        ]
    )

    return "\n".join(lines)


def save_json_result(
    combined_summary: dict[str, object],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            combined_summary,
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
            "BIST teknik ve temel analiz puanlarını "
            "tek birleşik puanda toplar."
        )
    )

    parser.add_argument(
        "--technical-input",
        type=Path,
        default=DEFAULT_TECHNICAL_INPUT_PATH,
        help="Toplu teknik analiz JSON dosyasının yolu.",
    )

    parser.add_argument(
        "--fundamental-input",
        type=Path,
        default=DEFAULT_FUNDAMENTAL_INPUT_PATH,
        help="Toplu temel analiz JSON dosyasının yolu.",
    )

    parser.add_argument(
        "--json-output",
        type=Path,
        default=DEFAULT_JSON_OUTPUT_PATH,
        help="Birleşik analiz JSON dosyasının yolu.",
    )

    parser.add_argument(
        "--report-output",
        type=Path,
        default=DEFAULT_MARKDOWN_OUTPUT_PATH,
        help="Birleşik analiz Markdown raporunun yolu.",
    )

    parser.add_argument(
        "--technical-weight",
        type=float,
        default=DEFAULT_TECHNICAL_WEIGHT,
        help="Teknik analiz ağırlığı. Varsayılan: 0.55",
    )

    parser.add_argument(
        "--fundamental-weight",
        type=float,
        default=DEFAULT_FUNDAMENTAL_WEIGHT,
        help="Temel analiz ağırlığı. Varsayılan: 0.45",
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        technical_summary = load_json_object(
            input_path=arguments.technical_input,
            description="Toplu teknik analiz dosyası",
        )

        fundamental_summary = load_json_object(
            input_path=arguments.fundamental_input,
            description="Toplu temel analiz dosyası",
        )

        combined_summary = combine_analysis_summaries(
            technical_summary=technical_summary,
            fundamental_summary=fundamental_summary,
            technical_weight=arguments.technical_weight,
            fundamental_weight=(
                arguments.fundamental_weight
            ),
        )

        save_json_result(
            combined_summary=combined_summary,
            output_path=arguments.json_output,
        )

        markdown_report = build_markdown_report(
            combined_summary
        )

        save_markdown_report(
            markdown_report=markdown_report,
            output_path=arguments.report_output,
        )

        combined_count = int(
            combined_summary["combined_count"]
        )

        unmatched_count = int(
            combined_summary["unmatched_count"]
        )

        if combined_count == 0:
            print(
                "HATA: Teknik ve temel analiz sonuçları "
                "birleştirilemedi."
            )
            return 1

        print(
            "BAŞARILI: Birleşik analiz tamamlandı."
        )
        print(
            f"Birleştirilen hisse: {combined_count}"
        )
        print(
            f"Eşleşmeyen hisse: {unmatched_count}"
        )

        results = combined_summary["results"]

        if isinstance(results, list) and results:
            top_result = results[0]

            if isinstance(top_result, dict):
                print(
                    f"En yüksek birleşik puan: "
                    f"{top_result['symbol']} - "
                    f"{top_result['combined_score']}"
                )

        print(
            f"JSON sonucu: "
            f"{arguments.json_output.resolve()}"
        )
        print(
            f"Markdown raporu: "
            f"{arguments.report_output.resolve()}"
        )

        return 0

    except Exception as error:
        print(f"HATA: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())