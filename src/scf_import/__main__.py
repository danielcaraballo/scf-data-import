#!/usr/bin/env python3
import argparse
import logging
import sys
import time
from pathlib import Path

from scf_import.builders.catalogos import build_catalogos
from scf_import.builders.organizacion import build_organizacion
from scf_import.builders.vehiculos import build_vehiculos
from scf_import.config import load_rules
from scf_import.extract import (
    extract_flota,
    find_latest_flota_file,
    read_catalogos,
    read_organizacion,
    read_vehiculos,
)
from scf_import.load import (
    build_django_fixtures,
    write_fixture_file,
    write_normalized_csv,
    write_normalized_excel,
    write_revision_csv,
)
from scf_import.report import generate_report, log_report
from scf_import.transform.canonical import CanonicalMapper
from scf_import.transform.row import NormalizedRow, transform_row
from scf_import.validate import validate_batch

logger = logging.getLogger("scf_import")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SCF Data Import - Pipeline ETL de Normalización de Flota",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--flota",
        "-f",
        type=Path,
        help="Ruta al archivo CSV o Excel de flota (ej. data/flota.2026-07-16.csv)",
    )
    input_group.add_argument(
        "--dir",
        "-d",
        type=Path,
        help="Directorio con archivos de flota (selecciona el flota.*.csv más reciente para cron)",
    )
    input_group.add_argument(
        "--input",
        "-i",
        type=Path,
        help="Modo legado: directorio con catalogos.csv, organizacion.csv, vehiculos.csv",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("output"),
        help="Directorio base para archivos de salida (por defecto: output/)",
    )
    parser.add_argument(
        "--mappings",
        "-m",
        type=Path,
        default=Path("config/mappings"),
        help="Directorio de mappings CSV editables (por defecto: config/mappings/)",
    )
    parser.add_argument(
        "--rules",
        "-r",
        type=Path,
        default=Path("config/rules.toml"),
        help="Archivo de reglas TOML (por defecto: config/rules.toml)",
    )
    parser.add_argument(
        "--fixtures",
        action="store_true",
        help="Generar fixtures JSON para Django (01_catalogos, 02_organizacion, 03_vehiculos)",
    )
    parser.add_argument(
        "--excel",
        "-x",
        action="store_true",
        help="Generar archivo Excel (.xlsx) con la flota normalizada",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Ejecutar transformación y validación sin escribir archivos en disco",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Activar registro detallado (DEBUG)",
    )
    return parser.parse_args()


def run_legacy_mode(
    input_dir: Path,
    output_dir: Path,
    *,
    is_dry_run: bool = False,
) -> None:
    logger.info("Ejecutando en modo legado desde: %s", input_dir)
    cat_df = read_catalogos(input_dir / "catalogos.csv")
    org_df = read_organizacion(input_dir / "organizacion.csv")
    veh_df = read_vehiculos(input_dir / "vehiculos.csv")

    cat_fixtures, cat_lookups, cat_errors = build_catalogos(cat_df)
    org_fixtures, org_lookups, org_errors = build_organizacion(org_df, cat_lookups)
    veh_fixtures, veh_errors = build_vehiculos(veh_df, cat_lookups, org_lookups)

    total_errors = len(cat_errors) + len(org_errors) + len(veh_errors)
    logger.info(
        "Modo legado completado: %d catálogos, %d org, %d vehículos (%d errores)",
        len(cat_fixtures),
        len(org_fixtures),
        len(veh_fixtures),
        total_errors,
    )

    if is_dry_run:
        logger.info("Dry-run activado: no se escribieron fixtures.")
        return

    write_fixture_file(output_dir / "01_catalogos.json", cat_fixtures)
    write_fixture_file(output_dir / "02_organizacion.json", org_fixtures)
    write_fixture_file(output_dir / "03_vehiculos.json", veh_fixtures)
    logger.info("Fixtures legadas escritas en: %s", output_dir)


def _resolve_input_file(args: argparse.Namespace) -> Path:
    if args.flota:
        return Path(args.flota)
    if args.dir:
        try:
            flota_path = find_latest_flota_file(args.dir)
        except FileNotFoundError:
            logger.exception("Error buscando archivo en %s", args.dir)
            sys.exit(1)
        else:
            logger.info("Archivo más reciente detectado: %s", flota_path)
            return flota_path

    logger.error("Debe especificar --flota, --dir o --input")
    sys.exit(1)


def main() -> None:
    start_time = time.time()
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.input:
        run_legacy_mode(args.input, args.output, is_dry_run=args.dry_run)
        return

    flota_path = _resolve_input_file(args)
    if not flota_path.exists():
        logger.error("No se encuentra el archivo de entrada: %s", flota_path)
        sys.exit(1)

    # 1. Load configuration and rules
    rules = load_rules(args.rules)
    mappings_dir = args.mappings
    mapper = CanonicalMapper(mappings_dir)

    # 2. Extract
    logger.info("Extrayendo datos de %s ...", flota_path)
    df, file_date = extract_flota(flota_path)
    logger.info("Registros extraídos: %d filas (Fecha snapshot: %s)", len(df), file_date)

    # 3. Transform
    logger.info("Transformando y canonicalizando registros...")
    raw_records = df.to_dict(orient="records")
    normalized_rows: list[NormalizedRow] = []

    for idx, raw_dict in enumerate(raw_records, start=2):
        row = transform_row(idx, raw_dict, mapper, rules)
        normalized_rows.append(row)

    # 4. Validate and Deduplicate
    logger.info("Validando reglas de negocio y deduplicando claves...")
    validated_rows = validate_batch(normalized_rows, rules)

    # 5. Load
    out_dir = args.output
    master_csv_path = out_dir / f"flota_normalizada.{file_date}.csv"
    revision_csv_path = out_dir / f"revision.{file_date}.csv"

    if not args.dry_run:
        write_normalized_csv(master_csv_path, validated_rows)
        write_revision_csv(revision_csv_path, validated_rows, mapper)

        if args.excel:
            master_excel_path = out_dir / f"flota_normalizada.{file_date}.xlsx"
            write_normalized_excel(master_excel_path, validated_rows)

        if args.fixtures:
            logger.info("Generando fixtures Django...")
            build_django_fixtures(validated_rows, out_dir)
    else:
        logger.info("Dry-run activado: validación y transformación completadas sin escribir.")

    # 6. Report
    elapsed = time.time() - start_time
    report_text = generate_report(validated_rows, mapper, elapsed)
    log_report(report_text, logger)


if __name__ == "__main__":
    main()
