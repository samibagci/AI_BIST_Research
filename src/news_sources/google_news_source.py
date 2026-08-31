from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ElementTree
from collections.abc import Mapping, Sequence
from urllib.parse import quote_plus

from src.download_bist_prices import (
    normalize_bist_symbol,
)
from src.news_relevance import (
    is_company_news_relevant,
)
from src.news_sources.rss_source import (
    DEFAULT_REQUEST_TIMEOUT,
    article_sort_datetime,
    deduplicate_articles,
    download_rss_feed,
    get_child_text,
    get_entry_link,
    local_name,
    parse_feed_datetime,
    resolve_company_aliases,
    safe_text,
)


SOURCE_NAME = "Google News"
DEFAULT_NEWS_COUNT = 30
DEFAULT_LOOKBACK_DAYS = 90

GOOGLE_NEWS_BASE_URL = (
    "https://news.google.com/rss/search"
)





def strip_html(
    value: object,
) -> str | None:
    cleaned_value = safe_text(value)

    if cleaned_value is None:
        return None

    without_tags = re.sub(
        r"<[^>]+>",
        " ",
        cleaned_value,
    )

    decoded_value = html.unescape(
        without_tags
    )

    return safe_text(decoded_value)


def normalize_match_text(
    value: object,
) -> str:
    cleaned_value = strip_html(value)

    if cleaned_value is None:
        return ""

    turkish_normalized = (
        cleaned_value.translate(
            str.maketrans(
                {
                    "I": "ı",
                    "İ": "i",
                }
            )
        )
    )

    return turkish_normalized.casefold()


def text_contains_alias(
    text: str,
    alias: str,
) -> bool:
    normalized_alias = (
        normalize_match_text(alias)
    )

    if not normalized_alias:
        return False

    pattern = (
        rf"(?<!\w)"
        rf"{re.escape(normalized_alias)}"
        rf"(?!\w)"
    )

    return (
        re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )
        is not None
    )


def article_combined_text(
    article: Mapping[str, object],
) -> str:
    title_text = normalize_match_text(
        article.get("title")
    )

    summary_text = normalize_match_text(
        article.get("summary")
    )

    return " ".join(
        value
        for value in [
            title_text,
            summary_text,
        ]
        if value
    )




def is_google_article_relevant(
    article: Mapping[str, object],
    aliases: Sequence[str],
) -> bool:
    return is_company_news_relevant(
        article=article,
        aliases=aliases,
    )
def quote_search_term(
    value: str,
) -> str:
    cleaned_value = safe_text(value)

    if cleaned_value is None:
        return ""

    if " " in cleaned_value:
        return f'"{cleaned_value}"'

    return cleaned_value


