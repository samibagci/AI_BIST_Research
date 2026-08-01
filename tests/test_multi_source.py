from __future__ import annotations

from datetime import datetime, timezone

import pytest

import src.news_sources.multi_source as module
from src.news_sources.multi_source import (
    RSS_SOURCE_NAME,
    SOURCE_NAME,
    YAHOO_SOURCE_NAME,
    add_source_metadata,
    article_sort_datetime,
    collect_multi_source_news,
    deduplicate_articles,
    extract_article_datetime,
    extract_article_title,
    extract_article_url,
    fetch_multi_source_news,
    fetch_source_safely,
    get_nested_value,
    normalize_article_title,
    normalize_article_url,
    parse_article_datetime,
    safe_text,
)


def create_yahoo_article(
    article_id: str = "yahoo-1",
    title: str = "Tüpraş yeni yatırım açıkladı",
    published_at: str = "2026-07-31T12:00:00Z",
    url: str = "https://finance.example.com/yahoo-1",
) -> dict[str, object]:
    return {
        "content": {
            "id": article_id,
            "title": title,
            "summary": "Şirket kapasite artışı planlıyor.",
            "pubDate": published_at,
            "provider": {
                "displayName": "Yahoo Kaynağı",
            },
            "canonicalUrl": {
                "url": url,
            },
        }
    }


def create_rss_article(
    article_id: str = "rss-1",
    title: str = "Tüpraş üretim kapasitesini artırdı",
    published_at: str = "2026-07-30T10:00:00+00:00",
    url: str = "https://news.example.com/rss-1",
) -> dict[str, object]:
    return {
        "id": article_id,
        "title": title,
        "summary": "Tüpraş yeni yatırım kararını açıkladı.",
        "publisher": "RSS Kaynağı",
        "publishedAt": published_at,
        "link": url,
        "relatedTickers": [
            "TUPRS.IS",
        ],
        "source_type": "rss",
    }


def test_safe_text_cleans_whitespace() -> None:
    assert safe_text("  Çoklu   Haber  ") == "Çoklu Haber"
    assert safe_text("") is None
    assert safe_text("   ") is None
    assert safe_text(123) is None


def test_get_nested_value_reads_nested_data() -> None:
    data = {
        "content": {
            "provider": {
                "displayName": "Kaynak",
            }
        }
    }

    assert (
        get_nested_value(
            data,
            "content",
            "provider",
            "displayName",
        )
        == "Kaynak"
    )

    assert (
        get_nested_value(
            data,
            "content",
            "missing",
        )
        is None
    )


def test_parse_article_datetime_accepts_iso_string() -> None:
    result = parse_article_datetime(
        "2026-07-31T12:30:00Z"
    )

    assert result == datetime(
        2026,
        7,
        31,
        12,
        30,
        tzinfo=timezone.utc,
    )


def test_parse_article_datetime_accepts_timestamp() -> None:
    expected = datetime(
        2026,
        7,
        31,
        12,
        30,
        tzinfo=timezone.utc,
    )

    result = parse_article_datetime(
        expected.timestamp()
    )

    assert result == expected


def test_parse_article_datetime_accepts_millisecond_timestamp() -> None:
    expected = datetime(
        2026,
        7,
        31,
        12,
        30,
        tzinfo=timezone.utc,
    )

    result = parse_article_datetime(
        expected.timestamp() * 1000
    )

    assert result == expected


def test_parse_article_datetime_accepts_naive_datetime() -> None:
    value = datetime(
        2026,
        7,
        31,
        12,
        30,
    )

    result = parse_article_datetime(value)

    assert result == datetime(
        2026,
        7,
        31,
        12,
        30,
        tzinfo=timezone.utc,
    )


@pytest.mark.parametrize(
    "value",
    [
        "",
        "geçersiz tarih",
        None,
        True,
        {},
    ],
)
def test_parse_article_datetime_rejects_invalid_values(
    value: object,
) -> None:
    assert parse_article_datetime(value) is None


def test_extract_article_title_reads_yahoo_format() -> None:
    article = create_yahoo_article()

    assert (
        extract_article_title(article)
        == "Tüpraş yeni yatırım açıkladı"
    )


def test_extract_article_title_reads_flat_format() -> None:
    article = create_rss_article()

    assert (
        extract_article_title(article)
        == "Tüpraş üretim kapasitesini artırdı"
    )


def test_extract_article_url_reads_yahoo_format() -> None:
    article = create_yahoo_article()

    assert (
        extract_article_url(article)
        == "https://finance.example.com/yahoo-1"
    )


def test_extract_article_url_reads_flat_format() -> None:
    article = create_rss_article()

    assert (
        extract_article_url(article)
        == "https://news.example.com/rss-1"
    )


