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
from src.run_bist_analysis import run_bist_analysis


def parse_symbol_inputs(values: list[str]) -> list[str]:
    symbols: list[str] = []

    for value in values:
        for symbol in value.split(","):
            cleaned_symbol = symbol.strip()

            if cleaned_symbol:
                symbols.append(cleaned_symbol)

    if not symbols:
        raise ValueError("En az bir hisse kodu girilmelidir.")

    return symbols


def extract_technical_score(
    analysis_result: dict[str, object],
) -> float:
    technical_analysis = analysis_result.get(
        "technical_analysis"
    )

    if not isinstance(technical_analysis, dict):
        raise ValueError(
            "Teknik analiz sonucu bulunamadı."
        )

    technical_score = technical_analysis.get(
        "technical_score"
    )

    if not isinstance(technical_score, (int, float)):
        raise ValueError(
            "Teknik puan bulunamadı."
        )

    return round(float(technical_score), 2)


def run_bist_batch_analysis(
    symbols: list[str],
    period: str = "1y",
    price_directory: Path = Path("data/prices"),
    report_directory: Path = Path("reports"),
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

            csv_output_path = (
                price_directory
                / f"{base_symbol}.csv"
            )

            json_output_path = (
                report_directory
                / f"{base_symbol}_technical_analysis.json"
            )

            markdown_output_path = (
                report_directory
                / f"{base_symbol}_technical_analysis.md"
            )

            analysis_result = run_bist_analysis(
                symbol=base_symbol,
                period=period,
                csv_output_path=csv_output_path,
                json_output_path=json_output_path,
                report_output_path=markdown_output_path,
            )

            technical_score = extract_technical_score(
                analysis_result
            )

            successful_results.append(
                {
                    "rank": 0,
                    "symbol": base_symbol,
                    "technical_score": technical_score,
                    "csv_output": str(csv_output_path),
                    "json_output": str(json_output_path),
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
            item["technical_score"]
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
        "period": period,
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
    period = summary["period"]
    success_count = summary["success_count"]
    failure_count = summary["failure_count"]
    results = summary["results"]
    errors = summary["errors"]

    lines = [
        "# BIST Toplu Teknik Analiz Raporu",
        "",
        f"- Oluşturulma zamanı: {generated_at}",
        f"- Veri dönemi: {period}",
        f"- Başarılı analiz: {success_count}",
        f"- Başarısız analiz: {failure_count}",
        "",
        "## Teknik Puan Sıralaması",
        "",
    ]

    if isinstance(results, list) and results:
        lines.extend(
            [
                "| Sıra | Hisse | Teknik puan |",
                "|---:|---|---:|",
            ]
        )

        for result in results:
            if not isinstance(result, dict):
                continue

            lines.append(
                f"| {result['rank']} "
                f"| {result['symbol']} "
                f"| {float(result['technical_score']):.2f} |"
            )
    else:
        lines.append(
            "Başarıyla tamamlanan analiz bulunamadı."
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

    return "\n".join(lines) + "\n"


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
            "Birden fazla BIST hissesini indirir, "
            "analiz eder ve teknik puana göre sıralar."
        )
    )

    parser.add_argument(
        "symbols",
        nargs="+",
        help=(
            "Hisse kodları. Örnek: "
            "THYAO ASELS TUPRS"
        ),
    )

    parser.add_argument(
        "--period",
        default="1y",
        help="İndirilecek veri dönemi. Varsayılan: 1y",
    )

    parser.add_argument(
        "--price-directory",
        type=Path,
        default=Path("data/prices"),
        help="Fiyat CSV dosyalarının kaydedileceği klasör.",
    )

    parser.add_argument(
        "--report-directory",
        type=Path,
        default=Path("reports"),
        help="Hisse raporlarının kaydedileceği klasör.",
    )

    parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
        help="Toplu JSON özet dosyasının yolu.",
    )

    parser.add_argument(
        "--report-output",
        type=Path,
        default=None,
        help="Toplu Markdown raporunun yolu.",
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        symbols = parse_symbol_inputs(
            arguments.symbols
        )

        json_output_path = arguments.json_output

        if json_output_path is None:
            json_output_path = (
                arguments.report_directory
                / "bist_batch_analysis.json"
            )

        markdown_output_path = (
            arguments.report_output
        )

        if markdown_output_path is None:
            markdown_output_path = (
                arguments.report_directory
                / "bist_batch_analysis.md"
            )

        summary = run_bist_batch_analysis(
            symbols=symbols,
            period=arguments.period,
            price_directory=arguments.price_directory,
            report_directory=arguments.report_directory,
        )

        save_json_summary(
            summary=summary,
            output_path=json_output_path,
        )

        markdown_report = build_markdown_report(
            summary
        )

        save_markdown_summary(
            markdown_report=markdown_report,
            output_path=markdown_output_path,
        )

        success_count = int(
            summary["success_count"]
        )
        failure_count = int(
            summary["failure_count"]
        )

        if success_count == 0:
            print(
                "HATA: Hiçbir hisse analiz edilemedi."
            )
            print(
                f"JSON sonucu: "
                f"{json_output_path.resolve()}"
            )
            print(
                f"Markdown raporu: "
                f"{markdown_output_path.resolve()}"
            )
            return 1

        print(
            "BAŞARILI: Toplu BIST analizi tamamlandı."
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
                    f"En yüksek puan: "
                    f"{top_result['symbol']} - "
                    f"{top_result['technical_score']}"
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