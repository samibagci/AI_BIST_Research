from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

import src.run_bist_analysis as module
from src.run_bist_analysis import run_bist_analysis


def create_price_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": [
                "2026-01-05",
                "2026-01-06",
                "2026-01-07",
            ],
            "open": [100.0, 102.0, 103.0],
            "high": [104.0, 105.0, 106.0],
            "low": [99.0, 101.0, 102.0],
            "close": [103.0, 104.0, 105.0],
            "volume": [
                1_000_000,
                1_200_000,
                1_100_000,
            ],
        }
    )


def create_analysis_result(
    symbol: str = "THYAO",
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "record_count": 3,
        "technical_analysis": {
            "technical_score": 62.5,
        },
    }


def test_run_bist_analysis_uses_default_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    captured_download: dict[str, object] = {}
    captured_pipeline: dict[str, object] = {}

    def fake_download(
        symbol: str,
        period: str,
    ) -> pd.DataFrame:
        captured_download["symbol"] = symbol
        captured_download["period"] = period
        return create_price_data()

    def fake_pipeline(
        **kwargs: object,
    ) -> dict[str, object]:
        captured_pipeline.update(kwargs)
        return create_analysis_result()

    monkeypatch.setattr(
        module,
        "download_bist_prices",
        fake_download,
    )

    monkeypatch.setattr(
        module,
        "run_pipeline",
        fake_pipeline,
    )

    result = run_bist_analysis(
        symbol="thyao",
        period="6mo",
    )

    assert result["symbol"] == "THYAO"
    assert captured_download["symbol"] == "THYAO.IS"
    assert captured_download["period"] == "6mo"

    assert captured_pipeline["input_path"] == Path(
        "data/prices/THYAO.csv"
    )
    assert captured_pipeline["symbol"] == "THYAO"
    assert captured_pipeline["json_output_path"] == Path(
        "reports/THYAO_technical_analysis.json"
    )
    assert captured_pipeline["report_output_path"] == Path(
        "reports/THYAO_technical_analysis.md"
    )
    assert captured_pipeline["generate_sample"] is False

    assert (
        tmp_path
        / "data"
        / "prices"
        / "THYAO.csv"
    ).exists()


def test_run_bist_analysis_uses_custom_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    csv_path = tmp_path / "prices.csv"
    json_path = tmp_path / "result.json"
    report_path = tmp_path / "report.md"

    captured_pipeline: dict[str, object] = {}

    monkeypatch.setattr(
        module,
        "download_bist_prices",
        lambda symbol, period: create_price_data(),
    )

    def fake_pipeline(
        **kwargs: object,
    ) -> dict[str, object]:
        captured_pipeline.update(kwargs)
        return create_analysis_result("ASELS")

    monkeypatch.setattr(
        module,
        "run_pipeline",
        fake_pipeline,
    )

    result = run_bist_analysis(
        symbol="ASELS.IS",
        period="1y",
        csv_output_path=csv_path,
        json_output_path=json_path,
        report_output_path=report_path,
    )

    assert result["symbol"] == "ASELS"
    assert csv_path.exists()
    assert captured_pipeline["input_path"] == csv_path
    assert captured_pipeline["json_output_path"] == json_path
    assert captured_pipeline["report_output_path"] == report_path


def test_main_completes_bist_analysis(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)

    captured_arguments: dict[str, object] = {}

    def fake_run_bist_analysis(
        **kwargs: object,
    ) -> dict[str, object]:
        captured_arguments.update(kwargs)
        return create_analysis_result()

    monkeypatch.setattr(
        module,
        "run_bist_analysis",
        fake_run_bist_analysis,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_bist_analysis.py",
            "THYAO",
            "--period",
            "6mo",
        ],
    )

    exit_code = module.main()
    terminal_output = capsys.readouterr().out

    assert exit_code == 0
    assert captured_arguments["symbol"] == "THYAO"
    assert captured_arguments["period"] == "6mo"

    assert "BAŞARILI" in terminal_output
    assert "Hisse: THYAO" in terminal_output
    assert "Teknik puan: 62.5" in terminal_output
    assert "THYAO.csv" in terminal_output


def test_main_returns_error_for_invalid_symbol(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_bist_analysis.py",
            "THY AO",
        ],
    )

    exit_code = module.main()
    terminal_output = capsys.readouterr().out

    assert exit_code == 1
    assert "HATA" in terminal_output
    assert "Geçersiz hisse kodu" in terminal_output


def test_main_returns_error_when_analysis_fails(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run_bist_analysis(
        **kwargs: object,
    ) -> dict[str, object]:
        raise ValueError("Veri indirilemedi.")

    monkeypatch.setattr(
        module,
        "run_bist_analysis",
        fake_run_bist_analysis,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_bist_analysis.py",
            "THYAO",
        ],
    )

    exit_code = module.main()
    terminal_output = capsys.readouterr().out

    assert exit_code == 1
    assert "HATA: Veri indirilemedi." in terminal_output