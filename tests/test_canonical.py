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
