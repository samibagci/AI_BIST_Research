from __future__ import annotations

import pytest

from src.news_relevance import (
    article_combined_text,
    contains_any_phrase,
    has_business_context,
    has_company_reference,
    has_non_business_context,
    is_company_news_relevant,
    matching_aliases,
    normalize_relevance_text,
    safe_text,
    text_contains_phrase,
)


def create_article(
    title: str = "Tüpraş yeni yatırım açıkladı",
    summary: str = "Şirket yeni tesis yatırımı yapacak.",
) -> dict[str, object]:
    return {
        "title": title,
        "summary": summary,
    }


def test_safe_text() -> None:
    assert (
        safe_text("  örnek   metin  ")
        == "örnek metin"
    )

    assert safe_text("") is None
    assert safe_text("   ") is None
    assert safe_text(None) is None
    assert safe_text(123) is None


def test_normalize_relevance_text() -> None:
    assert (
        normalize_relevance_text(
            "<b>TÜPRAŞ Şirketi</b>"
        )
        == "tupras sirketi"
    )


def test_normalize_relevance_text_invalid_value() -> None:
    assert normalize_relevance_text(None) == ""


def test_article_combined_text() -> None:
    article = create_article(
        title="Tüpraş yatırım açıkladı",
        summary="Yeni tesis kurulacak.",
    )

    assert (
        article_combined_text(article)
        == (
            "tupras yatirim acikladi "
            "yeni tesis kurulacak."
        )
    )


def test_article_combined_text_ignores_empty_values() -> None:
    article = {
        "title": "Tüpraş",
        "summary": None,
    }

    assert (
        article_combined_text(article)
        == "tupras"
    )


def test_text_contains_phrase() -> None:
    text = (
        "tupras yeni yatirim "
        "kararini acikladi"
    )

    assert text_contains_phrase(
        text,
        "Tüpraş",
    )

    assert text_contains_phrase(
        text,
        "yatırım",
    )


def test_text_contains_phrase_requires_word_boundary() -> None:
    text = "aselsan yeni proje acikladi"

    assert text_contains_phrase(
        text,
        "ASELSAN",
    )

    assert not text_contains_phrase(
        text,
        "ASEL",
    )


def test_text_contains_phrase_empty_phrase() -> None:
    assert not text_contains_phrase(
        "tupras haber",
        "",
    )


def test_contains_any_phrase() -> None:
    assert contains_any_phrase(
        text="sirket yeni yatirim acikladi",
        phrases=(
            "maç",
            "yatırım",
            "stadyum",
        ),
    )


def test_contains_any_phrase_returns_false() -> None:
    assert not contains_any_phrase(
        text="siradan bir metin",
        phrases=(
            "yatırım",
            "borsa",
        ),
    )


def test_matching_aliases() -> None:
    article = create_article(
        title=(
            "Tüpraş yeni yatırım "
            "planını açıkladı"
        ),
        summary="TUPRS hisseleri izlendi.",
    )

    result = matching_aliases(
        article=article,
        aliases=(
            "TUPRS",
            "Tüpraş",
            "Türkiye Petrol Rafinerileri",
        ),
    )

    assert result == (
        "TUPRS",
        "Tüpraş",
    )


def test_matching_aliases_removes_normalized_duplicates() -> None:
    article = create_article(
        title="Tüpraş yatırım açıkladı",
        summary="",
    )

    result = matching_aliases(
        article=article,
        aliases=(
            "Tüpraş",
            "TÜPRAŞ",
            "tupras",
        ),
    )

    assert result == (
        "Tüpraş",
    )


def test_matching_aliases_empty_article() -> None:
    result = matching_aliases(
        article={
            "title": None,
            "summary": None,
        },
        aliases=(
            "Tüpraş",
        ),
    )

    assert result == ()


def test_has_company_reference() -> None:
    article = create_article(
        title="ASELSAN sözleşme imzaladı",
        summary="Yeni proje açıklandı.",
    )

    assert has_company_reference(
        article=article,
        aliases=(
            "ASELS",
            "ASELSAN",
        ),
    )

    assert not has_company_reference(
        article=article,
        aliases=(
            "Tüpraş",
        ),
    )


