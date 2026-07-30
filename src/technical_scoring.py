from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = {
    "close",
    "ema_20",
    "ema_50",
    "rsi_14",
    "macd",
    "macd_signal",
    "macd_histogram",
    "atr_14",
    "adx",
    "positive_di",
    "negative_di",
    "relative_volume_20",
    "bollinger_bandwidth",
    "bollinger_percent_b",
}


def _clamp(value: float, minimum: float = 0, maximum: float = 100) -> float:
    """Bir değeri belirlenen aralıkta sınırlar."""
    return float(max(minimum, min(maximum, value)))


def _latest_value(series: pd.Series) -> float | None:
    """Serideki son geçerli sayısal değeri döndürür."""
    clean_series = pd.to_numeric(series, errors="coerce").dropna()

    if clean_series.empty:
        return None

    return float(clean_series.iloc[-1])


def _previous_value(series: pd.Series) -> float | None:
    """Serideki sondan bir önceki geçerli değeri döndürür."""
    clean_series = pd.to_numeric(series, errors="coerce").dropna()

    if len(clean_series) < 2:
        return None

    return float(clean_series.iloc[-2])


def _percentage_change(current: float, previous: float) -> float:
    """İki değer arasındaki yüzde değişimi hesaplar."""
    if previous == 0:
        return 0.0

    return ((current - previous) / abs(previous)) * 100


