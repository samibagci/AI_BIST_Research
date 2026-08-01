from __future__ import annotations

import yfinance as yf

from src.download_bist_prices import normalize_bist_symbol


DEFAULT_NEWS_COUNT = 30
SOURCE_NAME = "Yahoo Finance / yfinance"


def fetch_yahoo_news(
    symbol: str,
    count: int = DEFAULT_NEWS_COUNT,
) -> list[dict[str, object]]:
    if count < 1:
        raise ValueError(
            "Haber sayısı en az 1 olmalıdır."
        )

    yahoo_symbol = normalize_bist_symbol(symbol)
    ticker = yf.Ticker(yahoo_symbol)

    raw_news = ticker.get_news(
        count=count,
        tab="news",
    )

    if raw_news is None:
        return []

    if not isinstance(raw_news, list):
        raise ValueError(
            f"{yahoo_symbol} haber verisi "
            "beklenen formatta değil."
        )

    return [
        article
        for article in raw_news
        if isinstance(article, dict)
    ]