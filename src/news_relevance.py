from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from src.company_registry import (
    normalize_company_text,
)


STRONG_INVESTMENT_CONTEXT_TERMS = (
    # Finansal sonuçlar
    "bilanço",
    "bilanco",
    "finansal sonuç",
    "finansal sonuc",
    "faaliyet raporu",
    "ciro",
    "hasılat",
    "hasilat",
    "gelir",
    "kâr",
    "kar",
    "zarar",
    "favök",
    "favok",
    "ebitda",
    "temettü",
    "temettu",

    # Sermaye / piyasa
    "sermaye artırımı",
    "sermaye artirimi",
    "bedelsiz",
    "bedelli",
    "geri alım",
    "geri alim",
    "halka arz",
    "hedef fiyat",
    "model portföy",
    "model portfoy",
    "al tavsiyesi",
    "sat tavsiyesi",
    "kredi notu",

    # Operasyonel gelişmeler
    "yatırım",
    "yatirim",
    "sözleşme",
    "sozlesme",
    "anlaşma",
    "anlasma",
    "ihale",
    "sipariş",
    "siparis",
    "ihracat",
    "satın alma",
    "satin alma",
    "birleşme",
    "birlesme",
    "devralma",

    # Resmî bildirim
    "kap",
    "özel durum açıklaması",
    "ozel durum aciklamasi",
)


MODERATE_INVESTMENT_CONTEXT_TERMS = (
    "üretim",
    "uretim",
    "kapasite",
    "tesis",
    "fabrika",
    "satış",
    "satis",
    "tedarik",
    "teslimat",
    "ithalat",
    "müşteri",
    "musteri",
    "pazar",
    "operasyon",
    "finansman",
    "borç",
    "borc",
    "kredi",
    "marj",
    "nakit",
    "iştirak",
    "istirak",
    "ortaklık",
    "ortaklik",
    "atama",
    "istifa",
    "lisans",
    "ruhsat",
    "teşvik",
    "tesvik",
    "dava",
    "ceza",
    "iş birliği",
    "is birligi",
    "sponsorluk",
    "teknik analiz",
    "temel analiz",
    "açığa satış",
    "aciga satis",
    "takas oranı",
    "takas orani",
)


WEAK_INVESTMENT_CONTEXT_TERMS = (
    "ürün",
    "urun",
    "sistem",
    "teknoloji",
    "platform",
    "araç",
    "arac",
    "entegrasyon",
    "geliştirdi",
    "gelistirdi",
    "geliştiriyor",
    "gelistiriyor",
    "tanıttı",
    "tanitti",
    "proje",
)


LOW_VALUE_CORPORATE_CONTEXT_TERMS = (
    "çocuk şenliği",
    "cocuk senligi",
    "şenlik",
    "senlik",
    "öğrenci",
    "ogrenci",
    "lise",
    "okul",
    "kariyer günü",
    "kariyer gunu",
    "sosyal sorumluluk",
    "ziyaret etti",
    "ziyaret",
    "kabul etti",
    "ağırladı",
    "agirladi",
    "kutlama",
    "tören",
    "toren",
    "festival",
    "etkinlik",
    "konferans",
    "söyleşi",
    "soylesi",
    "teknofest",
)


NON_BUSINESS_CONTEXT_TERMS = (
    "stadyum",
    "stadı",
    "stadi",
    "stadium",
    "maç",
    "mac",
    "futbol",
    "basketbol",
    "voleybol",
    "taraftar",
    "bilet",
    "derbi",
    "gol",
    "transfer",
    "teknik direktör",
    "teknik direktor",
    "forma",
    "tribün",
    "tribun",
    "fikstür",
    "fikstur",
    "deplasman",
    "hakem",
    "penaltı",
    "penalti",
    "kupa",
    "şampiyonluk",
    "sampiyonluk",
)


BUSINESS_CONTEXT_TERMS = (
    STRONG_INVESTMENT_CONTEXT_TERMS
    + MODERATE_INVESTMENT_CONTEXT_TERMS
    + WEAK_INVESTMENT_CONTEXT_TERMS
    + (
        "şirket",
        "sirket",
        "hisse",
        "borsa",
        "bist",
        "yatırımcı",
        "yatirimci",
        "finans",
        "finansal",
        "faaliyet",
        "pay",
    )
)


INVESTMENT_CONTEXT_TERMS = (
    STRONG_INVESTMENT_CONTEXT_TERMS
    + MODERATE_INVESTMENT_CONTEXT_TERMS
    + WEAK_INVESTMENT_CONTEXT_TERMS
)


STRONG_INVESTMENT_WEIGHT = 4
MODERATE_INVESTMENT_WEIGHT = 2
WEAK_INVESTMENT_WEIGHT = 1

LOW_VALUE_CORPORATE_WEIGHT = -3
NON_BUSINESS_CONTEXT_WEIGHT = -4

