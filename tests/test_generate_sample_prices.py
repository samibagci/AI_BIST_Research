from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

from src.generate_sample_prices import (
    generate_sample_prices,
    main,
    save_sample_prices,
)


def test_generate_sample_prices_returns_expected_columns() -> None:
    result = generate_sample_prices(row_count=180)

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 180

    assert list(result.columns) == [
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]


def test_generated_prices_are_valid() -> None:
    result = generate_sample_prices(row_count=120)

    assert (result["open"] > 0).all()
    assert (result["high"] > 0).all()
    assert (result["low"] > 0).all()
    assert (result["close"] > 0).all()
    assert (result["volume"] > 0).all()

    assert (result["high"] >= result["open"]).all()
    assert (result["high"] >= result["close"]).all()
    assert (result["low"] <= result["open"]).all()
    assert (result["low"] <= result["close"]).all()


def test_generated_dates_are_business_days() -> None:
    result = generate_sample_prices(row_count=60)

    dates = pd.to_datetime(result["date"])

    assert (dates.dt.dayofweek < 5).all()


def test_generation_is_repeatable() -> None:
    first_result = generate_sample_prices(row_count=100)
    second_result = generate_sample_prices(row_count=100)

    pd.testing.assert_frame_equal(
        first_result,
        second_result,
    )


def test_less_than_sixty_rows_raises_error() -> None:
    with pytest.raises(
        ValueError,
        match="en az 60 satır",
    ):
        generate_sample_prices(row_count=59)


def test_save_sample_prices_creates_csv(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "sample_prices.csv"

    price_data = generate_sample_prices(row_count=80)

    save_sample_prices(
        price_data=price_data,
        output_path=output_path,
    )

    assert output_path.exists()

    saved_data = pd.read_csv(output_path)

    assert len(saved_data) == 80
    assert list(saved_data.columns) == [
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]


def test_main_creates_output_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_path = tmp_path / "generated_prices.csv"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "generate_sample_prices.py",
            "--output",
            str(output_path),
            "--rows",
            "90",
        ],
    )

    exit_code = main()
    output = capsys.readouterr().out

    assert exit_code == 0
    assert output_path.exists()
    assert "BAŞARILI" in output
    assert "Satır sayısı: 90" in output


def test_main_returns_error_for_invalid_row_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_path = tmp_path / "invalid.csv"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "generate_sample_prices.py",
            "--output",
            str(output_path),
            "--rows",
            "20",
        ],
    )

    exit_code = main()
    output = capsys.readouterr().out

    assert exit_code == 1
    assert not output_path.exists()
    assert "HATA" in output