from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_INPUT_PATH = (
    PROJECT_ROOT / "reports" / "technical_analysis.json"
)

DEFAULT_OUTPUT_PATH = (
    PROJECT_ROOT / "reports" / "technical_analysis.md"
)


def parse_arguments() -> argparse.Namespace:
    """Komut satırı seçeneklerini tanımlar."""
    parser = argparse.ArgumentParser(
        description=(
            "Teknik analiz JSON sonucunu okunabilir "
            "Markdown raporuna dönüştürür."
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help="Teknik analiz JSON dosyasının yolu.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Oluşturulacak Markdown raporunun yolu.",
    )

    return parser.parse_args()


def load_analysis(file_path: Path) -> dict[str, Any]:
    """Teknik analiz JSON dosyasını okur."""
    if not file_path.exists():
        raise FileNotFoundError(
            f"Teknik analiz dosyası bulunamadı: {file_path}"
        )

    try:
        with file_path.open(
            "r",
            encoding="utf-8",
        ) as input_file:
            data = json.load(input_file)

    except json.JSONDecodeError as error:
        raise ValueError(
            "Teknik analiz dosyası geçerli bir JSON değil. "
            f"Satır: {error.lineno}, sütun: {error.colno}"
        ) from error

    if not isinstance(data, dict):
        raise ValueError(
            "Teknik analiz JSON verisi bir nesne olmalıdır."
        )

    required_fields = {
        "symbol",
        "analysis_date",
        "indicators",
        "technical_analysis",
    }

    missing_fields = required_fields.difference(data)

    if missing_fields:
        missing_text = ", ".join(sorted(missing_fields))

        raise ValueError(
            f"Teknik analiz sonucunda eksik alanlar var: "
            f"{missing_text}"
        )

    return data


def format_number(
    value: Any,
    decimal_places: int = 2,
) -> str:
    """Sayısal değerleri rapor için biçimlendirir."""
    if value is None:
        return "Veri yok"

    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return str(value)

    return f"{numeric_value:.{decimal_places}f}"


def score_label(score: float) -> str:
    """Teknik puanı açıklayıcı etikete dönüştürür."""
    if score >= 80:
        return "Güçlü pozitif"
    if score >= 65:
        return "Pozitif"
    if score >= 50:
        return "Nötr"
    if score >= 35:
        return "Negatif"

    return "Güçlü negatif"


def create_list_section(
    title: str,
    items: list[str],
    empty_message: str,
) -> list[str]:
    """Markdown madde listesi oluşturur."""
    lines = [
        f"## {title}",
        "",
    ]

    if not items:
        lines.extend(
            [
                f"- {empty_message}",
                "",
            ]
        )

        return lines

    for item in items:
        lines.append(f"- {item}")

    lines.append("")

    return lines


def build_markdown_report(
    analysis: dict[str, Any],
) -> str:
    """Teknik analiz sonucundan Markdown raporu üretir."""
    symbol = str(analysis["symbol"]).upper()
    analysis_date = analysis.get("analysis_date")
    price_date = analysis.get("price_date")
    record_count = analysis.get("record_count", 0)

    indicators = analysis.get("indicators", {})
    technical_analysis = analysis.get(
        "technical_analysis",
        {},
    )

    technical_score = float(
        technical_analysis.get(
            "technical_score",
            technical_analysis.get("score", 0),
        )
    )

    signals = technical_analysis.get("signals", [])
    warnings = technical_analysis.get("warnings", [])

    lines = [
        f"# {symbol} Teknik Analiz Raporu",
        "",
        "> Bu rapor test ve araştırma amacıyla "
        "oluşturulmuştur. Kesin yatırım tavsiyesi değildir.",
        "",
        "## Analiz bilgileri",
        "",
        f"- **Hisse:** {symbol}",
        f"- **Analiz tarihi:** {analysis_date or 'Veri yok'}",
        f"- **Son fiyat tarihi:** {price_date or 'Veri yok'}",
        f"- **Kullanılan satır sayısı:** {record_count}",
        "",
        "## Teknik değerlendirme",
        "",
        f"- **Teknik puan:** "
        f"{format_number(technical_score)} / 100",
        f"- **Teknik görünüm:** {score_label(technical_score)}",
        f"- **Veri güven puanı:** "
        f"{format_number(technical_analysis.get('confidence_score'))}",
        "",
        "## Alt puanlar",
        "",
        "| Bileşen | Puan |",
        "|---|---:|",
        "| Trend | "
        f"{format_number(technical_analysis.get('trend_score'))} |",
        "| Momentum | "
        f"{format_number(technical_analysis.get('momentum_score'))} |",
        "| Hacim | "
        f"{format_number(technical_analysis.get('volume_score'))} |",
        "| Volatilite uygunluğu | "
        f"{format_number(technical_analysis.get('volatility_score'))} |",
        "",
        "## Güncel indikatörler",
        "",
        "| İndikatör | Değer |",
        "|---|---:|",
        f"| Kapanış | {format_number(indicators.get('close'))} |",
        f"| SMA 20 | {format_number(indicators.get('sma_20'))} |",
        f"| EMA 20 | {format_number(indicators.get('ema_20'))} |",
        f"| EMA 50 | {format_number(indicators.get('ema_50'))} |",
        f"| RSI 14 | {format_number(indicators.get('rsi_14'))} |",
        f"| MACD | {format_number(indicators.get('macd'), 4)} |",
        f"| MACD sinyal | "
        f"{format_number(indicators.get('macd_signal'), 4)} |",
        f"| MACD histogram | "
        f"{format_number(indicators.get('macd_histogram'), 4)} |",
        f"| Bollinger üst | "
        f"{format_number(indicators.get('bollinger_upper'))} |",
        f"| Bollinger orta | "
        f"{format_number(indicators.get('bollinger_middle'))} |",
        f"| Bollinger alt | "
        f"{format_number(indicators.get('bollinger_lower'))} |",
        f"| ATR 14 | {format_number(indicators.get('atr_14'))} |",
        f"| ADX | {format_number(indicators.get('adx'))} |",
        f"| Pozitif DI | "
        f"{format_number(indicators.get('positive_di'))} |",
        f"| Negatif DI | "
        f"{format_number(indicators.get('negative_di'))} |",
        f"| Göreceli hacim | "
        f"{format_number(indicators.get('relative_volume_20'))} |",
        "",
    ]

    lines.extend(
        create_list_section(
            title="Olumlu ve nötr sinyaller",
            items=signals,
            empty_message="Belirgin teknik sinyal bulunamadı.",
        )
    )

    lines.extend(
        create_list_section(
            title="Riskler ve uyarılar",
            items=warnings,
            empty_message="Teknik uyarı bulunamadı.",
        )
    )

    lines.extend(
        [
            "## Sonuç",
            "",
            (
                f"{symbol} için teknik analiz puanı "
                f"**{format_number(technical_score)} / 100** "
                f"ve görünüm **{score_label(technical_score)}** "
                "olarak hesaplanmıştır."
            ),
            "",
            "Bu sonuç yalnızca teknik verileri kapsar. "
            "Nihai karar için temel analiz, haber akışı, KAP, "
            "makroekonomi, sektör görünümü ve risk motoru da "
            "birlikte değerlendirilmelidir.",
            "",
        ]
    )

    return "\n".join(lines)


def save_report(
    report_text: str,
    output_path: Path,
) -> None:
    """Markdown raporunu dosyaya kaydeder."""
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        report_text,
        encoding="utf-8",
    )


def main() -> int:
    arguments = parse_arguments()

    try:
        analysis = load_analysis(arguments.input)

        report_text = build_markdown_report(
            analysis
        )

        save_report(
            report_text=report_text,
            output_path=arguments.output,
        )

    except (
        FileNotFoundError,
        ValueError,
        TypeError,
    ) as error:
        print(f"HATA: {error}")
        return 1

    print(
        "BAŞARILI: Teknik analiz raporu oluşturuldu.\n"
        f"Hisse: {analysis['symbol']}\n"
        f"Rapor dosyası: {arguments.output}"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
