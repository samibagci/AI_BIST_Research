from __future__ import annotations

from datetime import datetime, timezone
from urllib.error import URLError

import pytest

import src.news_sources.rss_source as module
from src.news_sources.rss_source import (
    MAX_FEED_SIZE_BYTES,
    article_deduplication_key,
    article_sort_datetime,
    deduplicate_articles,
    download_rss_feed,
    fetch_rss_news,
    fetch_single_rss_source,
    get_child_text,
    get_entry_link,
    is_article_relevant,
    local_name,
    normalize_article_url,
    normalize_match_text,
    parse_feed_datetime,
    parse_rss_feed,
    resolve_company_aliases,
    safe_text,
    strip_html,
    text_contains_alias,
    validate_feed_url,
)


RSS_DATA = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Ekonomi Haberleri</title>
        <item>
            <guid>haber-1</guid>
            <title><![CDATA[THY yeni seferlerini duyurdu]]></title>
            <description><![CDATA[
                <p>T&uuml;rk Hava Yollar&#305; yeni u&ccedil;u&#351; ba&#351;latt&#305;.</p>
            ]]></description>
            <pubDate>Fri, 31 Jul 2026 10:30:00 +0000</pubDate>
            <link>https://example.com/haber-1</link>
        </item>
        <item>
            <guid>haber-2</guid>
            <title>Koç Holding yatırım açıkladı</title>
            <description>Yeni yatırım kararı açıklandı.</description>
            <pubDate>Thu, 30 Jul 2026 09:00:00 +0000</pubDate>
            <link>https://example.com/haber-2</link>
        </item>
    </channel>
</rss>
""".encode("utf-8")


ATOM_DATA = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
    <title>Finans Akışı</title>
    <entry>
        <id>atom-1</id>
        <title>ASELSAN yeni sözleşme imzaladı</title>
        <summary>Şirket önemli bir ihale kazandı.</summary>
        <published>2026-07-31T12:00:00Z</published>
        <link href="https://example.com/atom-1" />
    </entry>
</feed>
""".encode("utf-8")


@pytest.fixture(autouse=True)
def mock_company_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get_company_aliases(
        symbol: str,
    ) -> tuple[str, ...]:
        if symbol == "THYAO":
            return (
                "THYAO",
                "Türk Hava Yolları",
                "Turkish Airlines",
            )

        if symbol == "TUPRS":
            return (
                "TUPRS",
                "Tüpraş",
                "Türkiye Petrol Rafinerileri",
            )

        if symbol == "ASELS":
            return (
                "ASELS",
                "ASELSAN",
            )

        return (
            symbol,
        )

    monkeypatch.setattr(
        module,
        "get_company_aliases",
        fake_get_company_aliases,
    )


def create_article(
    title: str = "Türk Hava Yolları yeni sefer başlattı",
    summary: str = "THYAO kapasite artışı açıkladı.",
    link: str = "https://example.com/haber",
    published_at: str = "2026-07-31T10:00:00+00:00",
) -> dict[str, object]:
    return {
        "id": link,
        "title": title,
        "summary": summary,
        "publisher": "Örnek Kaynak",
        "publishedAt": published_at,
        "link": link,
        "relatedTickers": [
            "THYAO.IS",
        ],
        "source_type": "rss",
    }


def test_safe_text_cleans_whitespace() -> None:
    assert safe_text(
        "  Örnek   metin  "
    ) == "Örnek metin"

    assert safe_text("") is None
    assert safe_text("   ") is None
    assert safe_text(123) is None


def test_strip_html_removes_tags_and_decodes_entities() -> None:
    result = strip_html(
        "<p>T&uuml;rk Hava Yollar&#305;</p>"
    )

    assert result == "Türk Hava Yolları"


def test_local_name_removes_namespace() -> None:
    assert (
        local_name(
            "{http://www.w3.org/2005/Atom}entry"
        )
        == "entry"
    )

    assert (
        local_name(
            "content:encoded"
        )
        == "encoded"
    )

    assert local_name("title") == "title"


def test_get_child_text_reads_requested_element() -> None:
    root = module.ElementTree.fromstring(
        """
        <item>
            <title>Haber başlığı</title>
            <description>Haber özeti</description>
        </item>
        """
    )

    assert (
        get_child_text(
            root,
            ("title",),
        )
        == "Haber başlığı"
    )

    assert (
        get_child_text(
            root,
            ("missing",),
        )
        is None
    )


def test_get_entry_link_reads_text_link() -> None:
    root = module.ElementTree.fromstring(
        """
        <item>
            <link>https://example.com/haber</link>
        </item>
        """
    )

    assert (
        get_entry_link(root)
        == "https://example.com/haber"
    )


