import json
from pathlib import Path


def _nested_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {
            key
            for nested in value.values()
            for key in _nested_keys(nested)
        }
    if isinstance(value, list):
        return {key for nested in value for key in _nested_keys(nested)}
    return set()


def test_level_three_damage_and_condition_spells_are_not_assisted_or_narrative() -> None:
    catalog = json.loads(
        Path("content/character_creation/catalog.json").read_text(encoding="utf-8")
    )
    accessible_ids = {
        spell_id
        for character_class in catalog["classes"]
        for field in ("cantrip_choices", "spell_choices")
        for spell_id in character_class.get(field) or ()
    }
    audited: list[str] = []
    for path in Path("content/spells").glob("*.json"):
        spell = json.loads(path.read_text(encoding="utf-8"))
        if spell.get("id") not in accessible_ids or int(spell.get("level", 99)) > 2:
            continue
        effect = spell.get("effect") or {}
        keys = _nested_keys(effect)
        has_damage = bool(
            {
                "damage",
                "damage_type",
                "damage_dice_count",
                "ongoing_damage_dice_count",
                "damage_fixed",
            }
            & keys
        )
        has_condition = bool(
            {
                "condition",
                "condition_options",
                "additional_conditions",
                "on_hit_condition",
            }
            & keys
        ) or effect.get("effect_kind") == "apply_condition"
        if not (has_damage or has_condition):
            continue
        audited.append(str(spell["id"]))
        assert effect.get("kind") in {"attack", "combat_action"}, spell["id"]
        assert effect.get("kind") != "assisted", spell["id"]
    assert audited
