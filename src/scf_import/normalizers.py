from typing import Any


def strip_value(val: str) -> str:
    return val.strip() if val else ""


def normalize_name(val: str) -> str:
    val = strip_value(val)
    if not val:
        return val
    return val.title().replace("S/E", "S. E.").replace("S / E", "S. E.")


def normalize_fk(val: str) -> str:
    return strip_value(val)


def normalize_vin(val: str) -> str:
    return strip_value(val).upper()


def normalize_placa(val: str) -> str:
    return strip_value(val).upper()


def normalize_anio(val: str) -> int:
    val = strip_value(val)
    if val.isdigit():
        return int(val)
    return 0


RAW_FIELDS = {"numero_economico", "serial_motor", "numero_unidad"}


def normalize_row(row: dict[str, Any], fk_fields: set[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, val in row.items():
        if key in fk_fields:
            out[key] = normalize_fk(val)
        elif key == "vin":
            out[key] = normalize_vin(val)
        elif key in ("placa", "placa_intt"):
            out[key] = normalize_placa(val)
        elif key == "anio":
            out[key] = normalize_anio(val)
        elif key in RAW_FIELDS:
            out[key] = strip_value(val)
        else:
            out[key] = normalize_name(val)
    return out
