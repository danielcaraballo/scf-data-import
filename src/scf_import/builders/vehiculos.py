import logging
from typing import Any

import pandas as pd

from scf_import.config import VEHICULO_COLUMN_MAP, VEHICULO_FK_MAP
from scf_import.normalizers import normalize_name, normalize_row

logger = logging.getLogger(__name__)

MAX_VIN_LENGTH = 17

REQUIRED_VEHICULO_FKS = {
    "gerencia",
    "categoria",
    "marca",
    "modelo",
    "estado",
    "emplazamiento",
    "estatus",
    "clase",
    "tipo_combustible",
}

OPTIONAL_VEHICULO_FKS = {
    "unidad_usuaria",
    "color_placa",
    "color",
    "tipo_uso",
}


def _resolve_fk(
    csv_col: str,
    val: str,
    all_lookups: dict[str, dict[str, int]],
) -> int | None:
    fk_info = VEHICULO_FK_MAP[csv_col]
    lookup_key = fk_info["lookup"]
    if not val:
        return None
    source = all_lookups.get(lookup_key, {})
    lookup_val = normalize_name(val)
    return source.get(lookup_val)


def _parse_anio(val: str) -> tuple[int, str | None]:
    if not val:
        return 0, None
    try:
        return int(val), None
    except ValueError:
        return 0, f"anio inválido '{val}'"


def _validate_row(
    i: int,
    numero_economico: str,
    vin: str,
    seen_economico: set[str],
    seen_vin: set[str],
) -> list[str]:
    row_errors: list[str] = []
    if not numero_economico:
        row_errors.append(f"vehiculos fila {i}: numero_economico vacío")
    elif not vin:
        row_errors.append(f"vehiculos fila {i}: vin vacío (numero_economico={numero_economico})")
    elif numero_economico.lower() in seen_economico:
        row_errors.append(f"vehiculos fila {i}: numero_economico duplicado: '{numero_economico}'")
    elif vin.lower() in seen_vin:
        row_errors.append(f"vehiculos fila {i}: vin duplicado: '{vin}'")
    return row_errors


def _process_unidad(
    val: str,
    seen_unidad: set[str],
    i: int,
    errors: list[str],
) -> str | None:
    unidad_raw = val.strip()
    if not unidad_raw:
        return None
    if unidad_raw.lower() in seen_unidad:
        errors.append(
            f"vehiculos fila {i}: numero_unidad '{unidad_raw}' duplicado, seteado a null"
        )
        return None
    seen_unidad.add(unidad_raw.lower())
    return unidad_raw


def _check_placa_color_constraint(
    fields: dict[str, Any],
    seen_placa_color: set[tuple[str, int]],
    i: int,
    errors: list[str],
) -> None:
    if fields.get("placa") and fields.get("color_placa"):
        pair = (str(fields["placa"]).lower(), int(fields["color_placa"]))
        if pair in seen_placa_color:
            fields["placa"] = None
            errors.append(
                f"vehiculos fila {i}: combinación placa+color_placa duplicada, seteada placa=null"
            )
        else:
            seen_placa_color.add(pair)


def _build_single_vehiculo_fields(
    i: int,
    normalized: dict[str, Any],
    all_lookups: dict[str, dict[str, int]],
    seen_unidad: set[str],
    errors: list[str],
) -> dict[str, Any] | None:
    fields: dict[str, Any] = {}
    fk_fields = set(VEHICULO_FK_MAP.keys())

    for csv_col, model_field in VEHICULO_COLUMN_MAP.items():
        val = normalized.get(csv_col, "")

        if csv_col in fk_fields:
            ref = _resolve_fk(csv_col, val, all_lookups)
            if ref is not None:
                fields[model_field] = ref
            elif csv_col in REQUIRED_VEHICULO_FKS:
                lookup_key = VEHICULO_FK_MAP[csv_col]["lookup"]
                errors.append(
                    f"vehiculos fila {i}: FK requerida '{csv_col}' "
                    f"= '{val}' no encontrada en {lookup_key}"
                )
                return None
            else:
                fields[model_field] = None
            continue

        if csv_col == "anio":
            anio_val, anio_err = _parse_anio(val)
            if anio_err:
                errors.append(f"vehiculos fila {i}: {anio_err}")
            fields[model_field] = anio_val
            continue

        if csv_col == "numero_unidad":
            fields[model_field] = _process_unidad(val, seen_unidad, i, errors)
            continue

        if csv_col == "placa":
            placa_raw = val.strip()
            fields[model_field] = placa_raw or None
            continue

        fields[model_field] = val

    return fields


def build_vehiculos(
    df: pd.DataFrame,
    catalog_lookups: dict[str, dict[str, int]],
    org_lookups: dict[str, dict[str, int]],
) -> tuple[list[dict[str, Any]], list[str]]:
    fixtures: list[dict[str, Any]] = []
    errors: list[str] = []
    fk_fields = set(VEHICULO_FK_MAP.keys())
    all_lookups = {**catalog_lookups, **org_lookups}
    pk = 0
    seen_economico: set[str] = set()
    seen_vin: set[str] = set()
    seen_unidad: set[str] = set()
    seen_placa_color: set[tuple[str, int]] = set()

    for i, (_, row) in enumerate(df.iterrows(), start=2):
        raw = {col: str(row.get(col, "")).strip() for col in VEHICULO_COLUMN_MAP}
        normalized = normalize_row(raw, fk_fields)

        numero_economico = normalized.get("numero_economico", "").strip()
        vin = normalized.get("vin", "").strip()

        row_errors = _validate_row(i, numero_economico, vin, seen_economico, seen_vin)
        if row_errors:
            errors.extend(row_errors)
            continue

        if len(vin) > MAX_VIN_LENGTH:
            errors.append(f"vehiculos fila {i}: vin '{vin}' excede 17 caracteres")
            continue

        fields = _build_single_vehiculo_fields(
            i, normalized, all_lookups, seen_unidad, errors
        )
        if fields is None:
            continue

        _check_placa_color_constraint(fields, seen_placa_color, i, errors)

        seen_economico.add(numero_economico.lower())
        seen_vin.add(vin.lower())

        pk += 1
        fields["codigo_qr"] = ""
        fields["estatus_activo"] = True

        fixtures.append(
            {
                "model": "vehiculos.vehiculo",
                "pk": pk,
                "fields": fields,
            }
        )

    return fixtures, errors
