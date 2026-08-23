import csv
import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

from scf_import.builders.catalogos import build_catalogos
from scf_import.builders.organizacion import build_organizacion
from scf_import.builders.vehiculos import build_vehiculos
from scf_import.derived import derive_catalogos_df, derive_organizacion_df
from scf_import.transform.canonical import CanonicalMapper
from scf_import.transform.row import NormalizedRow

logger = logging.getLogger(__name__)

EXCEL_COLUMNS = [
    "numero_economico",
    "vin",
    "placa",
    "color_placa",
    "placa_intt",
    "serial_motor",
    "numero_unidad",
    "marca",
    "modelo",
    "subtipo",
    "clase",
    "categoria",
    "anio",
    "color",
    "tipo_combustible",
    "tipo_aceite",
    "litros_aceite",
    "estatus",
    "tipo_uso",
    "estado",
    "gerencia",
    "unidad_usuaria",
    "emplazamiento",
    "kilometraje",
    "observaciones",
    "observacion_estatus",
]

MASTER_COLUMNS = [
    "numero_economico",
    "vin",
    "placa",
    "color_placa",
    "placa_intt",
    "serial_motor",
    "numero_unidad",
    "marca",
    "modelo",
    "subtipo",
    "clase",
    "categoria",
    "anio",
    "color",
    "tipo_combustible",
    "tipo_aceite",
    "litros_aceite",
    "estatus",
    "tipo_uso",
    "estado",
    "gerencia",
    "unidad_usuaria",
    "emplazamiento",
    "kilometraje",
    "calidad",
    "flags",
    "errores",
    "advertencias",
    "observaciones",
    "observacion_estatus",
]

REVISION_COLUMNS = [
    "fila_origen",
    "campo_afectado",
    "tipo_problema",
    "valor_original",
    "valor_normalizado",
    "sugerencia_o_detalle",
    "sap",
    "vin",
    "placa",
]

_STATIC_REVISION_MAP: dict[str, tuple[str, str, str, str]] = {
    "MARCA_DESCONOCIDA": (
        "marca",
        "marca",
        "marca",
        "Marca no presente en config/mappings/marcas.csv",
    ),
    "MODELO_DESCONOCIDO": (
        "modelo",
        "modelo",
        "modelo",
        "Modelo no presente en config/mappings/modelos.csv",
    ),
    "EMPLAZAMIENTO_DESCONOCIDO": (
        "emplazamiento",
        "emplazamiento",
        "emplazamiento",
        "Emplazamiento no presente en config/mappings/emplazamientos.csv",
    ),
    "VIN_VACIO": ("vin", "vin", "", "VIN ausente o no disponible"),
    "PLACA_MPPEE_INCOMPLETA": ("placa", "placa", "", "Prefijo MPPEE- sin número de placa"),
    "ANIO_FUERA_DE_RANGO": ("anio", "anio", "anio", "Año fuera del rango permitido"),
    "KM_FORMATO_INVALIDO": (
        "kilometraje",
        "kilometraje",
        "",
        "Formato numérico de kilometraje inválido",
    ),
    "SIN_IDENTIFICADOR": (
        "identificadores",
        "",
        "",
        "Fila sin ningún identificador de negocio",
    ),
    "SAP_NO_NUMERICO": (
        "numero_economico",
        "numero_economico",
        "numero_economico",
        "SAP contiene caracteres no numéricos",
    ),
}


