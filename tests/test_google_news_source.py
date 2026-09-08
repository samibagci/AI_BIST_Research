from __future__ import annotations

from datetime import datetime, timezone

import pytest

import src.news_sources.google_news_source as module
from src.news_sources.google_news_source import (
    SOURCE_NAME,
    build_google_news_query,
    build_google_news_url,
    fetch_google_news,
    get_google_news_source,
    parse_google_news_feed,
    quote_search_term,
    strip_html,
)
@pytest.fixture(autouse=True)
def mock_company_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_resolve_company_aliases(
        symbol: str,
        aliases=None,
    ) -> tuple[str, ...]:
        if symbol in {
            "TUPRS",
            "TUPRS.IS",
        }:
            result = [
                "TUPRS",
                "Tüpraş",
                "Türkiye Petrol Rafinerileri",
            ]
        else:
            result = [
                symbol.removesuffix(".IS"),
            ]

        if aliases is not None:
            result.extend(aliases)

        return tuple(dict.fromkeys(result))

    monkeypatch.setattr(
        module,
        "resolve_company_aliases",
        fake_resolve_company_aliases,
    )

GOOGLE_NEWS_DATA = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Google News</title>

        <item>
            <guid>haber-1</guid>
            <title><![CDATA[
                Tüpraş yeni yatırım kararını açıkladı
            ]]></title>
            <description><![CDATA[
                <p>Tüpraş kapasite artışı planlıyor.</p>
            ]]></description>
            <pubDate>
                Fri, 31 Jul 2026 12:00:00 +0000
            </pubDate>
            <link>
                https://news.google.com/rss/articles/haber-1
            </link>
            <source url="https://example.com">
                Ekonomi Haber
            </source>
        </item>

        <item>
            <guid>haber-2</guid>
            <title>
                Türkiye Petrol Rafinerileri üretim açıkladı
            </title>
            <description>
                Şirket üretim verilerini duyurdu.
            </description>
            <pubDate>
                Thu, 30 Jul 2026 10:00:00 +0000
            </pubDate>
            <link>
                https://news.google.com/rss/articles/haber-2
            </link>
            <source url="https://example.org">
                Finans Gündem
            </source>
        </item>
    </channel>
