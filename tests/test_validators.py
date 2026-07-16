import pytest

from scf_import.validators import (
    validate_required_fields,
    validate_fk_references,
    validate_unique,
)


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


class TestValidateFkReferences:
    def test_no_errors_when_fk_exists(self) -> None:
        records = [{"fields": {"marca": "Chevrolet"}}]
        lookup = {"Chevrolet": 1}
        errors = validate_fk_references("vehiculos", records, "marca", lookup)
        assert errors == []

    def test_error_when_fk_missing(self) -> None:
        records = [{"fields": {"marca": "Ferrari"}}]
        lookup = {"Chevrolet": 1}
        errors = validate_fk_references("vehiculos", records, "marca", lookup)
        assert len(errors) == 1
        assert "Ferrari" in errors[0]

    def test_ignores_empty_fk(self) -> None:
        records = [{"fields": {"marca": ""}}]
        errors = validate_fk_references("vehiculos", records, "marca", {})
        assert errors == []


class TestValidateUnique:
    def test_no_errors_when_unique(self) -> None:
        records = [
            {"fields": {"nombre": "Chevrolet"}},
            {"fields": {"nombre": "Ford"}},
        ]
        errors = validate_unique("cat", records, "nombre")
        assert errors == []

    def test_error_on_duplicate(self) -> None:
        records = [
            {"fields": {"nombre": "Chevrolet"}},
            {"fields": {"nombre": "Chevrolet"}},
        ]
        errors = validate_unique("cat", records, "nombre")
        assert len(errors) == 1
        assert "duplicado" in errors[0]

    def test_case_insensitive_duplicate(self) -> None:
        records = [
            {"fields": {"nombre": "chevrolet"}},
            {"fields": {"nombre": "Chevrolet"}},
        ]
        errors = validate_unique("cat", records, "nombre")
        assert len(errors) == 1

    def test_ignores_empty_values(self) -> None:
        records = [
            {"fields": {"nombre": ""}},
            {"fields": {"nombre": ""}},
        ]
        errors = validate_unique("cat", records, "nombre")
        assert errors == []
