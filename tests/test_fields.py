from scf_import.transform.fields import (
    extract_subtype_from_model,
    normalize_anio,
    normalize_km,
    normalize_placa,
    normalize_sap,
    normalize_vin,
)


class TestNormalizeSap:
    def test_sap_valid_digits(self) -> None:
        val, flags = normalize_sap("7612345")
        assert val == "7612345"
        assert flags == []

    def test_sap_na_patterns(self) -> None:
        for na_val in ["0", "S/N", "s/n", "S/P", "N/A", "NO POSEE", "N0 P0SEE", "", "-"]:
            val, flags = normalize_sap(na_val)
            assert val == ""
            assert flags == []

    def test_sap_non_numeric(self) -> None:
        val, flags = normalize_sap("MOTO-0585")
        assert val == "MOTO-0585"
        assert "SAP_NO_NUMERICO" in flags

    def test_sap_suspicious_length(self) -> None:
        val, flags = normalize_sap("20060000000")
        assert val == "20060000000"
        assert "SAP_LONGITUD_SOSPECHOSA" in flags


class TestNormalizeVin:
    def test_vin_valid(self) -> None:
        val, flags = normalize_vin("1HGCR2F83HA000001")
        assert val == "1HGCR2F83HA000001"
        assert flags == []

    def test_vin_invalid_length(self) -> None:
        val, flags = normalize_vin("8FD50N11517")
        assert val == "8FD50N11517"
        assert "VIN_LONGITUD_INVALIDA" in flags

    def test_vin_empty_or_na(self) -> None:
        for na_val in ["", "S/N", "S/P", "N/A", "0"]:
            val, flags = normalize_vin(na_val)
            assert val == ""
            assert "VIN_VACIO" in flags


class TestNormalizePlaca:
    def test_placa_valid(self) -> None:
        val, flags = normalize_placa("MPPEE-1234")
        assert val == "MPPEE-1234"
        assert flags == []

    def test_placa_mppee_incomplete(self) -> None:
        val, flags = normalize_placa("MPPEE-")
        assert val == ""
        assert "PLACA_MPPEE_INCOMPLETA" in flags

    def test_placa_na_patterns(self) -> None:
        for na_val in ["", "S/P", "S/N", "N/A"]:
            val, flags = normalize_placa(na_val)
            assert val == ""
            assert flags == []


class TestNormalizeAnio:
    def test_anio_valid(self) -> None:
        val, flags = normalize_anio("2020")
        assert val == 2020
        assert flags == []

    def test_anio_out_of_range(self) -> None:
        val, flags = normalize_anio("1940")
        assert val == 1940
        assert "ANIO_FUERA_DE_RANGO" in flags

    def test_anio_invalid_string(self) -> None:
        val, flags = normalize_anio("desconocido")
        assert val == 0
        assert "ANIO_INVALIDO" in flags


class TestNormalizeKm:
    def test_km_venezuelan_format(self) -> None:
        val, flags = normalize_km("231.302,00")
        assert val == 231302
        assert flags == []

        val, flags = normalize_km("364.639")
        assert val == 364639
        assert flags == []


class TestExtractSubtype:
    def test_extract_subtype_from_parentheses(self) -> None:
        base, subtype = extract_subtype_from_model("CAMION PLATAFORMA (TIPO 350)")
        assert base == "CAMION PLATAFORMA"
        assert subtype == "TIPO 350"
