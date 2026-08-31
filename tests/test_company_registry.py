from __future__ import annotations

from collections.abc import Mapping

import pytest

import src.company_registry as module
from src.company_registry import (
    CompanyProfile,
    ascii_company_name,
    build_company_aliases,
    build_company_profile,
    clean_company_name,
    clear_company_registry_cache,
    company_profile_to_dict,
    fetch_company_info,
    get_company_aliases,
    get_company_profile,
    get_company_sector,
    normalize_company_text,
    safe_text,
)


def create_company_info() -> dict[str, object]:
    return {
        "shortName": "Tüpraş",
        "longName": (
            "Türkiye Petrol Rafinerileri A.Ş."
        ),
        "sector": "Energy",
        "industry": "Oil & Gas Refining",
    }


def test_safe_text_cleans_whitespace() -> None:
    assert (
        safe_text("  Türkiye   Petrol  ")
        == "Türkiye Petrol"
    )

    assert safe_text("") is None
    assert safe_text("   ") is None
    assert safe_text(None) is None
    assert safe_text(123) is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (
            "TÜPRAŞ",
            "tupras",
        ),
        (
            "Tüpraş",
            "tupras",
        ),
        (
            "ŞİŞECAM",
            "sisecam",
        ),
        (
            "Türk Hava Yolları",
            "turk hava yollari",
        ),
        (
            "  Koç   Holding  ",
            "koc holding",
        ),
    ],
)
def test_normalize_company_text(
    value: str,
    expected: str,
) -> None:
    assert (
        normalize_company_text(value)
        == expected
    )


def test_normalize_company_text_invalid_value() -> None:
    assert normalize_company_text(None) == ""
    assert normalize_company_text(123) == ""


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (
            "Türkiye Petrol Rafinerileri A.Ş.",
            "Türkiye Petrol Rafinerileri",
        ),
        (
            "Örnek Holding AŞ",
            "Örnek Holding",
        ),
        (
            "Örnek Anonim Şirketi",
            "Örnek",
        ),
        (
            "Örnek Anonim Ortaklığı",
            "Örnek",
        ),
    ],
)
def test_clean_company_name(
    value: str,
    expected: str,
) -> None:
    assert clean_company_name(value) == expected


def test_clean_company_name_without_suffix() -> None:
    assert (
        clean_company_name("Tüpraş")
        == "Tüpraş"
    )


def test_clean_company_name_invalid_value() -> None:
    assert clean_company_name(None) is None
    assert clean_company_name("") is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (
            "Tüpraş",
            "tupras",
        ),
        (
            "Şişecam",
            "sisecam",
        ),
        (
            "Koç Holding",
            "koc holding",
        ),
    ],
)
def test_ascii_company_name(
    value: str,
    expected: str,
) -> None:
    assert (
        ascii_company_name(value)
        == expected
    )


def test_ascii_company_name_invalid_value() -> None:
    assert ascii_company_name(None) is None


def test_build_company_aliases() -> None:
    aliases = build_company_aliases(
        symbol="TUPRS",
        names=[
            "Tüpraş",
            (
                "Türkiye Petrol "
                "Rafinerileri A.Ş."
            ),
        ],
    )

    assert aliases[0] == "TUPRS"
    assert "Tüpraş" in aliases

    assert (
        "Türkiye Petrol Rafinerileri A.Ş."
        in aliases
    )

    assert (
        "Türkiye Petrol Rafinerileri"
        in aliases
    )


def test_build_company_aliases_removes_duplicates() -> None:
    aliases = build_company_aliases(
        symbol="TUPRS",
        names=[
            "Tüpraş",
            "TÜPRAŞ",
            "tupras",
        ],
    )

    normalized_aliases = [
        normalize_company_text(alias)
        for alias in aliases
    ]

    assert (
        normalized_aliases.count(
            "tupras"
        )
        == 1
    )


def test_build_company_aliases_ignores_empty_names() -> None:
    aliases = build_company_aliases(
        symbol="TUPRS",
        names=[
            None,
            "",
            "   ",
        ],
    )

    assert aliases == (
        "TUPRS",
    )


def test_build_company_profile() -> None:
    profile = build_company_profile(
        symbol="TUPRS",
        info=create_company_info(),
        source="test_source",
    )

    assert isinstance(
        profile,
        CompanyProfile,
    )

    assert profile.symbol == "TUPRS"
    assert profile.yahoo_symbol == "TUPRS.IS"
    assert profile.short_name == "Tüpraş"

    assert (
        profile.long_name
        == "Türkiye Petrol Rafinerileri A.Ş."
    )

    assert profile.sector == "Energy"

    assert (
        profile.industry
        == "Oil & Gas Refining"
    )

    assert "TUPRS" in profile.aliases
    assert "Tüpraş" in profile.aliases
    assert profile.source == "test_source"


def test_build_company_profile_with_empty_info() -> None:
    profile = build_company_profile(
        symbol="TUPRS",
        info=None,
        source="fallback",
    )

    assert profile.symbol == "TUPRS"
    assert profile.yahoo_symbol == "TUPRS.IS"
    assert profile.short_name is None
    assert profile.long_name is None
    assert profile.sector is None
    assert profile.industry is None

    assert profile.aliases == (
        "TUPRS",
    )


