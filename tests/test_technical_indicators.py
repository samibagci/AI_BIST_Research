from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.technical_indicators import (
    add_technical_indicators,
    atr,
    bollinger_bands,
    ema,
    macd,
    relative_volume,
    rsi,
    sma,
)


@pytest.fixture
def sample_price_data() -> pd.DataFrame:
    """Testlerde kullanılacak örnek OHLCV verisini oluşturur."""
    periods = 120
    index = pd.date_range(
        start="2025-01-01",
        periods=periods,
        freq="D",
    )

    trend = np.linspace(100, 160, periods)
    wave = np.sin(np.arange(periods) / 5) * 2
    close = trend + wave

    return pd.DataFrame(
        {
            "open": close - 0.5,
            "high": close + 1.5,
            "low": close - 1.5,
            "close": close,
            "volume": np.linspace(
                1_000_000,
                2_000_000,
                periods,
            ),
        },
        index=index,
    )


def test_sma_calculates_expected_value() -> None:
    series = pd.Series([1, 2, 3, 4, 5], dtype=float)

    result = sma(series, period=3)

    assert pd.isna(result.iloc[0])
    assert pd.isna(result.iloc[1])
    assert result.iloc[-1] == pytest.approx(4.0)


def test_ema_returns_values_after_period() -> None:
    series = pd.Series(
        range(1, 31),
        dtype=float,
    )

    result = ema(series, period=10)

    assert result.iloc[:9].isna().all()
    assert pd.notna(result.iloc[-1])
    assert result.iloc[-1] > result.iloc[10]


def test_rsi_is_100_for_continuously_rising_prices() -> None:
    series = pd.Series(
        range(1, 41),
        dtype=float,
    )

    result = rsi(series, period=14)

    assert result.iloc[-1] == pytest.approx(100.0)


def test_macd_returns_expected_columns() -> None:
    series = pd.Series(
        np.linspace(100, 150, 100),
        dtype=float,
    )

    result = macd(series)

    assert list(result.columns) == [
        "macd",
        "macd_signal",
        "macd_histogram",
    ]
    assert pd.notna(result["macd"].iloc[-1])
    assert pd.notna(result["macd_signal"].iloc[-1])
    assert pd.notna(result["macd_histogram"].iloc[-1])


def test_bollinger_band_order_is_valid() -> None:
    series = pd.Series(
        np.linspace(100, 130, 50),
        dtype=float,
    )

    result = bollinger_bands(series, period=20)
    last_row = result.iloc[-1]

    assert (
        last_row["bollinger_upper"]
        >= last_row["bollinger_middle"]
        >= last_row["bollinger_lower"]
    )


def test_atr_returns_positive_value(
    sample_price_data: pd.DataFrame,
) -> None:
    result = atr(
        sample_price_data["high"],
        sample_price_data["low"],
        sample_price_data["close"],
        period=14,
    )

    assert pd.notna(result.iloc[-1])
    assert result.iloc[-1] > 0


def test_relative_volume_is_one_for_constant_volume() -> None:
    volume = pd.Series(
        [1_000_000] * 30,
        dtype=float,
    )

    result = relative_volume(volume, period=20)

    assert result.iloc[-1] == pytest.approx(1.0)


def test_add_technical_indicators_adds_expected_columns(
    sample_price_data: pd.DataFrame,
) -> None:
    result = add_technical_indicators(sample_price_data)

    expected_columns = {
        "sma_20",
        "ema_20",
        "ema_50",
        "rsi_14",
        "atr_14",
        "macd",
        "macd_signal",
        "macd_histogram",
        "bollinger_middle",
        "bollinger_upper",
        "bollinger_lower",
        "bollinger_bandwidth",
        "bollinger_percent_b",
        "adx",
        "positive_di",
        "negative_di",
        "relative_volume_20",
    }

    assert expected_columns.issubset(result.columns)
    assert result.index.equals(sample_price_data.index)

    last_values = result[list(expected_columns)].iloc[-1]

    assert last_values.notna().all()


def test_missing_price_column_raises_error(
    sample_price_data: pd.DataFrame,
) -> None:
    invalid_data = sample_price_data.drop(columns=["volume"])

    with pytest.raises(
        ValueError,
        match="Eksik fiyat sütunları: volume",
    ):
        add_technical_indicators(invalid_data)


def test_invalid_period_raises_error() -> None:
    series = pd.Series([1, 2, 3], dtype=float)

    with pytest.raises(
        ValueError,
        match="Periyot pozitif bir tam sayı olmalıdır",
    ):
        sma(series, period=0)