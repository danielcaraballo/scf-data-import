from pathlib import Path

import pandas as pd

_UNSUPPORTED_MSG = "Formato no soportado: {}"


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
