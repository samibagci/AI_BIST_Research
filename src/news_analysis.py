from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from numbers import Real
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.download_bist_prices import normalize_bist_symbol
from src.news_sources.yahoo_source import (
    SOURCE_NAME,
    fetch_yahoo_news,
)


DEFAULT_REPORT_DIRECTORY = Path("reports")
DEFAULT_NEWS_COUNT = 30
DEFAULT_LOOKBACK_DAYS = 30


POSITIVE_KEYWORDS = {
    "rekor",
    "büyüme",
    "artış",
    "yükseliş",
    "kâr arttı",
    "kar arttı",
    "kâr artışı",
    "kar artışı",
    "beklentiyi aştı",
    "güçlü sonuç",
    "temettü",
    "ihale kazandı",
    "sözleşme imzaladı",
    "yeni sözleşme",
    "kapasite artışı",
    "yatırım kararı",
    "kredi notu yükseldi",
    "hedef fiyat yükseldi",
    "geri alım",
    "ihracat artışı",
    "satış artışı",
    "gelir artışı",
    "record",
    "growth",
    "increase",
    "rally",
    "profit rises",
    "earnings beat",
    "beats estimates",
    "strong results",
    "dividend",
    "contract awarded",
    "new contract",
    "capacity expansion",
    "share buyback",
    "upgrade",
}

NEGATIVE_KEYWORDS = {
    "zarar",
    "düşüş",
    "gerileme",
    "beklentinin altında",
    "kâr düştü",
    "kar düştü",
    "satış düştü",
    "gelir düştü",
    "ceza",
    "soruşturma",
    "inceleme başlatıldı",
    "dava",
    "iflas",
    "temerrüt",
    "borç krizi",
    "üretim durdu",
    "faaliyet durdu",
    "yangın",
    "kaza",
    "işten çıkarma",
    "kredi notu düştü",
    "hedef fiyat düştü",
    "downgrade",
    "loss",
    "decline",
    "falls",
    "earnings miss",
    "misses estimates",
    "weak results",
    "investigation",
    "lawsuit",
    "default",
    "bankruptcy",
    "fraud",
    "sanction",
    "production halted",
    "layoff",
}

RISK_KEYWORDS = {
    "ceza",
    "soruşturma",
    "inceleme başlatıldı",
    "dava",
    "iflas",
    "temerrüt",
    "borç krizi",
    "üretim durdu",
    "faaliyet durdu",
    "yangın",
    "kaza",
    "dolandırıcılık",
    "fraud",
    "investigation",
    "lawsuit",
    "default",
    "bankruptcy",
    "sanction",
    "production halted",
}


def safe_number(
    value: object,
) -> float | None:
    if isinstance(value, bool):
        return None

    if not isinstance(value, Real):
        return None

    numeric_value = float(value)

    if not math.isfinite(numeric_value):
        return None

    return numeric_value


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
        if not isinstance(current_value, dict):
            return None

        current_value = current_value.get(key)

    return current_value