def test_extract_article_datetime_reads_yahoo_format() -> None:
    article = create_yahoo_article()

    assert extract_article_datetime(
        article
    ) == datetime(
        2026,
        7,
        31,
        12,
        0,
        tzinfo=timezone.utc,
    )


def test_extract_article_datetime_reads_rss_format() -> None:
    article = create_rss_article()

    assert extract_article_datetime(
        article
    ) == datetime(
        2026,
        7,
        30,
        10,
        0,
        tzinfo=timezone.utc,
    )


def test_normalize_article_url() -> None:
    result = normalize_article_url(
        "HTTPS://NEWS.EXAMPLE.COM/haber/#bolum"
    )

    assert result == (
        "https://news.example.com/haber"
    )


def test_normalize_article_url_handles_relative_value() -> None:
    assert (
        normalize_article_url("/haber/1")
        == "/haber/1"
    )


def test_normalize_article_title() -> None:
    assert (
        normalize_article_title(
            "  Tüpraş   Yeni Yatırım  "
        )
        == "tüpraş yeni yatırım"
    )


def test_add_source_metadata_does_not_modify_original() -> None:
    original_article = create_yahoo_article()

    result = add_source_metadata(
        articles=[
            original_article,
        ],
        source_name="Örnek Kaynak",
        source_type="örnek",
    )

    assert result[0]["source_name"] == "Örnek Kaynak"
    assert result[0]["source_type"] == "örnek"
    assert "source_name" not in original_article
    assert result[0] is not original_article


def test_article_sort_datetime() -> None:
    article = create_rss_article(
        published_at=(
            "2026-07-30T10:00:00+00:00"
        )
    )

    assert article_sort_datetime(
        article
    ) == datetime(
        2026,
        7,
        30,
        10,
        0,
        tzinfo=timezone.utc,
    )


def test_article_sort_datetime_uses_minimum_for_missing_date() -> None:
    result = article_sort_datetime(
        {
            "title": "Tarihsiz haber",
        }
    )

    assert result == datetime.min.replace(
        tzinfo=timezone.utc
    )


def test_deduplicate_articles_by_url() -> None:
    first_article = create_rss_article(
        title="İlk haber",
        url="https://example.com/aynı",
    )

    duplicate_article = create_rss_article(
        title="Farklı başlık",
        url="https://example.com/aynı/",
    )

    result = deduplicate_articles(
        [
            first_article,
            duplicate_article,
        ]
    )

    assert result == [
        first_article,
    ]


def test_deduplicate_articles_by_title() -> None:
    first_article = create_rss_article(
        title="Tüpraş yatırım açıkladı",
        url="https://example.com/1",
    )

    duplicate_article = create_rss_article(
        title="TÜPRAŞ YATIRIM AÇIKLADI",
        url="https://example.com/2",
    )

    result = deduplicate_articles(
        [
            first_article,
            duplicate_article,
        ]
    )

    assert result == [
        first_article,
    ]


def test_deduplicate_articles_keeps_unique_articles() -> None:
    first_article = create_rss_article(
        title="Birinci haber",
        url="https://example.com/1",
    )

    second_article = create_rss_article(
        title="İkinci haber",
        url="https://example.com/2",
    )

    result = deduplicate_articles(
        [
            first_article,
            second_article,
        ]
    )

    assert result == [
        first_article,
        second_article,
    ]


def test_fetch_source_safely_success() -> None:
    result = fetch_source_safely(
        source_name="Örnek Kaynak",
        source_type="örnek",
        fetch_function=lambda: [
            create_rss_article(),
        ],
    )

    assert result["success"] is True
    assert result["fetched_count"] == 1
    assert result["error"] is None

    articles = result["articles"]

    assert isinstance(articles, list)
    assert articles[0]["source_name"] == "Örnek Kaynak"
    assert articles[0]["source_type"] == "örnek"


def test_fetch_source_safely_filters_invalid_items() -> None:
    result = fetch_source_safely(
        source_name="Örnek Kaynak",
        source_type="örnek",
        fetch_function=lambda: [
            create_rss_article(),
            "geçersiz",
            None,
            123,
        ],
    )

    assert result["success"] is True
    assert result["fetched_count"] == 1


def test_fetch_source_safely_handles_error() -> None:
    def failing_source() -> list[dict[str, object]]:
        raise RuntimeError(
            "Kaynak bağlantısı başarısız."
        )

    result = fetch_source_safely(
        source_name="Hatalı Kaynak",
        source_type="örnek",
        fetch_function=failing_source,
    )

    assert result["success"] is False
    assert result["fetched_count"] == 0
    assert (
        result["error"]
        == "Kaynak bağlantısı başarısız."
    )
    assert result["articles"] == []