def test_get_entry_link_reads_atom_href() -> None:
    root = module.ElementTree.fromstring(
        """
        <entry>
            <link href="https://example.com/atom" />
        </entry>
        """
    )

    assert (
        get_entry_link(root)
        == "https://example.com/atom"
    )


def test_parse_feed_datetime_accepts_rfc_date() -> None:
    result = parse_feed_datetime(
        "Fri, 31 Jul 2026 10:30:00 +0000"
    )

    assert result == datetime(
        2026,
        7,
        31,
        10,
        30,
        tzinfo=timezone.utc,
    )


def test_parse_feed_datetime_accepts_iso_date() -> None:
    result = parse_feed_datetime(
        "2026-07-31T12:00:00Z"
    )

    assert result == datetime(
        2026,
        7,
        31,
        12,
        0,
        tzinfo=timezone.utc,
    )


@pytest.mark.parametrize(
    "value",
    [
        "",
        "geçersiz tarih",
        None,
        123,
    ],
)
def test_parse_feed_datetime_rejects_invalid_values(
    value: object,
) -> None:
    assert parse_feed_datetime(
        value
    ) is None


def test_validate_feed_url_accepts_http_and_https() -> None:
    assert (
        validate_feed_url(
            "https://example.com/rss.xml"
        )
        == "https://example.com/rss.xml"
    )

    assert (
        validate_feed_url(
            "http://example.com/rss.xml"
        )
        == "http://example.com/rss.xml"
    )


@pytest.mark.parametrize(
    "url",
    [
        "",
        "example.com/rss.xml",
        "ftp://example.com/rss.xml",
        "https:///rss.xml",
    ],
)
def test_validate_feed_url_rejects_invalid_url(
    url: str,
) -> None:
    with pytest.raises(
        ValueError
    ):
        validate_feed_url(
            url
        )


def test_download_rss_feed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        headers = {
            "Content-Length": str(
                len(RSS_DATA)
            ),
        }

        def __enter__(
            self,
        ) -> FakeResponse:
            return self

        def __exit__(
            self,
            exc_type: object,
            exc_value: object,
            traceback: object,
        ) -> None:
            return None

        def read(
            self,
            size: int,
        ) -> bytes:
            captured[
                "read_size"
            ] = size

            return RSS_DATA

    def fake_urlopen(
        request: object,
        timeout: int,
    ) -> FakeResponse:
        captured[
            "request"
        ] = request

        captured[
            "timeout"
        ] = timeout

        return FakeResponse()

    monkeypatch.setattr(
        module,
        "urlopen",
        fake_urlopen,
    )

    result = download_rss_feed(
        "https://example.com/rss.xml",
        timeout=10,
    )

    assert result == RSS_DATA
    assert captured["timeout"] == 10

    assert (
        captured["read_size"]
        == MAX_FEED_SIZE_BYTES + 1
    )


def test_download_rss_feed_rejects_large_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        headers = {
            "Content-Length": str(
                MAX_FEED_SIZE_BYTES + 1
            ),
        }

        def __enter__(
            self,
        ) -> FakeResponse:
            return self

        def __exit__(
            self,
            exc_type: object,
            exc_value: object,
            traceback: object,
        ) -> None:
            return None

        def read(
            self,
            size: int,
        ) -> bytes:
            return b"data"

    monkeypatch.setattr(
        module,
        "urlopen",
        lambda request, timeout: (
            FakeResponse()
        ),
    )

    with pytest.raises(
        ValueError,
        match="boyutu aşıyor",
    ):
        download_rss_feed(
            "https://example.com/rss.xml"
        )


def test_download_rss_feed_rejects_empty_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        headers: dict[
            str,
            str,
        ] = {}

        def __enter__(
            self,
        ) -> FakeResponse:
            return self

        def __exit__(
            self,
            exc_type: object,
            exc_value: object,
            traceback: object,
        ) -> None:
            return None

        def read(
            self,
            size: int,
        ) -> bytes:
            return b""

    monkeypatch.setattr(
        module,
        "urlopen",
        lambda request, timeout: (
            FakeResponse()
        ),
    )

    with pytest.raises(
        ValueError,
        match="boş veri",
    ):
        download_rss_feed(
            "https://example.com/rss.xml"
        )


