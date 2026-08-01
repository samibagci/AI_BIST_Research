from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

import src.news_analysis as module
from src.news_analysis import (
    analyze_news_articles,
    build_markdown_report,
    calculate_article_sentiment,
    calculate_data_confidence,
    calculate_recency_weight,
    extract_news_article,
    fetch_company_news,
    get_nested_value,
    news_score_label,
    parse_datetime,
    run_news_analysis,
    safe_number,
    safe_text,
    save_json_result,
    save_markdown_report,
)


REFERENCE_TIME = datetime(
    2026,
    8,
    1,
    12,
    0,
    tzinfo=timezone.utc,
)


def create_raw_article(
    article_id: str = "haber-1",
    title: str = "Şirket rekor büyüme açıkladı",
    summary: str = "Kâr arttı ve güçlü sonuç elde edildi.",
    published_at: str = "2026-07-31T10:00:00Z",
    provider: str = "Örnek Haber",
    url: str = "https://example.com/haber-1",
) -> dict[str, object]:
    return {
        "content": {
            "id": article_id,
            "title": title,
            "summary": summary,
            "pubDate": published_at,
            "provider": {
                "displayName": provider,
            },
            "canonicalUrl": {
                "url": url,
            },
        },
        "relatedTickers": [
            "THYAO.IS",
        ],
    }


def create_analysis_result() -> dict[str, object]:
    return analyze_news_articles(
        symbol="THYAO",
        raw_articles=[
            create_raw_article(),
        ],
        lookback_days=30,
        reference_time=REFERENCE_TIME,
    )


def test_safe_number_accepts_real_numbers() -> None:
    assert safe_number(10) == 10.0
    assert safe_number(4.25) == 4.25


@pytest.mark.parametrize(
    "value",
    [
        True,
        False,
        "10",
        None,
        math.inf,
        -math.inf,
        math.nan,
    ],
)
def test_safe_number_rejects_invalid_values(
    value: object,
) -> None:
    assert safe_number(value) is None


def test_safe_text_cleans_whitespace() -> None:
    assert safe_text("  Örnek   Haber  ") == "Örnek Haber"
    assert safe_text("") is None
    assert safe_text("   ") is None
    assert safe_text(123) is None


def test_get_nested_value() -> None:
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


def test_parse_datetime_accepts_iso_string() -> None:
    result = parse_datetime(
        "2026-07-31T10:30:00Z"
    )

    assert result == datetime(
        2026,
        7,
        31,
        10,
        30,
        tzinfo=timezone.utc,
    )


def test_parse_datetime_accepts_timestamp() -> None:
    expected = datetime(
        2026,
        7,
        31,
        10,
        30,
        tzinfo=timezone.utc,
    )

    result = parse_datetime(
        expected.timestamp()
    )

    assert result == expected


def test_parse_datetime_accepts_millisecond_timestamp() -> None:
    expected = datetime(
        2026,
        7,
        31,
        10,
        30,
        tzinfo=timezone.utc,
    )

    result = parse_datetime(
        expected.timestamp() * 1000
    )

    assert result == expected


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
def test_parse_datetime_rejects_invalid_values(
    value: object,
) -> None:
    assert parse_datetime(value) is None


def test_extract_news_article_reads_nested_content() -> None:
    article = extract_news_article(
        create_raw_article()
    )

    assert article is not None
    assert article["id"] == "haber-1"
    assert (
        article["title"]
        == "Şirket rekor büyüme açıkladı"
    )
    assert article["provider"] == "Örnek Haber"
    assert (
        article["published_at"]
        == "2026-07-31T10:00:00+00:00"
    )
    assert (
        article["url"]
        == "https://example.com/haber-1"
    )
    assert article["related_tickers"] == [
        "THYAO.IS",
    ]


def test_extract_news_article_supports_flat_content() -> None:
    article = extract_news_article(
        {
            "uuid": "flat-1",
            "title": "Yeni sözleşme imzalandı",
            "summary": "Şirket yeni bir ihale kazandı.",
            "publisher": "Finans Haber",
            "providerPublishTime": (
                REFERENCE_TIME.timestamp()
            ),
            "link": "https://example.com/flat",
        }
    )

    assert article is not None
    assert article["id"] == "flat-1"
    assert article["provider"] == "Finans Haber"
    assert article["url"] == "https://example.com/flat"


def test_extract_news_article_rejects_missing_title() -> None:
    assert (
        extract_news_article(
            {
                "content": {
                    "summary": "Başlıksız haber",
                }
            }
        )
        is None
    )

    assert extract_news_article("haber") is None


