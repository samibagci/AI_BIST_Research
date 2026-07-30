from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.technical_indicators import add_technical_indicators
from src.technical_scoring import (
    calculate_data_confidence,
    calculate_technical_score,
    calculate_volatility_score,
    calculate_volume_score,
)


@pytest.fixture
def sample_indicator_data() -> pd.DataFrame:
    """Teknik puanlama testleri için örnek veri oluşturur."""
    periods = 160

    index = pd.date_range(
        start="2025-01-01",
        periods=periods,
        freq="D",
    )

    trend = np.linspace(100, 180, periods)
    wave = np.sin(np.arange(periods) / 7) * 2
    close = trend + wave

    price_data = pd.DataFrame(
        {
            "open": close - 0.5,
            "high": close + 1.5,
            "low": close - 1.5,
            "close": close,
            "volume": np.linspace(
                1_000_000,
                2_500_000,
                periods,
            ),
        },
        index=index,
    )

    return add_technical_indicators(price_data)


def test_technical_score_returns_expected_structure(
    sample_indicator_data: pd.DataFrame,
) -> None:
    result = calculate_technical_score(
        sample_indicator_data
    )

    expected_keys = {
        "score",
        "technical_score",
        "trend_score",
        "momentum_score",
        "volume_score",
        "volatility_score",
        "confidence_score",
        "signals",
        "warnings",
    }

    assert expected_keys.issubset(result.keys())


def test_all_scores_are_between_zero_and_one_hundred(
    sample_indicator_data: pd.DataFrame,
) -> None:
    result = calculate_technical_score(
        sample_indicator_data
    )

    score_fields = [
        "score",
        "technical_score",
        "trend_score",
        "momentum_score",
        "volume_score",
        "volatility_score",
        "confidence_score",
    ]

    for field in score_fields:
        assert 0 <= result[field] <= 100


def test_signals_and_warnings_are_lists(
    sample_indicator_data: pd.DataFrame,
) -> None:
    result = calculate_technical_score(
        sample_indicator_data
    )

    assert isinstance(result["signals"], list)
    assert isinstance(result["warnings"], list)


def test_complete_data_has_high_confidence(
    sample_indicator_data: pd.DataFrame,
) -> None:
    confidence = calculate_data_confidence(
        sample_indicator_data
    )

    assert confidence >= 95


def test_missing_required_column_raises_error(
    sample_indicator_data: pd.DataFrame,
) -> None:
    invalid_data = sample_indicator_data.drop(
        columns=["rsi_14"]
    )

    with pytest.raises(
        ValueError,
        match="Teknik puanlama için eksik sütunlar",
    ):
        calculate_technical_score(invalid_data)


def test_empty_dataframe_raises_error() -> None:
    empty_data = pd.DataFrame()

    with pytest.raises(
        ValueError,
        match="Teknik analiz verisi boş olamaz",
    ):
        calculate_technical_score(empty_data)


def test_invalid_input_type_raises_error() -> None:
    with pytest.raises(
        TypeError,
        match="pandas DataFrame olmalıdır",
    ):
        calculate_technical_score([])  # type: ignore[arg-type]


def test_high_volume_price_increase_receives_high_score() -> None:
    indicator_data = pd.DataFrame(
        {
            "close": [100.0, 101.0, 105.0],
            "relative_volume_20": [1.0, 1.0, 2.0],
        }
    )

    score, signals, warnings = calculate_volume_score(
        indicator_data
    )

    assert score >= 90
    assert any(
        "yüksek hacimle destekleniyor" in signal
        for signal in signals
    )
    assert isinstance(warnings, list)


def test_high_volume_price_decline_is_penalized() -> None:
    rising_data = pd.DataFrame(
        {
            "close": [100.0, 101.0, 105.0],
            "relative_volume_20": [1.0, 1.0, 2.0],
        }
    )

    falling_data = pd.DataFrame(
        {
            "close": [100.0, 101.0, 95.0],
            "relative_volume_20": [1.0, 1.0, 2.0],
        }
    )

    rising_score, _, _ = calculate_volume_score(
        rising_data
    )

    falling_score, _, falling_warnings = (
        calculate_volume_score(falling_data)
    )

    assert falling_score < rising_score

    assert any(
        "Fiyat düşüşü" in warning
        for warning in falling_warnings
    )


def test_low_volatility_receives_high_suitability_score() -> None:
    indicator_data = pd.DataFrame(
        {
            "close": [100.0],
            "atr_14": [1.5],
            "bollinger_bandwidth": [8.0],
            "bollinger_percent_b": [0.5],
        }
    )

    score, signals, warnings = calculate_volatility_score(
        indicator_data
    )

    assert score >= 80
    assert len(signals) > 0
    assert isinstance(warnings, list)


def test_technical_score_is_rounded_to_two_decimals(
    sample_indicator_data: pd.DataFrame,
) -> None:
    result = calculate_technical_score(
        sample_indicator_data
    )

    assert result["technical_score"] == round(
        result["technical_score"],
        2,
    )