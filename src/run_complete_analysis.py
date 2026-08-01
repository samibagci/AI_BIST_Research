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
)
from src.combined_candidate_selection import (
    build_markdown_report as build_final_candidate_report,
    save_json_result as save_final_candidate_json,
    save_markdown_report as save_final_candidate_report,
    select_combined_candidates,
)
from src.combined_scoring import (
    DEFAULT_FUNDAMENTAL_WEIGHT,
    DEFAULT_TECHNICAL_WEIGHT,
    build_markdown_report as build_combined_report,
    combine_analysis_summaries,
    save_json_result as save_combined_json,
    save_markdown_report as save_combined_report,
)
from src.run_bist_batch_analysis import (
    load_watchlist,
    parse_symbol_inputs,
)
from src.run_full_analysis import run_full_analysis
from src.run_fundamental_batch_analysis import (
    build_markdown_report as build_fundamental_report,
    run_fundamental_batch_analysis,
    save_json_summary as save_fundamental_json,
    save_markdown_summary as save_fundamental_report,
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


def run_complete_analysis(
    symbols: list[str],
    period: str = "1y",
    price_directory: Path = DEFAULT_PRICE_DIRECTORY,
    report_directory: Path = DEFAULT_REPORT_DIRECTORY,
    technical_weight: float = DEFAULT_TECHNICAL_WEIGHT,
    fundamental_weight: float = DEFAULT_FUNDAMENTAL_WEIGHT,
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
    fundamental_json_path: Path | None = None,
    fundamental_report_path: Path | None = None,
    combined_json_path: Path | None = None,
    combined_report_path: Path | None = None,
    final_candidate_json_path: Path | None = None,
    final_candidate_report_path: Path | None = None,
) -> dict[str, object]:
    if not symbols:
        raise ValueError(
            "En az bir hisse kodu girilmelidir."
        )

    report_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    technical_batch_json_path = (
        report_directory
        / "bist_batch_analysis.json"
    )

    technical_batch_report_path = (
        report_directory
        / "bist_batch_analysis.md"
    )

    technical_candidate_json_path = (
        report_directory
        / "bist_candidates.json"
    )

    technical_candidate_report_path = (
        report_directory
        / "bist_candidates.md"
    )

    if fundamental_json_path is None:
        fundamental_json_path = (
            report_directory
            / "bist_fundamental_batch_analysis.json"
        )

    if fundamental_report_path is None:
        fundamental_report_path = (
            report_directory
            / "bist_fundamental_batch_analysis.md"
        )

    if combined_json_path is None:
        combined_json_path = (
            report_directory
            / "bist_combined_analysis.json"
        )

    if combined_report_path is None:
        combined_report_path = (
            report_directory
            / "bist_combined_analysis.md"
        )

    if final_candidate_json_path is None:
        final_candidate_json_path = (
            report_directory
            / "bist_combined_candidates.json"
        )

    if final_candidate_report_path is None:
        final_candidate_report_path = (
            report_directory
            / "bist_combined_candidates.md"
        )

    technical_result = run_full_analysis(
        symbols=symbols,
        period=period,
        price_directory=price_directory,
        report_directory=report_directory,
        batch_json_path=technical_batch_json_path,
        batch_report_path=technical_batch_report_path,
        candidate_json_path=technical_candidate_json_path,
        candidate_report_path=technical_candidate_report_path,
        max_candidates=max_candidates,
        max_strong_candidates=max_strong_candidates,
        candidate_threshold=candidate_threshold,
        strong_threshold=strong_threshold,
    )

    technical_summary = technical_result.get(
        "batch_summary"
    )

    if not isinstance(technical_summary, dict):
        raise ValueError(
            "Teknik analiz sonucu kullanılamıyor."
        )

    fundamental_summary = (
        run_fundamental_batch_analysis(
            symbols=symbols,
            report_directory=report_directory,
        )
    )

    save_fundamental_json(
        summary=fundamental_summary,
        output_path=fundamental_json_path,
    )

    fundamental_markdown = (
        build_fundamental_report(
            fundamental_summary
        )
    )

    save_fundamental_report(
        markdown_report=fundamental_markdown,
        output_path=fundamental_report_path,
    )

    combined_summary = combine_analysis_summaries(
        technical_summary=technical_summary,
        fundamental_summary=fundamental_summary,
        technical_weight=technical_weight,
        fundamental_weight=fundamental_weight,
    )

    save_combined_json(
        combined_summary=combined_summary,
        output_path=combined_json_path,
    )

    combined_markdown = build_combined_report(
        combined_summary
    )

    save_combined_report(
        markdown_report=combined_markdown,
        output_path=combined_report_path,
    )

    final_candidate_selection = (
        select_combined_candidates(
            combined_summary=combined_summary,
            max_candidates=max_candidates,
            max_strong_candidates=(
                max_strong_candidates
            ),
            candidate_threshold=candidate_threshold,
            strong_threshold=strong_threshold,
        )
    )

    save_final_candidate_json(
        selection_result=final_candidate_selection,
        output_path=final_candidate_json_path,
    )

    final_candidate_markdown = (
        build_final_candidate_report(
            final_candidate_selection
        )
    )

    save_final_candidate_report(
        markdown_report=final_candidate_markdown,
        output_path=final_candidate_report_path,
    )

    return {
        "technical_analysis": technical_result,
        "fundamental_analysis": fundamental_summary,
        "combined_analysis": combined_summary,
        "final_candidate_selection": (
            final_candidate_selection
        ),
        "outputs": {
            "technical_batch_json": str(
                technical_batch_json_path
            ),
            "technical_batch_markdown": str(
                technical_batch_report_path
            ),
            "technical_candidates_json": str(
                technical_candidate_json_path
            ),
            "technical_candidates_markdown": str(
                technical_candidate_report_path
            ),
            "fundamental_json": str(
                fundamental_json_path
            ),
            "fundamental_markdown": str(
                fundamental_report_path
            ),
            "combined_json": str(
                combined_json_path
            ),
            "combined_markdown": str(
                combined_report_path
            ),
            "final_candidates_json": str(
                final_candidate_json_path
            ),
            "final_candidates_markdown": str(
                final_candidate_report_path
            ),
        },
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "BIST hisseleri için teknik analiz, "
            "temel analiz, birleşik puanlama ve "
            "nihai aday seçimini tek komutta çalıştırır."
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
        help=(
            "Teknik analiz için indirilecek "
            "fiyat dönemi. Varsayılan: 1y"
        ),
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
        help="Raporların kaydedileceği klasör.",
    )

    parser.add_argument(
        "--technical-weight",
        type=float,
        default=DEFAULT_TECHNICAL_WEIGHT,
        help="Teknik analiz ağırlığı. Varsayılan: 0.55",
    )

    parser.add_argument(
        "--fundamental-weight",
        type=float,
        default=DEFAULT_FUNDAMENTAL_WEIGHT,
        help="Temel analiz ağırlığı. Varsayılan: 0.45",
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
        help=(
            "Maksimum güçlü aday sayısı. "
            "Varsayılan: 3"
        ),
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
        help=(
            "Güçlü aday puan eşiği. "
            "Varsayılan: 60"
        ),
    )

    parser.add_argument(
        "--fundamental-json-output",
        type=Path,
        default=None,
        help="Toplu temel analiz JSON dosyasının yolu.",
    )

    parser.add_argument(
        "--fundamental-report-output",
        type=Path,
        default=None,
        help=(
            "Toplu temel analiz Markdown "
            "raporunun yolu."
        ),
    )

    parser.add_argument(
        "--combined-json-output",
        type=Path,
        default=None,
        help="Birleşik analiz JSON dosyasının yolu.",
    )

    parser.add_argument(
        "--combined-report-output",
        type=Path,
        default=None,
        help=(
            "Birleşik analiz Markdown "
            "raporunun yolu."
        ),
    )

    parser.add_argument(
        "--final-candidate-json-output",
        type=Path,
        default=None,
        help="Nihai aday JSON dosyasının yolu.",
    )

    parser.add_argument(
        "--final-candidate-report-output",
        type=Path,
        default=None,
        help="Nihai aday Markdown raporunun yolu.",
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

        result = run_complete_analysis(
            symbols=symbols,
            period=arguments.period,
            price_directory=arguments.price_directory,
            report_directory=arguments.report_directory,
            technical_weight=arguments.technical_weight,
            fundamental_weight=(
                arguments.fundamental_weight
            ),
            max_candidates=arguments.max_candidates,
            max_strong_candidates=(
                arguments.max_strong_candidates
            ),
            candidate_threshold=(
                arguments.candidate_threshold
            ),
            strong_threshold=arguments.strong_threshold,
            fundamental_json_path=(
                arguments.fundamental_json_output
            ),
            fundamental_report_path=(
                arguments.fundamental_report_output
            ),
            combined_json_path=(
                arguments.combined_json_output
            ),
            combined_report_path=(
                arguments.combined_report_output
            ),
            final_candidate_json_path=(
                arguments.final_candidate_json_output
            ),
            final_candidate_report_path=(
                arguments.final_candidate_report_output
            ),
        )

        technical_result = result.get(
            "technical_analysis"
        )
        fundamental_summary = result.get(
            "fundamental_analysis"
        )
        combined_summary = result.get(
            "combined_analysis"
        )
        final_candidate_selection = result.get(
            "final_candidate_selection"
        )
        outputs = result.get("outputs")

        if not isinstance(technical_result, dict):
            raise ValueError(
                "Teknik analiz sonucu kullanılamıyor."
            )

        if not isinstance(fundamental_summary, dict):
            raise ValueError(
                "Temel analiz sonucu kullanılamıyor."
            )

        if not isinstance(combined_summary, dict):
            raise ValueError(
                "Birleşik analiz sonucu kullanılamıyor."
            )

        if not isinstance(
            final_candidate_selection,
            dict,
        ):
            raise ValueError(
                "Nihai aday sonucu kullanılamıyor."
            )

        if not isinstance(outputs, dict):
            raise ValueError(
                "Çıktı yolları kullanılamıyor."
            )

        technical_summary = technical_result.get(
            "batch_summary"
        )
        technical_candidate_selection = (
            technical_result.get(
                "candidate_selection"
            )
        )

        if not isinstance(technical_summary, dict):
            raise ValueError(
                "Toplu teknik analiz sonucu kullanılamıyor."
            )

        if not isinstance(
            technical_candidate_selection,
            dict,
        ):
            raise ValueError(
                "Teknik aday sonucu kullanılamıyor."
            )

        technical_success_count = int(
            technical_summary["success_count"]
        )

        fundamental_success_count = int(
            fundamental_summary["success_count"]
        )

        combined_count = int(
            combined_summary["combined_count"]
        )

        technical_candidate_count = int(
            technical_candidate_selection[
                "candidate_count"
            ]
        )

        technical_strong_candidate_count = int(
            technical_candidate_selection[
                "strong_candidate_count"
            ]
        )

        final_candidate_count = int(
            final_candidate_selection[
                "candidate_count"
            ]
        )

        final_strong_candidate_count = int(
            final_candidate_selection[
                "strong_candidate_count"
            ]
        )

        if combined_count == 0:
            print(
                "HATA: Teknik ve temel analiz sonuçları "
                "birleştirilemedi."
            )
            return 1

        print(
            "BAŞARILI: Tam kapsamlı BIST analizi tamamlandı."
        )
        print(
            f"Teknik analiz: {technical_success_count}"
        )
        print(
            f"Temel analiz: {fundamental_success_count}"
        )
        print(
            f"Birleşik analiz: {combined_count}"
        )
        print(
            f"Teknik aday: {technical_candidate_count}"
        )
        print(
            "Güçlü teknik aday: "
            f"{technical_strong_candidate_count}"
        )
        print(
            f"Nihai aday: {final_candidate_count}"
        )
        print(
            "Güçlü nihai aday: "
            f"{final_strong_candidate_count}"
        )

        final_candidates = (
            final_candidate_selection.get(
                "candidates"
            )
        )

        if (
            isinstance(final_candidates, list)
            and final_candidates
        ):
            top_candidate = final_candidates[0]

            if isinstance(top_candidate, dict):
                print(
                    f"En yüksek nihai aday: "
                    f"{top_candidate['symbol']} - "
                    f"{top_candidate['combined_score']}"
                )

        print(
            f"Teknik analiz raporu: "
            f"{Path(str(outputs['technical_batch_markdown'])).resolve()}"
        )
        print(
            f"Temel analiz raporu: "
            f"{Path(str(outputs['fundamental_markdown'])).resolve()}"
        )
        print(
            f"Birleşik analiz raporu: "
            f"{Path(str(outputs['combined_markdown'])).resolve()}"
        )
        print(
            f"Nihai aday raporu: "
            f"{Path(str(outputs['final_candidates_markdown'])).resolve()}"
        )

        return 0

    except Exception as error:
        print(f"HATA: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())