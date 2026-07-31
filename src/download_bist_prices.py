from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd
import yfinance as yf


REQUIRED_COLUMNS = [
    "date",
    "open",
    "high",
    "low",
    "close",
    "volume",
]


def normalize_bist_symbol(symbol: str) -> str:
    normalized_symbol = symbol.strip().upper()

    if normalized_symbol.endswith(".IS"):
        base_symbol = normalized_symbol[:-3]
    else:
        base_symbol = normalized_symbol

    if not base_symbol or not re.fullmatch(
        r"[A-Z0-9]+",
        base_symbol,
    ):
        raise ValueError(
            "Geçersiz hisse kodu. Örnek: THYAO veya THYAO.IS"
        )

    return f"{base_symbol}.IS"


def download_bist_prices(
    symbol: str,
    period: str = "1y",
) -> pd.DataFrame:
    yahoo_symbol = normalize_bist_symbol(symbol)

    price_data = yf.download(
        tickers=yahoo_symbol,
        period=period,
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=False,
        timeout=30,
        multi_level_index=False,
    )

    if price_data is None or price_data.empty:
        raise ValueError(
            f"{yahoo_symbol} için fiyat verisi bulunamadı."
        )

    return prepare_price_data(price_data)


def prepare_price_data(
    price_data: pd.DataFrame,
) -> pd.DataFrame:
    prepared_data = price_data.copy()
    prepared_data = prepared_data.reset_index()

    prepared_data.columns = [
        str(column).strip().lower().replace(" ", "_")
        for column in prepared_data.columns
    ]

    if "datetime" in prepared_data.columns:
        prepared_data = prepared_data.rename(
            columns={"datetime": "date"}
        )

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in prepared_data.columns
    ]

    if missing_columns:
        raise ValueError(
            "Eksik fiyat sütunları: "
            + ", ".join(missing_columns)
        )

    prepared_data = prepared_data[REQUIRED_COLUMNS].copy()

    prepared_data["date"] = pd.to_datetime(
        prepared_data["date"],
        errors="coerce",
    )

    if prepared_data["date"].dt.tz is not None:
        prepared_data["date"] = (
            prepared_data["date"]
            .dt.tz_localize(None)
        )

    numeric_columns = [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    for column in numeric_columns:
        prepared_data[column] = pd.to_numeric(
            prepared_data[column],
            errors="coerce",
        )

    prepared_data = prepared_data.dropna(
        subset=REQUIRED_COLUMNS
    )

    prepared_data = prepared_data[
        prepared_data["volume"] >= 0
    ]

    prepared_data = prepared_data.sort_values(
        "date"
    ).reset_index(drop=True)

    if prepared_data.empty:
        raise ValueError(
            "İndirilen fiyat verileri kullanılamıyor."
        )

    prepared_data["date"] = prepared_data[
        "date"
    ].dt.strftime("%Y-%m-%d")

    return prepared_data


def save_price_data(
    price_data: pd.DataFrame,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    price_data.to_csv(
        output_path,
        index=False,
        encoding="utf-8",
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Yahoo Finance üzerinden BIST fiyat "
            "verilerini indirir."
        )
    )

    parser.add_argument(
        "symbol",
        help="BIST hisse kodu. Örnek: THYAO",
    )

    parser.add_argument(
        "--period",
        default="1y",
        help="Veri dönemi. Varsayılan: 1y",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="CSV çıktı dosyasının yolu.",
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        yahoo_symbol = normalize_bist_symbol(
            arguments.symbol
        )

        output_path = arguments.output

        if output_path is None:
            base_symbol = yahoo_symbol.removesuffix(".IS")
            output_path = (
                Path("data")
                / "prices"
                / f"{base_symbol}.csv"
            )

        price_data = download_bist_prices(
            symbol=yahoo_symbol,
            period=arguments.period,
        )

        save_price_data(
            price_data=price_data,
            output_path=output_path,
        )

        print(
            "BAŞARILI: BIST fiyat verileri indirildi."
        )
        print(f"Hisse: {yahoo_symbol}")
        print(f"Satır sayısı: {len(price_data)}")
        print(
            f"Başlangıç tarihi: "
            f"{price_data['date'].iloc[0]}"
        )
        print(
            f"Bitiş tarihi: "
            f"{price_data['date'].iloc[-1]}"
        )
        print(
            f"CSV dosyası: "
            f"{output_path.resolve()}"
        )

        return 0

    except Exception as error:
        print(f"HATA: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())