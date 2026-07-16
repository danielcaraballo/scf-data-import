from typing import Any

import pandas as pd

from scf_import.config import CATALOG_MODELS
from scf_import.normalizers import normalize_fk, normalize_name
from scf_import.validators import validate_required_fields


def build_catalogos(
    df: pd.DataFrame,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, int]], list[str]]:
    fixtures: list[dict[str, Any]] = []
    lookups: dict[str, dict[str, int]] = {}
    errors: list[str] = []
    pk_counters: dict[str, int] = {}

    for config_key, cfg in CATALOG_MODELS.items():
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

            for csv_col, fk_info in cfg.get("fk_map", {}).items():
                raw_fk = str(row.get(csv_col, "")).strip()
                fk_name = normalize_fk(raw_fk)
                lookup_key = fk_info["lookup"]
                model_field = fk_info["field"]
                if fk_name and lookup_key in lookups and fk_name in lookups[lookup_key]:
                    fields[model_field] = lookups[lookup_key][fk_name]

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