def test_fetch_company_info_uses_get_info(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    expected_info = create_company_info()

    class FakeTicker:
        def __init__(
            self,
            symbol: str,
        ) -> None:
            captured["symbol"] = symbol

        def get_info(
            self,
        ) -> dict[str, object]:
            captured["get_info"] = True
            return expected_info

    monkeypatch.setattr(
        module.yf,
        "Ticker",
        FakeTicker,
    )

    result = fetch_company_info(
        "TUPRS"
    )

    assert captured["symbol"] == "TUPRS.IS"
    assert captured["get_info"] is True
    assert result == expected_info


def test_fetch_company_info_falls_back_to_info(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    expected_info = create_company_info()

    class FakeTicker:
        def __init__(
            self,
            symbol: str,
        ) -> None:
            captured["symbol"] = symbol
            self.info = expected_info

    monkeypatch.setattr(
        module.yf,
        "Ticker",
        FakeTicker,
    )

    result = fetch_company_info(
        "TUPRS"
    )

    assert captured["symbol"] == "TUPRS.IS"
    assert result == expected_info


def test_fetch_company_info_rejects_invalid_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeTicker:
        def __init__(
            self,
            symbol: str,
        ) -> None:
            self.symbol = symbol

        def get_info(
            self,
        ) -> list[str]:
            return [
                "geçersiz",
            ]

    monkeypatch.setattr(
        module.yf,
        "Ticker",
        FakeTicker,
    )

    with pytest.raises(
        ValueError,
        match="beklenen formatta değil",
    ):
        fetch_company_info(
            "TUPRS"
        )


def test_get_company_profile_with_provided_info() -> None:
    profile = get_company_profile(
        symbol="TUPRS",
        info=create_company_info(),
    )

    assert profile.symbol == "TUPRS"
    assert profile.short_name == "Tüpraş"
    assert profile.sector == "Energy"

    assert (
        profile.source
        == "provided_info"
    )


def test_get_company_profile_fetches_and_caches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {
        "count": 0,
    }

    def fake_fetch_company_info(
        symbol: str,
    ) -> dict[str, object]:
        calls["count"] += 1
        return create_company_info()

    monkeypatch.setattr(
        module,
        "fetch_company_info",
        fake_fetch_company_info,
    )

    clear_company_registry_cache()

    first_result = get_company_profile(
        "TUPRS"
    )

    second_result = get_company_profile(
        "TUPRS"
    )

    assert calls["count"] == 1

    assert (
        first_result
        == second_result
    )

    clear_company_registry_cache()


def test_get_company_profile_uses_symbol_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failing_fetch(
        symbol: str,
    ) -> dict[str, object]:
        raise RuntimeError(
            "Bağlantı başarısız."
        )

    monkeypatch.setattr(
        module,
        "fetch_company_info",
        failing_fetch,
    )

    clear_company_registry_cache()

    profile = get_company_profile(
        "TUPRS"
    )

    assert profile.symbol == "TUPRS"

    assert profile.aliases == (
        "TUPRS",
    )

    assert (
        profile.source
        == "symbol_fallback"
    )

    clear_company_registry_cache()


def test_get_company_aliases() -> None:
    aliases = get_company_aliases(
        symbol="TUPRS",
        info=create_company_info(),
    )

    assert "TUPRS" in aliases
    assert "Tüpraş" in aliases

    assert (
        "Türkiye Petrol Rafinerileri"
        in aliases
    )


def test_get_company_sector() -> None:
    sector = get_company_sector(
        symbol="TUPRS",
        info=create_company_info(),
    )

    assert sector == "Energy"


def test_get_company_sector_missing() -> None:
    sector = get_company_sector(
        symbol="TUPRS",
        info={},
    )

    assert sector is None


def test_company_profile_to_dict() -> None:
    profile = build_company_profile(
        symbol="TUPRS",
        info=create_company_info(),
        source="test",
    )

    result = company_profile_to_dict(
        profile
    )

    assert isinstance(
        result,
        dict,
    )

    assert result["symbol"] == "TUPRS"
    assert result["yahoo_symbol"] == "TUPRS.IS"
    assert result["short_name"] == "Tüpraş"
    assert result["sector"] == "Energy"

    assert isinstance(
        result["aliases"],
        list,
    )

    assert "TUPRS" in result["aliases"]


def test_clear_company_registry_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {
        "count": 0,
    }

    def fake_fetch_company_info(
        symbol: str,
    ) -> dict[str, object]:
        calls["count"] += 1
        return create_company_info()

    monkeypatch.setattr(
        module,
        "fetch_company_info",
        fake_fetch_company_info,
    )

    clear_company_registry_cache()

    get_company_profile(
        "TUPRS"
    )

    clear_company_registry_cache()

    get_company_profile(
        "TUPRS"
    )

    assert calls["count"] == 2

    clear_company_registry_cache()