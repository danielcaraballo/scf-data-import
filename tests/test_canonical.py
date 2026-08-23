from pathlib import Path

from scf_import.transform.canonical import CanonicalMapper

MAPPINGS_DIR = Path(__file__).resolve().parents[1] / "config" / "mappings"


class TestCanonicalMapper:
    def test_known_brand_mapping(self) -> None:
        mapper = CanonicalMapper(MAPPINGS_DIR)
        val, is_known = mapper.map_value("marca", "CHEVY")
        assert is_known is True
        assert val == "CHEVROLET"

        val, is_known = mapper.map_value("marca", "General Motor")
        assert is_known is True
        assert val == "CHEVROLET"

        val, is_known = mapper.map_value("marca", "Toyota")
        assert is_known is True
        assert val == "TOYOTA"

    def test_known_state_mapping(self) -> None:
        mapper = CanonicalMapper(MAPPINGS_DIR)
        val, is_known = mapper.map_value("estado", "CAPITAL")
        assert is_known is True
        assert val == "DISTRITO CAPITAL"

        val, is_known = mapper.map_value("estado", "LA GUAIRA")
        assert is_known is True
        assert val == "VARGAS"

    def test_unknown_value_tracking(self) -> None:
        mapper = CanonicalMapper(MAPPINGS_DIR)
        val, is_known = mapper.map_value("marca", "MARCA_INVENTADA_XYZ")
        assert is_known is False
        assert val == "MARCA_INVENTADA_XYZ"

        unknowns = mapper.get_unknown_records()
        assert any(
            u["categoria"] == "marca" and u["valor_original"] == "MARCA_INVENTADA_XYZ"
            for u in unknowns
        )

    def test_empty_value_is_known_and_clean(self) -> None:
        mapper = CanonicalMapper(MAPPINGS_DIR)
        val, is_known = mapper.map_value("marca", "")
        assert is_known is True
        assert val == ""

    def test_suggest_canonical_fuzzy_match(self) -> None:
        mapper = CanonicalMapper(MAPPINGS_DIR)
        # Typo in CHEVROLET -> CHEVROLETT
        suggestions = mapper.suggest_canonical("marca", "CHEVROLETT", cutoff=0.7)
        assert len(suggestions) >= 1
        sug_name, score = suggestions[0]
        assert sug_name == "CHEVROLET"
        assert score > 0.8

        # Typo in TOYOTA -> TOYOTTA
        suggestions = mapper.suggest_canonical("marca", "TOYOTTA", cutoff=0.7)
        assert len(suggestions) >= 1
        assert suggestions[0][0] == "TOYOTA"

        # Empty / non-matching
        assert mapper.suggest_canonical("marca", "") == []
        assert mapper.suggest_canonical("marca", "TOTALMENTE_DESCONOCIDO_123456789") == []

    def test_suggest_canonical_caching(self) -> None:
        mapper = CanonicalMapper(MAPPINGS_DIR)
        first_call = mapper.suggest_canonical("marca", "CHEVROLETT", cutoff=0.7)
        second_call = mapper.suggest_canonical("marca", "CHEVROLETT", cutoff=0.7)
        assert first_call == second_call
        assert ("marca", "CHEVROLETT", 0.7, 1) in mapper._suggestion_cache

