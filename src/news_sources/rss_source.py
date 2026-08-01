from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ElementTree
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from src.download_bist_prices import normalize_bist_symbol


SOURCE_NAME = "Türkçe Finans RSS"
DEFAULT_NEWS_COUNT = 30
DEFAULT_REQUEST_TIMEOUT = 15
MAX_FEED_SIZE_BYTES = 5_000_000

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 "
    "(Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 "
    "(KHTML, like Gecko) "
    "Chrome/150.0 Safari/537.36"
)

DEFAULT_RSS_FEEDS: dict[str, str] = {
    "Habertürk Ekonomi": (
        "https://www.haberturk.com/rss/ekonomi.xml"
    ),
    "Habertürk İş Yaşam": (
        "https://www.haberturk.com/rss/kategori/"
        "is-yasam.xml"
    ),
    "Anadolu Ajansı": (
        "https://www.aa.com.tr/rss/"
        "ajansguncel.xml"
    ),
}

DEFAULT_COMPANY_ALIASES: dict[
    str,
    tuple[str, ...],
] = {
    "THYAO": (
        "THYAO",
        "Türk Hava Yolları",
        "Turkish Airlines",
    ),
    "ASELS": (
        "ASELS",
        "ASELSAN",
    ),
    "TUPRS": (
        "TUPRS",
        "Tüpraş",
        "Türkiye Petrol Rafinerileri",
    ),
    "KCHOL": (
        "KCHOL",
        "Koç Holding",
    ),
    "SISE": (
        "SISE",
        "Şişecam",
        "Türkiye Şişe ve Cam Fabrikaları",
    ),
}


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


def local_name(
    tag: str,
) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]

    if ":" in tag:
        return tag.rsplit(":", 1)[-1]

    return tag


def get_child_text(
    element: ElementTree.Element,
    names: Sequence[str],
) -> str | None:
    expected_names = {
        name.casefold()
        for name in names
    }

    for child in element:
        child_name = local_name(
            child.tag
        ).casefold()

        if child_name not in expected_names:
            continue

        cleaned_value = safe_text(
            child.text
        )

        if cleaned_value is not None:
            return cleaned_value

    return None


def get_entry_link(
    element: ElementTree.Element,
) -> str | None:
    for child in element:
        if (
            local_name(child.tag).casefold()
            != "link"
        ):
            continue

        href = safe_text(
            child.attrib.get("href")
        )

        if href is not None:
            return href

        text_value = safe_text(
            child.text
        )

        if text_value is not None:
            return text_value

    return None


def parse_feed_datetime(
    value: object,
) -> datetime | None:
    cleaned_value = safe_text(value)

    if cleaned_value is None:
        return None

    try:
        parsed_datetime = (
            parsedate_to_datetime(
                cleaned_value
            )
        )
    except (
        TypeError,
        ValueError,
        OverflowError,
    ):
        parsed_datetime = None

    if parsed_datetime is None:
        iso_value = cleaned_value

        if iso_value.endswith("Z"):
            iso_value = (
                iso_value[:-1]
                + "+00:00"
            )

        try:
            parsed_datetime = (
                datetime.fromisoformat(
                    iso_value
                )
            )
        except ValueError:
            return None

    if parsed_datetime.tzinfo is None:
        parsed_datetime = (
            parsed_datetime.replace(
                tzinfo=timezone.utc
            )
        )
    else:
        parsed_datetime = (
            parsed_datetime.astimezone(
                timezone.utc
            )
        )

    return parsed_datetime


def validate_feed_url(
    feed_url: str,
) -> str:
    cleaned_url = safe_text(feed_url)

    if cleaned_url is None:
        raise ValueError(
            "RSS adresi boş olamaz."
        )

    parsed_url = urlsplit(
        cleaned_url
    )

    if parsed_url.scheme not in {
        "http",
        "https",
    }:
        raise ValueError(
            "RSS adresi HTTP veya HTTPS "
            "olmalıdır."
        )

    if not parsed_url.netloc:
        raise ValueError(
            "Geçersiz RSS adresi."
        )

    return cleaned_url


