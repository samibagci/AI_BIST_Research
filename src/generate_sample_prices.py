from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_PATH = (
    PROJECT_ROOT / "examples" / "sample_prices.csv"
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test amacıyla örnek OHLCV fiyat verisi oluşturur."
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Oluşturulacak CSV dosyasının yolu.",
    )

    parser.add_argument(
        "--rows",
        type=int,
        default=180,
        help="Oluşturulacak veri satırı sayısı.",
    )

    return parser.parse_args()


def generate_sample_prices(
    row_count: int = 180,
) -> pd.DataFrame:
    """Tekrarlanabilir örnek OHLCV verisi oluşturur."""
    if row_count < 60:
        raise ValueError(
            "Teknik analiz için en az 60 satır oluşturulmalıdır."
        )

    random_generator = np.random.default_rng(seed=42)

    dates = pd.bdate_range(
        start="2025-01-02",
        periods=row_count,
    )

    trend = np.linspace(100, 165, row_count)
    cycle = np.sin(np.arange(row_count) / 8) * 3
    noise = random_generator.normal(
        loc=0,
        scale=0.8,
        size=row_count,
    )

    close = trend + cycle + noise

    open_price = close + random_generator.normal(
        loc=0,
        scale=0.7,
        size=row_count,
    )

    daily_range = random_generator.uniform(
        1.0,
        3.0,
        size=row_count,
    )

    high = np.maximum(open_price, close) + daily_range
    low = np.minimum(open_price, close) - daily_range

    volume_trend = np.linspace(
        1_000_000,
        2_500_000,
        row_count,
    )

    volume_noise = random_generator.normal(
        loc=0,
        scale=150_000,
        size=row_count,
    )

    volume = np.maximum(
        volume_trend + volume_noise,
        100_000,
    ).astype(int)

    return pd.DataFrame(
        {
            "date": dates,
            "open": open_price.round(2),
            "high": high.round(2),
            "low": low.round(2),
            "close": close.round(2),
            "volume": volume,
        }
    )


def save_sample_prices(
    price_data: pd.DataFrame,
    output_path: Path,
) -> None:
    """Örnek fiyat verisini CSV dosyasına kaydeder."""
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    price_data.to_csv(
        output_path,
        index=False,
        encoding="utf-8",
    )


def main() -> int:
    arguments = parse_arguments()

    try:
        price_data = generate_sample_prices(
            row_count=arguments.rows,
        )

        save_sample_prices(
            price_data=price_data,
            output_path=arguments.output,
        )

    except ValueError as error:
        print(f"HATA: {error}")
        return 1

    print(
        "BAŞARILI: Örnek fiyat verisi oluşturuldu.\n"
        f"Satır sayısı: {len(price_data)}\n"
        f"Dosya: {arguments.output}"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())