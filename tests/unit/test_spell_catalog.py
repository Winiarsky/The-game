import json
from pathlib import Path

from dnd_board_game.combat import SpellAreaShape
from dnd_board_game.scenarios.loader import (
    _parse_attack,
    _parse_healing_source,
    _parse_spell_definition,
    _spell_effect_payload,
)


SPELL_ROOT = Path("content/spells")
SRD_SPELL_IDS = {
    "sacred_flame",
    "healing_word",
    "fire_bolt",
    "burning_hands",
    "cure_wounds",
    "inflict_wounds",
}


def _spell_data(spell_id: str) -> dict[str, object]:
    return json.loads((SPELL_ROOT / f"{spell_id}.json").read_text(encoding="utf-8"))


def test_first_srd_spell_tranche_has_open_source_metadata() -> None:
    for spell_id in SRD_SPELL_IDS:
        data = _spell_data(spell_id)
        assert data["ruleset_id"] == "dnd_5e_2014"
        assert data["source_pack_ids"] == ["srd_5_1_cc_by_4_0"]


def test_fire_bolt_and_burning_hands_adapt_to_attack_sources() -> None:
    fire_bolt_data = _spell_data("fire_bolt")
    fire_bolt = _parse_spell_definition(fire_bolt_data, "fire_bolt")
    collection, effect = _spell_effect_payload(fire_bolt_data, fire_bolt)
    fire_bolt_attack = _parse_attack(effect, "catalog_caster")

    assert collection == "attack"
    assert fire_bolt_attack.range_feet == 120
    assert fire_bolt_attack.damage_components[0].dice is not None
    assert fire_bolt_attack.damage_components[0].dice.format() == "1d10"
    assert fire_bolt_attack.cantrip_damage_dice_per_tier == 1

    burning_hands_data = _spell_data("burning_hands")
    burning_hands = _parse_spell_definition(burning_hands_data, "burning_hands")
    _collection, effect = _spell_effect_payload(burning_hands_data, burning_hands)
    burning_hands_attack = _parse_attack(effect, "catalog_caster")

    assert burning_hands_attack.area is not None
    assert burning_hands_attack.area.shape == SpellAreaShape.CONE
    assert burning_hands_attack.area.length_feet == 15
    assert burning_hands_attack.save_damage_on_success == "half"
    assert burning_hands_attack.upcast_damage_dice_per_level == 1


def test_cure_wounds_uses_touch_range_and_caster_ability() -> None:
    data = _spell_data("cure_wounds")
    spell = _parse_spell_definition(data, "cure_wounds")
    collection, effect = _spell_effect_payload(data, spell)
    healing = _parse_healing_source(effect, "catalog_caster")

    assert collection == "healing"
    assert healing.range_feet == 5
    assert healing.ability == "wisdom"
    assert healing.healing_die_sides == 8
    assert healing.upcast_healing_dice_per_level == 1
