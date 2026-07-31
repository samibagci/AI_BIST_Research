from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

import src.download_bist_prices as module
from src.download_bist_prices import (
    download_bist_prices,
    normalize_bist_symbol,
    prepare_price_data,
    save_price_data,
)


def create_yahoo_price_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": [100.0, 102.0, 103.0],
            "High": [104.0, 105.0, 106.0],
            "Low": [99.0, 101.0, 102.0],
            "Close": [103.0, 104.0, 105.0],
            "Volume": [1_000_000, 1_200_000, 1_100_000],
        },
        index=pd.date_range(
            "2026-01-05",
            periods=3,
            freq="B",
            name="Date",
        ),
    )


@pytest.mark.parametrize(
    ("symbol", "expected"),
    [
        ("THYAO", "THYAO.IS"),
        ("thyao", "THYAO.IS"),
        (" THYAO.IS ", "THYAO.IS"),
        ("ASELS", "ASELS.IS"),
    ],
)
def test_normalize_bist_symbol(
    symbol: str,
    expected: str,
) -> None:
    assert normalize_bist_symbol(symbol) == expected


@pytest.mark.parametrize(
    "symbol",
    [
        "",
        ".IS",
        "THY AO",
        "THYAO-IS",
        "THYAO!",
    ],
)
def test_normalize_bist_symbol_rejects_invalid_values(
    symbol: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="Geçersiz hisse kodu",
    ):
        normalize_bist_symbol(symbol)


def test_prepare_price_data_creates_required_format() -> None:
    result = prepare_price_data(
        create_yahoo_price_data()
    )

    assert list(result.columns) == [
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    assert len(result) == 3
    assert result["date"].iloc[0] == "2026-01-05"
    assert result["close"].iloc[-1] == 105.0


def test_download_bist_prices_uses_yahoo_symbol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_arguments: dict[str, object] = {}

    def fake_download(**kwargs: object) -> pd.DataFrame:
        captured_arguments.update(kwargs)
        return create_yahoo_price_data()

    monkeypatch.setattr(
        module.yf,
        "download",
        fake_download,
    )

    result = download_bist_prices(
        symbol="THYAO",
        period="6mo",
    )

    assert captured_arguments["tickers"] == "THYAO.IS"
    assert captured_arguments["period"] == "6mo"
    assert captured_arguments["interval"] == "1d"
    assert captured_arguments["auto_adjust"] is True
    assert len(result) == 3


def test_download_bist_prices_rejects_empty_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        module.yf,
        "download",
        lambda **kwargs: pd.DataFrame(),
    )

    with pytest.raises(
        ValueError,
        match="fiyat verisi bulunamadı",
    ):
        download_bist_prices("THYAO")


def test_save_price_data_creates_csv(
    tmp_path: Path,
) -> None:
    output_path = (
        tmp_path
        / "data"
        / "prices"
        / "THYAO.csv"
    )

    price_data = prepare_price_data(
        create_yahoo_price_data()
    )

    save_price_data(
        price_data=price_data,
        output_path=output_path,
    )

    assert output_path.exists()

    saved_data = pd.read_csv(output_path)

    assert len(saved_data) == 3
    assert list(saved_data.columns) == [
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]


def test_main_downloads_and_saves_prices(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_path = tmp_path / "THYAO.csv"

    price_data = prepare_price_data(
        create_yahoo_price_data()
    )

    monkeypatch.setattr(
        module,
        "download_bist_prices",
        lambda symbol, period: price_data,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "download_bist_prices.py",
            "THYAO",
            "--period",
            "6mo",
            "--output",
            str(output_path),
        ],
    )

    exit_code = module.main()
    terminal_output = capsys.readouterr().out

    assert exit_code == 0
    assert output_path.exists()
    assert "BAŞARILI" in terminal_output
    assert "THYAO.IS" in terminal_output
    assert "Satır sayısı: 3" in terminal_output


def test_main_returns_error_for_invalid_symbol(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "download_bist_prices.py",
            "THY AO",
        ],
    )

    exit_code = module.main()
    terminal_output = capsys.readouterr().out

    assert exit_code == 1
    assert "HATA" in terminal_output