@pytest.mark.parametrize(
    "text",
    [
        "Tüpraş yeni yatırım açıkladı.",
        "Tüpraş bilanço sonuçlarını duyurdu.",
        "Tüpraş yeni tesis kuracak.",
        "Tüpraş KAP açıklaması yayımladı.",
        "Tüpraş temettü kararı aldı.",
        "Tüpraş yeni sözleşme imzaladı.",
    ],
)
def test_has_business_context(
    text: str,
) -> None:
    article = {
        "title": text,
        "summary": None,
    }

    assert has_business_context(
        article
    )


@pytest.mark.parametrize(
    "text",
    [
        "Tüpraş Stadyumu maç programı açıklandı.",
        "Tüpraş Stadı taraftarları ağırladı.",
        "Tüpraş'ta derbi heyecanı yaşandı.",
        "Tüpraş isimli statta futbol maçı oynandı.",
        "Tüpraş tribünlerinde taraftarlar toplandı.",
        "Tüpraş sahasında hakem kararı tartışıldı.",
    ],
)
def test_has_non_business_context(
    text: str,
) -> None:
    article = {
        "title": text,
        "summary": None,
    }

    assert has_non_business_context(
        article
    )


def test_company_news_relevant_for_business_article() -> None:
    article = create_article(
        title="Tüpraş yeni yatırım açıkladı",
        summary=(
            "Şirket üretim kapasitesini "
            "artıracak."
        ),
    )

    assert is_company_news_relevant(
        article=article,
        aliases=(
            "TUPRS",
            "Tüpraş",
        ),
    )


def test_company_news_irrelevant_without_company_reference() -> None:
    article = create_article(
        title="Yeni enerji yatırımı açıklandı",
        summary="Şirket üretimi artıracak.",
    )

    assert not is_company_news_relevant(
        article=article,
        aliases=(
            "TUPRS",
            "Tüpraş",
        ),
    )


def test_company_news_rejects_sports_only_context() -> None:
    article = create_article(
        title=(
            "Tüpraş Stadyumu'nda "
            "derbi oynandı"
        ),
        summary=(
            "Taraftarlar maç için "
            "tribünleri doldurdu."
        ),
    )

    assert not is_company_news_relevant(
        article=article,
        aliases=(
            "TUPRS",
            "Tüpraş",
        ),
    )


def test_business_context_overrides_non_business_context() -> None:
    article = create_article(
        title=(
            "Tüpraş sponsorluk "
            "anlaşmasını açıkladı"
        ),
        summary=(
            "Şirket stadyum isim "
            "sponsorluğu için yeni "
            "sözleşme imzaladı."
        ),
    )

    assert has_business_context(
        article
    )

    assert has_non_business_context(
        article
    )

    assert is_company_news_relevant(
        article=article,
        aliases=(
            "TUPRS",
            "Tüpraş",
        ),
    )


def test_company_news_accepts_neutral_company_reference() -> None:
    article = create_article(
        title="Tüpraş hakkında yeni açıklama",
        summary="Detaylar kamuoyuyla paylaşıldı.",
    )

    assert not has_business_context(
        article
    )

    assert not has_non_business_context(
        article
    )

    assert is_company_news_relevant(
        article=article,
        aliases=(
            "TUPRS",
            "Tüpraş",
        ),
    )


def test_filter_is_not_company_specific() -> None:
    article = create_article(
        title=(
            "ASELSAN yeni sözleşme "
            "imzaladı"
        ),
        summary=(
            "Şirket yeni sipariş aldı."
        ),
    )

    assert is_company_news_relevant(
        article=article,
        aliases=(
            "ASELS",
            "ASELSAN",
        ),
    )


def test_filter_rejects_sports_context_for_other_company() -> None:
    article = create_article(
        title=(
            "Örnek Holding Stadı'nda "
            "maç oynandı"
        ),
        summary=(
            "Taraftarlar tribünleri "
            "doldurdu."
        ),
    )

    assert not is_company_news_relevant(
        article=article,
        aliases=(
            "Örnek Holding",
        ),
    )