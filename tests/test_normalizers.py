
from scf_import.normalizers import (
    normalize_anio,
    normalize_fk,
    normalize_name,
    normalize_placa,
    normalize_row,
    normalize_vin,
)


class TestNormalizeName:
    def test_simple(self) -> None:
        assert normalize_name("chevrolet") == "Chevrolet"

    def test_with_accent(self) -> None:
        assert normalize_name("  eléctrico  ") == "Eléctrico"

    def test_slash_e_abbreviation(self) -> None:
        assert normalize_name("s/e") == "S. E."

    def test_empty(self) -> None:
        assert normalize_name("") == ""

    def test_whitespace(self) -> None:
        assert normalize_name("  ") == ""


class TestNormalizeFk:
    def test_simple(self) -> None:
        assert normalize_fk("  Chevrolet  ") == "Chevrolet"

    def test_empty(self) -> None:
        assert normalize_fk("") == ""


class TestNormalizeVin:
    def test_uppercase(self) -> None:
        assert normalize_vin("abc123") == "ABC123"

    def test_strip(self) -> None:
        assert normalize_vin("  abc  ") == "ABC"


class TestNormalizePlaca:
    def test_uppercase(self) -> None:
        assert normalize_placa("abc-123") == "ABC-123"


class TestNormalizeAnio:
    def test_valid(self) -> None:
        assert normalize_anio("2022") == 2022

    def test_invalid_returns_zero(self) -> None:
        assert normalize_anio("unknown") == 0

    def test_empty_returns_zero(self) -> None:
        assert normalize_anio("") == 0


class TestNormalizeRow:
    def test_normalizes_all_fields(self) -> None:
        row = {
            "marca": "  chevrolet  ",
            "vin": "abc123",
            "placa": "ab-123",
            "anio": "2022",
            "numero_economico": " ECO-01 ",
            "nombre": "  algún nombre  ",
        }
        fk_fields = {"marca"}
        result = normalize_row(row, fk_fields)
        assert result["marca"] == "chevrolet"
        assert result["vin"] == "ABC123"
        assert result["placa"] == "AB-123"
        assert result["anio"] == 2022
        assert result["numero_economico"] == "ECO-01"
        assert result["nombre"] == "Algún Nombre"

    def test_empty_values(self) -> None:
        row = {"marca": "", "vin": "", "anio": "", "nombre": ""}
        result = normalize_row(row, set())
        assert result["marca"] == ""
        assert result["vin"] == ""
        assert result["anio"] == 0
        assert result["nombre"] == ""
