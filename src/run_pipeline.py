from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from src.generate_sample_prices import (
        generate_sample_prices,
        save_sample_prices,
    )
    from src.run_technical_analysis import (
        build_analysis_result,
        load_price_data,
        save_result,
    )
    from src.technical_indicators import add_technical_indicators
    from src.technical_report import (
        build_markdown_report,
        save_report,
    )
except ModuleNotFoundError:
    from generate_sample_prices import (
        generate_sample_prices,
        save_sample_prices,
    )
    from run_technical_analysis import (
        build_analysis_result,
        load_price_data,
        save_result,
    )
    from technical_indicators import add_technical_indicators
    from technical_report import (
        build_markdown_report,
        save_report,
    )


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_INPUT_PATH = (
    PROJECT_ROOT / "examples" / "sample_prices.csv"
)

DEFAULT_JSON_OUTPUT_PATH = (
    PROJECT_ROOT / "reports" / "technical_analysis.json"
)

DEFAULT_MARKDOWN_OUTPUT_PATH = (
    PROJECT_ROOT / "reports" / "technical_analysis.md"
)


def parse_arguments() -> argparse.Namespace:
    """Ana işlem hattının komut satırı seçeneklerini tanımlar."""
    parser = argparse.ArgumentParser(
        description=(
            "Fiyat verisini hazırlar, teknik analiz yapar "
            "ve Markdown raporu oluşturur."
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help="OHLCV fiyat verisini içeren CSV dosyasının yolu.",
    )

    parser.add_argument(
        "--symbol",
        type=str,
        default="TEST",
        help="Analiz edilecek hisse kodu.",
    )

    parser.add_argument(
        "--json-output",
        type=Path,
        default=DEFAULT_JSON_OUTPUT_PATH,
        help="Teknik analiz JSON dosyasının yolu.",
    )

    parser.add_argument(
        "--report-output",
        type=Path,
        default=DEFAULT_MARKDOWN_OUTPUT_PATH,
        help="Markdown rapor dosyasının yolu.",
    )

    parser.add_argument(
        "--generate-sample",
        action="store_true",
        help="Analizden önce örnek fiyat verisi oluşturur.",
    )

    parser.add_argument(
        "--sample-rows",
        type=int,
        default=180,
        help="Örnek fiyat verisinin satır sayısı.",
    )

    return parser.parse_args()


def run_pipeline(
    input_path: Path,
    symbol: str,
    json_output_path: Path,
    report_output_path: Path,
    generate_sample: bool = False,
    sample_rows: int = 180,
) -> dict:
    """Teknik analiz ve raporlama işlemlerini sırayla çalıştırır."""
    if generate_sample:
        sample_price_data = generate_sample_prices(
            row_count=sample_rows,
        )

        save_sample_prices(
            price_data=sample_price_data,
            output_path=input_path,
        )

    price_data = load_price_data(input_path)

    indicator_data = add_technical_indicators(
        price_data,
    )

    analysis_result = build_analysis_result(
        symbol=symbol,
        indicator_data=indicator_data,
    )

    save_result(
        result=analysis_result,
        output_path=json_output_path,
    )

    report_text = build_markdown_report(
        analysis_result,
    )

    save_report(
        report_text=report_text,
        output_path=report_output_path,
    )

    return analysis_result


def main() -> int:
    """Ana işlem hattını çalıştırır."""
    arguments = parse_arguments()

    try:
        result = run_pipeline(
            input_path=arguments.input,
            symbol=arguments.symbol,
            json_output_path=arguments.json_output,
            report_output_path=arguments.report_output,
            generate_sample=arguments.generate_sample,
            sample_rows=arguments.sample_rows,
        )

    except (
        FileNotFoundError,
        ValueError,
        TypeError,
    ) as error:
        print(f"HATA: {error}")
        return 1

    technical_score = result["technical_analysis"][
        "technical_score"
    ]

    print(
        "BAŞARILI: Teknik analiz işlem hattı tamamlandı.\n"
        f"Hisse: {result['symbol']}\n"
        f"Teknik puan: {technical_score}\n"
        f"JSON sonucu: {arguments.json_output}\n"
        f"Markdown raporu: {arguments.report_output}"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())