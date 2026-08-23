import tempfile
from pathlib import Path

import pandas as pd

from scf_import.extract import extract_flota
from scf_import.load import (
    EXCEL_COLUMNS,
    MASTER_COLUMNS,
    build_django_fixtures,
    write_normalized_csv,
    write_normalized_excel,
    write_revision_csv,
)
from scf_import.transform.canonical import CanonicalMapper
from scf_import.transform.row import transform_row
from scf_import.validate import validate_batch

TESTS_DIR = Path(__file__).resolve().parent
DATA_PATH = TESTS_DIR / "data" / "flota_sucia.csv"
MAPPINGS_DIR = TESTS_DIR.parent / "config" / "mappings"


def test_golden_flota_pipeline() -> None:
    assert DATA_PATH.exists()
    assert MAPPINGS_DIR.exists()

    df, file_date = extract_flota(DATA_PATH)
    assert len(df) == 8

    mapper = CanonicalMapper(MAPPINGS_DIR)
    raw_records = df.to_dict(orient="records")

    rows = [transform_row(idx, raw, mapper) for idx, raw in enumerate(raw_records, start=2)]
    validated_rows = validate_batch(rows)

    # 1. Row 1 checks (CHEVY, CAPITAL, 231.302,00)
    r1 = validated_rows[0]
    assert r1.canonical["marca"] == "CHEVROLET"
    assert r1.canonical["estado"] == "DISTRITO CAPITAL"
    assert r1.canonical["kilometraje"] == 231302
    assert r1.canonical["emplazamiento"] == "S. E. El Bosque El Vigía"
    assert "SAP_DUPLICADO" in r1.flags
    assert "VIN_DUPLICADO" in r1.flags
    assert "PLACA_DUPLICADA" in r1.flags

    # 2. Row 2 checks (FORD F350 UNICESTA, S/N SAP, MPPEE-)
    r2 = validated_rows[1]
    assert r2.canonical["marca"] == "FORD"
    assert r2.canonical["modelo"] == "F-350"
    assert r2.canonical["numero_economico"] == ""
    assert r2.canonical["placa"] == ""
    assert "PLACA_MPPEE_INCOMPLETA" in r2.flags
    assert r2.canonical["kilometraje"] == 364639
    assert r2.quality == "ADVERTENCIA"

    # 3. Row 3 checks (HINO 300 (816), SAP 0)
    r3 = validated_rows[2]
    assert r3.canonical["marca"] == "HINO"
    assert r3.canonical["modelo"] == "300 (816)"
    assert r3.canonical["numero_economico"] == ""
    assert r3.canonical["kilometraje"] == 50000

    # 4. Row 5 checks (LA GUAIRA, SAP 20060000000)
    r5 = validated_rows[4]
    assert r5.canonical["estado"] == "VARGAS"
    assert "SAP_LONGITUD_SOSPECHOSA" in r5.flags
    assert r5.quality == "ADVERTENCIA"

    # 5. Row 7 checks (GENERAL MOTOR, sin identificadores)
    r7 = validated_rows[6]
    assert r7.canonical["marca"] == "CHEVROLET"
    assert r7.quality == "INVALIDO"
    assert "SIN_IDENTIFICADOR" in r7.flags

    # 6. Test writing outputs in temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir)
        master_csv = out_path / f"flota_normalizada.{file_date}.csv"
        master_excel = out_path / f"flota_normalizada.{file_date}.xlsx"
        rev_csv = out_path / f"revision.{file_date}.csv"

        write_normalized_csv(master_csv, validated_rows)
        write_normalized_excel(master_excel, validated_rows)
        write_revision_csv(rev_csv, validated_rows, mapper)

        assert master_csv.exists()
        assert master_excel.exists()
        assert rev_csv.exists()

        csv_df = pd.read_csv(master_csv)
        assert len(csv_df) == 8
        assert list(csv_df.columns) == MASTER_COLUMNS

        excel_df = pd.read_excel(master_excel)
        assert len(excel_df) == 8
        assert list(excel_df.columns) == EXCEL_COLUMNS
        assert "calidad" not in excel_df.columns
        assert "flags" not in excel_df.columns
        assert "marca" in excel_df.columns
        assert "modelo" in excel_df.columns
        assert excel_df.iloc[0]["marca"] == "CHEVROLET"

        fixtures_stats = build_django_fixtures(validated_rows, out_path)
        assert fixtures_stats["catalogos"] > 0
        assert fixtures_stats["organizacion"] > 0
        assert fixtures_stats["vehiculos"] > 0
