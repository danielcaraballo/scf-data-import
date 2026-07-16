from pathlib import Path

import pytest

from scf_import.builders.catalogos import build_catalogos
from scf_import.builders.organizacion import build_organizacion
from scf_import.readers import read_catalogos, read_organizacion

DATA_DIR = Path(__file__).resolve().parents[2] / "data_test"


def test_build_organizacion() -> None:
    cat_df = read_catalogos(DATA_DIR / "catalogos.csv")
    _, cat_lookups, _ = build_catalogos(cat_df)

    org_df = read_organizacion(DATA_DIR / "organizacion.csv")
    fixtures, lookups, errors = build_organizacion(org_df, cat_lookups)

    assert errors == []
    assert len(fixtures) > 0

    models = {f["model"] for f in fixtures}
    assert "organizacion.estado" in models
    assert "organizacion.gerencia" in models
    assert "organizacion.centrodeservicio" in models


def test_build_organizacion_centro_servicio_has_fk() -> None:
    cat_df = read_catalogos(DATA_DIR / "catalogos.csv")
    _, cat_lookups, _ = build_catalogos(cat_df)

    org_df = read_organizacion(DATA_DIR / "organizacion.csv")
    fixtures, _, errors = build_organizacion(org_df, cat_lookups)

    assert errors == []

    centro_fixtures = [f for f in fixtures if f["model"] == "organizacion.centrodeservicio"]
    assert len(centro_fixtures) == 2
    for cf in centro_fixtures:
        assert "estado" in cf["fields"]
        assert isinstance(cf["fields"]["estado"], int)