def test_fetch_source_safely_rejects_non_list_response() -> None:
    result = fetch_source_safely(
        source_name="Geçersiz Kaynak",
        source_type="örnek",
        fetch_function=lambda: {
            "haber": "geçersiz",
        },
    )

    assert result["success"] is False
    assert result["fetched_count"] == 0
    assert "liste döndürmedi" in str(
        result["error"]
    )


def test_collect_multi_source_news_combines_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    yahoo_article = create_yahoo_article(
        published_at="2026-07-31T12:00:00Z"
    )

    rss_article = create_rss_article(
        published_at=(
            "2026-07-30T10:00:00+00:00"
        )
    )

    monkeypatch.setattr(
        module,
        "fetch_yahoo_news",
        lambda symbol, count: [
            yahoo_article,
        ],
    )

    monkeypatch.setattr(
        module,
        "fetch_rss_news",
        lambda symbol, count: [
            rss_article,
        ],
    )

    result = collect_multi_source_news(
        symbol="TUPRS",
        count=10,
    )

    assert result["source"] == SOURCE_NAME
    assert result["symbol"] == "TUPRS"
    assert result["requested_count"] == 10
    assert result["fetched_count"] == 2
    assert result["unique_count"] == 2
    assert result["returned_count"] == 2

    assert result["successful_sources"] == [
        YAHOO_SOURCE_NAME,
        RSS_SOURCE_NAME,
    ]

    assert result["failed_sources"] == []

    articles = result["articles"]

    assert isinstance(articles, list)
    assert articles[0]["source_type"] == "yahoo"
    assert articles[1]["source_type"] == "rss"


def test_collect_multi_source_news_sorts_newest_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    older_yahoo_article = create_yahoo_article(
        title="Eski Yahoo haberi",
        published_at="2026-07-20T12:00:00Z",
    )

    newer_rss_article = create_rss_article(
        title="Yeni RSS haberi",
        published_at=(
            "2026-07-31T15:00:00+00:00"
        ),
    )

    monkeypatch.setattr(
        module,
        "fetch_yahoo_news",
        lambda symbol, count: [
            older_yahoo_article,
        ],
    )

    monkeypatch.setattr(
        module,
        "fetch_rss_news",
        lambda symbol, count: [
            newer_rss_article,
        ],
    )

    result = collect_multi_source_news(
        symbol="TUPRS",
        count=10,
    )

    articles = result["articles"]

    assert isinstance(articles, list)
    assert (
        extract_article_title(articles[0])
        == "Yeni RSS haberi"
    )


def test_collect_multi_source_news_deduplicates_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    yahoo_article = create_yahoo_article(
        title="Tüpraş yatırım açıkladı",
        url="https://example.com/aynı",
    )

    rss_article = create_rss_article(
        title="Farklı başlık",
        url="https://example.com/aynı/",
    )

    monkeypatch.setattr(
        module,
        "fetch_yahoo_news",
        lambda symbol, count: [
            yahoo_article,
        ],
    )

    monkeypatch.setattr(
        module,
        "fetch_rss_news",
        lambda symbol, count: [
            rss_article,
        ],
    )

    result = collect_multi_source_news(
        symbol="TUPRS",
        count=10,
    )

    assert result["fetched_count"] == 2
    assert result["unique_count"] == 1
    assert result["returned_count"] == 1


def test_collect_multi_source_news_respects_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    yahoo_articles = [
        create_yahoo_article(
            article_id=f"yahoo-{index}",
            title=f"Tüpraş Yahoo haber {index}",
            published_at=(
                f"2026-07-{31 - index:02d}"
                "T12:00:00Z"
            ),
            url=(
                "https://example.com/"
                f"yahoo-{index}"
            ),
        )
        for index in range(4)
    ]

    rss_articles = [
        create_rss_article(
            article_id=f"rss-{index}",
            title=f"Tüpraş RSS haber {index}",
            published_at=(
                f"2026-07-{27 - index:02d}"
                "T10:00:00+00:00"
            ),
            url=(
                "https://example.com/"
                f"rss-{index}"
            ),
        )
        for index in range(4)
    ]

    monkeypatch.setattr(
        module,
        "fetch_yahoo_news",
        lambda symbol, count: yahoo_articles,
    )

    monkeypatch.setattr(
        module,
        "fetch_rss_news",
        lambda symbol, count: rss_articles,
    )

    result = collect_multi_source_news(
        symbol="TUPRS",
        count=3,
    )

    assert result["fetched_count"] == 8
    assert result["unique_count"] == 8
    assert result["returned_count"] == 3
    assert len(result["articles"]) == 3


