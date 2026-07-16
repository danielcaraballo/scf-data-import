from pathlib import Path

import pytest

from scf_import.builders.catalogos import build_catalogos
from scf_import.readers import read_catalogos

DATA_DIR = Path(__file__).resolve().parents[2] / "data_test"


def test_build_catalogos() -> None:
    df = read_catalogos(DATA_DIR / "catalogos.csv")
    fixtures, lookups, errors = build_catalogos(df)

    assert errors == []
    assert len(fixtures) > 0

    models = {f["model"] for f in fixtures}
    assert "catalogos.marca" in models
    assert "catalogos.modelo" in models
    assert "catalogos.color" in models
    assert "catalogos.tipovehiculo" in models
    assert "catalogos.tipouso" in models
    assert "catalogos.estatusvehiculo" in models
    assert "catalogos.colorplaca" in models
    assert "catalogos.clasevehiculo" in models
    assert "catalogos.tipocombustible" in models
    assert "catalogos.sistemaafectado" in models
    assert "catalogos.tipofalla" in models

    assert "marca" in lookups
    assert "Chevrolet" in lookups["marca"]
    assert "Ford" in lookups["marca"]
    assert "Toyota" in lookups["marca"]


def test_build_catalogos_deduplicates() -> None:
    df = read_catalogos(DATA_DIR / "catalogos.csv")
    fixtures, lookups, errors = build_catalogos(df)

    marca_count = sum(1 for f in fixtures if f["model"] == "catalogos.marca")
    assert marca_count == 3  # Chevrolet, Ford, Toyota (sin duplicados)

    assert errors == []


def test_build_catalogos_fk_resolution() -> None:
    df = read_catalogos(DATA_DIR / "catalogos.csv")
    fixtures, lookups, errors = build_catalogos(df)

    assert errors == []

    tipo_falla_fixtures = [f for f in fixtures if f["model"] == "catalogos.tipofalla"]
    assert len(tipo_falla_fixtures) == 2

    for tf in tipo_falla_fixtures:
        assert "sistema_afectado" in tf["fields"]
        assert isinstance(tf["fields"]["sistema_afectado"], int)