def test_fetch_company_news_uses_yahoo_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_fetch_yahoo_news(
        symbol: str,
        count: int,
    ) -> list[dict[str, object]]:
        captured["symbol"] = symbol
        captured["count"] = count

        return [
            create_raw_article(),
        ]

    monkeypatch.setattr(
        module,
        "fetch_yahoo_news",
        fake_fetch_yahoo_news,
    )

    result = fetch_company_news(
        symbol="THYAO",
        count=15,
    )

    assert captured["symbol"] == "THYAO"
    assert captured["count"] == 15
    assert len(result) == 1


def test_fetch_company_news_returns_empty_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        module,
        "fetch_yahoo_news",
        lambda symbol, count: [],
    )

    assert fetch_company_news("THYAO") == []


def test_fetch_company_news_rejects_invalid_count() -> None:
    with pytest.raises(
        ValueError,
        match="Haber sayısı en az 1",
    ):
        fetch_company_news(
            symbol="THYAO",
            count=0,
        )


def test_calculate_positive_article_sentiment() -> None:
    result = calculate_article_sentiment(
        title="Şirket rekor büyüme açıkladı",
        summary="Kâr arttı ve beklentiyi aştı.",
    )

    assert result["sentiment_value"] == 1.0
    assert result["sentiment_score"] == 100.0
    assert result["sentiment_label"] == "OLUMLU"
    assert "rekor" in result["positive_keywords"]


def test_calculate_negative_article_sentiment() -> None:
    result = calculate_article_sentiment(
        title="Şirket zarar açıkladı",
        summary="Üretim durdu ve soruşturma başlatıldı.",
    )

    assert result["sentiment_value"] == -1.0
    assert result["sentiment_score"] == 0.0
    assert result["sentiment_label"] == "OLUMSUZ"
    assert "zarar" in result["negative_keywords"]
    assert "üretim durdu" in result["risk_keywords"]


def test_calculate_neutral_article_sentiment() -> None:
    result = calculate_article_sentiment(
        title="Şirket genel kurul tarihini açıkladı",
        summary=None,
    )

    assert result["sentiment_value"] == 0.0
    assert result["sentiment_score"] == 50.0
    assert result["sentiment_label"] == "NÖTR"


@pytest.mark.parametrize(
    ("published_at", "expected"),
    [
        (
            datetime(
                2026,
                7,
                31,
                tzinfo=timezone.utc,
            ),
            1.0,
        ),
        (
            datetime(
                2026,
                7,
                26,
                tzinfo=timezone.utc,
            ),
            0.85,
        ),
        (
            datetime(
                2026,
                7,
                20,
                tzinfo=timezone.utc,
            ),
            0.70,
        ),
        (
            datetime(
                2026,
                7,
                10,
                tzinfo=timezone.utc,
            ),
            0.50,
        ),
        (
            datetime(
                2026,
                6,
                1,
                tzinfo=timezone.utc,
            ),
            0.30,
        ),
        (
            None,
            0.40,
        ),
    ],
)
def test_calculate_recency_weight(
    published_at: datetime | None,
    expected: float,
) -> None:
    assert (
        calculate_recency_weight(
            published_at=published_at,
            reference_time=REFERENCE_TIME,
        )
        == expected
    )


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (70.0, "OLUMLU"),
        (60.0, "HAFİF OLUMLU"),
        (50.0, "NÖTR"),
        (40.0, "HAFİF OLUMSUZ"),
        (20.0, "OLUMSUZ"),
    ],
)
def test_news_score_label(
    score: float,
    expected: str,
) -> None:
    assert news_score_label(score) == expected


def test_calculate_data_confidence_full() -> None:
    articles = [
        {
            "published_at": (
                "2026-07-31T10:00:00+00:00"
            ),
            "provider": "Kaynak",
        }
        for _ in range(10)
    ]

    assert calculate_data_confidence(articles) == 100.0


def test_calculate_data_confidence_empty() -> None:
    assert calculate_data_confidence([]) == 0.0