def test_collect_multi_source_news_continues_after_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failing_yahoo(
        symbol: str,
        count: int,
    ) -> list[dict[str, object]]:
        raise RuntimeError(
            "Yahoo bağlantısı başarısız."
        )

    rss_article = create_rss_article()

    monkeypatch.setattr(
        module,
        "fetch_yahoo_news",
        failing_yahoo,
    )

    monkeypatch.setattr(
        module,
        "fetch_rss_news",
        lambda symbol, count: [
            rss_article,
        ],
    )

    result = collect_multi_source_news(
        symbol="TUPRS",
        count=10,
    )

    assert result["successful_sources"] == [
        RSS_SOURCE_NAME,
    ]

    failed_sources = result[
        "failed_sources"
    ]

    assert isinstance(
        failed_sources,
        list,
    )

    assert failed_sources == [
        {
            "source_name": YAHOO_SOURCE_NAME,
            "error": "Yahoo bağlantısı başarısız.",
        }
    ]

    assert result["returned_count"] == 1


def test_collect_multi_source_news_only_yahoo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    yahoo_article = create_yahoo_article()

    monkeypatch.setattr(
        module,
        "fetch_yahoo_news",
        lambda symbol, count: [
            yahoo_article,
        ],
    )

    result = collect_multi_source_news(
        symbol="TUPRS",
        count=10,
        include_yahoo=True,
        include_rss=False,
    )

    assert result["successful_sources"] == [
        YAHOO_SOURCE_NAME,
    ]
    assert result["returned_count"] == 1


def test_collect_multi_source_news_only_rss(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rss_article = create_rss_article()

    monkeypatch.setattr(
        module,
        "fetch_rss_news",
        lambda symbol, count: [
            rss_article,
        ],
    )

    result = collect_multi_source_news(
        symbol="TUPRS",
        count=10,
        include_yahoo=False,
        include_rss=True,
    )

    assert result["successful_sources"] == [
        RSS_SOURCE_NAME,
    ]
    assert result["returned_count"] == 1


def test_collect_multi_source_news_passes_custom_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_yahoo(
        symbol: str,
        count: int,
    ) -> list[dict[str, object]]:
        captured["yahoo_symbol"] = symbol
        captured["yahoo_count"] = count
        return []

    def fake_rss(
        symbol: str,
        count: int,
    ) -> list[dict[str, object]]:
        captured["rss_symbol"] = symbol
        captured["rss_count"] = count
        return []

    monkeypatch.setattr(
        module,
        "fetch_yahoo_news",
        fake_yahoo,
    )

    monkeypatch.setattr(
        module,
        "fetch_rss_news",
        fake_rss,
    )

    collect_multi_source_news(
        symbol="TUPRS",
        count=30,
        yahoo_count=50,
        rss_count=20,
    )

    assert captured["yahoo_symbol"] == "TUPRS"
    assert captured["yahoo_count"] == 50
    assert captured["rss_symbol"] == "TUPRS"
    assert captured["rss_count"] == 20


def test_collect_multi_source_news_rejects_invalid_count() -> None:
    with pytest.raises(
        ValueError,
        match="Haber sayısı en az 1",
    ):
        collect_multi_source_news(
            symbol="TUPRS",
            count=0,
        )


def test_collect_multi_source_news_rejects_disabled_sources() -> None:
    with pytest.raises(
        ValueError,
        match="En az bir haber kaynağı",
    ):
        collect_multi_source_news(
            symbol="TUPRS",
            include_yahoo=False,
            include_rss=False,
        )


def test_collect_multi_source_news_rejects_invalid_yahoo_count() -> None:
    with pytest.raises(
        ValueError,
        match="Yahoo haber sayısı en az 1",
    ):
        collect_multi_source_news(
            symbol="TUPRS",
            yahoo_count=0,
        )


def test_collect_multi_source_news_rejects_invalid_rss_count() -> None:
    with pytest.raises(
        ValueError,
        match="RSS haber sayısı en az 1",
    ):
        collect_multi_source_news(
            symbol="TUPRS",
            rss_count=0,
        )


def test_fetch_multi_source_news_returns_articles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_article = create_rss_article()

    monkeypatch.setattr(
        module,
        "collect_multi_source_news",
        lambda **kwargs: {
            "articles": [
                expected_article,
            ]
        },
    )

    result = fetch_multi_source_news(
        symbol="TUPRS",
        count=10,
    )

    assert result == [
        expected_article,
    ]


def test_fetch_multi_source_news_filters_invalid_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_article = create_rss_article()

    monkeypatch.setattr(
        module,
        "collect_multi_source_news",
        lambda **kwargs: {
            "articles": [
                expected_article,
                "geçersiz",
                None,
                123,
            ]
        },
    )

    result = fetch_multi_source_news(
        symbol="TUPRS"
    )

    assert result == [
        expected_article,
    ]


def test_fetch_multi_source_news_handles_invalid_articles_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        module,
        "collect_multi_source_news",
        lambda **kwargs: {
            "articles": None,
        },
    )

    assert (
        fetch_multi_source_news(
            symbol="TUPRS"
        )
        == []
    )