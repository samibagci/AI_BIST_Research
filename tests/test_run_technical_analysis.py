from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.run_technical_analysis import (
    build_analysis_result,
    load_price_data,
    main,
    save_result,
)
from src.technical_indicators import add_technical_indicators


def create_sample_price_data(
    row_count: int = 120,
) -> pd.DataFrame:
    """Testlerde kullanılacak örnek OHLCV verisini oluşturur."""
    dates = pd.date_range(
        start="2025-01-01",
        periods=row_count,
        freq="D",
    )

    trend = np.linspace(100, 160, row_count)
    wave = np.sin(np.arange(row_count) / 6) * 2
    close = trend + wave

    return pd.DataFrame(
        {
            "date": dates,
            "open": close - 0.5,
            "high": close + 1.5,
            "low": close - 1.5,
            "close": close,
            "volume": np.linspace(
                1_000_000,
                2_000_000,
                row_count,
            ),
        }
    )


def test_load_price_data_reads_valid_csv(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "prices.csv"

    create_sample_price_data().to_csv(
        csv_path,
        index=False,
    )

    result = load_price_data(csv_path)

    assert len(result) == 120
    assert isinstance(result.index, pd.DatetimeIndex)

    assert {
        "open",
        "high",
        "low",
        "close",
        "volume",
    }.issubset(result.columns)


def test_missing_csv_file_raises_error(
    tmp_path: Path,
) -> None:
    missing_path = tmp_path / "missing.csv"

    with pytest.raises(
        FileNotFoundError,
        match="Fiyat veri dosyası bulunamadı",
    ):
        load_price_data(missing_path)


def test_csv_with_missing_column_raises_error(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "invalid.csv"

    invalid_data = create_sample_price_data().drop(
        columns=["volume"]
    )

    invalid_data.to_csv(
        csv_path,
        index=False,
    )

    with pytest.raises(
        ValueError,
        match="CSV dosyasında eksik sütunlar var",
    ):
        load_price_data(csv_path)


def test_csv_with_less_than_sixty_rows_raises_error(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "short.csv"

    create_sample_price_data(
        row_count=30,
    ).to_csv(
        csv_path,
        index=False,
    )

    with pytest.raises(
        ValueError,
        match="en az 60 satır",
    ):
        load_price_data(csv_path)


def test_build_analysis_result_has_expected_structure() -> None:
    price_data = create_sample_price_data()

    price_data = (
        price_data
        .set_index("date")
    )

    indicator_data = add_technical_indicators(
        price_data
    )

    result = build_analysis_result(
        symbol="thyao",
        indicator_data=indicator_data,
    )

    assert result["symbol"] == "THYAO"
    assert result["record_count"] == 120
    assert result["price_date"] is not None

    assert "indicators" in result
    assert "technical_analysis" in result

    assert (
        0
        <= result["technical_analysis"]["technical_score"]
        <= 100
    )


def test_save_result_creates_json_file(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "result.json"

    result = {
        "symbol": "THYAO",
        "technical_analysis": {
            "technical_score": 75.5,
        },
    }

    save_result(
        result=result,
        output_path=output_path,
    )

    assert output_path.exists()

    with output_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        saved_result = json.load(file)

    assert saved_result == result


def test_main_creates_output_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_path = tmp_path / "prices.csv"
    output_path = tmp_path / "analysis.json"

    create_sample_price_data().to_csv(
        input_path,
        index=False,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_technical_analysis.py",
            str(input_path),
            "--symbol",
            "THYAO",
            "--output",
            str(output_path),
        ],
    )

    exit_code = main()

    captured_output = capsys.readouterr().out

    assert exit_code == 0
    assert output_path.exists()
    assert "BAŞARILI" in captured_output
    assert "THYAO" in captured_output