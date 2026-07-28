import json
from pathlib import Path

from dnd_board_game.scenarios.loader import _read_item_definition


CONTENT_ANCHOR = Path("content/character_creation/catalog.json")
SPELL_ROOT = Path("content/spells")


def _spell_materials() -> tuple[tuple[str, dict[str, object]], ...]:
    materials: list[tuple[str, dict[str, object]]] = []
    for path in sorted(SPELL_ROOT.glob("*.json")):
        spell = json.loads(path.read_text(encoding="utf-8"))
        materials.extend(
            (path.stem, material)
            for material in spell.get("components", {}).get("materials", [])
        )
    return tuple(materials)


def test_every_spell_material_resolves_to_an_item_with_sufficient_value() -> None:
    materials = _spell_materials()

    assert len({material["item_id"] for _, material in materials}) == 70
    for spell_id, material in materials:
        item = _read_item_definition(CONTENT_ANCHOR, str(material["item_id"]))
        assert int(item.get("value_cp", 0)) >= int(
            material.get("minimum_value_cp", 0)
        ), spell_id


def test_costly_or_consumed_materials_are_not_focus_replaceable() -> None:
    gated = {
        str(material["item_id"]): (
            int(material.get("minimum_value_cp", 0)),
            bool(material.get("consumed", False)),
        )
        for _, material in _spell_materials()
        if int(material.get("minimum_value_cp", 0))
        or bool(material.get("consumed", False))
    }

    assert gated["spell_component_find_familiar"] == (1000, True)
    assert gated["spell_component_illusory_script"] == (1000, True)
    assert gated["spell_component_identify"] == (10000, False)
    assert gated["spell_component_warding_bond"] == (5000, False)