def build_google_news_query(
    symbol: str,
    aliases: Sequence[str] | None = None,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> str:
    if lookback_days < 1:
        raise ValueError(
            "Google News inceleme dönemi "
            "en az 1 gün olmalıdır."
        )

    company_aliases = (
        resolve_company_aliases(
            symbol=symbol,
            aliases=aliases,
        )
    )

    search_terms = [
        quote_search_term(alias)
        for alias in company_aliases
        if quote_search_term(alias)
    ]

    if not search_terms:
        raise ValueError(
            "Şirket için arama terimi "
            "oluşturulamadı."
        )

    company_query = " OR ".join(
        search_terms
    )

    return (
        f"({company_query}) "
        f"when:{lookback_days}d"
    )


def build_google_news_url(
    symbol: str,
    aliases: Sequence[str] | None = None,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> str:
    query = build_google_news_query(
        symbol=symbol,
        aliases=aliases,
        lookback_days=lookback_days,
    )

    encoded_query = quote_plus(
        query
    )

    return (
        f"{GOOGLE_NEWS_BASE_URL}"
        f"?q={encoded_query}"
        f"&hl=tr"
        f"&gl=TR"
        f"&ceid=TR:tr"
    )


def get_google_news_source(
    element: ElementTree.Element,
) -> str | None:
    for child in element:
        if (
            local_name(
                child.tag
            ).casefold()
            != "source"
        ):
            continue

        source_name = safe_text(
            child.text
        )

        if source_name is not None:
            return source_name

    return None


def parse_google_news_feed(
    feed_data: bytes,
    symbol: str,
) -> list[dict[str, object]]:
    if not feed_data:
        return []

    yahoo_symbol = (
        normalize_bist_symbol(
            symbol
        )
    )

    try:
        root = ElementTree.fromstring(
            feed_data
        )
    except ElementTree.ParseError as error:
        raise ValueError(
            "Google News RSS verisi "
            "geçerli XML değil."
        ) from error

    articles: list[
        dict[str, object]
    ] = []

    for element in root.iter():
        if (
            local_name(
                element.tag
            ).casefold()
            != "item"
        ):
            continue

        title = strip_html(
            get_child_text(
                element,
                ("title",),
            )
        )

        if title is None:
            continue

        description = strip_html(
            get_child_text(
                element,
                (
                    "description",
                    "summary",
                ),
            )
        )

        published_text = (
            get_child_text(
                element,
                (
                    "pubDate",
                    "published",
                    "updated",
                ),
            )
        )

        published_datetime = (
            parse_feed_datetime(
                published_text
            )
        )

        article_url = (
            get_entry_link(
                element
            )
        )

        article_id = safe_text(
            get_child_text(
                element,
                (
                    "guid",
                    "id",
                ),
            )
        )

        if article_id is None:
            article_id = (
                article_url
                or title
            )

        publisher = (
            get_google_news_source(
                element
            )
        )

        articles.append(
            {
                "id": article_id,
                "title": title,
                "summary": description,
                "publisher": (
                    publisher
                    or SOURCE_NAME
                ),
                "publishedAt": (
                    published_datetime.isoformat()
                    if published_datetime
                    is not None
                    else None
                ),
                "link": article_url,
                "relatedTickers": [
                    yahoo_symbol,
                ],
                "source_name": (
                    SOURCE_NAME
                ),
                "source_type": (
                    "google_news"
                ),
            }
        )

    return articles


def filter_relevant_articles(
    symbol: str,
    articles: Sequence[
        dict[str, object]
    ],
    aliases: Sequence[str] | None = None,
) -> list[dict[str, object]]:
    company_aliases = (
        resolve_company_aliases(
            symbol=symbol,
            aliases=aliases,
        )
    )

    return [
        article
        for article in articles
        if is_google_article_relevant(
            article=article,
            aliases=company_aliases,
        )
    ]


def fetch_google_news(
    symbol: str,
    count: int = DEFAULT_NEWS_COUNT,
    aliases: Sequence[str] | None = None,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    timeout: int = DEFAULT_REQUEST_TIMEOUT,
) -> list[dict[str, object]]:
    if count < 1:
        raise ValueError(
            "Haber sayısı en az 1 olmalıdır."
        )

    if lookback_days < 1:
        raise ValueError(
            "Google News inceleme dönemi "
            "en az 1 gün olmalıdır."
        )

    if timeout < 1:
        raise ValueError(
            "Bağlantı zaman aşımı en az "
            "1 saniye olmalıdır."
        )

    normalize_bist_symbol(
        symbol
    )

    feed_url = (
        build_google_news_url(
            symbol=symbol,
            aliases=aliases,
            lookback_days=(
                lookback_days
            ),
        )
    )

    feed_data = download_rss_feed(
        feed_url=feed_url,
        timeout=timeout,
    )

    articles = (
        parse_google_news_feed(
            feed_data=feed_data,
            symbol=symbol,
        )
    )

    relevant_articles = (
        filter_relevant_articles(
            symbol=symbol,
            articles=articles,
            aliases=aliases,
        )
    )

    unique_articles = (
        deduplicate_articles(
            relevant_articles
        )
    )

    unique_articles.sort(
        key=article_sort_datetime,
        reverse=True,
    )

    return unique_articles[:count]