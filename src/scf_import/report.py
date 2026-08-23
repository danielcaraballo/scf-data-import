import logging

from scf_import.transform.canonical import CanonicalMapper
from scf_import.transform.row import NormalizedRow

logger = logging.getLogger(__name__)


def _format_identifiers_summary(rows: list[NormalizedRow]) -> list[str]:
    sap_v = sum(
        1 for r in rows
        if r.canonical.get("numero_economico")
        and not any(f in r.flags for f in ("SAP_NO_NUMERICO", "SAP_LONGITUD_SOSPECHOSA"))
    )
    sap_s = sum(
        1 for r in rows
        if any(f in r.flags for f in ("SAP_NO_NUMERICO", "SAP_LONGITUD_SOSPECHOSA"))
    )
    sap_e = sum(1 for r in rows if not r.canonical.get("numero_economico"))
    sap_d = sum(1 for r in rows if "SAP_DUPLICADO" in r.flags)

    vin_v = sum(
        1 for r in rows
        if r.canonical.get("vin") and "VIN_LONGITUD_INVALIDA" not in r.flags
    )
    vin_inv = sum(1 for r in rows if "VIN_LONGITUD_INVALIDA" in r.flags)
    vin_e = sum(1 for r in rows if not r.canonical.get("vin"))
    vin_d = sum(1 for r in rows if "VIN_DUPLICADO" in r.flags)

    placa_v = sum(1 for r in rows if r.canonical.get("placa"))
    placa_inc = sum(1 for r in rows if "PLACA_MPPEE_INCOMPLETA" in r.flags)
    placa_e = sum(
        1 for r in rows
        if not r.canonical.get("placa") and "PLACA_MPPEE_INCOMPLETA" not in r.flags
    )
    placa_d = sum(1 for r in rows if "PLACA_DUPLICADA" in r.flags)

    return [
        "--- Identificadores y Claves de Negocio ---",
        f"  SAP (Nro Económico) : {sap_v:,} válidos | {sap_s:,} formato dudoso | "
        f"{sap_e:,} vacíos | {sap_d:,} duplicados",
        f"  VIN (Serial Chasis) : {vin_v:,} válidos (17 car.) | {vin_inv:,} long. != 17 | "
        f"{vin_e:,} vacíos | {vin_d:,} duplicados",
        f"  Placa MPPEE         : {placa_v:,} válidas | {placa_inc:,} prefijo incompleto | "
        f"{placa_e:,} vacías | {placa_d:,} duplicadas",
    ]


def generate_report(
    rows: list[NormalizedRow],
    mapper: CanonicalMapper,
    execution_time: float = 0.0,
) -> str:
    total = len(rows)
    if total == 0:
        return "Reporte ETL: No se procesaron registros."

    ok_count = sum(1 for r in rows if r.quality == "OK")
    warn_count = sum(1 for r in rows if r.quality == "ADVERTENCIA")
    inv_count = sum(1 for r in rows if r.quality == "INVALIDO")

    marcas_unk = sum(1 for r in rows if "MARCA_DESCONOCIDA" in r.flags)
    modelos_unk = sum(1 for r in rows if "MODELO_DESCONOCIDO" in r.flags)
    empl_unk = sum(1 for r in rows if "EMPLAZAMIENTO_DESCONOCIDO" in r.flags)

    lines = [
        "==================================================",
        "          REPORTE ETL SCF INVENTARIO DE FLOTA      ",
        "==================================================",
        f"Total registros procesados : {total:,}",
        f"Tiempo de ejecución        : {execution_time:.2f} s",
        "",
        "--- Calidad de Registros ---",
        f"  ✓ OK            : {ok_count:6d} ({ok_count / total * 100:5.1f}%)",
        f"  ⚠ ADVERTENCIA   : {warn_count:6d} ({warn_count / total * 100:5.1f}%)",
        f"  ✗ INVALIDO      : {inv_count:6d} ({inv_count / total * 100:5.1f}%)",
        "",
    ]
    lines.extend(_format_identifiers_summary(rows))
    lines.extend([
        "",
        "--- Canonicalización de Catálogos ---",
        f"  Marcas no catalogadas         : {marcas_unk:,}",
        f"  Modelos no catalogados        : {modelos_unk:,}",
        f"  Emplazamientos no catalogados : {empl_unk:,}",
    ])

    unknown_items = mapper.get_unknown_records()
    if unknown_items:
        lines.append("")
        lines.append("--- Valores Desconocidos Frecuentes (para alimentar mappings) ---")
        lines.extend(
            f"  • [{item['categoria'].upper()}] '{item['valor_original']}' "
            f"({item['ocurrencias']} ocurrencias)"
            for item in unknown_items[:15]
        )

    lines.append("==================================================")
    return "\n".join(lines)


def log_report(report_str: str, report_logger: logging.Logger | None = None) -> None:
    target_logger = report_logger or logger
    for line in report_str.splitlines():
        target_logger.info(line)