MIN_INVESTMENT_RELEVANCE_SCORE = 0


TURKISH_WORD_SUFFIXES = (
    "lar",
    "ler",
    "lari",
    "leri",
    "lardan",
    "lerden",
    "larda",
    "lerde",
    "larin",
    "lerin",
    "im",
    "in",
    "i",
    "imiz",
    "iniz",
    "um",
    "un",
    "u",
    "umuz",
    "unuz",
    "a",
    "e",
    "ya",
    "ye",
    "yi",
    "yu",
    "da",
    "de",
    "ta",
    "te",
    "dan",
    "den",
    "tan",
    "ten",
    "nda",
    "nde",
    "nin",
    "nun",
    "dir",
    "tir",
    "dur",
    "tur",
    "di",
    "ti",
    "mis",
    "mus",
    "ken",
    "ci",
    "cu",
    "lik",
    "luk",
    "li",
    "lu",
    "siz",
    "suz",
)


SORTED_TURKISH_WORD_SUFFIXES = tuple(
    sorted(
        set(TURKISH_WORD_SUFFIXES),
        key=len,
        reverse=True,
    )
)


TURKISH_SUFFIX_PATTERN = (
    "(?:"
    + "|".join(
        re.escape(suffix)
        for suffix
        in SORTED_TURKISH_WORD_SUFFIXES
    )
    + ")"
)


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


def normalize_relevance_text(
    value: object,
) -> str:
    cleaned_value = safe_text(
        value
    )

    if cleaned_value is None:
        return ""

    cleaned_value = re.sub(
        r"<[^>]+>",
        " ",
        cleaned_value,
    )

    return normalize_company_text(
        cleaned_value
    )


def article_combined_text(
    article: Mapping[str, object],
) -> str:
    text_parts = [
        normalize_relevance_text(
            article.get(
                "title"
            )
        ),
        normalize_relevance_text(
            article.get(
                "summary"
            )
        ),
    ]

    return " ".join(
        part
        for part in text_parts
        if part
    ).strip()


def exact_phrase_pattern(
    normalized_phrase: str,
) -> str:
    escaped_phrase = re.escape(
        normalized_phrase
    ).replace(
        r"\ ",
        r"\s+",
    )

    return (
        rf"(?<!\w)"
        rf"{escaped_phrase}"
        rf"(?!\w)"
    )


def inflected_word_pattern(
    normalized_word: str,
) -> str:
    return (
        rf"(?<!\w)"
        rf"{re.escape(normalized_word)}"
        rf"(?:{TURKISH_SUFFIX_PATTERN})+"
        rf"(?!\w)"
    )


def inflected_phrase_pattern(
    normalized_phrase: str,
) -> str | None:
    words = normalized_phrase.split()

    if len(words) < 2:
        return None

    prefix_words = words[:-1]
    final_word = words[-1]

    escaped_prefix = r"\s+".join(
        re.escape(word)
        for word in prefix_words
    )

    return (
        rf"(?<!\w)"
        rf"{escaped_prefix}"
        rf"\s+"
        rf"{re.escape(final_word)}"
        rf"(?:{TURKISH_SUFFIX_PATTERN})+"
        rf"(?!\w)"
    )


def text_contains_phrase(
    text: str,
    phrase: str,
) -> bool:
    normalized_phrase = (
        normalize_relevance_text(
            phrase
        )
    )

    if not normalized_phrase:
        return False

    exact_pattern = (
        exact_phrase_pattern(
            normalized_phrase
        )
    )

    if (
        re.search(
            exact_pattern,
            text,
            flags=re.IGNORECASE,
        )
        is not None
    ):
        return True

    if " " in normalized_phrase:
        inflected_pattern = (
            inflected_phrase_pattern(
                normalized_phrase
            )
        )

        if inflected_pattern is None:
            return False

        return (
            re.search(
                inflected_pattern,
                text,
                flags=re.IGNORECASE,
            )
            is not None
        )

    inflected_pattern = (
        inflected_word_pattern(
            normalized_phrase
        )
    )

    return (
        re.search(
            inflected_pattern,
            text,
            flags=re.IGNORECASE,
        )
        is not None
    )


def contains_any_phrase(
    text: str,
    phrases: Sequence[str],
) -> bool:
    return any(
        text_contains_phrase(
            text,
            phrase,
        )
        for phrase in phrases
    )


def matching_phrases(
    article: Mapping[str, object],
    phrases: Sequence[str],
) -> tuple[str, ...]:
    combined_text = article_combined_text(
        article
    )

    if not combined_text:
        return ()

    matches: list[str] = []
    seen_matches: set[str] = set()

    for phrase in phrases:
        cleaned_phrase = safe_text(
            phrase
        )

        if cleaned_phrase is None:
            continue

        normalized_phrase = (
            normalize_relevance_text(
                cleaned_phrase
            )
        )

        if not normalized_phrase:
            continue

        if normalized_phrase in seen_matches:
            continue

        if not text_contains_phrase(
            combined_text,
            cleaned_phrase,
        ):
            continue

        seen_matches.add(
            normalized_phrase
        )

        matches.append(
            cleaned_phrase
        )

    return tuple(matches)


