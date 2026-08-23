from dataclasses import dataclass, field
from typing import Any

from scf_import.transform.canonical import CanonicalMapper
from scf_import.transform.fields import (
    extract_subtype_from_model,
    normalize_anio,
    normalize_km,
    normalize_placa,
    normalize_sap,
    normalize_unidad,
    normalize_vin,
)
from scf_import.transform.text import clean_str, normalize_code


@dataclass
class NormalizedRow:
    row_id: int
    raw_data: dict[str, str]
    canonical: dict[str, Any]
    flags: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    quality: str = "OK"

    def to_master_dict(self) -> dict[str, Any]:
        out = dict(self.canonical)
        out["calidad"] = self.quality
        out["flags"] = "; ".join(self.flags)
        out["errores"] = "; ".join(self.errors)
        out["advertencias"] = "; ".join(self.warnings)
        return out


def _transform_identifiers(
    raw_dict: dict[str, str],
    rules: dict[str, Any],
    flags: list[str],
    canonical: dict[str, Any],
) -> None:
    raw_sap = raw_dict.get("numero_economico", "")
    sap_rules = rules.get("sap", {})
    sap_val, sap_flags = normalize_sap(raw_sap, sap_rules)
    canonical["numero_economico"] = sap_val
    flags.extend(sap_flags)

    raw_vin = raw_dict.get("vin", "")
    vin_rules = rules.get("vin", {})
    vin_val, vin_flags = normalize_vin(raw_vin, vin_rules)
    canonical["vin"] = vin_val
    flags.extend(vin_flags)

    raw_placa = raw_dict.get("placa", "")
    placa_rules = rules.get("placa", {})
    placa_val, placa_flags = normalize_placa(raw_placa, placa_rules)
    canonical["placa"] = placa_val
    flags.extend(placa_flags)

    raw_placa_intt = raw_dict.get("placa_intt", "")
    placa_intt_val, placa_intt_flags = normalize_placa(raw_placa_intt, placa_rules)
    canonical["placa_intt"] = placa_intt_val
    flags.extend(placa_intt_flags)

    canonical["serial_motor"] = normalize_code(raw_dict.get("serial_motor", ""))
    canonical["numero_unidad"], _ = normalize_unidad(raw_dict.get("numero_unidad", ""))


def _transform_model_and_brand(
    raw_dict: dict[str, str],
    mapper: CanonicalMapper,
    flags: list[str],
    warnings: list[str],
    canonical: dict[str, Any],
) -> None:
    raw_marca = raw_dict.get("marca", "")
    marca_val, marca_known = mapper.map_value("marca", raw_marca)
    canonical["marca"] = marca_val
    if not marca_known and raw_marca.strip():
        flags.append("MARCA_DESCONOCIDA")
        warnings.append(f"Marca no catalogada: '{raw_marca}'")

    raw_modelo = raw_dict.get("modelo", "")
    base_modelo, extracted_subtype = extract_subtype_from_model(raw_modelo)
    modelo_val, modelo_known = mapper.map_value(
        "modelo", raw_modelo, context={"marca": marca_val}
    )
    if not modelo_known and base_modelo != raw_modelo:
        modelo_val, modelo_known = mapper.map_value(
            "modelo", base_modelo, context={"marca": marca_val}
        )

    canonical["modelo"] = modelo_val
    canonical["subtipo"] = extracted_subtype or ""
    if not modelo_known and raw_modelo.strip():
        flags.append("MODELO_DESCONOCIDO")
        warnings.append(f"Modelo no catalogado: '{raw_modelo}'")


def _transform_categoricals(
    raw_dict: dict[str, str],
    mapper: CanonicalMapper,
    flags: list[str],
    warnings: list[str],
    canonical: dict[str, Any],
) -> None:
    _transform_model_and_brand(raw_dict, mapper, flags, warnings, canonical)

    for field_name, cat in (
        ("color", "color"),
        ("clase", "clase"),
        ("categoria", "tipo_vehiculo"),
        ("tipo_combustible", "tipo_combustible"),
        ("estatus", "estatus"),
        ("tipo_uso", "tipo_uso"),
        ("color_placa", "color_placa"),
    ):
        raw_val = raw_dict.get(field_name, "")
        val, known = mapper.map_value(cat, raw_val)
        canonical[field_name] = val
        if not known and raw_val.strip() and field_name == "color":
            flags.append("COLOR_DESCONOCIDO")

    raw_estado = raw_dict.get("estado", "")
    estado_val, estado_known = mapper.map_value("estado", raw_estado)
    canonical["estado"] = estado_val
    if not estado_known and raw_estado.strip():
        flags.append("ESTADO_DESCONOCIDO")

    raw_gerencia = raw_dict.get("gerencia", "")
    gerencia_val, _ = mapper.map_value("gerencia", raw_gerencia)
    canonical["gerencia"] = gerencia_val

    raw_uu = raw_dict.get("unidad_usuaria", "") or raw_gerencia
    uu_val, _ = mapper.map_value("unidad_usuaria", raw_uu)
    canonical["unidad_usuaria"] = uu_val

    raw_empl = raw_dict.get("emplazamiento", "")
    empl_val, empl_known = mapper.map_value("emplazamiento", raw_empl)
    canonical["emplazamiento"] = empl_val
    if not empl_known and raw_empl.strip() and raw_empl.strip().upper() != "N/A":
        flags.append("EMPLAZAMIENTO_DESCONOCIDO")
        warnings.append(f"Emplazamiento no catalogado: '{raw_empl}'")


def _transform_numerics_and_metadata(
    raw_dict: dict[str, str],
    rules: dict[str, Any],
    flags: list[str],
    canonical: dict[str, Any],
) -> None:
    raw_anio = raw_dict.get("anio", "")
    anio_rules = rules.get("anio", {})
    min_year = int(anio_rules.get("min", 1950))
    max_year = int(anio_rules.get("max", 2026))
    anio_val, anio_flags = normalize_anio(raw_anio, min_year, max_year)
    canonical["anio"] = anio_val
    flags.extend(anio_flags)

    raw_km = raw_dict.get("kilometraje", "")
    km_val, km_flags = normalize_km(raw_km)
    canonical["kilometraje"] = km_val if km_val is not None else ""
    flags.extend(km_flags)

    for extra_col in (
        "tipo_aceite",
        "litros_aceite",
        "observaciones",
        "observacion_estatus",
        "nombres",
        "apellidos",
        "cedula_identidad",
        "numero_personal",
        "cargo",
        "telefono",
        "correo_institucional",
    ):
        if extra_col in raw_dict:
            canonical[extra_col] = clean_str(raw_dict[extra_col])


def transform_row(
    row_idx: int,
    raw_dict: dict[str, str],
    mapper: CanonicalMapper,
    rules: dict[str, Any] | None = None,
) -> NormalizedRow:
    rules = rules or {}
    flags: list[str] = []
    warnings: list[str] = []
    canonical: dict[str, Any] = {}

    _transform_identifiers(raw_dict, rules, flags, canonical)
    _transform_categoricals(raw_dict, mapper, flags, warnings, canonical)
    _transform_numerics_and_metadata(raw_dict, rules, flags, canonical)

    return NormalizedRow(
        row_id=row_idx,
        raw_data=raw_dict,
        canonical=canonical,
        flags=flags,
        warnings=warnings,
    )