def _validate_indicator_data(indicator_data: pd.DataFrame) -> None:
    """Teknik puanlama için gerekli verileri doğrular."""
    if not isinstance(indicator_data, pd.DataFrame):
        raise TypeError("Teknik analiz verisi pandas DataFrame olmalıdır.")

    if indicator_data.empty:
        raise ValueError("Teknik analiz verisi boş olamaz.")

    missing_columns = REQUIRED_COLUMNS.difference(indicator_data.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        raise ValueError(
            f"Teknik puanlama için eksik sütunlar: {missing_text}"
        )


def calculate_trend_score(
    indicator_data: pd.DataFrame,
) -> tuple[float, list[str], list[str]]:
    """Trend göstergelerine göre 0–100 arasında puan üretir."""
    score = 50.0
    signals: list[str] = []
    warnings: list[str] = []

    close = _latest_value(indicator_data["close"])
    ema_20 = _latest_value(indicator_data["ema_20"])
    ema_50 = _latest_value(indicator_data["ema_50"])
    adx = _latest_value(indicator_data["adx"])
    positive_di = _latest_value(indicator_data["positive_di"])
    negative_di = _latest_value(indicator_data["negative_di"])

    if close is None or ema_20 is None or ema_50 is None:
        warnings.append("Hareketli ortalama verisi yetersiz.")
        return 0.0, signals, warnings

    if close > ema_20:
        score += 12
        signals.append("Fiyat EMA20 üzerinde.")
    else:
        score -= 12
        signals.append("Fiyat EMA20 altında.")

    if ema_20 > ema_50:
        score += 18
        signals.append("EMA20, EMA50 üzerinde.")
    else:
        score -= 18
        signals.append("EMA20, EMA50 altında.")

    ema_20_clean = indicator_data["ema_20"].dropna()

    if len(ema_20_clean) >= 6:
        ema_20_current = float(ema_20_clean.iloc[-1])
        ema_20_previous = float(ema_20_clean.iloc[-6])

        if ema_20_current > ema_20_previous:
            score += 10
            signals.append("EMA20 eğimi pozitif.")
        else:
            score -= 10
            signals.append("EMA20 eğimi negatif.")
    else:
        warnings.append("EMA20 eğimi için yeterli veri yok.")

    distance_from_ema_20 = abs(
        _percentage_change(close, ema_20)
    )

    if distance_from_ema_20 <= 5:
        score += 8
    elif distance_from_ema_20 > 12:
        score -= 8
        warnings.append(
            "Fiyat EMA20 seviyesinden aşırı uzaklaşmış olabilir."
        )

    if adx is not None:
        if adx >= 30:
            score += 8
            signals.append("ADX güçlü trend gösteriyor.")
        elif adx >= 20:
            score += 4
            signals.append("ADX orta kuvvette trend gösteriyor.")
        else:
            score -= 4
            warnings.append("ADX zayıf trend gösteriyor.")
    else:
        warnings.append("ADX verisi bulunamadı.")

    if positive_di is not None and negative_di is not None:
        if positive_di > negative_di:
            score += 6
            signals.append("Pozitif yön göstergesi üstün.")
        else:
            score -= 6
            signals.append("Negatif yön göstergesi üstün.")

    return _clamp(score), signals, warnings


def calculate_momentum_score(
    indicator_data: pd.DataFrame,
) -> tuple[float, list[str], list[str]]:
    """Momentum göstergelerine göre 0–100 arasında puan üretir."""
    score = 50.0
    signals: list[str] = []
    warnings: list[str] = []

    rsi_value = _latest_value(indicator_data["rsi_14"])
    macd_value = _latest_value(indicator_data["macd"])
    signal_value = _latest_value(indicator_data["macd_signal"])
    histogram_value = _latest_value(
        indicator_data["macd_histogram"]
    )
    previous_histogram = _previous_value(
        indicator_data["macd_histogram"]
    )

    if rsi_value is None:
        warnings.append("RSI verisi bulunamadı.")
    elif 50 <= rsi_value <= 65:
        score += 18
        signals.append("RSI pozitif ve dengeli bölgede.")
    elif 40 <= rsi_value < 50:
        score += 5
        signals.append("RSI nötr bölgede.")
    elif 65 < rsi_value <= 75:
        score += 10
        signals.append("RSI güçlü momentum gösteriyor.")
    elif 30 <= rsi_value < 40:
        score -= 5
        warnings.append("RSI zayıf momentum gösteriyor.")
    elif rsi_value > 75:
        score -= 12
        warnings.append("RSI aşırı alım bölgesinde.")
    else:
        score -= 15
        warnings.append("RSI aşırı satım bölgesinde.")

    if macd_value is None or signal_value is None:
        warnings.append("MACD verisi bulunamadı.")
    elif macd_value > signal_value:
        score += 16
        signals.append("MACD, sinyal çizgisinin üzerinde.")
    else:
        score -= 16
        signals.append("MACD, sinyal çizgisinin altında.")

    if histogram_value is not None:
        if histogram_value > 0:
            score += 8
            signals.append("MACD histogramı pozitif.")
        else:
            score -= 8
            signals.append("MACD histogramı negatif.")

    if (
        histogram_value is not None
        and previous_histogram is not None
    ):
        if histogram_value > previous_histogram:
            score += 8
            signals.append("MACD momentumu güçleniyor.")
        else:
            score -= 5
            warnings.append("MACD momentumu zayıflıyor.")

    return _clamp(score), signals, warnings


def calculate_volume_score(
    indicator_data: pd.DataFrame,
) -> tuple[float, list[str], list[str]]:
    """Göreceli hacme göre 0–100 arasında puan üretir."""
    signals: list[str] = []
    warnings: list[str] = []

    relative_volume = _latest_value(
        indicator_data["relative_volume_20"]
    )
    close = _latest_value(indicator_data["close"])
    previous_close = _previous_value(indicator_data["close"])

    if relative_volume is None:
        warnings.append("Göreceli hacim verisi bulunamadı.")
        return 0.0, signals, warnings

    if relative_volume >= 2:
        score = 90.0
        signals.append("İşlem hacmi ortalamanın iki katından yüksek.")
    elif relative_volume >= 1.5:
        score = 80.0
        signals.append("İşlem hacmi belirgin şekilde yüksek.")
    elif relative_volume >= 1.2:
        score = 68.0
        signals.append("İşlem hacmi ortalamanın üzerinde.")
    elif relative_volume >= 0.8:
        score = 50.0
        signals.append("İşlem hacmi normal seviyede.")
    elif relative_volume >= 0.5:
        score = 35.0
        warnings.append("İşlem hacmi ortalamanın altında.")
    else:
        score = 20.0
        warnings.append("İşlem hacmi oldukça düşük.")

    if close is not None and previous_close is not None:
        price_change = _percentage_change(close, previous_close)

        if price_change > 0 and relative_volume > 1.2:
            score += 8
            signals.append("Fiyat artışı yüksek hacimle destekleniyor.")
        elif price_change < 0 and relative_volume > 1.2:
            score -= 12
            warnings.append(
                "Fiyat düşüşü yüksek işlem hacmiyle gerçekleşiyor."
            )

    return _clamp(score), signals, warnings


def calculate_volatility_score(
    indicator_data: pd.DataFrame,
) -> tuple[float, list[str], list[str]]:
    """
    Düşük risk profiline göre volatilite uygunluk puanı üretir.

    Yüksek puan, daha kontrollü volatilite anlamına gelir.
    """
    signals: list[str] = []
    warnings: list[str] = []

    close = _latest_value(indicator_data["close"])
    atr_value = _latest_value(indicator_data["atr_14"])
    bandwidth = _latest_value(
        indicator_data["bollinger_bandwidth"]
    )
    percent_b = _latest_value(
        indicator_data["bollinger_percent_b"]
    )

    component_scores: list[float] = []

    if close is not None and atr_value is not None and close > 0:
        atr_percentage = (atr_value / close) * 100

        if atr_percentage <= 2:
            component_scores.append(90)
            signals.append("ATR düşük ve kontrollü.")
        elif atr_percentage <= 3:
            component_scores.append(80)
            signals.append("ATR kabul edilebilir seviyede.")
        elif atr_percentage <= 4.5:
            component_scores.append(65)
        elif atr_percentage <= 6:
            component_scores.append(45)
            warnings.append("ATR yüksek seviyede.")
        else:
            component_scores.append(25)
            warnings.append("ATR çok yüksek seviyede.")
    else:
        warnings.append("ATR yüzdesi hesaplanamadı.")

    if bandwidth is not None:
        if bandwidth <= 10:
            component_scores.append(85)
            signals.append("Bollinger bant genişliği düşük.")
        elif bandwidth <= 20:
            component_scores.append(72)
        elif bandwidth <= 30:
            component_scores.append(55)
        else:
            component_scores.append(35)
            warnings.append("Bollinger bant genişliği yüksek.")
    else:
        warnings.append("Bollinger bant genişliği bulunamadı.")

    if percent_b is not None:
        if 0.2 <= percent_b <= 0.8:
            component_scores.append(75)
        elif 0 <= percent_b <= 1:
            component_scores.append(60)
        else:
            component_scores.append(35)
            warnings.append(
                "Fiyat Bollinger bantlarının dışında olabilir."
            )

    if not component_scores:
        return 0.0, signals, warnings

    return (
        _clamp(float(np.mean(component_scores))),
        signals,
        warnings,
    )


def calculate_data_confidence(
    indicator_data: pd.DataFrame,
) -> float:
    """Teknik analiz verisinin kullanılabilirlik puanını hesaplar."""
    latest_row = indicator_data.iloc[-1]
    available_values = latest_row[list(REQUIRED_COLUMNS)].notna().sum()
    completeness = available_values / len(REQUIRED_COLUMNS)

    length_score = min(len(indicator_data) / 100, 1.0)

    confidence = (
        completeness * 80
        + length_score * 20
    )

    return round(_clamp(confidence), 2)


def calculate_technical_score(
    indicator_data: pd.DataFrame,
) -> dict[str, Any]:
    """Teknik analiz alt puanlarını ve toplam puanı üretir."""
    _validate_indicator_data(indicator_data)

    trend_score, trend_signals, trend_warnings = (
        calculate_trend_score(indicator_data)
    )

    momentum_score, momentum_signals, momentum_warnings = (
        calculate_momentum_score(indicator_data)
    )

    volume_score, volume_signals, volume_warnings = (
        calculate_volume_score(indicator_data)
    )

    volatility_score, volatility_signals, volatility_warnings = (
        calculate_volatility_score(indicator_data)
    )

    technical_score = (
        trend_score * 0.35
        + momentum_score * 0.30
        + volume_score * 0.20
        + volatility_score * 0.15
    )

    confidence_score = calculate_data_confidence(indicator_data)

    all_signals = list(
        dict.fromkeys(
            trend_signals
            + momentum_signals
            + volume_signals
            + volatility_signals
        )
    )

    all_warnings = list(
        dict.fromkeys(
            trend_warnings
            + momentum_warnings
            + volume_warnings
            + volatility_warnings
        )
    )

    return {
        "score": round(_clamp(technical_score), 2),
        "technical_score": round(
            _clamp(technical_score),
            2,
        ),
        "trend_score": round(trend_score, 2),
        "momentum_score": round(momentum_score, 2),
        "volume_score": round(volume_score, 2),
        "volatility_score": round(volatility_score, 2),
        "confidence_score": confidence_score,
        "signals": all_signals,
        "warnings": all_warnings,
    }