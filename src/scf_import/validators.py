from typing import Any


def validate_required_fields(
    entity_type: str,
    records: list[dict[str, Any]],
    required: list[str],
) -> list[str]:
    errors = []
    for i, rec in enumerate(records, start=2):
        fields = rec.get("fields", {})
        for field in required:
            val = fields.get(field)
            if val is None or (isinstance(val, str) and not val.strip()):
                errors.append(f"{entity_type} fila {i}: '{field}' está vacío")
    return errors


def validate_fk_references(
    entity_type: str,
    records: list[dict[str, Any]],
    fk_field: str,
    lookup: dict[str, int],
) -> list[str]:
    errors = []
    for i, rec in enumerate(records, start=2):
        fields = rec.get("fields", {})
        val = fields.get(fk_field)
        if val and val not in lookup:
            errors.append(f"{entity_type} fila {i}: '{fk_field}' = '{val}' no existe en catálogo")
    return errors


def validate_unique(
    entity_type: str,
    records: list[dict[str, Any]],
    field: str,
) -> list[str]:
    seen: set[str] = set()
    errors = []
    for i, rec in enumerate(records, start=2):
        fields = rec.get("fields", {})
        val = fields.get(field)
        if val:
            normalized = val.strip().lower() if isinstance(val, str) else str(val)
            if normalized in seen:
                errors.append(f"{entity_type} fila {i}: '{field}' duplicado: '{val}'")
            seen.add(normalized)
    return errors
