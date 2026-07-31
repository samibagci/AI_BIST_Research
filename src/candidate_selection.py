from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_INPUT_PATH = Path(
    "reports/bist_batch_analysis.json"
)
DEFAULT_JSON_OUTPUT_PATH = Path(
    "reports/bist_candidates.json"
)
DEFAULT_MARKDOWN_OUTPUT_PATH = Path(
    "reports/bist_candidates.md"
)

DEFAULT_MAX_CANDIDATES = 5
DEFAULT_MAX_STRONG_CANDIDATES = 3
DEFAULT_CANDIDATE_THRESHOLD = 50.0
DEFAULT_STRONG_THRESHOLD = 60.0


def load_batch_summary(
    input_path: Path,
) -> dict[str, object]:
    if not input_path.exists():
        raise FileNotFoundError(
            f"Toplu analiz dosyası bulunamadı: {input_path}"
        )

    try:
        loaded_data = json.loads(
            input_path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as error:
        raise ValueError(
            "Toplu analiz dosyası geçerli JSON değil."
        ) from error

    if not isinstance(loaded_data, dict):
        raise ValueError(
            "Toplu analiz sonucu JSON nesnesi olmalıdır."
        )

    return loaded_data


def validate_selection_settings(
    max_candidates: int,
    max_strong_candidates: int,
    candidate_threshold: float,
    strong_threshold: float,
) -> None:
    if max_candidates < 1:
        raise ValueError(
            "Maksimum aday sayısı en az 1 olmalıdır."
        )

    if max_strong_candidates < 0:
        raise ValueError(
            "Maksimum güçlü aday sayısı negatif olamaz."
        )

    if max_strong_candidates > max_candidates:
        raise ValueError(
            "Güçlü aday sayısı toplam aday sayısını aşamaz."
        )

    if not 0 <= candidate_threshold <= 100:
        raise ValueError(
            "Aday puan eşiği 0 ile 100 arasında olmalıdır."
        )

    if not 0 <= strong_threshold <= 100:
        raise ValueError(
            "Güçlü aday eşiği 0 ile 100 arasında olmalıdır."
        )

    if strong_threshold < candidate_threshold:
        raise ValueError(
            "Güçlü aday eşiği aday eşiğinden düşük olamaz."
        )


def prepare_scored_results(
    batch_summary: dict[str, object],
) -> list[dict[str, object]]:
    raw_results = batch_summary.get("results")

    if not isinstance(raw_results, list):
        raise ValueError(
            "Toplu analiz sonuç listesi bulunamadı."
        )

    prepared_results: list[dict[str, object]] = []
    processed_symbols: set[str] = set()

    for raw_result in raw_results:
        if not isinstance(raw_result, dict):
            continue

        symbol = raw_result.get("symbol")
        technical_score = raw_result.get(
            "technical_score"
        )

        if not isinstance(symbol, str):
            continue

        normalized_symbol = symbol.strip().upper()

        if not normalized_symbol:
            continue

        if normalized_symbol in processed_symbols:
            continue

        if isinstance(technical_score, bool):
            continue

        if not isinstance(
            technical_score,
            (int, float),
        ):
            continue

        score = round(float(technical_score), 2)

        if not 0 <= score <= 100:
            continue

        processed_symbols.add(normalized_symbol)

        prepared_results.append(
            {
                "symbol": normalized_symbol,
                "technical_score": score,
            }
        )

    prepared_results.sort(
        key=lambda item: float(
            item["technical_score"]
        ),
        reverse=True,
    )

    return prepared_results


def select_candidates(
    batch_summary: dict[str, object],
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

    scored_results = prepare_scored_results(
        batch_summary
    )

    candidates: list[dict[str, object]] = []
    excluded_results: list[dict[str, object]] = []
    strong_candidate_count = 0

    for result in scored_results:
        symbol = str(result["symbol"])
        technical_score = float(
            result["technical_score"]
        )

        if technical_score < candidate_threshold:
            excluded_results.append(
                {
                    "symbol": symbol,
                    "technical_score": technical_score,
                    "reason": (
                        "Teknik puan aday eşiğinin altında."
                    ),
                }
            )
            continue

        if len(candidates) >= max_candidates:
            excluded_results.append(
                {
                    "symbol": symbol,
                    "technical_score": technical_score,
                    "reason": (
                        "Maksimum aday sayısına ulaşıldı."
                    ),
                }
            )
            continue

        is_strong_candidate = (
            technical_score >= strong_threshold
            and strong_candidate_count
            < max_strong_candidates
        )

        if is_strong_candidate:
            candidate_label = "GÜÇLÜ ADAY"
            strong_candidate_count += 1
            selection_reason = (
                "Teknik puan güçlü aday eşiğini karşıladı."
            )
        else:
            candidate_label = "ADAY"
            selection_reason = (
                "Teknik puan aday eşiğini karşıladı."
            )

        candidates.append(
            {
                "rank": len(candidates) + 1,
                "symbol": symbol,
                "technical_score": technical_score,
                "label": candidate_label,
                "reason": selection_reason,
            }
        )

    return {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "source_generated_at": batch_summary.get(
            "generated_at"
        ),
        "period": batch_summary.get("period"),
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


def build_markdown_report(
    selection_result: dict[str, object],
) -> str:
    generated_at = selection_result["generated_at"]
    period = selection_result.get("period")
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
            "Aday seçim ayarları bulunamadı."
        )

    lines = [
        "# BIST Teknik Aday Seçim Raporu",
        "",
        f"- Oluşturulma zamanı: {generated_at}",
        f"- Veri dönemi: {period}",
        f"- Seçilen aday: {candidate_count}",
        (
            "- Güçlü aday: "
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
        "## Seçilen Adaylar",
        "",
    ]

    if isinstance(candidates, list) and candidates:
        lines.extend(
            [
                (
                    "| Sıra | Hisse | Teknik puan "
                    "| Etiket |"
                ),
                "|---:|---|---:|---|",
            ]
        )

        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue

            lines.append(
                f"| {candidate['rank']} "
                f"| {candidate['symbol']} "
                f"| {float(candidate['technical_score']):.2f} "
                f"| {candidate['label']} |"
            )
    else:
        lines.append(
            "Aday puan eşiğini geçen hisse bulunamadı."
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
                f"({float(excluded_result['technical_score']):.2f}): "
                f"{excluded_result['reason']}"
            )
    else:
        lines.append(
            "Aday dışı kalan hisse bulunmuyor."
        )

    lines.extend(
        [
            "",
            "> Bu rapor yalnızca teknik puanlara dayalıdır "
            "ve yatırım tavsiyesi değildir.",
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
            "Toplu BIST teknik analiz sonuçlarından "
            "en fazla 5 aday ve 3 güçlü aday seçer."
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help="Toplu analiz JSON dosyasının yolu.",
    )

    parser.add_argument(
        "--json-output",
        type=Path,
        default=DEFAULT_JSON_OUTPUT_PATH,
        help="Aday seçim JSON dosyasının yolu.",
    )

    parser.add_argument(
        "--report-output",
        type=Path,
        default=DEFAULT_MARKDOWN_OUTPUT_PATH,
        help="Aday seçim Markdown raporunun yolu.",
    )

    parser.add_argument(
        "--max-candidates",
        type=int,
        default=DEFAULT_MAX_CANDIDATES,
        help="Maksimum aday sayısı. Varsayılan: 5",
    )

    parser.add_argument(
        "--max-strong-candidates",
        type=int,
        default=DEFAULT_MAX_STRONG_CANDIDATES,
        help="Maksimum güçlü aday sayısı. Varsayılan: 3",
    )

    parser.add_argument(
        "--candidate-threshold",
        type=float,
        default=DEFAULT_CANDIDATE_THRESHOLD,
        help="Aday olmak için gereken puan. Varsayılan: 50",
    )

    parser.add_argument(
        "--strong-threshold",
        type=float,
        default=DEFAULT_STRONG_THRESHOLD,
        help=(
            "Güçlü aday olmak için gereken puan. "
            "Varsayılan: 60"
        ),
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        batch_summary = load_batch_summary(
            arguments.input
        )

        selection_result = select_candidates(
            batch_summary=batch_summary,
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
            "BAŞARILI: Teknik aday seçimi tamamlandı."
        )
        print(
            "Seçilen aday: "
            f"{selection_result['candidate_count']}"
        )
        print(
            "Güçlü aday: "
            f"{selection_result['strong_candidate_count']}"
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