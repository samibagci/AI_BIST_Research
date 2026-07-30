from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    from src.technical_indicators import add_technical_indicators
    from src.technical_scoring import calculate_technical_score
except ModuleNotFoundError:
    from technical_indicators import add_technical_indicators
    from technical_scoring import calculate_technical_score


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_PATH = (
    PROJECT_ROOT / "reports" / "technical_analysis.json"
)

REQUIRED_PRICE_COLUMNS = {
    "open",
    "high",
    "low",
    "close",
    "volume",
}


def parse_arguments() -> argparse.Namespace:
    """Komut satırı seçeneklerini tanımlar."""
    parser = argparse.ArgumentParser(
        description=(
            "CSV dosyasındaki OHLCV verisini kullanarak "
            "teknik analiz ve teknik puan üretir."
        )
    )

    parser.add_argument(
        "input_file",
        type=Path,
        help="OHLCV verisini içeren CSV dosyasının yolu.",
    )

    parser.add_argument(
        "--symbol",
        type=str,
        default="UNKNOWN",
        help="Analiz edilecek hisse kodu.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="JSON sonuç dosyasının yolu.",
    )

    return parser.parse_args()


def load_price_data(file_path: Path) -> pd.DataFrame:
    """CSV dosyasını okuyup teknik analize hazırlar."""
    if not file_path.exists():
        raise FileNotFoundError(
            f"Fiyat veri dosyası bulunamadı: {file_path}"
        )

    try:
        price_data = pd.read_csv(file_path)
    except pd.errors.EmptyDataError as error:
        raise ValueError(
            "Fiyat veri dosyası boş."
        ) from error
    except pd.errors.ParserError as error:
        raise ValueError(
            "CSV dosyası okunamadı."
        ) from error

    price_data.columns = [
        str(column).strip().lower()
        for column in price_data.columns
    ]

    missing_columns = REQUIRED_PRICE_COLUMNS.difference(
        price_data.columns
    )

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))

        raise ValueError(
            f"CSV dosyasında eksik sütunlar var: {missing_text}"
        )

    if "date" in price_data.columns:
        price_data["date"] = pd.to_datetime(
            price_data["date"],
            errors="coerce",
        )

        if price_data["date"].isna().any():
            raise ValueError(
                "CSV dosyasında geçersiz tarih değerleri var."
            )

        price_data = (
            price_data
            .sort_values("date")
            .set_index("date")
        )

    for column in REQUIRED_PRICE_COLUMNS:
        price_data[column] = pd.to_numeric(
            price_data[column],
            errors="coerce",
        )

    if price_data[list(REQUIRED_PRICE_COLUMNS)].isna().any().any():
        raise ValueError(
            "OHLCV sütunlarında geçersiz veya eksik sayısal veri var."
        )

    if len(price_data) < 60:
        raise ValueError(
            "Teknik analiz için en az 60 satır fiyat verisi gereklidir."
        )

    if (price_data["volume"] < 0).any():
        raise ValueError(
            "İşlem hacmi negatif olamaz."
        )

    invalid_price_rows = (
        (price_data["high"] < price_data["low"])
        | (price_data["open"] <= 0)
        | (price_data["high"] <= 0)
        | (price_data["low"] <= 0)
        | (price_data["close"] <= 0)
    )

    if invalid_price_rows.any():
        raise ValueError(
            "CSV dosyasında geçersiz fiyat satırları var."
        )

    return price_data


def make_json_serializable(value: Any) -> Any:
    """NumPy ve pandas değerlerini JSON uyumlu hâle getirir."""
    if value is None:
        return None

    if isinstance(value, (np.integer,)):
        return int(value)

    if isinstance(value, (np.floating,)):
        if np.isnan(value) or np.isinf(value):
            return None

        return float(value)

    if isinstance(value, pd.Timestamp):
        return value.isoformat()

    if isinstance(value, dict):
        return {
            key: make_json_serializable(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            make_json_serializable(item)
            for item in value
        ]

    return value


def build_analysis_result(
    symbol: str,
    indicator_data: pd.DataFrame,
) -> dict[str, Any]:
    """Teknik analiz sonucunu standart sözlük yapısına dönüştürür."""
    technical_score = calculate_technical_score(
        indicator_data
    )

    latest_row = indicator_data.iloc[-1]

    price_date: str | None = None

    if isinstance(indicator_data.index, pd.DatetimeIndex):
        price_date = indicator_data.index[-1].isoformat()

    indicators = {
        "close": latest_row.get("close"),
        "sma_20": latest_row.get("sma_20"),
        "ema_20": latest_row.get("ema_20"),
        "ema_50": latest_row.get("ema_50"),
        "rsi_14": latest_row.get("rsi_14"),
        "macd": latest_row.get("macd"),
        "macd_signal": latest_row.get("macd_signal"),
        "macd_histogram": latest_row.get(
            "macd_histogram"
        ),
        "bollinger_upper": latest_row.get(
            "bollinger_upper"
        ),
        "bollinger_middle": latest_row.get(
            "bollinger_middle"
        ),
        "bollinger_lower": latest_row.get(
            "bollinger_lower"
        ),
        "atr_14": latest_row.get("atr_14"),
        "adx": latest_row.get("adx"),
        "positive_di": latest_row.get("positive_di"),
        "negative_di": latest_row.get("negative_di"),
        "relative_volume_20": latest_row.get(
            "relative_volume_20"
        ),
    }

    result = {
        "symbol": symbol.strip().upper(),
        "analysis_date": datetime.now().astimezone().isoformat(),
        "price_date": price_date,
        "record_count": len(indicator_data),
        "indicators": indicators,
        "technical_analysis": technical_score,
    }

    return make_json_serializable(result)


def save_result(
    result: dict[str, Any],
    output_path: Path,
) -> None:
    """Teknik analiz sonucunu JSON dosyasına kaydeder."""
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as output_file:
        json.dump(
            result,
            output_file,
            ensure_ascii=False,
            indent=2,
        )


def main() -> int:
    arguments = parse_arguments()

    try:
        price_data = load_price_data(
            arguments.input_file
        )

        indicator_data = add_technical_indicators(
            price_data
        )

        result = build_analysis_result(
            symbol=arguments.symbol,
            indicator_data=indicator_data,
        )

        save_result(
            result=result,
            output_path=arguments.output,
        )

    except (
        FileNotFoundError,
        ValueError,
        TypeError,
    ) as error:
        print(f"HATA: {error}")
        return 1

    print(
        "BAŞARILI: Teknik analiz tamamlandı.\n"
        f"Hisse: {result['symbol']}\n"
        f"Teknik puan: "
        f"{result['technical_analysis']['technical_score']}\n"
        f"Sonuç dosyası: {arguments.output}"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())