import logging
from typing import Any

import pandas as pd

from scf_import.config import VEHICULO_COLUMN_MAP, VEHICULO_FK_MAP
from scf_import.normalizers import normalize_name, normalize_row

logger = logging.getLogger(__name__)


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

    for i, (_, row) in enumerate(df.iterrows(), start=2):
        raw = {col: str(row.get(col, "")).strip() for col in VEHICULO_COLUMN_MAP}
        normalized = normalize_row(raw, fk_fields)

        numero_economico = normalized.get("numero_economico", "").strip()
        vin = normalized.get("vin", "").strip()

        row_errors = _validate_row(i, numero_economico, vin, seen_economico, seen_vin)
        if row_errors:
            errors.extend(row_errors)
            continue

        seen_economico.add(numero_economico.lower())
        seen_vin.add(vin.lower())

        pk += 1
        fields: dict[str, Any] = {}

        for csv_col, model_field in VEHICULO_COLUMN_MAP.items():
            val = normalized.get(csv_col, "")

            if csv_col in fk_fields:
                ref = _resolve_fk(csv_col, val, all_lookups)
                if ref is not None:
                    fields[model_field] = ref
                elif val:
                    lookup_key = VEHICULO_FK_MAP[csv_col]["lookup"]
                    msg = (
                        f"vehiculos fila {i}: FK '{csv_col}' "
                        f"= '{val}' no encontrado en {lookup_key}"
                    )
                    errors.append(msg)
                continue

            if csv_col == "anio":
                anio_val, anio_err = _parse_anio(val)
                if anio_err:
                    errors.append(f"vehiculos fila {i}: {anio_err}")
                fields[model_field] = anio_val
                continue

            fields[model_field] = val

        fields["estatus_activo"] = True

        fixtures.append(
            {
                "model": "vehiculos.vehiculo",
                "pk": pk,
                "fields": fields,
            }
        )

    return fixtures, errors
