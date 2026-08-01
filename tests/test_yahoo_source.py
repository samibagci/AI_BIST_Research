from __future__ import annotations

import pytest

import src.news_sources.yahoo_source as module
from src.news_sources.yahoo_source import (
    fetch_yahoo_news,
)


def create_raw_article() -> dict[str, object]:
    return {
        "content": {
            "id": "haber-1",
            "title": "Şirket büyüme açıkladı",
        }
    }


def test_fetch_yahoo_news_uses_bist_symbol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeTicker:
        def __init__(self, symbol: str) -> None:
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

    assert captured["symbol"] == "THYAO.IS"
    assert captured["count"] == 20
    assert captured["tab"] == "news"
    assert len(result) == 1


def test_fetch_yahoo_news_returns_empty_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeTicker:
        def __init__(self, symbol: str) -> None:
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

    assert fetch_yahoo_news("THYAO") == []


def test_fetch_yahoo_news_filters_invalid_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeTicker:
        def __init__(self, symbol: str) -> None:
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

    result = fetch_yahoo_news("THYAO")

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
        def __init__(self, symbol: str) -> None:
            self.symbol = symbol

        def get_news(
            self,
            count: int,
            tab: str,
        ) -> dict[str, object]:
            return {
                "haber": "geçersiz format",
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
        fetch_yahoo_news("THYAO")