</rss>
""".encode("utf-8")


def create_article(
    article_id: str = "haber-1",
    title: str = "Tüpraş yatırım açıkladı",
    published_at: str = "2026-07-31T12:00:00+00:00",
    link: str = "https://example.com/haber-1",
) -> dict[str, object]:
    return {
        "id": article_id,
        "title": title,
        "summary": "Şirket kapasite artışı açıkladı.",
        "publisher": "Örnek Kaynak",
        "publishedAt": published_at,
        "link": link,
        "relatedTickers": [
            "TUPRS.IS",
        ],
        "source_name": SOURCE_NAME,
        "source_type": "google_news",
    }


def test_strip_html() -> None:
    assert (
        strip_html(
            "<p>T&uuml;pra&#351; yatırım açıkladı.</p>"
        )
        == "Tüpraş yatırım açıkladı."
    )


def test_strip_html_empty_value() -> None:
    assert strip_html("") is None
    assert strip_html(None) is None


def test_quote_search_term_single_word() -> None:
    assert (
        quote_search_term("TUPRS")
        == "TUPRS"
    )


def test_quote_search_term_multiple_words() -> None:
    assert (
        quote_search_term(
            "Türkiye Petrol Rafinerileri"
        )
        == '"Türkiye Petrol Rafinerileri"'
    )


def test_quote_search_term_empty_value() -> None:
    assert quote_search_term("") == ""


def test_build_google_news_query() -> None:
    query = build_google_news_query(
        symbol="TUPRS",
        lookback_days=30,
    )

    assert "TUPRS" in query
    assert "Tüpraş" in query
    assert (
        '"Türkiye Petrol Rafinerileri"'
        in query
    )
    assert "when:30d" in query


def test_build_google_news_query_with_custom_alias() -> None:
    query = build_google_news_query(
        symbol="TUPRS",
        aliases=[
            "Tüpraş Rafineri",
        ],
        lookback_days=60,
    )

    assert '"Tüpraş Rafineri"' in query
    assert "when:60d" in query


def test_build_google_news_query_rejects_invalid_lookback() -> None:
    with pytest.raises(
        ValueError,
        match="en az 1 gün",
    ):
        build_google_news_query(
            symbol="TUPRS",
            lookback_days=0,
        )


def test_build_google_news_url() -> None:
    url = build_google_news_url(
        symbol="TUPRS",
        lookback_days=30,
    )

    assert url.startswith(
        "https://news.google.com/rss/search?"
    )

    assert "hl=tr" in url
    assert "gl=TR" in url
    assert "ceid=TR:tr" in url
    assert "when%3A30d" in url


def test_get_google_news_source() -> None:
    element = module.ElementTree.fromstring(
        """
        <item>
            <source url="https://example.com">
                Ekonomi Haber
            </source>
        </item>
        """
    )

    assert (
        get_google_news_source(element)
        == "Ekonomi Haber"
    )


def test_get_google_news_source_missing() -> None:
    element = module.ElementTree.fromstring(
        """
        <item>
            <title>Haber</title>
        </item>
        """
    )

    assert (
        get_google_news_source(element)
        is None
    )


def test_parse_google_news_feed() -> None:
    articles = parse_google_news_feed(
        feed_data=GOOGLE_NEWS_DATA,
        symbol="TUPRS",
    )

    assert len(articles) == 2

    first_article = articles[0]

    assert first_article["id"] == "haber-1"

    assert (
        first_article["title"]
        == "Tüpraş yeni yatırım kararını açıkladı"
    )

    assert (
        first_article["summary"]
        == "Tüpraş kapasite artışı planlıyor."
    )

    assert (
        first_article["publisher"]
        == "Ekonomi Haber"
    )

    assert (
        first_article["publishedAt"]
        == "2026-07-31T12:00:00+00:00"
    )

    assert (
        first_article["link"]
        == "https://news.google.com/rss/articles/haber-1"
    )

    assert first_article[
        "relatedTickers"
    ] == [
        "TUPRS.IS",
    ]

    assert (
        first_article["source_name"]
        == SOURCE_NAME
    )

    assert (
        first_article["source_type"]
        == "google_news"
    )


def test_parse_google_news_feed_returns_empty() -> None:
    assert (
        parse_google_news_feed(
            feed_data=b"",
            symbol="TUPRS",
        )
        == []
    )


def test_parse_google_news_feed_rejects_invalid_xml() -> None:
    with pytest.raises(
        ValueError,
        match="geçerli XML değil",
    ):
        parse_google_news_feed(
            feed_data=b"<rss><item>",
            symbol="TUPRS",
        )


def test_parse_google_news_feed_skips_missing_title() -> None:
    feed_data = """
    <rss>
        <channel>
            <item>
                <guid>haber-1</guid>
                <description>Başlık yok</description>
            </item>
        </channel>
    </rss>
    """.encode("utf-8")

    assert (
        parse_google_news_feed(
            feed_data=feed_data,
            symbol="TUPRS",
        )
        == []
    )


def test_parse_google_news_feed_uses_source_name_when_publisher_missing() -> None:
    feed_data = """
    <rss>
        <channel>
            <item>
                <guid>haber-1</guid>
                <title>Tüpraş haberi</title>
                <pubDate>
                    Fri, 31 Jul 2026 12:00:00 +0000
                </pubDate>
                <link>
                    https://example.com/haber
                </link>
            </item>
        </channel>
    </rss>
    """.encode("utf-8")

    articles = parse_google_news_feed(
        feed_data=feed_data,
        symbol="TUPRS",
    )

    assert len(articles) == 1

    assert (
        articles[0]["publisher"]
        == SOURCE_NAME
    )


def test_fetch_google_news(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_download_rss_feed(
        feed_url: str,
        timeout: int,
    ) -> bytes:
        captured["feed_url"] = feed_url
        captured["timeout"] = timeout

        return GOOGLE_NEWS_DATA

    monkeypatch.setattr(
        module,
        "download_rss_feed",
        fake_download_rss_feed,
    )

    result = fetch_google_news(
        symbol="TUPRS",
        count=10,
        lookback_days=90,
        timeout=12,
    )

    assert len(result) == 2

    assert captured["timeout"] == 12

    assert (
        "news.google.com/rss/search"
        in str(captured["feed_url"])
    )


def test_fetch_google_news_sorts_newest_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    older_article = create_article(
        article_id="old",
        title="Tüpraş eski haber",
        published_at=(
            "2026-07-20T10:00:00+00:00"
        ),
        link="https://example.com/old",
    )

    newer_article = create_article(
        article_id="new",
        title="Tüpraş yeni haber",
        published_at=(
            "2026-07-31T10:00:00+00:00"
        ),
        link="https://example.com/new",
    )

    monkeypatch.setattr(
        module,
        "download_rss_feed",
        lambda feed_url, timeout: b"<rss />",
    )

    monkeypatch.setattr(
        module,
        "parse_google_news_feed",
        lambda feed_data, symbol: [
            older_article,
            newer_article,
        ],
    )

    result = fetch_google_news(
        symbol="TUPRS",
        count=10,
    )

    assert result == [
        newer_article,
        older_article,
    ]


def test_fetch_google_news_deduplicates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_article = create_article(
        article_id="1",
        title="Tüpraş yatırım açıkladı",
        link="https://example.com/aynı",
    )

    duplicate_article = create_article(
        article_id="2",
        title="Başka başlık",
        link="https://example.com/aynı/",
    )

    monkeypatch.setattr(
        module,
        "download_rss_feed",
        lambda feed_url, timeout: b"<rss />",
    )

    monkeypatch.setattr(
        module,
        "parse_google_news_feed",
        lambda feed_data, symbol: [
            first_article,
            duplicate_article,
        ],
    )

    result = fetch_google_news(
        symbol="TUPRS",
        count=10,
    )

    assert result == [
        first_article,
    ]


def test_fetch_google_news_respects_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    articles = [
        create_article(
            article_id=str(index),
            title=f"Tüpraş haber {index}",
            published_at=(
                f"2026-07-{31 - index:02d}"
                "T10:00:00+00:00"
            ),
            link=(
                "https://example.com/"
                f"{index}"
            ),
        )
        for index in range(5)
    ]

    monkeypatch.setattr(
        module,
        "download_rss_feed",
        lambda feed_url, timeout: b"<rss />",
    )

    monkeypatch.setattr(
        module,
        "parse_google_news_feed",
        lambda feed_data, symbol: articles,
    )

    result = fetch_google_news(
        symbol="TUPRS",
        count=2,
    )

    assert len(result) == 2
    assert result == articles[:2]


def test_fetch_google_news_rejects_invalid_count() -> None:
    with pytest.raises(
        ValueError,
        match="Haber sayısı en az 1",
    ):
        fetch_google_news(
            symbol="TUPRS",
            count=0,
        )


def test_fetch_google_news_rejects_invalid_lookback() -> None:
    with pytest.raises(
        ValueError,
        match="en az 1 gün",
    ):
        fetch_google_news(
            symbol="TUPRS",
            lookback_days=0,
        )


def test_fetch_google_news_rejects_invalid_timeout() -> None:
    with pytest.raises(
        ValueError,
        match="zaman aşımı en az",
    ):
        fetch_google_news(
            symbol="TUPRS",
            timeout=0,
        )

def test_fetch_google_news_prioritizes_investment_score_over_recency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    older_high_score_article = create_article(
        article_id="high-score",
        title="ASELSAN güçlü yatırım haberi",
        published_at=(
            "2026-07-20T10:00:00+00:00"
        ),
        link="https://example.com/high-score",
    )

    newer_zero_score_article = create_article(
        article_id="zero-score",
        title="ASELSAN genel açıklama",
        published_at=(
            "2026-07-31T10:00:00+00:00"
        ),
        link="https://example.com/zero-score",
    )

    monkeypatch.setattr(
        module,
        "download_rss_feed",
        lambda feed_url, timeout: b"<rss />",
    )

    monkeypatch.setattr(
        module,
        "parse_google_news_feed",
        lambda feed_data, symbol: [
            newer_zero_score_article,
            older_high_score_article,
        ],
    )

    monkeypatch.setattr(
        module,
        "filter_relevant_articles",
        lambda symbol, articles, aliases=None: list(
            articles
        ),
    )

    monkeypatch.setattr(
        module,
        "calculate_investment_relevance_score",
        lambda article: (
            4
            if article.get("id") == "high-score"
            else 0
        ),
    )

    result = fetch_google_news(
        symbol="ASELS",
        count=2,
    )

    assert result == [
        older_high_score_article,
        newer_zero_score_article,
    ]        