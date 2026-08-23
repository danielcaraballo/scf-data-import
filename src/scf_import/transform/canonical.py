import csv
import difflib
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

from scf_import.transform.text import clean_str, normalize_key

logger = logging.getLogger(__name__)

CATEGORY_FILE_MAP: dict[str, str] = {
    "marca": "marcas.csv",
    "modelo": "modelos.csv",
    "color": "colores.csv",
    "tipo_vehiculo": "tipos.csv",
    "categoria": "tipos.csv",
    "estatus": "estatus.csv",
    "estatus_vehiculo": "estatus.csv",
    "tipo_uso": "adscripcion.csv",
    "adscripcion": "adscripcion.csv",
    "estado": "estados.csv",
    "gerencia": "gerencias.csv",
    "unidad_usuaria": "gerencias.csv",
    "emplazamiento": "emplazamientos.csv",
    "centro_servicio": "emplazamientos.csv",
    "clase": "clases.csv",
    "clase_vehiculo": "clases.csv",
    "tipo_combustible": "combustibles.csv",
    "color_placa": "colores_placa.csv",
}


def _load_mapping_file(filepath: Path) -> tuple[dict[str, str], set[str]]:
    table: dict[str, str] = {}
    canon_set: set[str] = set()

    with filepath.open(encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header:
            return table, canon_set

        for row in reader:
            if not row or not row[0].strip():
                continue
            alias = clean_str(row[0])
            canonical = clean_str(row[1]) if len(row) > 1 else alias
            key = normalize_key(alias)
            if key:
                table[key] = canonical
            canon_key = normalize_key(canonical)
            if canon_key:
                table[canon_key] = canonical
            if canonical:
                canon_set.add(canonical)

    return table, canon_set


class CanonicalMapper:
    def __init__(self, mappings_dir: Path | str = "config/mappings") -> None:
        self.mappings_dir = Path(mappings_dir)
        self.tables: dict[str, dict[str, str]] = defaultdict(dict)
        self.canonical_sets: dict[str, set[str]] = defaultdict(set)
        self.unknown_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.load_mappings()

    def load_mappings(self) -> None:
        if not self.mappings_dir.exists():
            logger.warning("Directorio de mappings no encontrado: %s", self.mappings_dir)
            return

        loaded_files: set[str] = set()
        for cat, filename in CATEGORY_FILE_MAP.items():
            filepath = self.mappings_dir / filename
            if not filepath.exists():
                continue

            if filename in loaded_files:
                canonical_source_cat = next(
                    c for c, f in CATEGORY_FILE_MAP.items() if f == filename and c in self.tables
                )
                self.tables[cat] = self.tables[canonical_source_cat]
                self.canonical_sets[cat] = self.canonical_sets[canonical_source_cat]
                continue

            table, canon_set = _load_mapping_file(filepath)
            self.tables[cat] = table
            self.canonical_sets[cat] = canon_set
            loaded_files.add(filename)

    def map_value(
        self,
        category: str,
        raw_value: Any,
        context: dict[str, Any] | None = None,
    ) -> tuple[str, bool]:
        cleaned = clean_str(raw_value)
        if not cleaned:
            return "", True

        key = normalize_key(cleaned)
        table = self.tables.get(category, {})

        if category == "modelo" and context and "marca" in context:
            marca_key = normalize_key(context["marca"])
            composite_key = f"{marca_key}:{key}"
            if composite_key in table:
                return table[composite_key], True

        if key in table:
            return table[key], True

        self.unknown_counts[category][cleaned] += 1
        return cleaned, False

    def is_known(self, category: str, raw_value: Any) -> bool:
        cleaned = clean_str(raw_value)
        if not cleaned:
            return True
        key = normalize_key(cleaned)
        return key in self.tables.get(category, {})

    def get_canonical_catalog(self, category: str) -> list[str]:
        return sorted(self.canonical_sets.get(category, set()))

    def suggest_canonical(
        self,
        category: str,
        raw_value: Any,
        cutoff: float = 0.6,
        n: int = 1,
    ) -> list[tuple[str, float]]:
        cleaned = clean_str(raw_value)
        if not cleaned:
            return []

        canonicals = list(self.canonical_sets.get(category, set()))
        if not canonicals:
            return []

        norm_raw = normalize_key(cleaned)
        scored: list[tuple[str, float]] = []
        for canon in canonicals:
            norm_canon = normalize_key(canon)
            ratio = difflib.SequenceMatcher(None, norm_raw, norm_canon).ratio()
            if ratio >= cutoff:
                scored.append((canon, round(ratio, 2)))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:n]

    def get_unknown_records(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for cat, val_counts in sorted(self.unknown_counts.items()):
            for val, count in sorted(val_counts.items(), key=lambda x: -x[1]):
                results.append(
                    {
                        "categoria": cat,
                        "valor_original": val,
                        "ocurrencias": count,
                    }
                )
        return results

