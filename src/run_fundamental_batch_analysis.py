from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.download_bist_prices import normalize_bist_symbol
from src.fundamental_analysis import (
    build_markdown_report as build_company_report,
    run_fundamental_analysis,
    save_json_result as save_company_json,
    save_markdown_report as save_company_report,
)
from src.run_bist_batch_analysis import (
    load_watchlist,
    parse_symbol_inputs,
)


DEFAULT_WATCHLIST_PATH = Path(
    "config/bist_watchlist.txt"
)
DEFAULT_REPORT_DIRECTORY = Path("reports")
DEFAULT_JSON_OUTPUT_PATH = Path(
    "reports/bist_fundamental_batch_analysis.json"
)
DEFAULT_MARKDOWN_OUTPUT_PATH = Path(
    "reports/bist_fundamental_batch_analysis.md"
)


def extract_fundamental_score(
    analysis_result: dict[str, object],
) -> float:
    fundamental_score = analysis_result.get(
        "fundamental_score"
    )

    if isinstance(fundamental_score, bool):
        raise ValueError(
            "Temel analiz puanı bulunamadı."
        )

    if not isinstance(
        fundamental_score,
        (int, float),
    ):
        raise ValueError(
            "Temel analiz puanı bulunamadı."
        )

    return round(float(fundamental_score), 2)


def extract_data_confidence(
    analysis_result: dict[str, object],
) -> float:
    data_confidence = analysis_result.get(
        "data_confidence"
    )

    if isinstance(data_confidence, bool):
        return 0.0

    if not isinstance(
        data_confidence,
        (int, float),
    ):
        return 0.0

    return round(float(data_confidence), 2)


def extract_label(
    analysis_result: dict[str, object],
) -> str:
    label = analysis_result.get("label")

    if not isinstance(label, str):
        return "BELİRSİZ"

    cleaned_label = label.strip()

    if not cleaned_label:
        return "BELİRSİZ"

    return cleaned_label


def run_fundamental_batch_analysis(
    symbols: list[str],
    report_directory: Path = DEFAULT_REPORT_DIRECTORY,
) -> dict[str, object]:
    if not symbols:
        raise ValueError(
            "En az bir hisse kodu girilmelidir."
        )

    successful_results: list[dict[str, object]] = []
    failed_results: list[dict[str, str]] = []
    processed_symbols: set[str] = set()

    for symbol in symbols:
        try:
            yahoo_symbol = normalize_bist_symbol(symbol)
            base_symbol = yahoo_symbol.removesuffix(".IS")

            if base_symbol in processed_symbols:
                continue

            processed_symbols.add(base_symbol)

            json_output_path = (
                report_directory
                / f"{base_symbol}_fundamental_analysis.json"
            )

            markdown_output_path = (
                report_directory
                / f"{base_symbol}_fundamental_analysis.md"
            )

            analysis_result = run_fundamental_analysis(
                symbol=base_symbol
            )

            save_company_json(
                analysis_result=analysis_result,
                output_path=json_output_path,
            )

            markdown_report = build_company_report(
                analysis_result
            )

            save_company_report(
                markdown_report=markdown_report,
                output_path=markdown_output_path,
            )

            fundamental_score = (
                extract_fundamental_score(
                    analysis_result
                )
            )

            data_confidence = extract_data_confidence(
                analysis_result
            )

            label = extract_label(
                analysis_result
            )

            company = analysis_result.get("company")
            company_name: str | None = None
            sector: str | None = None

            if isinstance(company, dict):
                raw_company_name = company.get("name")
                raw_sector = company.get("sector")

                if isinstance(raw_company_name, str):
                    company_name = raw_company_name

                if isinstance(raw_sector, str):
                    sector = raw_sector

            successful_results.append(
                {
                    "rank": 0,
                    "symbol": base_symbol,
                    "company_name": company_name,
                    "sector": sector,
                    "fundamental_score": fundamental_score,
                    "data_confidence": data_confidence,
                    "label": label,
                    "json_output": str(
                        json_output_path
                    ),
                    "markdown_output": str(
                        markdown_output_path
                    ),
                }
            )

        except Exception as error:
            failed_results.append(
                {
                    "symbol": symbol.strip().upper(),
                    "error": str(error),
                }
            )

    successful_results.sort(
        key=lambda item: float(
            item["fundamental_score"]
        ),
        reverse=True,
    )

    for rank, result in enumerate(
        successful_results,
        start=1,
    ):
        result["rank"] = rank

    return {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "requested_count": len(symbols),
        "processed_count": (
            len(successful_results)
            + len(failed_results)
        ),
        "success_count": len(successful_results),
        "failure_count": len(failed_results),
        "results": successful_results,
        "errors": failed_results,
    }


