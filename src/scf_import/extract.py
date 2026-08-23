import csv
import logging
import re
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from scf_import.config import FLOTA_COLUMN_MAP

logger = logging.getLogger(__name__)

_UNSUPPORTED_MSG = "Formato no soportado: {}"
_NA_PATTERNS = {"s/p", "s/n", "s/i", "n/a"}


def clean_header(name: str) -> str:
    name = str(name).strip().strip("\ufeff").strip('"')
    name = re.sub(r"\s*\([^)]*\)", "", name)
    name = re.sub(r"[^\w\s/-]", "", name)
    name = name.strip()
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", name).strip().upper()


def clean_na_value(val: Any) -> str:
    if val is None:
        return ""
    text = str(val).strip()
    return "" if text.lower() in _NA_PATTERNS else text


def extract_date_from_filename(filename: str) -> str:
    match = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
    if match:
        return match.group(1)
    match_digits = re.search(r"(\d{8})", filename)
    if match_digits:
        d = match_digits.group(1)
        return f"{d[:4]}-{d[4:6]}-{d[6:]}"
    return datetime.now(UTC).date().isoformat()


def detect_delimiter(file_path: Path) -> str:
    with file_path.open("r", encoding="utf-8", errors="ignore") as f:
        sample = "".join(f.readline() for _ in range(5))
    try:
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample, delimiters=";,|\t")
    except (csv.Error, TypeError, ValueError):
        semi_count = sample.count(";")
        comma_count = sample.count(",")
        return ";" if semi_count >= comma_count else ","
    else:
        return dialect.delimiter


def find_latest_flota_file(dir_path: Path) -> Path:
    candidates = list(dir_path.glob("flota*.[cC][sS][vV]")) + list(
        dir_path.glob("flota*.[xX][lL][sS][xX]")
    )
    if not candidates:
        msg = f"No se encontraron archivos de flota en: {dir_path}"
        raise FileNotFoundError(msg)

    def sort_key(p: Path) -> tuple[str, float]:
        d = extract_date_from_filename(p.name)
        return (d, p.stat().st_mtime)

    candidates.sort(key=sort_key, reverse=True)
    return candidates[0]


def extract_flota(file_path: Path) -> tuple[pd.DataFrame, str]:
    file_date = extract_date_from_filename(file_path.name)
    ext = file_path.suffix.lower()

    if ext == ".csv":
        sep = detect_delimiter(file_path)
        logger.debug("Leyendo CSV %s con separador '%s'", file_path, sep)
        df = pd.read_csv(file_path, sep=sep, dtype=str, keep_default_na=False, encoding="utf-8")
    elif ext in (".xls", ".xlsx"):
        df = pd.read_excel(file_path, dtype=str, keep_default_na=False)
    else:
        raise ValueError(_UNSUPPORTED_MSG.format(ext))

    renamed: dict[str, str | None] = {}
    for col in df.columns:
        cleaned = clean_header(col)
        if cleaned in FLOTA_COLUMN_MAP:
            renamed[col] = FLOTA_COLUMN_MAP[cleaned]
        else:
            renamed[col] = None

    df = df.rename(columns={k: v for k, v in renamed.items() if v is not None})
    keep_cols = [c for c in df.columns if c in FLOTA_COLUMN_MAP.values()]
    df = df.loc[:, keep_cols]

    for col in df.columns:
        df[col] = df[col].apply(clean_na_value)

    return df, file_date


def read_input(path: Path) -> pd.DataFrame:
    ext = path.suffix.lower()
    if ext == ".csv":
        return pd.read_csv(path, dtype=str, keep_default_na=False)
    if ext in (".xls", ".xlsx"):
        return pd.read_excel(path, dtype=str, keep_default_na=False)
    raise ValueError(_UNSUPPORTED_MSG.format(ext))


def _check_columns(df: pd.DataFrame, required: set[str], name: str) -> None:
    missing = required - set(df.columns)
    if missing:
        msg = f"{name}: faltan columnas: {missing}"
        raise ValueError(msg)


def read_catalogos(path: Path) -> pd.DataFrame:
    df = read_input(path)
    _check_columns(df, {"tipo", "nombre"}, "catalogos.csv")
    return df


def read_organizacion(path: Path) -> pd.DataFrame:
    df = read_input(path)
    _check_columns(df, {"tipo", "nombre"}, "organizacion.csv")
    return df


def read_vehiculos(path: Path) -> pd.DataFrame:
    df = read_input(path)
    _check_columns(df, {"numero_economico", "vin", "marca", "modelo"}, "vehiculos.csv")
    return df


def read_flota(path: Path) -> pd.DataFrame:
    df, _ = extract_flota(path)
    if "numero_economico" in df.columns:
        df["numero_economico"] = df["numero_economico"].replace(
            ["0", "NO POSEE", "N0 P0SEE", "S/P", "S/N", "S/I", "N/A"], ""
        )
    if "unidad_usuaria" in df.columns and "gerencia" in df.columns:
        df["unidad_usuaria"] = df["gerencia"]
    return df
