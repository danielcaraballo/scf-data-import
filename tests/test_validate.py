from scf_import.transform.row import NormalizedRow
from scf_import.validate import validate_batch, validate_required_fields


def test_validate_required_fields_legacy() -> None:
    records = [{"fields": {"nombre": "Chevrolet"}}]
    errors = validate_required_fields("cat", records, ["nombre"])
    assert errors == []

    records = [{"fields": {"nombre": ""}}]
    errors = validate_required_fields("cat", records, ["nombre"])
    assert len(errors) == 1
    assert "nombre' está vacío" in errors[0]


def test_validate_batch_deduplication() -> None:
    row1 = NormalizedRow(
        row_id=1,
        raw_data={},
        canonical={
            "marca": "TOYOTA",
            "modelo": "Hilux",
            "estado": "ZULIA",
            "numero_economico": "7612345",
            "vin": "VIN001",
            "placa": "MPPEE-001",
        },
    )
    row2 = NormalizedRow(
        row_id=2,
        raw_data={},
        canonical={
            "marca": "TOYOTA",
            "modelo": "Hilux",
            "estado": "ZULIA",
            "numero_economico": "7612345",
            "vin": "VIN002",
            "placa": "MPPEE-002",
        },
    )
    row3 = NormalizedRow(
        row_id=3,
        raw_data={},
        canonical={
            "marca": "TOYOTA",
            "modelo": "Hilux",
            "estado": "ZULIA",
            "numero_economico": "7699999",
            "vin": "VIN003",
            "placa": "MPPEE-003",
        },
    )

    validated = validate_batch([row1, row2, row3])
    assert "SAP_DUPLICADO" in validated[0].flags
    assert "SAP_DUPLICADO" in validated[1].flags
    assert "SAP_DUPLICADO" not in validated[2].flags
    assert validated[0].quality == "ADVERTENCIA"
    assert validated[1].quality == "ADVERTENCIA"
    assert validated[2].quality == "OK"


def test_validate_batch_missing_required_or_identifiers() -> None:
    row_no_id = NormalizedRow(
        row_id=1,
        raw_data={},
        canonical={
            "marca": "TOYOTA",
            "modelo": "Hilux",
            "estado": "ZULIA",
            "numero_economico": "",
            "vin": "",
            "placa": "",
        },
    )
    row_no_brand = NormalizedRow(
        row_id=2,
        raw_data={},
        canonical={
            "marca": "",
            "modelo": "Hilux",
            "estado": "ZULIA",
            "numero_economico": "7612345",
            "vin": "VIN002",
            "placa": "MPPEE-002",
        },
    )

    validated = validate_batch([row_no_id, row_no_brand])
    assert validated[0].quality == "INVALIDO"
    assert "SIN_IDENTIFICADOR" in validated[0].flags

    assert validated[1].quality == "INVALIDO"
    assert "CAMPO_REQUERIDO_VACIO" in validated[1].flags