def download_rss_feed(
    feed_url: str,
    timeout: int = DEFAULT_REQUEST_TIMEOUT,
) -> bytes:
    if timeout < 1:
        raise ValueError(
            "Bağlantı zaman aşımı en az "
            "1 saniye olmalıdır."
        )

    validated_url = validate_feed_url(
        feed_url
    )

    request = Request(
        validated_url,
        headers={
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": (
                "application/rss+xml, "
                "application/atom+xml, "
                "application/xml, "
                "text/xml;q=0.9, "
                "*/*;q=0.8"
            ),
        },
    )

    with urlopen(
        request,
        timeout=timeout,
    ) as response:
        content_length = response.headers.get(
            "Content-Length"
        )

        if content_length is not None:
            try:
                declared_size = int(
                    content_length
                )
            except ValueError:
                declared_size = 0

            if (
                declared_size
                > MAX_FEED_SIZE_BYTES
            ):
                raise ValueError(
                    "RSS verisi izin verilen "
                    "boyutu aşıyor."
                )

        feed_data = response.read(
            MAX_FEED_SIZE_BYTES + 1
        )

    if (
        len(feed_data)
        > MAX_FEED_SIZE_BYTES
    ):
        raise ValueError(
            "RSS verisi izin verilen "
            "boyutu aşıyor."
        )

    if not feed_data:
        raise ValueError(
            "RSS kaynağı boş veri döndürdü."
        )

    return feed_data