def parse_datetime(
    value: object,
) -> datetime | None:
    if isinstance(value, datetime):
        parsed_datetime = value

    elif isinstance(value, Real) and not isinstance(
        value,
        bool,
    ):
        timestamp = float(value)

        if timestamp > 10_000_000_000:
            timestamp /= 1000

        try:
            parsed_datetime = datetime.fromtimestamp(
                timestamp,
                tz=timezone.utc,
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
            parsed_datetime = datetime.fromisoformat(
                cleaned_value
            )
        except ValueError:
            return None

    else:
        return None

    if parsed_datetime.tzinfo is None:
        parsed_datetime = parsed_datetime.replace(
            tzinfo=timezone.utc
        )
    else:
        parsed_datetime = parsed_datetime.astimezone(
            timezone.utc
        )

    return parsed_datetime


def extract_url(
    raw_article: dict[str, object],
    content: dict[str, object],
) -> str | None:
    possible_values = [
        get_nested_value(
            content,
            "canonicalUrl",
            "url",
        ),
        get_nested_value(
            content,
            "clickThroughUrl",
            "url",
        ),
        content.get("link"),
        content.get("url"),
        raw_article.get("link"),
        raw_article.get("url"),
    ]

    for value in possible_values:
        cleaned_value = safe_text(value)

        if cleaned_value is not None:
            return cleaned_value

    return None


def extract_provider(
    raw_article: dict[str, object],
    content: dict[str, object],
) -> str | None:
    possible_values = [
        get_nested_value(
            content,
            "provider",
            "displayName",
        ),
        content.get("publisher"),
        raw_article.get("publisher"),
        raw_article.get("provider"),
    ]

    for value in possible_values:
        if isinstance(value, dict):
            value = value.get("displayName")

        cleaned_value = safe_text(value)

        if cleaned_value is not None:
            return cleaned_value

    return None


def extract_news_article(
    raw_article: object,
) -> dict[str, object] | None:
    if not isinstance(raw_article, dict):
        return None

    raw_content = raw_article.get("content")

    if isinstance(raw_content, dict):
        content = raw_content
    else:
        content = raw_article

    title = (
        safe_text(content.get("title"))
        or safe_text(raw_article.get("title"))
    )

    if title is None:
        return None

    summary = (
        safe_text(content.get("summary"))
        or safe_text(content.get("description"))
        or safe_text(raw_article.get("summary"))
        or safe_text(raw_article.get("description"))
    )

    published_value = (
        content.get("pubDate")
        or content.get("publishedAt")
        or raw_article.get("providerPublishTime")
        or raw_article.get("pubDate")
        or raw_article.get("publishedAt")
    )

    published_datetime = parse_datetime(
        published_value
    )

    article_id = (
        safe_text(content.get("id"))
        or safe_text(raw_article.get("uuid"))
        or safe_text(raw_article.get("id"))
    )

    related_tickers_value = (
        raw_article.get("relatedTickers")
        or content.get("relatedTickers")
    )

    related_tickers: list[str] = []

    if isinstance(related_tickers_value, list):
        for ticker in related_tickers_value:
            cleaned_ticker = safe_text(ticker)

            if cleaned_ticker:
                related_tickers.append(
                    cleaned_ticker.upper()
                )

    return {
        "id": article_id,
        "title": title,
        "summary": summary,
        "provider": extract_provider(
            raw_article,
            content,
        ),
        "published_at": (
            published_datetime.isoformat()
            if published_datetime is not None
            else None
        ),
        "url": extract_url(
            raw_article,
            content,
        ),
        "related_tickers": related_tickers,
    }


def fetch_company_news(
    symbol: str,
    count: int = DEFAULT_NEWS_COUNT,
) -> list[dict[str, object]]:
    return fetch_yahoo_news(
        symbol=symbol,
        count=count,
    )


def find_keyword_hits(
    text: str,
    keywords: set[str],
) -> list[str]:
    normalized_text = text.casefold()

    return sorted(
        keyword
        for keyword in keywords
        if keyword.casefold() in normalized_text
    )


def calculate_article_sentiment(
    title: str,
    summary: str | None,
) -> dict[str, object]:
    combined_text = " ".join(
        value
        for value in [
            title,
            summary or "",
        ]
        if value
    )

    positive_hits = find_keyword_hits(
        combined_text,
        POSITIVE_KEYWORDS,
    )

    negative_hits = find_keyword_hits(
        combined_text,
        NEGATIVE_KEYWORDS,
    )

    risk_hits = find_keyword_hits(
        combined_text,
        RISK_KEYWORDS,
    )

    positive_count = len(positive_hits)
    negative_count = len(negative_hits)
    total_hit_count = (
        positive_count
        + negative_count
    )

    if total_hit_count == 0:
        sentiment_value = 0.0
    else:
        sentiment_value = (
            positive_count
            - negative_count
        ) / total_hit_count

    sentiment_value = max(
        -1.0,
        min(1.0, sentiment_value),
    )

    sentiment_score = round(
        50
        + sentiment_value
        * 50,
        2,
    )

    if sentiment_value > 0:
        sentiment_label = "OLUMLU"
    elif sentiment_value < 0:
        sentiment_label = "OLUMSUZ"
    else:
        sentiment_label = "NÖTR"

    return {
        "sentiment_value": round(
            sentiment_value,
            4,
        ),
        "sentiment_score": sentiment_score,
        "sentiment_label": sentiment_label,
        "positive_keywords": positive_hits,
        "negative_keywords": negative_hits,
        "risk_keywords": risk_hits,
    }


def calculate_recency_weight(
    published_at: datetime | None,
    reference_time: datetime,
) -> float:
    if published_at is None:
        return 0.40

    age = reference_time - published_at
    age_days = max(
        0.0,
        age.total_seconds()
        / 86_400,
    )

    if age_days <= 3:
        return 1.0

    if age_days <= 7:
        return 0.85

    if age_days <= 14:
        return 0.70

    if age_days <= 30:
        return 0.50

    return 0.30


def news_score_label(
    score: float,
) -> str:
    if score >= 65:
        return "OLUMLU"

    if score >= 55:
        return "HAFİF OLUMLU"

    if score >= 45:
        return "NÖTR"

    if score >= 35:
        return "HAFİF OLUMSUZ"

    return "OLUMSUZ"


def calculate_data_confidence(
    articles: list[dict[str, object]],
) -> float:
    if not articles:
        return 0.0

    article_count_score = min(
        len(articles) / 10,
        1.0,
    ) * 70

    dated_count = sum(
        1
        for article in articles
        if article.get("published_at") is not None
    )

    provider_count = sum(
        1
        for article in articles
        if article.get("provider") is not None
    )

    dated_ratio = (
        dated_count
        / len(articles)
    )

    provider_ratio = (
        provider_count
        / len(articles)
    )

    return round(
        article_count_score
        + dated_ratio * 20
        + provider_ratio * 10,
        2,
    )


def analyze_news_articles(
    symbol: str,
    raw_articles: list[dict[str, object]],
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    reference_time: datetime | None = None,
) -> dict[str, object]:
    if lookback_days < 1:
        raise ValueError(
            "Haber inceleme dönemi en az 1 gün olmalıdır."
        )

    yahoo_symbol = normalize_bist_symbol(symbol)
    base_symbol = yahoo_symbol.removesuffix(".IS")

    if reference_time is None:
        reference_time = datetime.now(
            timezone.utc
        )
    elif reference_time.tzinfo is None:
        reference_time = reference_time.replace(
            tzinfo=timezone.utc
        )
    else:
        reference_time = reference_time.astimezone(
            timezone.utc
        )

    cutoff_time = reference_time - timedelta(
        days=lookback_days
    )

    analyzed_articles: list[
        dict[str, object]
    ] = []

    for raw_article in raw_articles:
        article = extract_news_article(
            raw_article
        )

        if article is None:
            continue

        published_datetime = parse_datetime(
            article.get("published_at")
        )

        if (
            published_datetime is not None
            and published_datetime < cutoff_time
        ):
            continue

        title = str(article["title"])
        summary = article.get("summary")

        sentiment_result = (
            calculate_article_sentiment(
                title=title,
                summary=(
                    summary
                    if isinstance(summary, str)
                    else None
                ),
            )
        )

        recency_weight = (
            calculate_recency_weight(
                published_at=published_datetime,
                reference_time=reference_time,
            )
        )

        analyzed_articles.append(
            {
                **article,
                **sentiment_result,
                "recency_weight": recency_weight,
            }
        )

    analyzed_articles.sort(
        key=lambda article: (
            parse_datetime(
                article.get("published_at")
            )
            or datetime.min.replace(
                tzinfo=timezone.utc
            )
        ),
        reverse=True,
    )

    positive_count = sum(
        1
        for article in analyzed_articles
        if article["sentiment_label"] == "OLUMLU"
    )

    negative_count = sum(
        1
        for article in analyzed_articles
        if article["sentiment_label"] == "OLUMSUZ"
    )

    neutral_count = (
        len(analyzed_articles)
        - positive_count
        - negative_count
    )

    total_weight = sum(
        float(article["recency_weight"])
        for article in analyzed_articles
    )

    if total_weight > 0:
        weighted_sentiment = sum(
            float(article["sentiment_value"])
            * float(article["recency_weight"])
            for article in analyzed_articles
        ) / total_weight
    else:
        weighted_sentiment = 0.0

    news_sentiment_score = round(
        max(
            0.0,
            min(
                100.0,
                50
                + weighted_sentiment
                * 50,
            ),
        ),
        2,
    )

    risk_keywords = sorted(
        {
            keyword
            for article in analyzed_articles
            for keyword in article["risk_keywords"]
            if isinstance(keyword, str)
        }
    )

    data_confidence = (
        calculate_data_confidence(
            analyzed_articles
        )
    )

    notes = [
        (
            "Haber duygu puanı başlık ve özetlerdeki "
            "Türkçe ve İngilizce anahtar kelimelerle "
            "hesaplanmıştır."
        ),
        (
            "Yeni haberler, eski haberlere göre daha "
            "yüksek ağırlıkla değerlendirilmiştir."
        ),
        (
            "Bu ilk sürüm Yahoo Finance haber akışını "
            "kullanır; KAP bildirimleri ayrı veri "
            "kaynağı olarak eklenecektir."
        ),
        (
            "Haber puanı tek başına yatırım kararı "
            "vermek için kullanılmamalıdır."
        ),
    ]

    if not analyzed_articles:
        notes.insert(
            0,
            "Belirlenen dönem içinde kullanılabilir haber bulunamadı.",
        )

    if data_confidence < 50:
        notes.insert(
            0,
            "Haber sayısı veya haber metadatası sınırlı olduğu için veri güveni düşüktür.",
        )

    return {
        "generated_at": reference_time.isoformat(),
        "symbol": base_symbol,
        "yahoo_symbol": yahoo_symbol,
        "source": SOURCE_NAME,
        "lookback_days": lookback_days,
        "fetched_count": len(raw_articles),
        "analyzed_count": len(
            analyzed_articles
        ),
        "positive_count": positive_count,
        "neutral_count": neutral_count,
        "negative_count": negative_count,
        "news_sentiment_score": (
            news_sentiment_score
        ),
        "label": news_score_label(
            news_sentiment_score
        ),
        "data_confidence": data_confidence,
        "risk_keywords": risk_keywords,
        "articles": analyzed_articles,
        "notes": notes,
    }


def run_news_analysis(
    symbol: str,
    count: int = DEFAULT_NEWS_COUNT,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> dict[str, object]:
    raw_articles = fetch_company_news(
        symbol=symbol,
        count=count,
    )

    return analyze_news_articles(
        symbol=symbol,
        raw_articles=raw_articles,
        lookback_days=lookback_days,
    )


def escape_markdown_text(
    value: object,
) -> str:
    cleaned_value = safe_text(value)

    if cleaned_value is None:
        return "Veri yok"

    return (
        cleaned_value
        .replace("|", "\\|")
        .replace("\n", " ")
    )


def build_markdown_report(
    analysis_result: dict[str, object],
) -> str:
    symbol = analysis_result["symbol"]
    generated_at = analysis_result[
        "generated_at"
    ]
    lookback_days = analysis_result[
        "lookback_days"
    ]
    analyzed_count = analysis_result[
        "analyzed_count"
    ]
    positive_count = analysis_result[
        "positive_count"
    ]
    neutral_count = analysis_result[
        "neutral_count"
    ]
    negative_count = analysis_result[
        "negative_count"
    ]
    sentiment_score = analysis_result[
        "news_sentiment_score"
    ]
    label = analysis_result["label"]
    data_confidence = analysis_result[
        "data_confidence"
    ]
    risk_keywords = analysis_result[
        "risk_keywords"
    ]
    articles = analysis_result["articles"]
    notes = analysis_result["notes"]

    lines = [
        f"# {symbol} Haber Analizi Raporu",
        "",
        f"- Oluşturulma zamanı: {generated_at}",
        f"- İncelenen dönem: Son {lookback_days} gün",
        f"- Analiz edilen haber: {analyzed_count}",
        "",
        "## Genel Sonuç",
        "",
        (
            "- Haber duygu puanı: "
            f"**{float(sentiment_score):.2f} / 100**"
        ),
        f"- Değerlendirme: **{label}**",
        (
            "- Veri güveni: "
            f"**{float(data_confidence):.2f}%**"
        ),
        f"- Olumlu haber: {positive_count}",
        f"- Nötr haber: {neutral_count}",
        f"- Olumsuz haber: {negative_count}",
        "",
        "## Haberler",
        "",
    ]

    if isinstance(articles, list) and articles:
        lines.extend(
            [
                (
                    "| Tarih | Başlık | Kaynak "
                    "| Duygu | Puan |"
                ),
                "|---|---|---|---|---:|",
            ]
        )

        for article in articles:
            if not isinstance(article, dict):
                continue

            published_at = (
                safe_text(
                    article.get("published_at")
                )
                or "Tarih yok"
            )

            if published_at != "Tarih yok":
                published_at = published_at[:10]

            title = escape_markdown_text(
                article.get("title")
            )

            url = safe_text(
                article.get("url")
            )

            if url:
                title = f"[{title}]({url})"

            provider = escape_markdown_text(
                article.get("provider")
            )

            sentiment_label = (
                escape_markdown_text(
                    article.get(
                        "sentiment_label"
                    )
                )
            )

            sentiment_value = safe_number(
                article.get(
                    "sentiment_score"
                )
            )

            score_text = (
                f"{sentiment_value:.2f}"
                if sentiment_value is not None
                else "Veri yok"
            )

            lines.append(
                f"| {published_at} "
                f"| {title} "
                f"| {provider} "
                f"| {sentiment_label} "
                f"| {score_text} |"
            )
    else:
        lines.append(
            "Belirlenen dönem içinde kullanılabilir haber bulunamadı."
        )

    lines.extend(
        [
            "",
            "## Risk Anahtar Kelimeleri",
            "",
        ]
    )

    if (
        isinstance(risk_keywords, list)
        and risk_keywords
    ):
        for keyword in risk_keywords:
            lines.append(f"- {keyword}")
    else:
        lines.append(
            "Belirgin risk anahtar kelimesi bulunmadı."
        )

    lines.extend(
        [
            "",
            "## Notlar",
            "",
        ]
    )

    if isinstance(notes, list):
        for note in notes:
            lines.append(f"- {note}")

    lines.extend(
        [
            "",
            (
                "> Bu rapor araştırma amacıyla "
                "oluşturulmuştur ve yatırım tavsiyesi değildir."
            ),
            "",
        ]
    )

    return "\n".join(lines)


def save_json_result(
    analysis_result: dict[str, object],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            analysis_result,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def save_markdown_report(
    markdown_report: str,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        markdown_report,
        encoding="utf-8",
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Yahoo Finance haberleriyle BIST "
            "şirketi haber analizi yapar."
        )
    )

    parser.add_argument(
        "symbol",
        help="BIST hisse kodu. Örnek: THYAO",
    )

    parser.add_argument(
        "--count",
        type=int,
        default=DEFAULT_NEWS_COUNT,
        help="İndirilecek haber sayısı. Varsayılan: 30",
    )

    parser.add_argument(
        "--lookback-days",
        type=int,
        default=DEFAULT_LOOKBACK_DAYS,
        help="İncelenecek gün sayısı. Varsayılan: 30",
    )

    parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
        help="JSON analiz sonucunun yolu.",
    )

    parser.add_argument(
        "--report-output",
        type=Path,
        default=None,
        help="Markdown analiz raporunun yolu.",
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        yahoo_symbol = normalize_bist_symbol(
            arguments.symbol
        )
        base_symbol = yahoo_symbol.removesuffix(".IS")

        json_output_path = arguments.json_output

        if json_output_path is None:
            json_output_path = (
                DEFAULT_REPORT_DIRECTORY
                / f"{base_symbol}_news_analysis.json"
            )

        markdown_output_path = (
            arguments.report_output
        )

        if markdown_output_path is None:
            markdown_output_path = (
                DEFAULT_REPORT_DIRECTORY
                / f"{base_symbol}_news_analysis.md"
            )

        analysis_result = run_news_analysis(
            symbol=base_symbol,
            count=arguments.count,
            lookback_days=arguments.lookback_days,
        )

        save_json_result(
            analysis_result=analysis_result,
            output_path=json_output_path,
        )

        markdown_report = build_markdown_report(
            analysis_result
        )

        save_markdown_report(
            markdown_report=markdown_report,
            output_path=markdown_output_path,
        )

        print(
            "BAŞARILI: Haber analizi tamamlandı."
        )
        print(f"Hisse: {base_symbol}")
        print(
            "Analiz edilen haber: "
            f"{analysis_result['analyzed_count']}"
        )
        print(
            "Haber duygu puanı: "
            f"{analysis_result['news_sentiment_score']}"
        )
        print(
            "Veri güveni: "
            f"{analysis_result['data_confidence']}%"
        )
        print(
            f"JSON sonucu: "
            f"{json_output_path.resolve()}"
        )
        print(
            f"Markdown raporu: "
            f"{markdown_output_path.resolve()}"
        )

        return 0

    except Exception as error:
        print(f"HATA: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())