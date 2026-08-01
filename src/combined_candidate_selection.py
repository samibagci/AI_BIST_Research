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


from src.candidate_selection import (
    DEFAULT_CANDIDATE_THRESHOLD,
    DEFAULT_MAX_CANDIDATES,
    DEFAULT_MAX_STRONG_CANDIDATES,
    DEFAULT_STRONG_THRESHOLD,
    validate_selection_settings,
)


DEFAULT_INPUT_PATH = Path(
    "reports/bist_combined_analysis.json"
)
DEFAULT_JSON_OUTPUT_PATH = Path(
    "reports/bist_combined_candidates.json"
)
DEFAULT_MARKDOWN_OUTPUT_PATH = Path(
    "reports/bist_combined_candidates.md"
)


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


def load_combined_summary(
    input_path: Path,
) -> dict[str, object]:
    if not input_path.exists():
        raise FileNotFoundError(
            f"Birleşik analiz dosyası bulunamadı: {input_path}"
        )

    try:
        loaded_data = json.loads(
            input_path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as error:
        raise ValueError(
            "Birleşik analiz dosyası geçerli JSON değil."
        ) from error

    if not isinstance(loaded_data, dict):
        raise ValueError(
            "Birleşik analiz sonucu JSON nesnesi olmalıdır."
        )

    return loaded_data


def prepare_combined_results(
    combined_summary: dict[str, object],
) -> list[dict[str, object]]:
    raw_results = combined_summary.get("results")

    if not isinstance(raw_results, list):
        raise ValueError(
            "Birleşik analiz sonuç listesi bulunamadı."
        )

    prepared_results: list[dict[str, object]] = []
    processed_symbols: set[str] = set()

    for raw_result in raw_results:
        if not isinstance(raw_result, dict):
            continue

        raw_symbol = raw_result.get("symbol")

        if not isinstance(raw_symbol, str):
            continue

        symbol = raw_symbol.strip().upper()

        if symbol.endswith(".IS"):
            symbol = symbol[:-3]

        if not symbol or symbol in processed_symbols:
            continue

        combined_score = safe_number(
            raw_result.get("combined_score")
        )

        if (
            combined_score is None
            or not 0 <= combined_score <= 100
        ):
            continue

        technical_score = safe_number(
            raw_result.get("technical_score")
        )
        fundamental_score = safe_number(
            raw_result.get("fundamental_score")
        )
        data_confidence = safe_number(
            raw_result.get(
                "fundamental_data_confidence"
            )
        )

        company_name = raw_result.get(
            "company_name"
        )
        sector = raw_result.get("sector")

        processed_symbols.add(symbol)

        prepared_results.append(
            {
                "symbol": symbol,
                "company_name": (
                    company_name.strip()
                    if isinstance(company_name, str)
                    and company_name.strip()
                    else None
                ),
                "sector": (
                    sector.strip()
                    if isinstance(sector, str)
                    and sector.strip()
                    else None
                ),
                "technical_score": (
                    round(technical_score, 2)
                    if technical_score is not None
                    else None
                ),
                "fundamental_score": (
                    round(fundamental_score, 2)
                    if fundamental_score is not None
                    else None
                ),
                "combined_score": round(
                    combined_score,
                    2,
                ),
                "fundamental_data_confidence": (
                    round(data_confidence, 2)
                    if data_confidence is not None
                    else 0.0
                ),
            }
        )

    prepared_results.sort(
        key=lambda item: float(
            item["combined_score"]
        ),
        reverse=True,
    )

    return prepared_results


def select_combined_candidates(
    combined_summary: dict[str, object],
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
    max_strong_candidates: int = (
        DEFAULT_MAX_STRONG_CANDIDATES
    ),
    candidate_threshold: float = (
        DEFAULT_CANDIDATE_THRESHOLD
    ),
    strong_threshold: float = (
        DEFAULT_STRONG_THRESHOLD
    ),
) -> dict[str, object]:
    validate_selection_settings(
        max_candidates=max_candidates,
        max_strong_candidates=max_strong_candidates,
        candidate_threshold=candidate_threshold,
        strong_threshold=strong_threshold,
    )

    scored_results = prepare_combined_results(
        combined_summary
    )

    candidates: list[dict[str, object]] = []
    excluded_results: list[dict[str, object]] = []
    strong_candidate_count = 0

    for result in scored_results:
        symbol = str(result["symbol"])
        combined_score = float(
            result["combined_score"]
        )

        if combined_score < candidate_threshold:
            excluded_results.append(
                {
                    **result,
                    "reason": (
                        "Birleşik puan aday eşiğinin altında."
                    ),
                }
            )
            continue

        if len(candidates) >= max_candidates:
            excluded_results.append(
                {
                    **result,
                    "reason": (
                        "Maksimum aday sayısına ulaşıldı."
                    ),
                }
            )
            continue

        is_strong_candidate = (
            combined_score >= strong_threshold
            and strong_candidate_count
            < max_strong_candidates
        )

        if is_strong_candidate:
            label = "GÜÇLÜ NİHAİ ADAY"
            reason = (
                "Birleşik puan güçlü aday "
                "eşiğini karşıladı."
            )
            strong_candidate_count += 1
        else:
            label = "NİHAİ ADAY"
            reason = (
                "Birleşik puan aday eşiğini karşıladı."
            )

        candidates.append(
            {
                "rank": len(candidates) + 1,
                **result,
                "label": label,
                "reason": reason,
            }
        )

    return {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "source_generated_at": combined_summary.get(
            "generated_at"
        ),
        "weights": combined_summary.get("weights"),
        "settings": {
            "max_candidates": max_candidates,
            "max_strong_candidates": (
                max_strong_candidates
            ),
            "candidate_threshold": (
                candidate_threshold
            ),
            "strong_threshold": strong_threshold,
        },
        "analyzed_count": len(scored_results),
        "candidate_count": len(candidates),
        "strong_candidate_count": (
            strong_candidate_count
        ),
        "candidates": candidates,
        "excluded": excluded_results,
    }


def format_score(
    value: object,
) -> str:
    numeric_value = safe_number(value)

    if numeric_value is None:
        return "Veri yok"

    return f"{numeric_value:.2f}"


def build_markdown_report(
    selection_result: dict[str, object],
) -> str:
    generated_at = selection_result["generated_at"]
    candidate_count = selection_result[
        "candidate_count"
    ]
    strong_candidate_count = selection_result[
        "strong_candidate_count"
    ]
    settings = selection_result["settings"]
    candidates = selection_result["candidates"]
    excluded_results = selection_result["excluded"]

    if not isinstance(settings, dict):
        raise ValueError(
            "Nihai aday seçim ayarları bulunamadı."
        )

    lines = [
        "# BIST Nihai Aday Seçim Raporu",
        "",
        f"- Oluşturulma zamanı: {generated_at}",
        f"- Seçilen nihai aday: {candidate_count}",
        (
            "- Güçlü nihai aday: "
            f"{strong_candidate_count}"
        ),
        (
            "- Aday puan eşiği: "
            f"{float(settings['candidate_threshold']):.2f}"
        ),
        (
            "- Güçlü aday eşiği: "
            f"{float(settings['strong_threshold']):.2f}"
        ),
        "",
        "## Seçilen Nihai Adaylar",
        "",
    ]

    if isinstance(candidates, list) and candidates:
        lines.extend(
            [
                (
                    "| Sıra | Hisse | Teknik puan "
                    "| Temel puan | Birleşik puan "
                    "| Veri güveni | Etiket |"
                ),
                "|---:|---|---:|---:|---:|---:|---|",
            ]
        )

        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue

            lines.append(
                f"| {candidate['rank']} "
                f"| {candidate['symbol']} "
                f"| {format_score(candidate.get('technical_score'))} "
                f"| {format_score(candidate.get('fundamental_score'))} "
                f"| {format_score(candidate.get('combined_score'))} "
                f"| {format_score(candidate.get('fundamental_data_confidence'))}% "
                f"| {candidate['label']} |"
            )
    else:
        lines.append(
            "Birleşik puan eşiğini geçen hisse bulunamadı."
        )

    lines.extend(
        [
            "",
            "## Aday Dışı Kalanlar",
            "",
        ]
    )

    if (
        isinstance(excluded_results, list)
        and excluded_results
    ):
        for excluded_result in excluded_results:
            if not isinstance(excluded_result, dict):
                continue

            lines.append(
                f"- **{excluded_result['symbol']}** "
                f"({format_score(excluded_result.get('combined_score'))}): "
                f"{excluded_result['reason']}"
            )
    else:
        lines.append(
            "Aday dışı kalan hisse bulunmuyor."
        )

    lines.extend(
        [
            "",
            (
                "> Nihai adaylar teknik ve temel analiz "
                "puanlarının birleşimine göre seçilmiştir."
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
    selection_result: dict[str, object],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            selection_result,
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
            "Birleşik BIST analiz sonuçlarından "
            "nihai yatırım araştırma adaylarını seçer."
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help="Birleşik analiz JSON dosyasının yolu.",
    )

    parser.add_argument(
        "--json-output",
        type=Path,
        default=DEFAULT_JSON_OUTPUT_PATH,
        help="Nihai aday JSON dosyasının yolu.",
    )

    parser.add_argument(
        "--report-output",
        type=Path,
        default=DEFAULT_MARKDOWN_OUTPUT_PATH,
        help="Nihai aday Markdown raporunun yolu.",
    )

    parser.add_argument(
        "--max-candidates",
        type=int,
        default=DEFAULT_MAX_CANDIDATES,
        help="Maksimum nihai aday sayısı. Varsayılan: 5",
    )

    parser.add_argument(
        "--max-strong-candidates",
        type=int,
        default=DEFAULT_MAX_STRONG_CANDIDATES,
        help=(
            "Maksimum güçlü nihai aday sayısı. "
            "Varsayılan: 3"
        ),
    )

    parser.add_argument(
        "--candidate-threshold",
        type=float,
        default=DEFAULT_CANDIDATE_THRESHOLD,
        help="Nihai aday puan eşiği. Varsayılan: 50",
    )

    parser.add_argument(
        "--strong-threshold",
        type=float,
        default=DEFAULT_STRONG_THRESHOLD,
        help=(
            "Güçlü nihai aday puan eşiği. "
            "Varsayılan: 60"
        ),
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        combined_summary = load_combined_summary(
            arguments.input
        )

        selection_result = select_combined_candidates(
            combined_summary=combined_summary,
            max_candidates=arguments.max_candidates,
            max_strong_candidates=(
                arguments.max_strong_candidates
            ),
            candidate_threshold=(
                arguments.candidate_threshold
            ),
            strong_threshold=arguments.strong_threshold,
        )

        save_json_result(
            selection_result=selection_result,
            output_path=arguments.json_output,
        )

        markdown_report = build_markdown_report(
            selection_result
        )

        save_markdown_report(
            markdown_report=markdown_report,
            output_path=arguments.report_output,
        )

        print(
            "BAŞARILI: Nihai aday seçimi tamamlandı."
        )
        print(
            "Seçilen nihai aday: "
            f"{selection_result['candidate_count']}"
        )
        print(
            "Güçlü nihai aday: "
            f"{selection_result['strong_candidate_count']}"
        )

        candidates = selection_result["candidates"]

        if isinstance(candidates, list) and candidates:
            top_candidate = candidates[0]

            if isinstance(top_candidate, dict):
                print(
                    f"En yüksek nihai aday: "
                    f"{top_candidate['symbol']} - "
                    f"{top_candidate['combined_score']}"
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