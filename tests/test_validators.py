import pytest

from scf_import.validators import validate_required_fields


class TestValidateRequiredFields:
    def test_no_errors_when_field_present(self) -> None:
        records = [{"fields": {"nombre": "Chevrolet"}}]
        errors = validate_required_fields("cat", records, ["nombre"])
        assert errors == []

    def test_error_when_field_empty(self) -> None:
        records = [{"fields": {"nombre": ""}}]
        errors = validate_required_fields("cat", records, ["nombre"])
        assert len(errors) == 1
        assert "nombre' está vacío" in errors[0]

    def test_error_when_field_missing(self) -> None:
        records = [{"fields": {}}]
        errors = validate_required_fields("cat", records, ["nombre"])
        assert len(errors) == 1
