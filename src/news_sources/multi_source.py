from __future__ import annotations

import copy
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from numbers import Real
from urllib.parse import urlsplit, urlunsplit

from src.news_sources.google_news_source import (
    SOURCE_NAME as GOOGLE_SOURCE_NAME,
)
from src.news_sources.google_news_source import (
    fetch_google_news,
)
from src.news_sources.rss_source import (
    SOURCE_NAME as RSS_SOURCE_NAME,
)
from src.news_sources.rss_source import (
    fetch_rss_news,
)
from src.news_sources.yahoo_source import (
    SOURCE_NAME as YAHOO_SOURCE_NAME,
)
from src.news_sources.yahoo_source import (
    fetch_yahoo_news,
)


SOURCE_NAME = "Çoklu Haber Kaynağı"

DEFAULT_NEWS_COUNT = 30
DEFAULT_GOOGLE_LOOKBACK_DAYS = 90


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

        current_value = current_value.get(
            key
        )

    return current_value


def parse_article_datetime(
    value: object,
) -> datetime | None:
    if isinstance(value, datetime):
        parsed_datetime = value

    elif (
        isinstance(value, Real)
        and not isinstance(value, bool)
    ):
        timestamp = float(value)

        if timestamp > 10_000_000_000:
            timestamp /= 1000

        try:
            parsed_datetime = (
                datetime.fromtimestamp(
                    timestamp,
                    tz=timezone.utc,
                )
            )
        except (
            OverflowError,
            OSError,
            ValueError,
        ):
            return None

    elif isinstance(value, str):
        cleaned_value = value.strip()

        if not cleaned_value:
            return None

        if cleaned_value.endswith("Z"):
            cleaned_value = (
                cleaned_value[:-1]
                + "+00:00"
            )

        try:
            parsed_datetime = (
                datetime.fromisoformat(
                    cleaned_value
                )
            )
        except ValueError:
            return None

    else:
        return None

    if parsed_datetime.tzinfo is None:
        return parsed_datetime.replace(
            tzinfo=timezone.utc
        )

    return parsed_datetime.astimezone(
        timezone.utc
    )


