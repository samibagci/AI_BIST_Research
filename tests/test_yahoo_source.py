from __future__ import annotations

import pytest

import src.news_sources.yahoo_source as module
from src.news_sources.yahoo_source import (
    build_yahoo_relevance_article,
    fetch_relevant_yahoo_news,
    fetch_yahoo_news,
    filter_yahoo_news_by_relevance,
    get_nested_value,
    safe_text,
)


def create_raw_article(
    title: str = "Şirket büyüme açıkladı",
    summary: str | None = None,
    article_id: str = "haber-1",
) -> dict[str, object]:
    content: dict[str, object] = {
        "id": article_id,
        "title": title,
    }

    if summary is not None:
        content["summary"] = summary

    return {
        "content": content,
    }


def test_safe_text_cleans_whitespace() -> None:
    assert (
        safe_text("  örnek   metin  ")
        == "örnek metin"
    )

    assert safe_text("") is None
    assert safe_text("   ") is None
    assert safe_text(None) is None
    assert safe_text(123) is None


def test_get_nested_value() -> None:
    data = {
        "content": {
            "title": "Tüpraş yatırım açıkladı",
        }
    }

    assert (
        get_nested_value(
            data,
            "content",
            "title",
        )
        == "Tüpraş yatırım açıkladı"
    )


def test_get_nested_value_returns_none_for_missing_path() -> None:
    data = {
        "content": {
            "title": "Haber",
        }
    }

    assert (
        get_nested_value(
            data,
            "content",
            "summary",
        )
        is None
    )

    assert (
        get_nested_value(
            data,
            "missing",
            "title",
        )
        is None
    )


def test_build_yahoo_relevance_article_reads_nested_fields() -> None:
    article = {
        "content": {
            "title": (
                "Tüpraş yeni yatırım açıkladı"
            ),
            "summary": (
                "Şirket üretim kapasitesini artıracak."
            ),
        }
    }

    result = build_yahoo_relevance_article(
        article
    )

    assert result == {
        "title": (
            "Tüpraş yeni yatırım açıkladı"
        ),
        "summary": (
            "Şirket üretim kapasitesini artıracak."
        ),
    }


def test_build_yahoo_relevance_article_uses_description() -> None:
    article = {
        "content": {
            "title": (
                "ASELSAN yeni sözleşme imzaladı"
            ),
            "description": (
                "Şirket yeni sipariş aldı."
            ),
        }
    }

    result = build_yahoo_relevance_article(
        article
    )

    assert result == {
        "title": (
            "ASELSAN yeni sözleşme imzaladı"
        ),
        "summary": (
            "Şirket yeni sipariş aldı."
        ),
    }


def test_build_yahoo_relevance_article_uses_top_level_fields() -> None:
    article = {
        "title": (
            "Tüpraş bilanço sonuçlarını açıkladı"
        ),
        "summary": (
            "Şirket finansal sonuçlarını yayımladı."
        ),
    }

    result = build_yahoo_relevance_article(
        article
    )

    assert result == {
        "title": (
            "Tüpraş bilanço sonuçlarını açıkladı"
        ),
        "summary": (
            "Şirket finansal sonuçlarını yayımladı."
        ),
    }


def test_build_yahoo_relevance_article_handles_missing_text() -> None:
    result = build_yahoo_relevance_article(
        {
            "content": {
                "id": "haber-1",
            }
        }
    )

    assert result == {
        "title": None,
        "summary": None,
    }


def test_filter_yahoo_news_by_relevance_keeps_business_news() -> None:
    relevant_article = create_raw_article(
        title=(
            "Tüpraş yeni yatırım açıkladı"
        ),
        summary=(
            "Şirket yeni tesis kuracak."
        ),
    )

    result = filter_yahoo_news_by_relevance(
        articles=[
            relevant_article,
        ],
        aliases=(
            "TUPRS",
            "Tüpraş",
        ),
    )

    assert result == [
        relevant_article,
    ]


def test_filter_yahoo_news_by_relevance_rejects_unrelated_news() -> None:
    unrelated_article = create_raw_article(
        title=(
            "Air Transat yeni uçuş rotası açıkladı"
        ),
        summary=(
            "Havayolu şirketi yeni sefer başlatacak."
        ),
    )

    result = filter_yahoo_news_by_relevance(
        articles=[
            unrelated_article,
        ],
        aliases=(
            "THYAO",
            "Türk Hava Yolları",
            "Turkish Airlines",
        ),
    )

    assert result == []


def test_filter_yahoo_news_by_relevance_rejects_sports_context() -> None:
    sports_article = create_raw_article(
        title=(
            "Tüpraş Stadyumu'nda derbi oynandı"
        ),
        summary=(
            "Taraftarlar tribünleri doldurdu."
        ),
    )

    result = filter_yahoo_news_by_relevance(
        articles=[
            sports_article,
        ],
        aliases=(
            "TUPRS",
            "Tüpraş",
        ),
    )

    assert result == []


def test_filter_yahoo_news_by_relevance_keeps_business_context_even_with_sports_term() -> None:
    sponsorship_article = create_raw_article(
        title=(
            "Tüpraş sponsorluk anlaşmasını açıkladı"
        ),
        summary=(
            "Şirket stadyum isim sponsorluğu "
            "için sözleşme imzaladı."
        ),
    )

    result = filter_yahoo_news_by_relevance(
        articles=[
            sponsorship_article,
        ],
        aliases=(
            "TUPRS",
            "Tüpraş",
        ),
    )

    assert result == [
        sponsorship_article,
    ]


