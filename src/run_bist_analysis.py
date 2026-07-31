from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.download_bist_prices import (
    download_bist_prices,
    normalize_bist_symbol,
    save_price_data,
)
from src.run_pipeline import run_pipeline


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "BIST fiyat verisini indirir ve teknik analiz "
            "işlem hattını çalıştırır."
        )
    )

    parser.add_argument(
        "symbol",
        help="BIST hisse kodu. Örnek: THYAO",
    )

    parser.add_argument(
        "--period",
        default="1y",
        help="İndirilecek veri dönemi. Varsayılan: 1y",
    )

    parser.add_argument(
        "--csv-output",
        type=Path,
        default=None,
        help="Fiyat verisinin kaydedileceği CSV yolu.",
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
        help="Markdown raporunun yolu.",
    )

    return parser.parse_args()


def run_bist_analysis(
    symbol: str,
    period: str = "1y",
    csv_output_path: Path | None = None,
    json_output_path: Path | None = None,
    report_output_path: Path | None = None,
) -> dict[str, object]:
    yahoo_symbol = normalize_bist_symbol(symbol)
    base_symbol = yahoo_symbol.removesuffix(".IS")

    if csv_output_path is None:
        csv_output_path = (
            Path("data")
            / "prices"
            / f"{base_symbol}.csv"
        )

    if json_output_path is None:
        json_output_path = (
            Path("reports")
            / f"{base_symbol}_technical_analysis.json"
        )

    if report_output_path is None:
        report_output_path = (
            Path("reports")
            / f"{base_symbol}_technical_analysis.md"
        )

    price_data = download_bist_prices(
        symbol=yahoo_symbol,
        period=period,
    )

    save_price_data(
        price_data=price_data,
        output_path=csv_output_path,
    )

    result = run_pipeline(
        input_path=csv_output_path,
        symbol=base_symbol,
        json_output_path=json_output_path,
        report_output_path=report_output_path,
        generate_sample=False,
        sample_rows=180,
    )

    return result


def main() -> int:
    arguments = parse_arguments()

    try:
        yahoo_symbol = normalize_bist_symbol(
            arguments.symbol
        )
        base_symbol = yahoo_symbol.removesuffix(".IS")

        csv_output_path = arguments.csv_output
        json_output_path = arguments.json_output
        report_output_path = arguments.report_output

        if csv_output_path is None:
            csv_output_path = (
                Path("data")
                / "prices"
                / f"{base_symbol}.csv"
            )

        if json_output_path is None:
            json_output_path = (
                Path("reports")
                / f"{base_symbol}_technical_analysis.json"
            )

        if report_output_path is None:
            report_output_path = (
                Path("reports")
                / f"{base_symbol}_technical_analysis.md"
            )

        result = run_bist_analysis(
            symbol=base_symbol,
            period=arguments.period,
            csv_output_path=csv_output_path,
            json_output_path=json_output_path,
            report_output_path=report_output_path,
        )

        technical_score = result["technical_analysis"][
            "technical_score"
        ]

        print("BAŞARILI: BIST analizi tamamlandı.")
        print(f"Hisse: {base_symbol}")
        print(f"Teknik puan: {technical_score}")
        print(
            f"Fiyat verisi: "
            f"{csv_output_path.resolve()}"
        )
        print(
            f"JSON sonucu: "
            f"{json_output_path.resolve()}"
        )
        print(
            f"Markdown raporu: "
            f"{report_output_path.resolve()}"
        )

        return 0

    except Exception as error:
        print(f"HATA: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())