def build_markdown_report(
    summary: dict[str, object],
) -> str:
    generated_at = summary["generated_at"]
    success_count = summary["success_count"]
    failure_count = summary["failure_count"]
    results = summary["results"]
    errors = summary["errors"]

    lines = [
        "# BIST Toplu Temel Analiz Raporu",
        "",
        f"- Oluşturulma zamanı: {generated_at}",
        f"- Başarılı analiz: {success_count}",
        f"- Başarısız analiz: {failure_count}",
        "",
        "## Temel Puan Sıralaması",
        "",
    ]

    if isinstance(results, list) and results:
        lines.extend(
            [
                (
                    "| Sıra | Hisse | Şirket | Sektör "
                    "| Temel puan | Veri güveni | Sonuç |"
                ),
                "|---:|---|---|---|---:|---:|---|",
            ]
        )

        for result in results:
            if not isinstance(result, dict):
                continue

            company_name = (
                result.get("company_name")
                or "Veri yok"
            )
            sector = (
                result.get("sector")
                or "Veri yok"
            )

            lines.append(
                f"| {result['rank']} "
                f"| {result['symbol']} "
                f"| {company_name} "
                f"| {sector} "
                f"| {float(result['fundamental_score']):.2f} "
                f"| {float(result['data_confidence']):.2f}% "
                f"| {result['label']} |"
            )
    else:
        lines.append(
            "Başarıyla tamamlanan temel analiz bulunamadı."
        )

    lines.extend(
        [
            "",
            "## Başarısız Analizler",
            "",
        ]
    )

    if isinstance(errors, list) and errors:
        for error_result in errors:
            if not isinstance(error_result, dict):
                continue

            lines.append(
                f"- **{error_result['symbol']}**: "
                f"{error_result['error']}"
            )
    else:
        lines.append(
            "Başarısız analiz bulunmuyor."
        )

    lines.extend(
        [
            "",
            (
                "> Temel puanlar sektör farklılıkları "
                "dikkate alınarak değerlendirilmelidir."
            ),
            (
                "> Bu rapor araştırma amacıyla "
                "oluşturulmuştur ve yatırım tavsiyesi değildir."
            ),
            "",
        ]
    )

    return "\n".join(lines)


def save_json_summary(
    summary: dict[str, object],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            summary,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def save_markdown_summary(
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
            "Birden fazla BIST şirketinin temel "
            "analizini yapar ve puana göre sıralar."
        )
    )

    parser.add_argument(
        "symbols",
        nargs="*",
        help=(
            "İsteğe bağlı hisse kodları. "
            "Örnek: THYAO ASELS TUPRS"
        ),
    )

    parser.add_argument(
        "--watchlist",
        type=Path,
        default=DEFAULT_WATCHLIST_PATH,
        help="İzleme listesi dosyasının yolu.",
    )

    parser.add_argument(
        "--report-directory",
        type=Path,
        default=DEFAULT_REPORT_DIRECTORY,
        help="Şirket raporlarının kaydedileceği klasör.",
    )

    parser.add_argument(
        "--json-output",
        type=Path,
        default=DEFAULT_JSON_OUTPUT_PATH,
        help="Toplu temel analiz JSON dosyasının yolu.",
    )

    parser.add_argument(
        "--report-output",
        type=Path,
        default=DEFAULT_MARKDOWN_OUTPUT_PATH,
        help="Toplu temel analiz Markdown raporunun yolu.",
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        if arguments.symbols:
            symbols = parse_symbol_inputs(
                arguments.symbols
            )
        else:
            symbols = load_watchlist(
                arguments.watchlist
            )

        summary = run_fundamental_batch_analysis(
            symbols=symbols,
            report_directory=arguments.report_directory,
        )

        save_json_summary(
            summary=summary,
            output_path=arguments.json_output,
        )

        markdown_report = build_markdown_report(
            summary
        )

        save_markdown_summary(
            markdown_report=markdown_report,
            output_path=arguments.report_output,
        )

        success_count = int(
            summary["success_count"]
        )
        failure_count = int(
            summary["failure_count"]
        )

        if success_count == 0:
            print(
                "HATA: Hiçbir şirketin temel analizi "
                "tamamlanamadı."
            )
            print(
                f"JSON sonucu: "
                f"{arguments.json_output.resolve()}"
            )
            print(
                f"Markdown raporu: "
                f"{arguments.report_output.resolve()}"
            )
            return 1

        print(
            "BAŞARILI: Toplu temel analiz tamamlandı."
        )
        print(
            f"Başarılı analiz: {success_count}"
        )
        print(
            f"Başarısız analiz: {failure_count}"
        )

        results = summary["results"]

        if isinstance(results, list) and results:
            top_result = results[0]

            if isinstance(top_result, dict):
                print(
                    f"En yüksek temel puan: "
                    f"{top_result['symbol']} - "
                    f"{top_result['fundamental_score']}"
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