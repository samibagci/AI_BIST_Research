from __future__ import annotations

from collections.abc import Mapping, Sequence

import yfinance as yf

from src.company_registry import (
    get_company_aliases,
)
from src.download_bist_prices import (
    normalize_bist_symbol,
)
from src.news_relevance import (
    is_company_news_relevant,
)


DEFAULT_NEWS_COUNT = 30
SOURCE_NAME = "Yahoo Finance / yfinance"


def safe_text(
    value: object,
) -> str | None:
    if not isinstance(value, str):
        return None

    cleaned_value = " ".join(
        value.strip().split()
    )

    if not cleaned_value:
        return None

    return cleaned_value


def get_nested_value(
    data: object,
    *keys: str,
) -> object:
    current_value = data

    for key in keys:
        if not isinstance(
            current_value,
            Mapping,
        ):
            return None

        current_value = (
            current_value.get(key)
        )

    return current_value


def build_yahoo_relevance_article(
    article: Mapping[str, object],
) -> dict[str, object]:
    title = (
        safe_text(
            get_nested_value(
                article,
                "content",
                "title",
            )
        )
        or safe_text(
            article.get("title")
        )
    )

    summary = (
        safe_text(
            get_nested_value(
                article,
                "content",
                "summary",
            )
        )
        or safe_text(
            get_nested_value(
                article,
                "content",
                "description",
            )
        )
        or safe_text(
            article.get("summary")
        )
        or safe_text(
            article.get("description")
        )
    )

    return {
        "title": title,
        "summary": summary,
    }


def filter_yahoo_news_by_relevance(
    articles: Sequence[
        dict[str, object]
    ],
    aliases: Sequence[str],
) -> list[dict[str, object]]:
    relevant_articles: list[
        dict[str, object]
    ] = []

    for article in articles:
        relevance_article = (
            build_yahoo_relevance_article(
                article
            )
        )

        if not is_company_news_relevant(
            article=relevance_article,
            aliases=aliases,
        ):
            continue

        relevant_articles.append(
            article
        )

    return relevant_articles


def fetch_yahoo_news(
    symbol: str,
    count: int = DEFAULT_NEWS_COUNT,
) -> list[dict[str, object]]:
    if count < 1:
        raise ValueError(
            "Haber sayısı en az 1 olmalıdır."
        )

    yahoo_symbol = (
        normalize_bist_symbol(symbol)
    )

    ticker = yf.Ticker(
        yahoo_symbol
    )

    raw_news = ticker.get_news(
        count=count,
        tab="news",
    )

    if raw_news is None:
        return []

    if not isinstance(
        raw_news,
        list,
    ):
        raise ValueError(
            f"{yahoo_symbol} haber verisi "
            "beklenen formatta değil."
        )

    return [
        article
        for article in raw_news
        if isinstance(
            article,
            dict,
        )
    ]


def fetch_relevant_yahoo_news(
    symbol: str,
    count: int = DEFAULT_NEWS_COUNT,
) -> list[dict[str, object]]:
    raw_articles = fetch_yahoo_news(
        symbol=symbol,
        count=count,
    )

    if not raw_articles:
        return []

    aliases = get_company_aliases(
        symbol
    )

    return filter_yahoo_news_by_relevance(
        articles=raw_articles,
        aliases=aliases,
    )