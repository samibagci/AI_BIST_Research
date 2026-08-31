from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from functools import lru_cache

import yfinance as yf

from src.download_bist_prices import (
    normalize_bist_symbol,
)


TURKISH_CHARACTER_TRANSLATION = str.maketrans(
    {
        "I": "ı",
        "İ": "i",
        "Ç": "ç",
        "Ğ": "ğ",
        "Ö": "ö",
        "Ş": "ş",
        "Ü": "ü",
    }
)

ASCII_TRANSLATION = str.maketrans(
    {
        "ç": "c",
        "ğ": "g",
        "ı": "i",
        "ö": "o",
        "ş": "s",
        "ü": "u",
    }
)


LEGAL_SUFFIX_PATTERNS = (
    r"\s+a\.?\s*ş\.?$",
    r"\s+a\.?\s*s\.?$",
    r"\s+anonim şirketi$",
    r"\s+anonim sirketi$",
    r"\s+anonim ortaklığı$",
    r"\s+anonim ortakligi$",
)


@dataclass(frozen=True)
class CompanyProfile:
    symbol: str
    yahoo_symbol: str
    short_name: str | None
    long_name: str | None
    sector: str | None
    industry: str | None
    aliases: tuple[str, ...]
    source: str


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


def normalize_company_text(
    value: object,
) -> str:
    cleaned_value = safe_text(value)

    if cleaned_value is None:
        return ""

    normalized_value = (
        cleaned_value
        .translate(
            TURKISH_CHARACTER_TRANSLATION
        )
        .casefold()
        .translate(
            ASCII_TRANSLATION
        )
    )

    normalized_value = re.sub(
        r"\s+",
        " ",
        normalized_value,
    )

    return normalized_value.strip()


def clean_company_name(
    value: object,
) -> str | None:
    cleaned_value = safe_text(value)

    if cleaned_value is None:
        return None

    result = cleaned_value

    for pattern in LEGAL_SUFFIX_PATTERNS:
        result = re.sub(
            pattern,
            "",
            result,
            flags=re.IGNORECASE,
        ).strip()

    return safe_text(result)


def add_unique_alias(
    aliases: list[str],
    seen_aliases: set[str],
    value: object,
) -> None:
    cleaned_value = safe_text(value)

    if cleaned_value is None:
        return

    normalized_value = (
        normalize_company_text(
            cleaned_value
        )
    )

    if not normalized_value:
        return

    if normalized_value in seen_aliases:
        return

    seen_aliases.add(
        normalized_value
    )

    aliases.append(
        cleaned_value
    )


def ascii_company_name(
    value: object,
) -> str | None:
    cleaned_value = safe_text(value)

    if cleaned_value is None:
        return None

    normalized_value = (
        cleaned_value
        .translate(
            TURKISH_CHARACTER_TRANSLATION
        )
        .casefold()
        .translate(
            ASCII_TRANSLATION
        )
    )

    return safe_text(
        normalized_value
    )


def build_company_aliases(
    symbol: str,
    names: Sequence[object],
) -> tuple[str, ...]:
    yahoo_symbol = normalize_bist_symbol(
        symbol
    )

    base_symbol = yahoo_symbol.removesuffix(
        ".IS"
    )

    aliases: list[str] = []
    seen_aliases: set[str] = set()

    add_unique_alias(
        aliases,
        seen_aliases,
        base_symbol,
    )

    for name in names:
        cleaned_name = safe_text(name)

        if cleaned_name is None:
            continue

        add_unique_alias(
            aliases,
            seen_aliases,
            cleaned_name,
        )

        company_name = clean_company_name(
            cleaned_name
        )

        add_unique_alias(
            aliases,
            seen_aliases,
            company_name,
        )

        ascii_name = ascii_company_name(
            cleaned_name
        )

        add_unique_alias(
            aliases,
            seen_aliases,
            ascii_name,
        )

        ascii_clean_name = (
            ascii_company_name(
                company_name
            )
        )

        add_unique_alias(
            aliases,
            seen_aliases,
            ascii_clean_name,
        )

    return tuple(aliases)


def fetch_company_info(
    symbol: str,
) -> dict[str, object]:
    yahoo_symbol = normalize_bist_symbol(
        symbol
    )

    ticker = yf.Ticker(
        yahoo_symbol
    )

    raw_info: object

    try:
        raw_info = ticker.get_info()
    except AttributeError:
        raw_info = ticker.info

    if not isinstance(
        raw_info,
        Mapping,
    ):
        raise ValueError(
            f"{yahoo_symbol} şirket bilgisi "
            "beklenen formatta değil."
        )

    return dict(raw_info)


def build_company_profile(
    symbol: str,
    info: Mapping[str, object] | None,
    source: str,
) -> CompanyProfile:
    yahoo_symbol = normalize_bist_symbol(
        symbol
    )

    base_symbol = yahoo_symbol.removesuffix(
        ".IS"
    )

    company_info: Mapping[
        str,
        object
    ] = (
        info
        if info is not None
        else {}
    )

    short_name = safe_text(
        company_info.get(
            "shortName"
        )
    )

    long_name = safe_text(
        company_info.get(
            "longName"
        )
    )

    sector = safe_text(
        company_info.get(
            "sector"
        )
    )

    industry = safe_text(
        company_info.get(
            "industry"
        )
    )

    aliases = build_company_aliases(
        symbol=base_symbol,
        names=[
            short_name,
            long_name,
        ],
    )

    return CompanyProfile(
        symbol=base_symbol,
        yahoo_symbol=yahoo_symbol,
        short_name=short_name,
        long_name=long_name,
        sector=sector,
        industry=industry,
        aliases=aliases,
        source=source,
    )


@lru_cache(maxsize=1024)
def _get_company_profile_cached(
    symbol: str,
) -> CompanyProfile:
    yahoo_symbol = normalize_bist_symbol(
        symbol
    )

    base_symbol = yahoo_symbol.removesuffix(
        ".IS"
    )

    try:
        info = fetch_company_info(
            base_symbol
        )

        return build_company_profile(
            symbol=base_symbol,
            info=info,
            source=(
                "Yahoo Finance / yfinance"
            ),
        )

    except Exception:
        return build_company_profile(
            symbol=base_symbol,
            info=None,
            source="symbol_fallback",
        )


def get_company_profile(
    symbol: str,
    info: Mapping[str, object] | None = None,
) -> CompanyProfile:
    yahoo_symbol = normalize_bist_symbol(
        symbol
    )

    base_symbol = yahoo_symbol.removesuffix(
        ".IS"
    )

    if info is not None:
        return build_company_profile(
            symbol=base_symbol,
            info=info,
            source="provided_info",
        )

    return _get_company_profile_cached(
        base_symbol
    )


def get_company_aliases(
    symbol: str,
    info: Mapping[str, object] | None = None,
) -> tuple[str, ...]:
    profile = get_company_profile(
        symbol=symbol,
        info=info,
    )

    return profile.aliases


def get_company_sector(
    symbol: str,
    info: Mapping[str, object] | None = None,
) -> str | None:
    profile = get_company_profile(
        symbol=symbol,
        info=info,
    )

    return profile.sector


def company_profile_to_dict(
    profile: CompanyProfile,
) -> dict[str, object]:
    result = asdict(profile)

    result["aliases"] = list(
        profile.aliases
    )

    return result


def clear_company_registry_cache() -> None:
    _get_company_profile_cached.cache_clear()