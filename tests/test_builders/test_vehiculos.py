from pathlib import Path

import pytest

from scf_import.builders.catalogos import build_catalogos
from scf_import.builders.organizacion import build_organizacion
from scf_import.builders.vehiculos import build_vehiculos
from scf_import.readers import read_catalogos, read_organizacion, read_vehiculos

DATA_DIR = Path(__file__).resolve().parents[2] / "data_test"


@pytest.fixture()
def lookups() -> tuple[dict, dict]:
    cat_df = read_catalogos(DATA_DIR / "catalogos.csv")
    _, cat_lookups, _ = build_catalogos(cat_df)

    org_df = read_organizacion(DATA_DIR / "organizacion.csv")
    _, org_lookups, _ = build_organizacion(org_df, cat_lookups)

    return cat_lookups, org_lookups


def test_build_vehiculos(lookups: tuple[dict, dict]) -> None:
    cat_lookups, org_lookups = lookups
    df = read_vehiculos(DATA_DIR / "vehiculos.csv")
    fixtures, errors = build_vehiculos(df, cat_lookups, org_lookups)

    assert errors == []
    assert len(fixtures) == 3

    for f in fixtures:
        assert f["model"] == "vehiculos.vehiculo"
        fields = f["fields"]
        assert "numero_economico" in fields
        assert "vin" in fields
        assert "marca" in fields
        assert "modelo" in fields
        assert isinstance(fields["marca"], int)
        assert isinstance(fields["modelo"], int)


def test_build_vehiculos_invalid_anio(lookups: tuple[dict, dict]) -> None:
    cat_lookups, org_lookups = lookups
    df = read_vehiculos(DATA_DIR / "vehiculos.csv")
    fixtures, errors = build_vehiculos(df, cat_lookups, org_lookups)

    assert errors == []
    for f in fixtures:
        assert isinstance(f["fields"].get("anio", 0), int)