def test_analyze_news_articles_filters_old_news() -> None:
    recent_positive = create_raw_article(
        article_id="positive",
        title="Şirket rekor büyüme açıkladı",
        summary="Kâr arttı.",
        published_at="2026-07-31T10:00:00Z",
    )

    recent_negative = create_raw_article(
        article_id="negative",
        title="Şirket zarar açıkladı",
        summary="Üretim durdu.",
        published_at="2026-07-22T10:00:00Z",
    )

    old_article = create_raw_article(
        article_id="old",
        title="Eski haber",
        summary="Temettü açıklandı.",
        published_at="2026-06-01T10:00:00Z",
    )

    result = analyze_news_articles(
        symbol="THYAO",
        raw_articles=[
            recent_positive,
            recent_negative,
            old_article,
        ],
        lookback_days=30,
        reference_time=REFERENCE_TIME,
    )

    assert result["symbol"] == "THYAO"
    assert result["yahoo_symbol"] == "THYAO.IS"
    assert result["fetched_count"] == 3
    assert result["analyzed_count"] == 2
    assert result["positive_count"] == 1
    assert result["negative_count"] == 1
    assert result["neutral_count"] == 0
    assert result["news_sentiment_score"] == 58.82
    assert result["label"] == "HAFİF OLUMLU"
    assert "üretim durdu" in result["risk_keywords"]


def test_analyze_news_articles_handles_empty_news() -> None:
    result = analyze_news_articles(
        symbol="THYAO",
        raw_articles=[],
        reference_time=REFERENCE_TIME,
    )

    assert result["analyzed_count"] == 0
    assert result["news_sentiment_score"] == 50.0
    assert result["label"] == "NÖTR"
    assert result["data_confidence"] == 0.0


def test_analyze_news_articles_rejects_invalid_lookback() -> None:
    with pytest.raises(
        ValueError,
        match="en az 1 gün",
    ):
        analyze_news_articles(
            symbol="THYAO",
            raw_articles=[],
            lookback_days=0,
        )


def test_run_news_analysis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        module,
        "fetch_company_news",
        lambda symbol, count: [
            create_raw_article(),
        ],
    )

    result = run_news_analysis(
        symbol="THYAO",
        count=10,
        lookback_days=30,
    )

    assert result["symbol"] == "THYAO"
    assert result["fetched_count"] == 1
    assert result["analyzed_count"] == 1


def test_build_markdown_report_contains_news() -> None:
    result = create_analysis_result()

    markdown = build_markdown_report(result)

    assert "# THYAO Haber Analizi Raporu" in markdown
    assert "Haber duygu puanı: **100.00 / 100**" in markdown
    assert "Şirket rekor büyüme açıkladı" in markdown
    assert "Örnek Haber" in markdown
    assert "https://example.com/haber-1" in markdown
    assert "yatırım tavsiyesi değildir" in markdown


def test_save_analysis_files(
    tmp_path: Path,
) -> None:
    result = create_analysis_result()

    json_path = tmp_path / "reports" / "news.json"
    markdown_path = tmp_path / "reports" / "news.md"

    save_json_result(
        analysis_result=result,
        output_path=json_path,
    )

    save_markdown_report(
        markdown_report="# Haber Analizi\n",
        output_path=markdown_path,
    )

    assert json_path.exists()
    assert markdown_path.exists()

    saved_result = json.loads(
        json_path.read_text(encoding="utf-8")
    )

    assert saved_result["symbol"] == "THYAO"
    assert saved_result["analyzed_count"] == 1

    assert (
        markdown_path.read_text(encoding="utf-8")
        == "# Haber Analizi\n"
    )


def test_main_completes_news_analysis(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    json_path = tmp_path / "news.json"
    markdown_path = tmp_path / "news.md"
    analysis_result = create_analysis_result()

    monkeypatch.setattr(
        module,
        "run_news_analysis",
        lambda **kwargs: analysis_result,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "news_analysis.py",
            "THYAO",
            "--count",
            "20",
            "--lookback-days",
            "30",
            "--json-output",
            str(json_path),
            "--report-output",
            str(markdown_path),
        ],
    )

    exit_code = module.main()
    terminal_output = capsys.readouterr().out

    assert exit_code == 0
    assert json_path.exists()
    assert markdown_path.exists()

    assert "BAŞARILI" in terminal_output
    assert "Hisse: THYAO" in terminal_output
    assert "Analiz edilen haber: 1" in terminal_output
    assert "Haber duygu puanı: 100.0" in terminal_output


def test_main_returns_error_for_invalid_symbol(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "news_analysis.py",
            "THY AO",
        ],
    )

    exit_code = module.main()
    terminal_output = capsys.readouterr().out

    assert exit_code == 1
    assert "HATA" in terminal_output
    assert "Geçersiz hisse kodu" in terminal_output