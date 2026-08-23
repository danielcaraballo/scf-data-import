#!/usr/bin/env python3
"""
SCF Data Import - Lanzador Interactivo
Permite seleccionar archivos y opciones del pipeline ETL de forma interactiva.
"""
import sys
import time
from pathlib import Path

# Asegurar que src/ esté en el PYTHONPATH
SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from scf_import.config import load_rules
from scf_import.extract import extract_flota, find_latest_flota_file
from scf_import.load import (
    build_django_fixtures,
    write_normalized_csv,
    write_normalized_excel,
    write_revision_csv,
)
from scf_import.report import generate_report
from scf_import.transform.canonical import CanonicalMapper
from scf_import.transform.row import transform_row
from scf_import.validate import validate_batch

DATA_DIR = Path("data")
OUTPUT_DIR = Path("output")
MAPPINGS_DIR = Path("config/mappings")
RULES_PATH = Path("config/rules.toml")


def _print_header() -> None:
    print("\n" + "=" * 56)
    print("      🚀 SCF DATA IMPORT — ETL DE FLOTA VEHICULAR      ")
    print("=" * 56)


def _list_data_files() -> list[Path]:
    if not DATA_DIR.exists():
        return []
    candidates = list(DATA_DIR.glob("*.csv")) + list(DATA_DIR.glob("*.xlsx"))
    candidates = [f for f in candidates if not f.name.startswith(".")]
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates


def _format_size(num_bytes: int) -> str:
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes / (1024 * 1024):.1f} MB"


def _select_file() -> Path | None:
    files = _list_data_files()
    if not files:
        print("\n❌ No se encontraron archivos de datos en la carpeta 'data/'.")
        print("   Por favor, copie su archivo CSV o Excel en 'data/' e intente de nuevo.")
        return None

    print("\n📁 Archivos encontrados en 'data/':")
    for idx, f in enumerate(files, 1):
        tag = " (Más reciente)" if idx == 1 else ""
        size = _format_size(f.stat().st_size)
        print(f"  [{idx}] {f.name} [{size}]{tag}")

    while True:
        choice = input(f"\nSeleccione un archivo [1-{len(files)}] (Enter para [1]): ").strip()
        if not choice:
            return files[0]
        if choice.isdigit() and 1 <= int(choice) <= len(files):
            return files[int(choice) - 1]
        print("⚠️ Opción inválida. Intente de nuevo.")


def _run_pipeline(
    flota_path: Path,
    *,
    generate_excel: bool = True,
    generate_fixtures: bool = True,
    dry_run: bool = False,
) -> None:
    start_time = time.time()
    print(f"\n⏳ Extrayendo datos de: {flota_path} ...")

    df, file_date = extract_flota(flota_path)
    total_rows = len(df)
    print(f"✓ Registros extraídos: {total_rows:,} filas (Fecha snapshot: {file_date})")

    print("⏳ Normalizando y canonicalizando registros...")
    rules = load_rules(RULES_PATH)
    mapper = CanonicalMapper(MAPPINGS_DIR)
    raw_records = df.to_dict(orient="records")
    normalized_rows = [
        transform_row(idx, raw, mapper, rules)
        for idx, raw in enumerate(raw_records, start=2)
    ]

    print("⏳ Validando reglas de negocio y deduplicando claves...")
    validated_rows = validate_batch(normalized_rows, rules)

    if not dry_run:
        print("⏳ Guardando archivos de salida...")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        master_csv_path = OUTPUT_DIR / f"flota_normalizada.{file_date}.csv"
        write_normalized_csv(master_csv_path, validated_rows)

        revision_csv_path = OUTPUT_DIR / f"revision.{file_date}.csv"
        write_revision_csv(revision_csv_path, validated_rows, mapper)

        if generate_excel:
            master_excel_path = OUTPUT_DIR / f"flota_normalizada.{file_date}.xlsx"
            write_normalized_excel(master_excel_path, validated_rows)

        if generate_fixtures:
            print("⏳ Generando fixtures para Django...")
            build_django_fixtures(validated_rows, OUTPUT_DIR)
    else:
        print("ℹ️ Modo Dry-Run activado: validación completada sin escribir en disco.")

    elapsed = time.time() - start_time
    report_text = generate_report(validated_rows, mapper, elapsed)
    print("\n" + report_text)

    if not dry_run:
        print("\n🎉 Proceso completado con éxito. Archivos generados:")
        print(f"  📄 CSV Maestro : output/flota_normalizada.{file_date}.csv")
        print(f"  🔍 CSV Revisión: output/revision.{file_date}.csv")
        if generate_excel:
            print(f"  📊 Excel Limpio: output/flota_normalizada.{file_date}.xlsx")
        if generate_fixtures:
            print("  📦 Fixtures    : output/fixtures/ (01_catalogos, 02_organizacion, 03_vehiculos)")


