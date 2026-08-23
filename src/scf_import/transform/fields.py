import re
from typing import Any

from scf_import.transform.text import clean_str, normalize_code, parse_number_ve

_DEFAULT_MIN_YEAR = 1950
_DEFAULT_MAX_YEAR = 2026
_DEFAULT_SAP_MIN = 6
_DEFAULT_SAP_MAX = 7
_DEFAULT_VIN_LEN = 17
_MPPEE_PREFIX_LEN = 6

DEFAULT_SAP_NA = {
    "",
    "0",
    "NO POSEE",
    "N0 P0SEE",
    "NO TIENE",
    "S/P",
    "S/N",
    "S/I",
    "N/A",
    "NA",
    "NO APLICA",
    "NONE",
    "NULL",
    "-",
    ".",
    "000000",
    "0000000",
}

DEFAULT_VIN_NA = {
    "",
    "S/P",
    "S/N",
    "S/I",
    "N/A",
    "NA",
    "NO POSEE",
    "N0 P0SEE",
    "NO TIENE",
    "0",
    "-",
    "SIN VIN",
}

DEFAULT_PLACA_NA = {
    "",
    "S/P",
    "S/N",
    "S/I",
    "N/A",
    "NA",
    "NO POSEE",
    "MPPEE-",
    "MPPEE",
    "MPPEE ",
    "-",
}


def normalize_sap(
    val: Any,
    rules: dict[str, Any] | None = None,
) -> tuple[str, list[str]]:
    text = clean_str(val).upper()
    na_patterns = set(rules.get("na_patterns", DEFAULT_SAP_NA)) if rules else DEFAULT_SAP_NA

    if text in na_patterns:
        return "", []

    flags: list[str] = []
    if not text.isdigit():
        flags.append("SAP_NO_NUMERICO")
        return text, flags

    min_digits = int(rules.get("min_digits", _DEFAULT_SAP_MIN)) if rules else _DEFAULT_SAP_MIN
    max_digits = int(rules.get("max_digits", _DEFAULT_SAP_MAX)) if rules else _DEFAULT_SAP_MAX

    if len(text) < min_digits or len(text) > max_digits:
        flags.append("SAP_LONGITUD_SOSPECHOSA")

    return text, flags


def normalize_vin(
    val: Any,
    rules: dict[str, Any] | None = None,
) -> tuple[str, list[str]]:
    text = normalize_code(val)
    na_patterns = set(rules.get("na_patterns", DEFAULT_VIN_NA)) if rules else DEFAULT_VIN_NA

    if text in na_patterns or not text:
        return "", ["VIN_VACIO"]

    flags: list[str] = []
    expected_len = (
        int(rules.get("expected_length", _DEFAULT_VIN_LEN)) if rules else _DEFAULT_VIN_LEN
    )

    if len(text) != expected_len:
        flags.append("VIN_LONGITUD_INVALIDA")

    return text, flags


def normalize_placa(
    val: Any,
    rules: dict[str, Any] | None = None,
) -> tuple[str, list[str]]:
    text = clean_str(val).upper()
    na_patterns = set(rules.get("na_patterns", DEFAULT_PLACA_NA)) if rules else DEFAULT_PLACA_NA

    if text in ("MPPEE-", "MPPEE", "MPPEE "):
        return "", ["PLACA_MPPEE_INCOMPLETA"]

    if text in na_patterns or not text:
        return "", []

    flags: list[str] = []
    if text.startswith("MPPEE-") and len(text) <= _MPPEE_PREFIX_LEN:
        flags.append("PLACA_MPPEE_INCOMPLETA")
        return "", flags

    return text, flags


def normalize_anio(
    val: Any,
    min_year: int = _DEFAULT_MIN_YEAR,
    max_year: int = _DEFAULT_MAX_YEAR,
) -> tuple[int, list[str]]:
    text = clean_str(val)
    if not text:
        return 0, []

    flags: list[str] = []
    if not text.isdigit():
        flags.append("ANIO_INVALIDO")
        return 0, flags

    year = int(text)
    if year < min_year or year > max_year:
        flags.append("ANIO_FUERA_DE_RANGO")

    return year, flags


def normalize_km(val: Any) -> tuple[int | None, list[str]]:
    text = clean_str(val)
    if not text:
        return None, []

    parsed = parse_number_ve(text)
    if parsed is None:
        return None, ["KM_FORMATO_INVALIDO"]

    return int(parsed), []


def normalize_unidad(val: Any) -> tuple[str, list[str]]:
    text = clean_str(val).upper()
    if text in ("S/P", "S/N", "S/I", "N/A", "NA", "0", "-", ""):
        return "", []
    return text, []


def extract_subtype_from_model(model_raw: str) -> tuple[str, str | None]:
    text = clean_str(model_raw)
    match = re.search(r"\(([^)]+)\)", text)
    if match:
        subtype = match.group(1).strip()
        base_model = re.sub(r"\s*\([^)]*\)", "", text).strip()
        return base_model, subtype
    return text, None