def test_parse_rss_feed() -> None:
    articles = parse_rss_feed(
        feed_data=RSS_DATA,
        source_name="Örnek Ekonomi",
        yahoo_symbol="THYAO.IS",
    )

    assert len(articles) == 2

    first_article = articles[0]

    assert (
        first_article["id"]
        == "haber-1"
    )

    assert (
        first_article["title"]
        == "THY yeni seferlerini duyurdu"
    )

    assert (
        first_article["summary"]
        == "Türk Hava Yolları yeni uçuş başlattı."
    )

    assert (
        first_article["publisher"]
        == "Örnek Ekonomi"
    )

    assert (
        first_article["publishedAt"]
        == "2026-07-31T10:30:00+00:00"
    )

    assert (
        first_article["link"]
        == "https://example.com/haber-1"
    )

    assert (
        first_article[
            "relatedTickers"
        ]
        == ["THYAO.IS"]
    )

    assert (
        first_article[
            "source_type"
        ]
        == "rss"
    )


def test_parse_atom_feed() -> None:
    articles = parse_rss_feed(
        feed_data=ATOM_DATA,
        source_name="Atom Kaynağı",
        yahoo_symbol="ASELS.IS",
    )

    assert len(articles) == 1

    assert (
        articles[0]["title"]
        == "ASELSAN yeni sözleşme imzaladı"
    )

    assert (
        articles[0]["link"]
        == "https://example.com/atom-1"
    )


def test_parse_rss_feed_rejects_invalid_xml() -> None:
    with pytest.raises(
        ValueError,
        match="geçerli XML değil",
    ):
        parse_rss_feed(
            feed_data=b"<rss><item>",
            source_name="Kaynak",
            yahoo_symbol="THYAO.IS",
        )


def test_parse_rss_feed_skips_missing_title() -> None:
    feed_data = """
    <rss>
        <channel>
            <item>
                <description>Başlıksız haber</description>
            </item>
        </channel>
    </rss>
    """.encode("utf-8")

    assert (
        parse_rss_feed(
            feed_data=feed_data,
            source_name="Kaynak",
            yahoo_symbol="THYAO.IS",
        )
        == []
    )


def test_normalize_match_text() -> None:
    assert (
        normalize_match_text(
            "<b>Türk Hava Yolları</b>"
        )
        == "turk hava yollari"
    )


def test_text_contains_alias_matches_complete_word() -> None:
    text = normalize_match_text(
        "Türk Hava Yolları yeni uçuş açıkladı."
    )

    assert text_contains_alias(
        text,
        "Türk Hava Yolları",
    )

    assert not text_contains_alias(
        text,
        "Türk Hava Yol",
    )


def test_resolve_company_aliases() -> None:
    aliases = resolve_company_aliases(
        symbol="THYAO",
        aliases=[
            "THY",
            "Turkish Airlines",
        ],
    )

    assert aliases[0] == "THYAO"

    assert (
        "Türk Hava Yolları"
        in aliases
    )

    assert (
        "Turkish Airlines"
        in aliases
    )

    assert "THY" in aliases

    assert (
        aliases.count(
            "Turkish Airlines"
        )
        == 1
    )


def test_is_article_relevant() -> None:
    article = create_article()

    assert is_article_relevant(
        article,
        (
            "THYAO",
            "Türk Hava Yolları",
        ),
    )

    assert not is_article_relevant(
        article,
        (
            "ASELSAN",
        ),
    )


def test_normalize_article_url() -> None:
    result = normalize_article_url(
        "HTTPS://EXAMPLE.COM/haber/#bolum"
    )

    assert result == (
        "https://example.com/haber"
    )


def test_article_deduplication_key_prefers_url() -> None:
    article = create_article(
        title="Başlık",
        link="https://example.com/haber/",
    )

    assert (
        article_deduplication_key(
            article
        )
        == "url:https://example.com/haber"
    )


def test_article_deduplication_key_uses_title() -> None:
    article = {
        "title": "Örnek Haber Başlığı",
        "link": None,
    }

    assert (
        article_deduplication_key(
            article
        )
        == "title:ornek haber basligi"
    )


def test_deduplicate_articles() -> None:
    first_article = create_article(
        title="İlk başlık",
        link="https://example.com/aynı",
    )

    duplicate_article = create_article(
        title="Farklı başlık",
        link="https://example.com/aynı/",
    )

    unique_article = create_article(
        title="Başka haber",
        link="https://example.com/farkli",
    )

    result = deduplicate_articles(
        [
            first_article,
            duplicate_article,
            unique_article,
        ]
    )

    assert result == [
        first_article,
        unique_article,
    ]


def test_article_sort_datetime() -> None:
    article = create_article(
        published_at=(
            "2026-07-31T10:00:00+00:00"
        )
    )

    assert (
        article_sort_datetime(
            article
        )
        == datetime(
            2026,
            7,
            31,
            10,
            0,
            tzinfo=timezone.utc,
        )
    )


