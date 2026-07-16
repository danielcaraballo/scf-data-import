#!/usr/bin/env python3
import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from scf_import.builders.catalogos import build_catalogos
from scf_import.builders.organizacion import build_organizacion
from scf_import.builders.vehiculos import build_vehiculos
from scf_import.readers import read_catalogos, read_organizacion, read_vehiculos

logger = logging.getLogger(__name__)

FIXTURE_ORDER: list[tuple[str, str]] = [
    ("01_catalogos.json", "catalogos"),
    ("02_organizacion.json", "organizacion"),
    ("03_vehiculos.json", "vehiculos"),
]


def write_fixture(path: Path, fixtures: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(fixtures, f, ensure_ascii=False, indent=2)


def print_report(stage: str, count: int, errors: list[str]) -> None:
    if errors:
        logger.warning("%s: %d registros, %d errores", stage, count, len(errors))
        for err in errors:
            logger.warning("  ⚠ %s", err)
    else:
        logger.info("%s: %d registros", stage, count)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SCF Data Import ETL")
    parser.add_argument("--input", "-i", required=True, help="Directorio con los CSVs de entrada")
    parser.add_argument(
        "--output",
        "-o",
        default="output/fixtures",
        help="Directorio de salida para fixtures",
    )
    parser.add_argument("--dry-run", action="store_true", help="Solo validar sin escribir archivos")
    parser.add_argument("--verbose", "-v", action="store_true", help="Activar logging detallado")
    return parser.parse_args()


def validate_inputs(input_dir: Path) -> dict[str, Path]:
    csv_files = {
        "catalogos.csv": input_dir / "catalogos.csv",
        "organizacion.csv": input_dir / "organizacion.csv",
        "vehiculos.csv": input_dir / "vehiculos.csv",
    }
    for path in csv_files.values():
        if not path.exists():
            logger.error("No se encuentra %s", path)
            sys.exit(1)
    return csv_files


def process_catalogos(
    path: Path,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, int]], list[str]]:
    logger.info("Procesando catálogos...")
    df = read_catalogos(path)
    return build_catalogos(df)


def process_organizacion(
    path: Path,
    catalog_lookups: dict[str, dict[str, int]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, int]], list[str]]:
    logger.info("Procesando organización...")
    df = read_organizacion(path)
    return build_organizacion(df, catalog_lookups)


def process_vehiculos(
    path: Path,
    catalog_lookups: dict[str, dict[str, int]],
    org_lookups: dict[str, dict[str, int]],
) -> tuple[list[dict[str, Any]], list[str]]:
    logger.info("Procesando vehículos...")
    df = read_vehiculos(path)
    return build_vehiculos(df, catalog_lookups, org_lookups)


def write_outputs(
    output_dir: Path,
    cat_fixtures: list[dict[str, Any]],
    org_fixtures: list[dict[str, Any]],
    veh_fixtures: list[dict[str, Any]],
) -> None:
    fixture_map = {
        "catalogos": cat_fixtures,
        "organizacion": org_fixtures,
        "vehiculos": veh_fixtures,
    }
    logger.info("Escribiendo fixtures...")
    for filename, key in FIXTURE_ORDER:
        fixtures = fixture_map.get(key)
        if fixtures is None:
            continue
        dst = output_dir / filename
        write_fixture(dst, fixtures)
        logger.info("  ✓ %s (%d registros)", dst, len(fixtures))
    logger.info("ETL completado. Fixtures en: %s", output_dir.resolve())


def main() -> None:
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    input_dir = Path(args.input)
    output_dir = Path(args.output)

    if not input_dir.is_dir():
        logger.error("'%s' no es un directorio válido", input_dir)
        sys.exit(1)

    csv_files = validate_inputs(input_dir)
    all_errors: list[str] = []

    cat_fixtures, catalog_lookups, cat_errors = process_catalogos(csv_files["catalogos.csv"])
    all_errors.extend(cat_errors)
    print_report("catalogos.csv", len(cat_fixtures), cat_errors)

    org_fixtures, org_lookups, org_errors = process_organizacion(
        csv_files["organizacion.csv"],
        catalog_lookups,
    )
    all_errors.extend(org_errors)
    print_report("organizacion.csv", len(org_fixtures), org_errors)

    veh_fixtures, veh_errors = process_vehiculos(
        csv_files["vehiculos.csv"],
        catalog_lookups,
        org_lookups,
    )
    all_errors.extend(veh_errors)
    print_report("vehiculos.csv", len(veh_fixtures), veh_errors)

    total = len(cat_fixtures) + len(org_fixtures) + len(veh_fixtures)
    logger.info("Total: %d registros, %d errores", total, len(all_errors))

    if all_errors:
        logger.warning("%d errores encontrados:", len(all_errors))
        for err in all_errors:
            logger.warning("  • %s", err)
        if args.dry_run:
            logger.error("Dry-run: no se escribirán fixtures por errores.")
            sys.exit(1)

    if args.dry_run:
        logger.info("Dry-run completado. No se escribieron archivos.")
        return

    write_outputs(output_dir, cat_fixtures, org_fixtures, veh_fixtures)


if __name__ == "__main__":
    main()
