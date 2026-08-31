from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from src.company_registry import (
    normalize_company_text,
)


BUSINESS_CONTEXT_TERMS = (
    "şirket",
    "hisse",
    "borsa",
    "bist",
    "yatırım",
    "yatırımcı",
    "finans",
    "finansal",
    "gelir",
    "ciro",
    "kâr",
    "kar",
    "zarar",
    "temettü",
    "temettu",
    "kap",
    "sermaye",
    "ortaklık",
    "ortaklik",
    "satış",
    "satis",
    "üretim",
    "uretim",
    "ihracat",
    "ithalat",
    "sözleşme",
    "sozlesme",
    "anlaşma",
    "anlasma",
    "ihale",
    "sipariş",
    "siparis",
    "fabrika",
    "tesis",
    "faaliyet",
    "bilanço",
    "bilanco",
    "finansman",
    "borç",
    "borc",
    "kredi",
    "pay",
    "halka arz",
    "geri alım",
    "geri alim",
    "sponsorluk",
    "iş birliği",
    "is birligi",
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
    "leri",
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
    return (
        rf"(?<!\w)"
        rf"{re.escape(normalized_phrase)}"
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
        return False

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


def matching_aliases(
    article: Mapping[str, object],
    aliases: Sequence[str],
) -> tuple[str, ...]:
    combined_text = article_combined_text(
        article
    )

    if not combined_text:
        return ()

    matches: list[str] = []
    seen_matches: set[str] = set()

    for alias in aliases:
        cleaned_alias = safe_text(
            alias
        )

        if cleaned_alias is None:
            continue

        normalized_alias = (
            normalize_relevance_text(
                cleaned_alias
            )
        )

        if not normalized_alias:
            continue

        if normalized_alias in seen_matches:
            continue

        if not text_contains_phrase(
            combined_text,
            cleaned_alias,
        ):
            continue

        seen_matches.add(
            normalized_alias
        )

        matches.append(
            cleaned_alias
        )

    return tuple(matches)


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
    combined_text = article_combined_text(
        article
    )

    if not combined_text:
        return False

    return contains_any_phrase(
        text=combined_text,
        phrases=BUSINESS_CONTEXT_TERMS,
    )


def has_non_business_context(
    article: Mapping[str, object],
) -> bool:
    combined_text = article_combined_text(
        article
    )

    if not combined_text:
        return False

    return contains_any_phrase(
        text=combined_text,
        phrases=NON_BUSINESS_CONTEXT_TERMS,
    )


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