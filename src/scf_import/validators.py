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