def matching_aliases(
    article: Mapping[str, object],
    aliases: Sequence[str],
) -> tuple[str, ...]:
    return matching_phrases(
        article=article,
        phrases=aliases,
    )


def has_company_reference(
    article: Mapping[str, object],
    aliases: Sequence[str],
) -> bool:
    return bool(
        matching_aliases(
            article=article,
            aliases=aliases,
        )
    )


def has_business_context(
    article: Mapping[str, object],
) -> bool:
    return bool(
        matching_phrases(
            article=article,
            phrases=BUSINESS_CONTEXT_TERMS,
        )
    )


def has_non_business_context(
    article: Mapping[str, object],
) -> bool:
    return bool(
        matching_phrases(
            article=article,
            phrases=NON_BUSINESS_CONTEXT_TERMS,
        )
    )


def has_investment_context(
    article: Mapping[str, object],
) -> bool:
    return bool(
        matching_phrases(
            article=article,
            phrases=INVESTMENT_CONTEXT_TERMS,
        )
    )


def has_low_value_corporate_context(
    article: Mapping[str, object],
) -> bool:
    return bool(
        matching_phrases(
            article=article,
            phrases=LOW_VALUE_CORPORATE_CONTEXT_TERMS,
        )
    )


def calculate_investment_relevance_score(
    article: Mapping[str, object],
) -> int:
    strong_matches = matching_phrases(
        article=article,
        phrases=(
            STRONG_INVESTMENT_CONTEXT_TERMS
        ),
    )

    moderate_matches = matching_phrases(
        article=article,
        phrases=(
            MODERATE_INVESTMENT_CONTEXT_TERMS
        ),
    )

    weak_matches = matching_phrases(
        article=article,
        phrases=(
            WEAK_INVESTMENT_CONTEXT_TERMS
        ),
    )

    low_value_matches = matching_phrases(
        article=article,
        phrases=(
            LOW_VALUE_CORPORATE_CONTEXT_TERMS
        ),
    )

    non_business_matches = matching_phrases(
        article=article,
        phrases=(
            NON_BUSINESS_CONTEXT_TERMS
        ),
    )

    score = 0

    score += (
        len(strong_matches)
        * STRONG_INVESTMENT_WEIGHT
    )

    score += (
        len(moderate_matches)
        * MODERATE_INVESTMENT_WEIGHT
    )

    score += (
        len(weak_matches)
        * WEAK_INVESTMENT_WEIGHT
    )

    score += (
        len(low_value_matches)
        * LOW_VALUE_CORPORATE_WEIGHT
    )

    score += (
        len(non_business_matches)
        * NON_BUSINESS_CONTEXT_WEIGHT
    )

    return score


def investment_relevance_breakdown(
    article: Mapping[str, object],
) -> dict[str, object]:
    strong_matches = matching_phrases(
        article=article,
        phrases=(
            STRONG_INVESTMENT_CONTEXT_TERMS
        ),
    )

    moderate_matches = matching_phrases(
        article=article,
        phrases=(
            MODERATE_INVESTMENT_CONTEXT_TERMS
        ),
    )

    weak_matches = matching_phrases(
        article=article,
        phrases=(
            WEAK_INVESTMENT_CONTEXT_TERMS
        ),
    )

    low_value_matches = matching_phrases(
        article=article,
        phrases=(
            LOW_VALUE_CORPORATE_CONTEXT_TERMS
        ),
    )

    non_business_matches = matching_phrases(
        article=article,
        phrases=(
            NON_BUSINESS_CONTEXT_TERMS
        ),
    )

    score = calculate_investment_relevance_score(
        article
    )

    return {
        "score": score,
        "strong_matches": list(
            strong_matches
        ),
        "moderate_matches": list(
            moderate_matches
        ),
        "weak_matches": list(
            weak_matches
        ),
        "low_value_matches": list(
            low_value_matches
        ),
        "non_business_matches": list(
            non_business_matches
        ),
    }


def is_company_news_relevant(
    article: Mapping[str, object],
    aliases: Sequence[str],
) -> bool:
    if not has_company_reference(
        article=article,
        aliases=aliases,
    ):
        return False

    if has_business_context(
        article
    ):
        return True

    if has_non_business_context(
        article
    ):
        return False

    return True


def is_investment_relevant_company_news(
    article: Mapping[str, object],
    aliases: Sequence[str],
) -> bool:
    if not has_company_reference(
        article=article,
        aliases=aliases,
    ):
        return False

    relevance_score = (
        calculate_investment_relevance_score(
            article
        )
    )

    return (
        relevance_score
        >= MIN_INVESTMENT_RELEVANCE_SCORE
    )