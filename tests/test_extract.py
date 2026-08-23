import tempfile
from pathlib import Path

import pytest

from scf_import.extract import (
    clean_header,
    clean_na_value,
    detect_delimiter,
    extract_date_from_filename,
    find_latest_flota_file,
)


class TestExtractUtils:
    def test_clean_header_accents_and_parentheses(self) -> None:
        assert clean_header("ESTADO ✅") == "ESTADO"
        assert clean_header("EMPLAZAMIENTO (SAP) ✅") == "EMPLAZAMIENTO"
        assert (
            clean_header("DENOMINACION DEL ACTIVO FIJO (TIPO) ✅")
            == "DENOMINACION DEL ACTIVO FIJO"
        )
        assert clean_header("AÑO") == "ANO"
        assert clean_header('\ufeff"SERIAL DE CARROCERÍA"') == "SERIAL DE CARROCERIA"

    def test_clean_na_value(self) -> None:
        assert clean_na_value("S/P") == ""
        assert clean_na_value("s/n") == ""
        assert clean_na_value("N/A") == ""
        assert clean_na_value("TOYOTA") == "TOYOTA"
        assert clean_na_value(None) == ""

    def test_extract_date_from_filename(self) -> None:
        assert extract_date_from_filename("flota.2026-07-16.csv") == "2026-07-16"
        assert extract_date_from_filename("flota_20260716.csv") == "2026-07-16"
        assert len(extract_date_from_filename("flota_sin_fecha.csv")) == 10

    def test_detect_delimiter(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("A;B;C\n1;2;3\n")
            path_semi = Path(f.name)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("A,B,C\n1,2,3\n")
            path_comma = Path(f.name)

        try:
            assert detect_delimiter(path_semi) == ";"
            assert detect_delimiter(path_comma) == ","
        finally:
            path_semi.unlink(missing_ok=True)
            path_comma.unlink(missing_ok=True)

    def test_find_latest_flota_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = Path(tmpdir)
            (dir_path / "flota.2026-01-01.csv").touch()
            (dir_path / "flota.2026-07-16.csv").touch()
            (dir_path / "flota.2025-12-31.csv").touch()

            latest = find_latest_flota_file(dir_path)
            assert latest.name == "flota.2026-07-16.csv"

    def test_find_latest_flota_file_empty_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir, pytest.raises(FileNotFoundError):
            find_latest_flota_file(Path(tmpdir))