def _run_tests() -> None:
    import subprocess
    print("\n🧪 Ejecutando suite de pruebas, linter y comprobador de tipos...")
    python_exe = sys.executable
    cmd = f"{python_exe} -m pytest && {python_exe} -m ruff check . && {python_exe} -m mypy src run.py"
    res = subprocess.run(cmd, shell=True, check=False)
    if res.returncode == 0:
        print("\n✅ Todas las pruebas, análisis de tipos y linter pasaron al 100%.")
    else:
        print("\n❌ Se detectaron fallos en las pruebas o en el linter.")


def main() -> None:
    while True:
        _print_header()
        print("[1] 🚀 Procesar archivo más reciente (Todo incluido: CSV + Excel + Fixtures)")
        print("[2] 📊 Generar solo Excel limpio (.xlsx) y CSV maestro")
        print("[3] 📦 Generar solo Fixtures Django (.json) y CSV maestro")
        print("[4] 📁 Seleccionar un archivo específico de data/")
        print("[5] 🔍 Modo Dry-Run (Validar y ver reporte sin escribir en disco)")
        print("[6] 🧪 Ejecutar suite de pruebas y calidad (pytest/ruff/mypy)")
        print("[0] 🚪 Salir")
        print("=" * 56)

        try:
            choice = input("Seleccione una opción [0-6] (Enter para [1]): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Operación cancelada por el usuario.")
            break

        if choice in ("", "1"):
            try:
                latest = find_latest_flota_file(DATA_DIR)
            except FileNotFoundError:
                print("\n❌ No se encontraron archivos en 'data/'.")
                input("\nPresione Enter para continuar...")
                continue
            _run_pipeline(latest, generate_excel=True, generate_fixtures=True)
            input("\nPresione Enter para volver al menú...")

        elif choice == "2":
            try:
                latest = find_latest_flota_file(DATA_DIR)
            except FileNotFoundError:
                print("\n❌ No se encontraron archivos en 'data/'.")
                input("\nPresione Enter para continuar...")
                continue
            _run_pipeline(latest, generate_excel=True, generate_fixtures=False)
            input("\nPresione Enter para volver al menú...")

        elif choice == "3":
            try:
                latest = find_latest_flota_file(DATA_DIR)
            except FileNotFoundError:
                print("\n❌ No se encontraron archivos en 'data/'.")
                input("\nPresione Enter para continuar...")
                continue
            _run_pipeline(latest, generate_excel=False, generate_fixtures=True)
            input("\nPresione Enter para volver al menú...")

        elif choice == "4":
            selected = _select_file()
            if not selected:
                input("\nPresione Enter para continuar...")
                continue
            print(f"\nArchivo seleccionado: {selected.name}")
            gen_excel = input("¿Generar archivo Excel (.xlsx)? [S/n]: ").strip().lower() != "n"
            gen_fixtures = input("¿Generar fixtures Django (.json)? [S/n]: ").strip().lower() != "n"
            _run_pipeline(selected, generate_excel=gen_excel, generate_fixtures=gen_fixtures)
            input("\nPresione Enter para volver al menú...")

        elif choice == "5":
            try:
                latest = find_latest_flota_file(DATA_DIR)
            except FileNotFoundError:
                print("\n❌ No se encontraron archivos en 'data/'.")
                input("\nPresione Enter para continuar...")
                continue
            _run_pipeline(latest, generate_excel=False, generate_fixtures=False, dry_run=True)
            input("\nPresione Enter para volver al menú...")

        elif choice == "6":
            _run_tests()
            input("\nPresione Enter para volver al menú...")

        elif choice == "0":
            print("\n👋 ¡Hasta luego!\n")
            break
        else:
            print("⚠️ Opción no válida. Ingrese un número entre 0 y 6.")
            time.sleep(1)


if __name__ == "__main__":
    main()
