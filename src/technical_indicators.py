from __future__ import annotations

import numpy as np
import pandas as pd


def _validate_period(period: int) -> None:
    """İndikatör periyodunun geçerli olup olmadığını kontrol eder."""
    if not isinstance(period, int) or period <= 0:
        raise ValueError("Periyot pozitif bir tam sayı olmalıdır.")


def _prepare_series(series: pd.Series, name: str) -> pd.Series:
    """Seriyi sayısal formata çevirir ve doğrular."""
    if not isinstance(series, pd.Series):
        raise TypeError(f"{name} verisi pandas Series olmalıdır.")

    result = pd.to_numeric(series, errors="coerce").astype(float)

    if result.dropna().empty:
        raise ValueError(f"{name} serisinde kullanılabilir sayısal veri bulunamadı.")

    return result


def sma(close: pd.Series, period: int = 20) -> pd.Series:
    """Basit hareketli ortalama hesaplar."""
    _validate_period(period)
    close = _prepare_series(close, "close")

    return close.rolling(
        window=period,
        min_periods=period,
    ).mean()


def ema(close: pd.Series, period: int = 20) -> pd.Series:
    """Üssel hareketli ortalama hesaplar."""
    _validate_period(period)
    close = _prepare_series(close, "close")

    return close.ewm(
        span=period,
        adjust=False,
        min_periods=period,
    ).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder yöntemine göre RSI hesaplar."""
    _validate_period(period)
    close = _prepare_series(close, "close")

    price_change = close.diff()

    gains = price_change.clip(lower=0)
    losses = -price_change.clip(upper=0)

    average_gain = gains.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period,
    ).mean()

    average_loss = losses.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period,
    ).mean()

    relative_strength = average_gain / average_loss.replace(0, np.nan)

    result = 100 - (100 / (1 + relative_strength))

    result = result.mask(
        (average_loss == 0) & (average_gain > 0),
        100,
    )

    result = result.mask(
        (average_loss == 0) & (average_gain == 0),
        50,
    )

    return result


def macd(
    close: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> pd.DataFrame:
    """MACD, sinyal ve histogram değerlerini hesaplar."""
    _validate_period(fast_period)
    _validate_period(slow_period)
    _validate_period(signal_period)

    if fast_period >= slow_period:
        raise ValueError(
            "MACD hızlı periyodu, yavaş periyottan küçük olmalıdır."
        )

    close = _prepare_series(close, "close")

    fast_ema = ema(close, fast_period)
    slow_ema = ema(close, slow_period)

    macd_line = fast_ema - slow_ema

    signal_line = macd_line.ewm(
        span=signal_period,
        adjust=False,
        min_periods=signal_period,
    ).mean()

    histogram = macd_line - signal_line

    return pd.DataFrame(
        {
            "macd": macd_line,
            "macd_signal": signal_line,
            "macd_histogram": histogram,
        },
        index=close.index,
    )


def bollinger_bands(
    close: pd.Series,
    period: int = 20,
    standard_deviation: float = 2.0,
) -> pd.DataFrame:
    """Bollinger Bantlarını hesaplar."""
    _validate_period(period)

    if standard_deviation <= 0:
        raise ValueError("Standart sapma katsayısı pozitif olmalıdır.")

    close = _prepare_series(close, "close")

    middle_band = sma(close, period)

    rolling_std = close.rolling(
        window=period,
        min_periods=period,
    ).std(ddof=0)

    upper_band = middle_band + standard_deviation * rolling_std
    lower_band = middle_band - standard_deviation * rolling_std

    band_width = (
        (upper_band - lower_band)
        / middle_band.replace(0, np.nan)
    ) * 100

    percent_b = (
        (close - lower_band)
        / (upper_band - lower_band).replace(0, np.nan)
    )

    return pd.DataFrame(
        {
            "bollinger_middle": middle_band,
            "bollinger_upper": upper_band,
            "bollinger_lower": lower_band,
            "bollinger_bandwidth": band_width,
            "bollinger_percent_b": percent_b,
        },
        index=close.index,
    )


def true_range(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
) -> pd.Series:
    """True Range değerini hesaplar."""
    high = _prepare_series(high, "high")
    low = _prepare_series(low, "low")
    close = _prepare_series(close, "close")

    previous_close = close.shift(1)

    ranges = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    )

    return ranges.max(axis=1)


def atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> pd.Series:
    """Wilder yöntemine göre ATR hesaplar."""
    _validate_period(period)

    range_values = true_range(high, low, close)

    return range_values.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period,
    ).mean()


def adx(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> pd.DataFrame:
    """ADX, pozitif DI ve negatif DI değerlerini hesaplar."""
    _validate_period(period)

    high = _prepare_series(high, "high")
    low = _prepare_series(low, "low")
    close = _prepare_series(close, "close")

    upward_move = high.diff()
    downward_move = -low.diff()

    positive_dm = upward_move.where(
        (upward_move > downward_move) & (upward_move > 0),
        0.0,
    )

    negative_dm = downward_move.where(
        (downward_move > upward_move) & (downward_move > 0),
        0.0,
    )

    atr_values = atr(high, low, close, period)

    smoothed_positive_dm = positive_dm.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period,
    ).mean()

    smoothed_negative_dm = negative_dm.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period,
    ).mean()

    positive_di = (
        100
        * smoothed_positive_dm
        / atr_values.replace(0, np.nan)
    )

    negative_di = (
        100
        * smoothed_negative_dm
        / atr_values.replace(0, np.nan)
    )

    directional_sum = positive_di + negative_di

    dx = (
        100
        * (positive_di - negative_di).abs()
        / directional_sum.replace(0, np.nan)
    )

    adx_line = dx.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period,
    ).mean()

    return pd.DataFrame(
        {
            "adx": adx_line,
            "positive_di": positive_di,
            "negative_di": negative_di,
        },
        index=close.index,
    )


def relative_volume(
    volume: pd.Series,
    period: int = 20,
) -> pd.Series:
    """Mevcut hacmin dönem ortalamasına oranını hesaplar."""
    _validate_period(period)
    volume = _prepare_series(volume, "volume")

    average_volume = volume.rolling(
        window=period,
        min_periods=period,
    ).mean()

    return volume / average_volume.replace(0, np.nan)


def add_technical_indicators(
    price_data: pd.DataFrame,
) -> pd.DataFrame:
    """OHLCV verisine temel teknik indikatörleri ekler."""
    required_columns = {
        "open",
        "high",
        "low",
        "close",
        "volume",
    }

    missing_columns = required_columns.difference(price_data.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        raise ValueError(
            f"Eksik fiyat sütunları: {missing_text}"
        )

    result = price_data.copy()

    result["sma_20"] = sma(result["close"], 20)
    result["ema_20"] = ema(result["close"], 20)
    result["ema_50"] = ema(result["close"], 50)
    result["rsi_14"] = rsi(result["close"], 14)
    result["atr_14"] = atr(
        result["high"],
        result["low"],
        result["close"],
        14,
    )

    macd_values = macd(result["close"])
    bollinger_values = bollinger_bands(result["close"])
    adx_values = adx(
        result["high"],
        result["low"],
        result["close"],
        14,
    )

    result = result.join(macd_values)
    result = result.join(bollinger_values)
    result = result.join(adx_values)

    result["relative_volume_20"] = relative_volume(
        result["volume"],
        20,
    )

    return result