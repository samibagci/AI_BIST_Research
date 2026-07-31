from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.candidate_selection import (
    DEFAULT_CANDIDATE_THRESHOLD,
    DEFAULT_MAX_CANDIDATES,
    DEFAULT_MAX_STRONG_CANDIDATES,
    DEFAULT_STRONG_THRESHOLD,
    build_markdown_report as build_candidate_report,
    save_json_result,
    save_markdown_report as save_candidate_report,
    select_candidates,
)
from src.run_bist_batch_analysis import (
    build_markdown_report as build_batch_report,
    load_watchlist,
    parse_symbol_inputs,
    run_bist_batch_analysis,
    save_json_summary,
    save_markdown_summary,
)


DEFAULT_WATCHLIST_PATH = Path(
    "config/bist_watchlist.txt"
)
DEFAULT_PRICE_DIRECTORY = Path(
    "data/prices"
)
DEFAULT_REPORT_DIRECTORY = Path(
    "reports"
)


def run_full_analysis(
    symbols: list[str],
    period: str = "1y",
    price_directory: Path = DEFAULT_PRICE_DIRECTORY,
    report_directory: Path = DEFAULT_REPORT_DIRECTORY,
    batch_json_path: Path | None = None,
    batch_report_path: Path | None = None,
    candidate_json_path: Path | None = None,
    candidate_report_path: Path | None = None,
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
    max_strong_candidates: int = (
        DEFAULT_MAX_STRONG_CANDIDATES
    ),
    candidate_threshold: float = (
        DEFAULT_CANDIDATE_THRESHOLD
    ),
    strong_threshold: float = (
        DEFAULT_STRONG_THRESHOLD
    ),
) -> dict[str, object]:
    if batch_json_path is None:
        batch_json_path = (
            report_directory
            / "bist_batch_analysis.json"
        )

    if batch_report_path is None:
        batch_report_path = (
            report_directory
            / "bist_batch_analysis.md"
        )

    if candidate_json_path is None:
        candidate_json_path = (
            report_directory
            / "bist_candidates.json"
        )

    if candidate_report_path is None:
        candidate_report_path = (
            report_directory
            / "bist_candidates.md"
        )

    batch_summary = run_bist_batch_analysis(
        symbols=symbols,
        period=period,
        price_directory=price_directory,
        report_directory=report_directory,
    )

    save_json_summary(
        summary=batch_summary,
        output_path=batch_json_path,
    )

    batch_markdown = build_batch_report(
        batch_summary
    )

    save_markdown_summary(
        markdown_report=batch_markdown,
        output_path=batch_report_path,
    )

    selection_result = select_candidates(
        batch_summary=batch_summary,
        max_candidates=max_candidates,
        max_strong_candidates=max_strong_candidates,
        candidate_threshold=candidate_threshold,
        strong_threshold=strong_threshold,
    )

    save_json_result(
        selection_result=selection_result,
        output_path=candidate_json_path,
    )

    candidate_markdown = build_candidate_report(
        selection_result
    )

    save_candidate_report(
        markdown_report=candidate_markdown,
        output_path=candidate_report_path,
    )

    return {
        "batch_summary": batch_summary,
        "candidate_selection": selection_result,
        "outputs": {
            "batch_json": str(batch_json_path),
            "batch_markdown": str(batch_report_path),
            "candidate_json": str(candidate_json_path),
            "candidate_markdown": str(
                candidate_report_path
            ),
        },
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "BIST hisselerini indirir, teknik analiz eder, "
            "sıralar ve adayları seçer."
        )
    )

    parser.add_argument(
        "symbols",
        nargs="*",
        help=(
            "İsteğe bağlı hisse kodları. "
            "Örnek: THYAO ASELS TUPRS"
        ),
    )

    parser.add_argument(
        "--watchlist",
        type=Path,
        default=DEFAULT_WATCHLIST_PATH,
        help="İzleme listesi dosyasının yolu.",
    )

    parser.add_argument(
        "--period",
        default="1y",
        help="İndirilecek veri dönemi. Varsayılan: 1y",
    )

    parser.add_argument(
        "--price-directory",
        type=Path,
        default=DEFAULT_PRICE_DIRECTORY,
        help="Fiyat CSV dosyalarının kaydedileceği klasör.",
    )

    parser.add_argument(
        "--report-directory",
        type=Path,
        default=DEFAULT_REPORT_DIRECTORY,
        help="Rapor dosyalarının kaydedileceği klasör.",
    )

    parser.add_argument(
        "--batch-json-output",
        type=Path,
        default=None,
        help="Toplu analiz JSON dosyasının yolu.",
    )

    parser.add_argument(
        "--batch-report-output",
        type=Path,
        default=None,
        help="Toplu analiz Markdown raporunun yolu.",
    )

    parser.add_argument(
        "--candidate-json-output",
        type=Path,
        default=None,
        help="Aday seçim JSON dosyasının yolu.",
    )

    parser.add_argument(
        "--candidate-report-output",
        type=Path,
        default=None,
        help="Aday seçim Markdown raporunun yolu.",
    )

    parser.add_argument(
        "--max-candidates",
        type=int,
        default=DEFAULT_MAX_CANDIDATES,
        help="Maksimum aday sayısı. Varsayılan: 5",
    )

    parser.add_argument(
        "--max-strong-candidates",
        type=int,
        default=DEFAULT_MAX_STRONG_CANDIDATES,
        help="Maksimum güçlü aday sayısı. Varsayılan: 3",
    )

    parser.add_argument(
        "--candidate-threshold",
        type=float,
        default=DEFAULT_CANDIDATE_THRESHOLD,
        help="Aday puan eşiği. Varsayılan: 50",
    )

    parser.add_argument(
        "--strong-threshold",
        type=float,
        default=DEFAULT_STRONG_THRESHOLD,
        help="Güçlü aday puan eşiği. Varsayılan: 60",
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        if arguments.symbols:
            symbols = parse_symbol_inputs(
                arguments.symbols
            )
        else:
            symbols = load_watchlist(
                arguments.watchlist
            )

        result = run_full_analysis(
            symbols=symbols,
            period=arguments.period,
            price_directory=arguments.price_directory,
            report_directory=arguments.report_directory,
            batch_json_path=arguments.batch_json_output,
            batch_report_path=arguments.batch_report_output,
            candidate_json_path=(
                arguments.candidate_json_output
            ),
            candidate_report_path=(
                arguments.candidate_report_output
            ),
            max_candidates=arguments.max_candidates,
            max_strong_candidates=(
                arguments.max_strong_candidates
            ),
            candidate_threshold=(
                arguments.candidate_threshold
            ),
            strong_threshold=arguments.strong_threshold,
        )

        batch_summary = result["batch_summary"]
        selection_result = result[
            "candidate_selection"
        ]
        outputs = result["outputs"]

        if not isinstance(batch_summary, dict):
            raise ValueError(
                "Toplu analiz sonucu kullanılamıyor."
            )

        if not isinstance(selection_result, dict):
            raise ValueError(
                "Aday seçim sonucu kullanılamıyor."
            )

        if not isinstance(outputs, dict):
            raise ValueError(
                "Çıktı yolları kullanılamıyor."
            )

        success_count = int(
            batch_summary["success_count"]
        )
        failure_count = int(
            batch_summary["failure_count"]
        )
        candidate_count = int(
            selection_result["candidate_count"]
        )
        strong_candidate_count = int(
            selection_result[
                "strong_candidate_count"
            ]
        )

        if success_count == 0:
            print(
                "HATA: Hiçbir hisse analiz edilemedi."
            )
            return 1

        print(
            "BAŞARILI: Tam BIST analiz işlemi tamamlandı."
        )
        print(
            f"Başarılı analiz: {success_count}"
        )
        print(
            f"Başarısız analiz: {failure_count}"
        )
        print(
            f"Seçilen aday: {candidate_count}"
        )
        print(
            f"Güçlü aday: {strong_candidate_count}"
        )

        candidates = selection_result["candidates"]

        if isinstance(candidates, list) and candidates:
            top_candidate = candidates[0]

            if isinstance(top_candidate, dict):
                print(
                    f"En yüksek aday: "
                    f"{top_candidate['symbol']} - "
                    f"{top_candidate['technical_score']}"
                )

        print(
            f"Toplu analiz raporu: "
            f"{Path(str(outputs['batch_markdown'])).resolve()}"
        )
        print(
            f"Aday seçim raporu: "
            f"{Path(str(outputs['candidate_markdown'])).resolve()}"
        )

        return 0

    except Exception as error:
        print(f"HATA: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())