def write_normalized_csv(path: Path, rows: list[NormalizedRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MASTER_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_master_dict())
    logger.info("CSV maestro normalizado guardado en: %s (%d filas)", path, len(rows))


def write_normalized_excel(path: Path, rows: list[NormalizedRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    records = [row.canonical for row in rows]
    df = pd.DataFrame(records)
    for col in EXCEL_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[EXCEL_COLUMNS]
    df.to_excel(path, index=False, engine="openpyxl")
    logger.info("Excel maestro normalizado guardado en: %s (%d filas)", path, len(rows))


def _resolve_revision_entry(
    flag: str,
    row: NormalizedRow,
) -> tuple[str, str, str, str]:
    if flag in _STATIC_REVISION_MAP:
        campo, orig_key, norm_key, detalle = _STATIC_REVISION_MAP[flag]
        val_orig = row.raw_data.get(orig_key, "") if orig_key else "SAP/VIN/Placa vacíos"
        val_norm = str(row.canonical.get(norm_key, "")) if norm_key else ""
        return campo, val_orig, val_norm, detalle

    if flag == "VIN_LONGITUD_INVALIDA":
        val_norm = str(row.canonical.get("vin", ""))
        return "vin", row.raw_data.get("vin", ""), val_norm, f"Longitud {len(val_norm)} != 17"

    if flag == "SAP_LONGITUD_SOSPECHOSA":
        val_norm = str(row.canonical.get("numero_economico", ""))
        return (
            "numero_economico",
            row.raw_data.get("numero_economico", ""),
            val_norm,
            f"Longitud {len(val_norm)} sospechosa (esperado 6-7 dígitos)",
        )

    if flag in ("SAP_DUPLICADO", "VIN_DUPLICADO", "PLACA_DUPLICADA"):
        campo = flag.split("_", maxsplit=1)[0].lower()
        key_field = "numero_economico" if campo == "sap" else campo
        return (
            campo,
            row.raw_data.get(key_field, ""),
            str(row.canonical.get(key_field, "")),
            f"Clave de negocio duplicada ({flag})",
        )

    if flag == "CAMPO_REQUERIDO_VACIO":
        return "requeridos", "", "", "; ".join(row.errors)

    return "general", "", "", flag


def write_revision_csv(
    path: Path,
    rows: list[NormalizedRow],
    _mapper: CanonicalMapper | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    revision_records: list[dict[str, Any]] = []

    for row in rows:
        sap = str(row.canonical.get("numero_economico", ""))
        vin = str(row.canonical.get("vin", ""))
        placa = str(row.canonical.get("placa", ""))

        for flag in row.flags:
            campo, val_orig, val_norm, detalle = _resolve_revision_entry(flag, row)
            revision_records.append(
                {
                    "fila_origen": row.row_id,
                    "campo_afectado": campo,
                    "tipo_problema": flag,
                    "valor_original": val_orig,
                    "valor_normalizado": val_norm,
                    "sugerencia_o_detalle": detalle,
                    "sap": sap,
                    "vin": vin,
                    "placa": placa,
                }
            )

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=REVISION_COLUMNS)
        writer.writeheader()
        for rec in revision_records:
            writer.writerow(rec)

    logger.info("CSV de revisión guardado en: %s (%d observaciones)", path, len(revision_records))


def write_fixture_file(path: Path, fixtures: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(fixtures, f, ensure_ascii=False, indent=2)


def build_django_fixtures(
    rows: list[NormalizedRow],
    output_dir: Path,
) -> dict[str, int]:
    records = [r.canonical for r in rows]
    df = pd.DataFrame(records)

    catalogos_df = derive_catalogos_df(df)
    organizacion_df = derive_organizacion_df(df)

    cat_fixtures, catalog_lookups, cat_errors = build_catalogos(catalogos_df)
    org_fixtures, org_lookups, org_errors = build_organizacion(organizacion_df, catalog_lookups)
    veh_fixtures, veh_errors = build_vehiculos(df, catalog_lookups, org_lookups)

    fixture_dir = output_dir / "fixtures"
    fixture_dir.mkdir(parents=True, exist_ok=True)

    write_fixture_file(fixture_dir / "01_catalogos.json", cat_fixtures)
    write_fixture_file(fixture_dir / "02_organizacion.json", org_fixtures)
    write_fixture_file(fixture_dir / "03_vehiculos.json", veh_fixtures)

    logger.info(
        "Fixtures Django generadas en %s (Catálogos: %d, Org: %d, Vehículos: %d)",
        fixture_dir,
        len(cat_fixtures),
        len(org_fixtures),
        len(veh_fixtures),
    )

    if cat_errors or org_errors or veh_errors:
        logger.warning(
            "Errores en fixtures: %d catálogos, %d org, %d vehículos",
            len(cat_errors),
            len(org_errors),
            len(veh_errors),
        )

    return {
        "catalogos": len(cat_fixtures),
        "organizacion": len(org_fixtures),
        "vehiculos": len(veh_fixtures),
        "errores": len(cat_errors) + len(org_errors) + len(veh_errors),
    }