def test_fetch_single_rss_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_download_rss_feed(
        feed_url: str,
        timeout: int,
    ) -> bytes:
        captured[
            "feed_url"
        ] = feed_url

        captured[
            "timeout"
        ] = timeout

        return RSS_DATA

    monkeypatch.setattr(
        module,
        "download_rss_feed",
        fake_download_rss_feed,
    )

    result = fetch_single_rss_source(
        source_name="Ekonomi",
        feed_url=(
            "https://example.com/rss.xml"
        ),
        symbol="THYAO",
        timeout=12,
    )

    assert (
        captured["feed_url"]
        == "https://example.com/rss.xml"
    )

    assert (
        captured["timeout"]
        == 12
    )

    assert len(result) == 2

    assert (
        result[0][
            "relatedTickers"
        ]
        == ["THYAO.IS"]
    )


def test_fetch_rss_news_filters_and_sorts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    older_relevant = create_article(
        title="THYAO yeni yatırım açıkladı",
        link="https://example.com/eski",
        published_at=(
            "2026-07-29T10:00:00+00:00"
        ),
    )

    newer_relevant = create_article(
        title=(
            "Türk Hava Yolları kapasite artırdı"
        ),
        link="https://example.com/yeni",
        published_at=(
            "2026-07-31T10:00:00+00:00"
        ),
    )

    irrelevant = create_article(
        title=(
            "ASELSAN yeni sözleşme imzaladı"
        ),
        summary=(
            "Savunma sanayisi haberi."
        ),
        link=(
            "https://example.com/ilgisiz"
        ),
    )

    def fake_fetch_single_rss_source(
        source_name: str,
        feed_url: str,
        symbol: str,
        timeout: int,
    ) -> list[
        dict[str, object]
    ]:
        if (
            source_name
            == "Kaynak 1"
        ):
            return [
                older_relevant,
                irrelevant,
            ]

        return [
            newer_relevant,
            older_relevant,
        ]

    monkeypatch.setattr(
        module,
        "fetch_single_rss_source",
        fake_fetch_single_rss_source,
    )

    result = fetch_rss_news(
        symbol="THYAO",
        count=10,
        feed_urls={
            "Kaynak 1": (
                "https://example.com/1.xml"
            ),
            "Kaynak 2": (
                "https://example.com/2.xml"
            ),
        },
    )

    assert result == [
        newer_relevant,
        older_relevant,
    ]


def test_fetch_rss_news_continues_after_source_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    successful_article = (
        create_article()
    )

    def fake_fetch_single_rss_source(
        source_name: str,
        feed_url: str,
        symbol: str,
        timeout: int,
    ) -> list[
        dict[str, object]
    ]:
        if (
            source_name
            == "Hatalı Kaynak"
        ):
            raise URLError(
                "Bağlantı kurulamadı"
            )

        return [
            successful_article,
        ]

    monkeypatch.setattr(
        module,
        "fetch_single_rss_source",
        fake_fetch_single_rss_source,
    )

    result = fetch_rss_news(
        symbol="THYAO",
        feed_urls={
            "Hatalı Kaynak": (
                "https://example.com/error.xml"
            ),
            "Çalışan Kaynak": (
                "https://example.com/success.xml"
            ),
        },
    )

    assert result == [
        successful_article,
    ]


def test_fetch_rss_news_respects_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    articles = [
        create_article(
            title=(
                f"THYAO haber {index}"
            ),
            link=(
                "https://example.com/"
                f"{index}"
            ),
            published_at=(
                f"2026-07-{31 - index:02d}"
                "T10:00:00+00:00"
            ),
        )
        for index in range(5)
    ]

    monkeypatch.setattr(
        module,
        "fetch_single_rss_source",
        lambda **kwargs: articles,
    )

    result = fetch_rss_news(
        symbol="THYAO",
        count=2,
        feed_urls={
            "Kaynak": (
                "https://example.com/rss.xml"
            ),
        },
    )

    assert len(result) == 2

    assert result == (
        articles[:2]
    )


def test_fetch_rss_news_returns_empty_for_empty_sources() -> None:
    assert (
        fetch_rss_news(
            symbol="THYAO",
            feed_urls={},
        )
        == []
    )


def test_fetch_rss_news_rejects_invalid_count() -> None:
    with pytest.raises(
        ValueError,
        match="Haber sayısı en az 1",
    ):
        fetch_rss_news(
            symbol="THYAO",
            count=0,
        )


def test_fetch_rss_news_rejects_invalid_timeout() -> None:
    with pytest.raises(
        ValueError,
        match="zaman aşımı en az",
    ):
        fetch_rss_news(
            symbol="THYAO",
            timeout=0,
        )