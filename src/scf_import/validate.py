from collections import defaultdict
from typing import Any

from scf_import.transform.row import NormalizedRow


def _index_business_keys(
    rows: list[NormalizedRow],
) -> dict[str, dict[str, list[int]]]:
    indices: dict[str, dict[str, list[int]]] = {
        "sap": defaultdict(list),
        "vin": defaultdict(list),
        "placa": defaultdict(list),
    }

    for i, row in enumerate(rows):
        sap = str(row.canonical.get("numero_economico", "")).strip()
        vin = str(row.canonical.get("vin", "")).strip().upper()
        placa = str(row.canonical.get("placa", "")).strip().upper()

        if sap:
            indices["sap"][sap].append(i)
        if vin:
            indices["vin"][vin].append(i)
        if placa:
            indices["placa"][placa].append(i)

    return indices


def _check_duplicates(
    row: NormalizedRow,
    i: int,
    rows: list[NormalizedRow],
    key_indices: dict[str, dict[str, list[int]]],
) -> None:
    c = row.canonical
    sap = str(c.get("numero_economico", "")).strip()
    vin = str(c.get("vin", "")).strip().upper()
    placa = str(c.get("placa", "")).strip().upper()

    sap_indices = key_indices["sap"]
    vin_indices = key_indices["vin"]
    placa_indices = key_indices["placa"]

    if sap and len(sap_indices[sap]) > 1:
        other_rows = [rows[idx].row_id for idx in sap_indices[sap] if idx != i]
        row.warnings.append(f"SAP duplicado '{sap}' (en filas {other_rows})")
        if "SAP_DUPLICADO" not in row.flags:
            row.flags.append("SAP_DUPLICADO")

    if vin and len(vin_indices[vin]) > 1:
        other_rows = [rows[idx].row_id for idx in vin_indices[vin] if idx != i]
        row.warnings.append(f"VIN duplicado '{vin}' (en filas {other_rows})")
        if "VIN_DUPLICADO" not in row.flags:
            row.flags.append("VIN_DUPLICADO")

    if placa and len(placa_indices[placa]) > 1:
        other_rows = [rows[idx].row_id for idx in placa_indices[placa] if idx != i]
        row.warnings.append(f"Placa duplicada '{placa}' (en filas {other_rows})")
        if "PLACA_DUPLICADA" not in row.flags:
            row.flags.append("PLACA_DUPLICADA")


def _check_required_and_identifiers(
    row: NormalizedRow,
    required_fields: list[str],
) -> None:
    c = row.canonical
    sap = str(c.get("numero_economico", "")).strip()
    vin = str(c.get("vin", "")).strip().upper()
    placa = str(c.get("placa", "")).strip().upper()

    for field_name in required_fields:
        val = str(c.get(field_name, "")).strip()
        if not val:
            row.errors.append(f"Campo requerido '{field_name}' está vacío")
            if "CAMPO_REQUERIDO_VACIO" not in row.flags:
                row.flags.append("CAMPO_REQUERIDO_VACIO")

    if not sap and not vin and not placa:
        row.errors.append("Sin identificador: fila no posee SAP, VIN ni Placa")
        if "SIN_IDENTIFICADOR" not in row.flags:
            row.flags.append("SIN_IDENTIFICADOR")


def validate_batch(
    rows: list[NormalizedRow],
    rules: dict[str, Any] | None = None,
) -> list[NormalizedRow]:
    rules = rules or {}
    fields_rules = rules.get("fields", {})
    required_fields: list[str] = fields_rules.get("required", ["marca", "modelo", "estado"])

    key_indices = _index_business_keys(rows)

    for i, row in enumerate(rows):
        _check_required_and_identifiers(row, required_fields)
        _check_duplicates(row, i, rows, key_indices)

        if row.errors:
            row.quality = "INVALIDO"
        elif row.warnings or row.flags:
            row.quality = "ADVERTENCIA"
        else:
            row.quality = "OK"

    return rows


# Backward compatibility for legacy tests
def validate_required_fields(
    entity_type: str,
    records: list[dict[str, Any]],
    required: list[str],
) -> list[str]:
    errors = []
    for i, rec in enumerate(records, start=2):
        fields = rec.get("fields", {})
        for field in required:
            val = fields.get(field)
            if val is None or (isinstance(val, str) and not val.strip()):
                errors.append(f"{entity_type} fila {i}: '{field}' está vacío")
    return errors
