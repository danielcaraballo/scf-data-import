from typing import Any

import pandas as pd

from scf_import.config import ORGANIZACION_MODELS
from scf_import.normalizers import normalize_fk, normalize_name
from scf_import.validators import validate_required_fields


def build_organizacion(
    df: pd.DataFrame,
    catalog_lookups: dict[str, dict[str, int]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, int]], list[str]]:
    fixtures: list[dict[str, Any]] = []
    lookups: dict[str, dict[str, int]] = {}
    errors: list[str] = []
    pk_counters: dict[str, int] = {}

    for config_key, cfg in ORGANIZACION_MODELS.items():
        model_name: str = cfg["model"]
        subset = df[df["tipo"].str.strip().str.lower() == config_key]
        records: list[dict[str, Any]] = []
        seen_keys: set[str] = set()

        for _, row in subset.iterrows():
            raw_nombre = str(row.get("nombre", "")).strip()
            if not raw_nombre:
                continue

            nombre = normalize_name(raw_nombre)

            dedup_key = nombre.lower()
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            pk_counters[config_key] = pk_counters.get(config_key, 0) + 1
            pk = pk_counters[config_key]
            fields: dict[str, Any] = {"nombre": nombre, "estatus_activo": True}

            for field, lookup_key in cfg.get("fk_map", {}).items():
                raw_fk = str(row.get(field, "")).strip()
                fk_name = normalize_fk(raw_fk)
                if fk_name:
                    source_lookup = lookups.get(lookup_key) or catalog_lookups.get(lookup_key)
                    if source_lookup and fk_name in source_lookup:
                        fields[field] = source_lookup[fk_name]

            records.append(
                {
                    "model": model_name,
                    "pk": pk,
                    "fields": fields,
                }
            )

            if config_key not in lookups:
                lookups[config_key] = {}
            lookups[config_key][nombre] = pk

        fixtures.extend(records)

        required_fields = ["nombre"]
        errors.extend(validate_required_fields(config_key, records, required_fields))

    return fixtures, lookups, errors
