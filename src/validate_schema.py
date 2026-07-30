from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "analysis.schema.json"
SAMPLE_PATH = PROJECT_ROOT / "examples" / "sample_analysis.json"


def load_json(file_path: Path) -> dict:
    """Bir JSON dosyasını okuyup sözlük olarak döndürür."""
    try:
        with file_path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"HATA: Dosya bulunamadı: {file_path}")
        raise
    except json.JSONDecodeError as error:
        print(
            f"HATA: Geçersiz JSON: {file_path}\n"
            f"Satır: {error.lineno}, sütun: {error.colno}\n"
            f"Açıklama: {error.msg}"
        )
        raise


def format_error_path(error) -> str:
    """Doğrulama hatasının JSON içindeki konumunu okunabilir hâle getirir."""
    if not error.absolute_path:
        return "root"

    return ".".join(str(part) for part in error.absolute_path)


def validate_analysis() -> bool:
    """Örnek analiz dosyasını JSON şemasına göre doğrular."""
    schema = load_json(SCHEMA_PATH)
    sample_data = load_json(SAMPLE_PATH)

    validator = Draft202012Validator(
        schema=schema,
        format_checker=FormatChecker(),
    )

    errors = sorted(
        validator.iter_errors(sample_data),
        key=lambda error: list(error.absolute_path),
    )

    if not errors:
        print("BAŞARILI: Örnek analiz verisi JSON şemasına uygundur.")
        return True

    print(f"BAŞARISIZ: {len(errors)} doğrulama hatası bulundu.\n")

    for index, error in enumerate(errors, start=1):
        print(f"{index}. Konum: {format_error_path(error)}")
        print(f"   Hata: {error.message}\n")

    return False


def main() -> int:
    try:
        is_valid = validate_analysis()
    except (FileNotFoundError, json.JSONDecodeError):
        return 1

    return 0 if is_valid else 1


if __name__ == "__main__":
    sys.exit(main())
