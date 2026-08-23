from scf_import.transform.text import (
    clean_str,
    normalize_code,
    normalize_key,
    parse_number_ve,
    title_case,
)


class TestCleanStr:
    def test_clean_str_strips_bom_and_quotes(self) -> None:
        assert clean_str('\ufeff"  test  "') == "test"
        assert clean_str("  multi   space  ") == "multi space"
        assert clean_str(None) == ""


class TestNormalizeKey:
    def test_normalize_key_accents_and_case(self) -> None:
        assert normalize_key("Camión Eléctrico") == "camion electrico"
        assert normalize_key("CHEVY") == "chevy"
        assert normalize_key("HINO 300 (816)") == "hino 300 816"
        assert normalize_key("S/E EL B0SQUE EL VIGIA") == "s e el b0sque el vigia"
        assert normalize_key("D'INNOCENZO") == "d innocenzo"
        assert normalize_key("") == ""
        assert normalize_key(None) == ""


class TestParseNumberVe:
    def test_venezuelan_thousands_and_decimals(self) -> None:
        assert parse_number_ve("231.302,00") == 231302
        assert parse_number_ve("364.639") == 364639
        assert parse_number_ve("1.234.567,89") == 1234567.89
        assert parse_number_ve("5") == 5
        assert parse_number_ve("0") == 0
        assert parse_number_ve("invalid") is None
        assert parse_number_ve("") is None
        assert parse_number_ve(None) is None


class TestNormalizeCode:
    def test_normalize_code(self) -> None:
        assert normalize_code(" 1hg cr2 f83ha000001 ") == "1HGCR2F83HA000001"
        assert normalize_code("mppee-1234") == "MPPEE-1234"


class TestTitleCase:
    def test_title_case_preserves_acronyms(self) -> None:
        assert title_case("s/e el bosque") == "S. E. El Bosque"
        assert title_case("gerencia corporacion sap") == "Gerencia Corporacion SAP"
        assert title_case("f-350 unicesta") == "F-350 Unicesta"
        assert title_case("") == ""
