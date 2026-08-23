from typing import Any

import pandas as pd


def _mode_or_first(series: pd.Series) -> str:
    vals = series[series != ""].dropna()
    if vals.empty:
        return ""
    res = vals.mode().iloc[0] if not vals.mode().empty else vals.iloc[0]
    return str(res)


def _add_unique(
    records: list[dict[str, Any]],
    seen: set[str],
    tipo: str,
    nombre: str,
    extra: dict[str, str] | None = None,
) -> None:
    clean = nombre.strip()
    if clean and clean.lower() not in seen:
        seen.add(clean.lower())
        row: dict[str, Any] = {"tipo": tipo, "nombre": clean}
        if extra:
            row.update(extra)
        records.append(row)


def derive_catalogos_df(flota_df: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    seen: set[str] = set()

    for raw in flota_df["marca"].dropna().unique():
        _add_unique(records, seen, "marca", raw, {"marca": "", "sistema": ""})

    modelo_marca = (
        flota_df[["modelo", "marca"]]
        .replace("", pd.NA)
        .dropna(subset=["modelo"])
        .groupby("modelo")["marca"]
        .apply(_mode_or_first)
        .reset_index()
    )
    seen_m: set[str] = set()
    for _, row in modelo_marca.iterrows():
        nombre = str(row["modelo"]).strip()
        marca = str(row["marca"]).strip() if pd.notna(row["marca"]) else ""
        if nombre and marca and nombre.lower() not in seen_m:
            seen_m.add(nombre.lower())
            records.append(
                {"tipo": "modelo", "nombre": nombre, "marca": marca, "sistema": ""}
            )

    seen.clear()
    for raw in flota_df["color"].dropna().unique():
        _add_unique(records, seen, "color", raw, {"marca": "", "sistema": ""})

    seen.clear()
    for raw in flota_df["clase"].dropna().unique():
        _add_unique(records, seen, "clase_vehiculo", raw, {"marca": "", "sistema": ""})

    if "categoria" in flota_df.columns:
        seen.clear()
        for raw in flota_df["categoria"].dropna().unique():
            _add_unique(
                records, seen, "tipo_vehiculo", raw, {"marca": "", "sistema": ""}
            )

    if "tipo_uso" in flota_df.columns:
        seen.clear()
        for raw in flota_df["tipo_uso"].dropna().unique():
            _add_unique(records, seen, "tipo_uso", raw, {"marca": "", "sistema": ""})

    if "estatus" in flota_df.columns:
        seen.clear()
        for raw in flota_df["estatus"].dropna().unique():
            _add_unique(
                records, seen, "estatus_vehiculo", raw, {"marca": "", "sistema": ""}
            )

    if "color_placa" in flota_df.columns:
        seen.clear()
        for raw in flota_df["color_placa"].dropna().unique():
            _add_unique(
                records, seen, "color_placa", raw, {"marca": "", "sistema": ""}
            )

    if "tipo_combustible" in flota_df.columns:
        seen.clear()
        for raw in flota_df["tipo_combustible"].dropna().unique():
            _add_unique(
                records, seen, "tipo_combustible", raw, {"marca": "", "sistema": ""}
            )

    return pd.DataFrame(records)


def derive_organizacion_df(flota_df: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    seen: set[str] = set()

    if "estado" in flota_df.columns:
        for raw in flota_df["estado"].dropna().unique():
            _add_unique(records, seen, "estado", raw, {"estado": ""})

    if "gerencia" in flota_df.columns:
        seen.clear()
        for raw in flota_df["gerencia"].dropna().unique():
            _add_unique(records, seen, "gerencia", raw, {"estado": ""})

    if "emplazamiento" in flota_df.columns:
        empl_estado = (
            flota_df[["emplazamiento", "estado"]]
            .replace("", pd.NA)
            .dropna(subset=["emplazamiento"])
        )
        if not empl_estado.empty:
            grouped = (
                empl_estado.groupby("emplazamiento")["estado"]
                .apply(_mode_or_first)
                .reset_index()
            )
            seen.clear()
            for _, row in grouped.iterrows():
                nombre = str(row["emplazamiento"]).strip()
                estado = str(row["estado"]).strip() if pd.notna(row["estado"]) else ""
                if nombre and nombre.lower() not in seen:
                    seen.add(nombre.lower())
                    records.append(
                        {"tipo": "centro_servicio", "nombre": nombre, "estado": estado}
                    )

    return pd.DataFrame(records)