def extract_article_title(
    article: Mapping[str, object],
) -> str | None:
    return (
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


def extract_article_url(
    article: Mapping[str, object],
) -> str | None:
    possible_values = [
        get_nested_value(
            article,
            "content",
            "canonicalUrl",
            "url",
        ),
        get_nested_value(
            article,
            "content",
            "clickThroughUrl",
            "url",
        ),
        get_nested_value(
            article,
            "content",
            "link",
        ),
        get_nested_value(
            article,
            "content",
            "url",
        ),
        article.get("link"),
        article.get("url"),
    ]

    for value in possible_values:
        cleaned_value = safe_text(value)

        if cleaned_value is not None:
            return cleaned_value

    return None


def extract_article_datetime(
    article: Mapping[str, object],
) -> datetime | None:
    possible_values = [
        get_nested_value(
            article,
            "content",
            "pubDate",
        ),
        get_nested_value(
            article,
            "content",
            "publishedAt",
        ),
        article.get(
            "providerPublishTime"
        ),
        article.get("pubDate"),
        article.get("publishedAt"),
    ]

    for value in possible_values:
        parsed_datetime = (
            parse_article_datetime(
                value
            )
        )

        if parsed_datetime is not None:
            return parsed_datetime

    return None


def normalize_article_url(
    value: object,
) -> str | None:
    cleaned_url = safe_text(value)

    if cleaned_url is None:
        return None

    parsed_url = urlsplit(
        cleaned_url
    )

    if not parsed_url.netloc:
        return cleaned_url.casefold()

    return urlunsplit(
        (
            parsed_url.scheme.casefold(),
            parsed_url.netloc.casefold(),
            parsed_url.path.rstrip("/"),
            parsed_url.query,
            "",
        )
    )


def normalize_article_title(
    value: object,
) -> str | None:
    cleaned_title = safe_text(value)

    if cleaned_title is None:
        return None

    turkish_normalized_title = (
        cleaned_title.translate(
            str.maketrans(
                {
                    "I": "ı",
                    "İ": "i",
                }
            )
        )
    )

    return (
        turkish_normalized_title
        .casefold()
    )


def add_source_metadata(
    articles: list[
        dict[str, object]
    ],
    source_name: str,
    source_type: str,
) -> list[dict[str, object]]:
    tagged_articles: list[
        dict[str, object]
    ] = []

    for article in articles:
        copied_article = copy.deepcopy(
            article
        )

        copied_article[
            "source_name"
        ] = source_name

        copied_article[
            "source_type"
        ] = source_type

        tagged_articles.append(
            copied_article
        )

    return tagged_articles


def article_sort_datetime(
    article: Mapping[str, object],
) -> datetime:
    return (
        extract_article_datetime(
            article
        )
        or datetime.min.replace(
            tzinfo=timezone.utc
        )
    )


def deduplicate_articles(
    articles: list[
        dict[str, object]
    ],
) -> list[dict[str, object]]:
    unique_articles: list[
        dict[str, object]
    ] = []

    seen_urls: set[str] = set()
    seen_titles: set[str] = set()

    for article in articles:
        normalized_url = (
            normalize_article_url(
                extract_article_url(
                    article
                )
            )
        )

        normalized_title = (
            normalize_article_title(
                extract_article_title(
                    article
                )
            )
        )

        if (
            normalized_url is not None
            and normalized_url
            in seen_urls
        ):
            continue

        if (
            normalized_title is not None
            and normalized_title
            in seen_titles
        ):
            continue

        if normalized_url is not None:
            seen_urls.add(
                normalized_url
            )

        if (
            normalized_title
            is not None
        ):
            seen_titles.add(
                normalized_title
            )

        unique_articles.append(
            article
        )

    return unique_articles


def fetch_source_safely(
    source_name: str,
    fetch_function: Callable[
        [],
        list[dict[str, object]],
    ],
    source_type: str,
) -> dict[str, object]:
    try:
        articles = fetch_function()

        if not isinstance(
            articles,
            list,
        ):
            raise ValueError(
                "Haber kaynağı liste "
                "döndürmedi."
            )

        valid_articles = [
            article
            for article in articles
            if isinstance(
                article,
                dict,
            )
        ]

        tagged_articles = (
            add_source_metadata(
                articles=(
                    valid_articles
                ),
                source_name=(
                    source_name
                ),
                source_type=(
                    source_type
                ),
            )
        )

        return {
            "source_name": (
                source_name
            ),
            "source_type": (
                source_type
            ),
            "success": True,
            "fetched_count": len(
                tagged_articles
            ),
            "error": None,
            "articles": (
                tagged_articles
            ),
        }

    except Exception as error:
        return {
            "source_name": (
                source_name
            ),
            "source_type": (
                source_type
            ),
            "success": False,
            "fetched_count": 0,
            "error": str(error),
            "articles": [],
        }


def collect_multi_source_news(
    symbol: str,
    count: int = DEFAULT_NEWS_COUNT,
    yahoo_count: int | None = None,
    rss_count: int | None = None,
    google_count: int | None = None,
    google_lookback_days: int = (
        DEFAULT_GOOGLE_LOOKBACK_DAYS
    ),
    include_yahoo: bool = True,
    include_rss: bool = True,
    include_google: bool = False,
) -> dict[str, object]:
    if count < 1:
        raise ValueError(
            "Haber sayısı en az "
            "1 olmalıdır."
        )

    if (
        not include_yahoo
        and not include_rss
        and not include_google
    ):
        raise ValueError(
            "En az bir haber kaynağı "
            "etkin olmalıdır."
        )

    resolved_yahoo_count = (
        yahoo_count
        if yahoo_count is not None
        else count
    )

    resolved_rss_count = (
        rss_count
        if rss_count is not None
        else count
    )

    resolved_google_count = (
        google_count
        if google_count is not None
        else count
    )

    if resolved_yahoo_count < 1:
        raise ValueError(
            "Yahoo haber sayısı "
            "en az 1 olmalıdır."
        )

    if resolved_rss_count < 1:
        raise ValueError(
            "RSS haber sayısı "
            "en az 1 olmalıdır."
        )

    if resolved_google_count < 1:
        raise ValueError(
            "Google News haber sayısı "
            "en az 1 olmalıdır."
        )

    if google_lookback_days < 1:
        raise ValueError(
            "Google News inceleme "
            "dönemi en az 1 gün "
            "olmalıdır."
        )

    source_results: list[
        dict[str, object]
    ] = []

    if include_yahoo:
        source_results.append(
            fetch_source_safely(
                source_name=(
                    YAHOO_SOURCE_NAME
                ),
                source_type="yahoo",
                fetch_function=lambda: (
                    fetch_yahoo_news(
                        symbol=symbol,
                        count=(
                            resolved_yahoo_count
                        ),
                    )
                ),
            )
        )

    if include_rss:
        source_results.append(
            fetch_source_safely(
                source_name=(
                    RSS_SOURCE_NAME
                ),
                source_type="rss",
                fetch_function=lambda: (
                    fetch_rss_news(
                        symbol=symbol,
                        count=(
                            resolved_rss_count
                        ),
                    )
                ),
            )
        )

    if include_google:
        source_results.append(
            fetch_source_safely(
                source_name=(
                    GOOGLE_SOURCE_NAME
                ),
                source_type=(
                    "google_news"
                ),
                fetch_function=lambda: (
                    fetch_google_news(
                        symbol=symbol,
                        count=(
                            resolved_google_count
                        ),
                        lookback_days=(
                            google_lookback_days
                        ),
                    )
                ),
            )
        )

    collected_articles: list[
        dict[str, object]
    ] = []

    for source_result in (
        source_results
    ):
        source_articles = (
            source_result.get(
                "articles"
            )
        )

        if not isinstance(
            source_articles,
            list,
        ):
            continue

        collected_articles.extend(
            article
            for article
            in source_articles
            if isinstance(
                article,
                dict,
            )
        )

    collected_articles.sort(
        key=article_sort_datetime,
        reverse=True,
    )

    unique_articles = (
        deduplicate_articles(
            collected_articles
        )
    )

    selected_articles = (
        unique_articles[:count]
    )

    successful_sources = [
        str(
            result[
                "source_name"
            ]
        )
        for result
        in source_results
        if result.get(
            "success"
        )
        is True
    ]

    failed_sources = [
        {
            "source_name": (
                result[
                    "source_name"
                ]
            ),
            "error": (
                result["error"]
            ),
        }
        for result
        in source_results
        if result.get(
            "success"
        )
        is False
    ]

    return {
        "source": SOURCE_NAME,
        "symbol": symbol,
        "requested_count": count,
        "fetched_count": len(
            collected_articles
        ),
        "unique_count": len(
            unique_articles
        ),
        "returned_count": len(
            selected_articles
        ),
        "successful_sources": (
            successful_sources
        ),
        "failed_sources": (
            failed_sources
        ),
        "source_results": [
            {
                key: value
                for key, value
                in result.items()
                if key != "articles"
            }
            for result
            in source_results
        ],
        "articles": (
            selected_articles
        ),
    }


def fetch_multi_source_news(
    symbol: str,
    count: int = DEFAULT_NEWS_COUNT,
    yahoo_count: int | None = None,
    rss_count: int | None = None,
    google_count: int | None = None,
    google_lookback_days: int = (
        DEFAULT_GOOGLE_LOOKBACK_DAYS
    ),
    include_yahoo: bool = True,
    include_rss: bool = True,
    include_google: bool = True,
) -> list[dict[str, object]]:
    result = (
        collect_multi_source_news(
            symbol=symbol,
            count=count,
            yahoo_count=(
                yahoo_count
            ),
            rss_count=(
                rss_count
            ),
            google_count=(
                google_count
            ),
            google_lookback_days=(
                google_lookback_days
            ),
            include_yahoo=(
                include_yahoo
            ),
            include_rss=(
                include_rss
            ),
            include_google=(
                include_google
            ),
        )
    )

    articles = result[
        "articles"
    ]

    if not isinstance(
        articles,
        list,
    ):
        return []

    return [
        article
        for article in articles
        if isinstance(
            article,
            dict,
        )
    ]