def parse_rss_feed(
    feed_data: bytes,
    source_name: str,
    yahoo_symbol: str,
) -> list[dict[str, object]]:
    cleaned_source_name = (
        safe_text(source_name)
    )

    if cleaned_source_name is None:
        raise ValueError(
            "RSS kaynak adı boş olamaz."
        )

    if not feed_data:
        return []

    try:
        root = ElementTree.fromstring(
            feed_data
        )
    except ElementTree.ParseError as error:
        raise ValueError(
            "RSS verisi geçerli XML değil."
        ) from error

    articles: list[
        dict[str, object]
    ] = []

    for element in root.iter():
        element_name = local_name(
            element.tag
        ).casefold()

        if element_name not in {
            "item",
            "entry",
        }:
            continue

        title = strip_html(
            get_child_text(
                element,
                (
                    "title",
                ),
            )
        )

        if title is None:
            continue

        summary = strip_html(
            get_child_text(
                element,
                (
                    "description",
                    "summary",
                    "content",
                    "encoded",
                ),
            )
        )

        published_text = get_child_text(
            element,
            (
                "pubDate",
                "published",
                "updated",
                "date",
            ),
        )

        published_datetime = (
            parse_feed_datetime(
                published_text
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

        article_url = get_entry_link(
            element
        )

        if article_id is None:
            article_id = (
                article_url
                or title
            )

        articles.append(
            {
                "id": article_id,
                "title": title,
                "summary": summary,
                "publisher": (
                    cleaned_source_name
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
                "source_type": "rss",
            }
        )

    return articles


def normalize_match_text(
    value: object,
) -> str:
    cleaned_value = strip_html(value)

    if cleaned_value is None:
        return ""

    return cleaned_value.casefold()


def text_contains_alias(
    text: str,
    alias: str,
) -> bool:
    normalized_alias = normalize_match_text(
        alias
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


def resolve_company_aliases(
    symbol: str,
    aliases: Sequence[str] | None = None,
) -> tuple[str, ...]:
    yahoo_symbol = normalize_bist_symbol(
        symbol
    )
    base_symbol = yahoo_symbol.removesuffix(
        ".IS"
    )

    alias_values: list[str] = [
        base_symbol,
    ]

    alias_values.extend(
        DEFAULT_COMPANY_ALIASES.get(
            base_symbol,
            (),
        )
    )

    if aliases is not None:
        alias_values.extend(aliases)

    unique_aliases: list[str] = []
    seen_aliases: set[str] = set()

    for alias in alias_values:
        cleaned_alias = safe_text(alias)

        if cleaned_alias is None:
            continue

        normalized_alias = (
            cleaned_alias.casefold()
        )

        if normalized_alias in seen_aliases:
            continue

        seen_aliases.add(
            normalized_alias
        )
        unique_aliases.append(
            cleaned_alias
        )

    return tuple(unique_aliases)


def is_article_relevant(
    article: Mapping[str, object],
    aliases: Sequence[str],
) -> bool:
    combined_text = " ".join(
        [
            normalize_match_text(
                article.get("title")
            ),
            normalize_match_text(
                article.get("summary")
            ),
        ]
    )

    return any(
        text_contains_alias(
            combined_text,
            alias,
        )
        for alias in aliases
    )


def normalize_article_url(
    value: object,
) -> str | None:
    cleaned_url = safe_text(value)

    if cleaned_url is None:
        return None

    parsed_url = urlsplit(
        cleaned_url
    )

    normalized_url = urlunsplit(
        (
            parsed_url.scheme.casefold(),
            parsed_url.netloc.casefold(),
            parsed_url.path.rstrip("/"),
            parsed_url.query,
            "",
        )
    )

    return normalized_url


def article_deduplication_key(
    article: Mapping[str, object],
) -> str | None:
    normalized_url = normalize_article_url(
        article.get("link")
    )

    if normalized_url:
        return f"url:{normalized_url}"

    normalized_title = normalize_match_text(
        article.get("title")
    )

    if normalized_title:
        return f"title:{normalized_title}"

    return None


def deduplicate_articles(
    articles: Sequence[
        dict[str, object]
    ],
) -> list[dict[str, object]]:
    unique_articles: list[
        dict[str, object]
    ] = []

    seen_keys: set[str] = set()

    for article in articles:
        deduplication_key = (
            article_deduplication_key(
                article
            )
        )

        if deduplication_key is None:
            continue

        if deduplication_key in seen_keys:
            continue

        seen_keys.add(
            deduplication_key
        )
        unique_articles.append(
            article
        )

    return unique_articles


def article_sort_datetime(
    article: Mapping[str, object],
) -> datetime:
    parsed_datetime = parse_feed_datetime(
        article.get("publishedAt")
    )

    if parsed_datetime is not None:
        return parsed_datetime

    return datetime.min.replace(
        tzinfo=timezone.utc
    )


def fetch_single_rss_source(
    source_name: str,
    feed_url: str,
    symbol: str,
    timeout: int = DEFAULT_REQUEST_TIMEOUT,
) -> list[dict[str, object]]:
    yahoo_symbol = normalize_bist_symbol(
        symbol
    )

    feed_data = download_rss_feed(
        feed_url=feed_url,
        timeout=timeout,
    )

    return parse_rss_feed(
        feed_data=feed_data,
        source_name=source_name,
        yahoo_symbol=yahoo_symbol,
    )


def fetch_rss_news(
    symbol: str,
    count: int = DEFAULT_NEWS_COUNT,
    feed_urls: Mapping[str, str] | None = None,
    aliases: Sequence[str] | None = None,
    timeout: int = DEFAULT_REQUEST_TIMEOUT,
) -> list[dict[str, object]]:
    if count < 1:
        raise ValueError(
            "Haber sayısı en az 1 olmalıdır."
        )

    if timeout < 1:
        raise ValueError(
            "Bağlantı zaman aşımı en az "
            "1 saniye olmalıdır."
        )

    normalize_bist_symbol(symbol)

    selected_feeds = (
        dict(feed_urls)
        if feed_urls is not None
        else dict(DEFAULT_RSS_FEEDS)
    )

    if not selected_feeds:
        return []

    company_aliases = (
        resolve_company_aliases(
            symbol=symbol,
            aliases=aliases,
        )
    )

    collected_articles: list[
        dict[str, object]
    ] = []

    for (
        source_name,
        feed_url,
    ) in selected_feeds.items():
        try:
            source_articles = (
                fetch_single_rss_source(
                    source_name=source_name,
                    feed_url=feed_url,
                    symbol=symbol,
                    timeout=timeout,
                )
            )

        except (
            HTTPError,
            URLError,
            TimeoutError,
            ValueError,
            OSError,
        ):
            continue

        relevant_articles = [
            article
            for article in source_articles
            if is_article_relevant(
                article,
                company_aliases,
            )
        ]

        collected_articles.extend(
            relevant_articles
        )

    unique_articles = (
        deduplicate_articles(
            collected_articles
        )
    )

    unique_articles.sort(
        key=article_sort_datetime,
        reverse=True,
    )

    return unique_articles[:count]