def test_filter_yahoo_news_by_relevance_is_company_independent() -> None:
    article = create_raw_article(
        title=(
            "ASELSAN yeni sözleşme imzaladı"
        ),
        summary=(
            "Şirket yeni sipariş aldı."
        ),
    )

    result = filter_yahoo_news_by_relevance(
        articles=[
            article,
        ],
        aliases=(
            "ASELS",
            "ASELSAN",
        ),
    )

    assert result == [
        article,
    ]


def test_fetch_yahoo_news_uses_bist_symbol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeTicker:
        def __init__(
            self,
            symbol: str,
        ) -> None:
            captured["symbol"] = symbol

        def get_news(
            self,
            count: int,
            tab: str,
        ) -> list[dict[str, object]]:
            captured["count"] = count
            captured["tab"] = tab

            return [
                create_raw_article(),
            ]

    monkeypatch.setattr(
        module.yf,
        "Ticker",
        FakeTicker,
    )

    result = fetch_yahoo_news(
        symbol="THYAO",
        count=20,
    )

    assert (
        captured["symbol"]
        == "THYAO.IS"
    )

    assert captured["count"] == 20
    assert captured["tab"] == "news"
    assert len(result) == 1


def test_fetch_yahoo_news_returns_empty_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeTicker:
        def __init__(
            self,
            symbol: str,
        ) -> None:
            self.symbol = symbol

        def get_news(
            self,
            count: int,
            tab: str,
        ) -> None:
            return None

    monkeypatch.setattr(
        module.yf,
        "Ticker",
        FakeTicker,
    )

    assert (
        fetch_yahoo_news("THYAO")
        == []
    )


def test_fetch_yahoo_news_filters_invalid_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeTicker:
        def __init__(
            self,
            symbol: str,
        ) -> None:
            self.symbol = symbol

        def get_news(
            self,
            count: int,
            tab: str,
        ) -> list[object]:
            return [
                create_raw_article(),
                "geçersiz haber",
                None,
                123,
            ]

    monkeypatch.setattr(
        module.yf,
        "Ticker",
        FakeTicker,
    )

    result = fetch_yahoo_news(
        "THYAO"
    )

    assert result == [
        create_raw_article(),
    ]


def test_fetch_yahoo_news_rejects_invalid_count() -> None:
    with pytest.raises(
        ValueError,
        match="Haber sayısı en az 1",
    ):
        fetch_yahoo_news(
            symbol="THYAO",
            count=0,
        )


def test_fetch_yahoo_news_rejects_invalid_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeTicker:
        def __init__(
            self,
            symbol: str,
        ) -> None:
            self.symbol = symbol

        def get_news(
            self,
            count: int,
            tab: str,
        ) -> dict[str, object]:
            return {
                "haber": (
                    "geçersiz format"
                ),
            }

    monkeypatch.setattr(
        module.yf,
        "Ticker",
        FakeTicker,
    )

    with pytest.raises(
        ValueError,
        match="beklenen formatta değil",
    ):
        fetch_yahoo_news(
            "THYAO"
        )


def test_fetch_relevant_yahoo_news(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    relevant_article = create_raw_article(
        title=(
            "Tüpraş yeni yatırım açıkladı"
        ),
        summary=(
            "Şirket üretim kapasitesini artıracak."
        ),
        article_id="relevant",
    )

    irrelevant_article = create_raw_article(
        title=(
            "Beşiktaş maç hazırlıklarını tamamladı"
        ),
        summary=(
            "Tüpraş Stadyumu'nda derbi oynanacak."
        ),
        article_id="irrelevant",
    )

    captured: dict[str, object] = {}

    def fake_fetch_yahoo_news(
        symbol: str,
        count: int,
    ) -> list[dict[str, object]]:
        captured[
            "fetch_symbol"
        ] = symbol

        captured[
            "fetch_count"
        ] = count

        return [
            relevant_article,
            irrelevant_article,
        ]

    def fake_get_company_aliases(
        symbol: str,
    ) -> tuple[str, ...]:
        captured[
            "alias_symbol"
        ] = symbol

        return (
            "TUPRS",
            "Tüpraş",
            "Türkiye Petrol Rafinerileri",
        )

    monkeypatch.setattr(
        module,
        "fetch_yahoo_news",
        fake_fetch_yahoo_news,
    )

    monkeypatch.setattr(
        module,
        "get_company_aliases",
        fake_get_company_aliases,
    )

    result = fetch_relevant_yahoo_news(
        symbol="TUPRS",
        count=20,
    )

    assert (
        captured["fetch_symbol"]
        == "TUPRS"
    )

    assert (
        captured["fetch_count"]
        == 20
    )

    assert (
        captured["alias_symbol"]
        == "TUPRS"
    )

    assert result == [
        relevant_article,
    ]


def test_fetch_relevant_yahoo_news_returns_empty_without_registry_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        module,
        "fetch_yahoo_news",
        lambda symbol, count: [],
    )

    def unexpected_registry_call(
        symbol: str,
    ) -> tuple[str, ...]:
        raise AssertionError(
            "Boş haber listesinde şirket "
            "kaydı sorgulanmamalı."
        )

    monkeypatch.setattr(
        module,
        "get_company_aliases",
        unexpected_registry_call,
    )

    result = fetch_relevant_yahoo_news(
        symbol="TUPRS",
        count=10,
    )

    assert result == []