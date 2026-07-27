from dnd_board_game.actors import ActorId
from dnd_board_game.combat import (
    attack_source_at_actor_level,
    attack_source_at_cast_level,
    healing_source_at_cast_level,
)
from dnd_board_game.scenarios import (
    build_encounter_from_scenario,
    load_scenario,
)


def _cleric_sources():
    encounter = build_encounter_from_scenario(
        load_scenario("content/scenarios/abandoned_watchtower.json")
    )
    cleric_id = ActorId("cleric")
    attacks = {
        source.id: source
        for source in encounter.attack_source_options_by_actor[cleric_id]
    }
    healing = {
        source.id: source
        for source in encounter.healing_sources_by_actor[cleric_id]
    }
    return attacks, healing


def test_damage_spell_adds_dice_per_slot_level() -> None:
    attacks, _healing = _cleric_sources()

    scaled = attack_source_at_cast_level(attacks["radiant_line"], 3)

    assert scaled.cast_level == 3
    assert scaled.damage_components[0].dice is not None
    assert scaled.damage_components[0].dice.format() == "3d8"
    assert "3d8" in scaled.damage_hint


def test_healing_spell_adds_dice_per_slot_level() -> None:
    _attacks, healing = _cleric_sources()

    scaled = healing_source_at_cast_level(healing["healing_word"], 3)

    assert scaled.cast_level == 3
    assert scaled.healing_dice_count == 3
    assert scaled.healing_hint == "3d4 + 3"


def test_base_level_keeps_authored_formula() -> None:
    attacks, healing = _cleric_sources()

    damage = attack_source_at_cast_level(attacks["radiant_line"], 1)
    restored = healing_source_at_cast_level(healing["healing_word"], 1)

    assert damage.damage_components[0].dice is not None
    assert damage.damage_components[0].dice.format() == "1d8"
    assert restored.healing_hint == "1d4 + 3"


def test_cantrip_damage_scales_at_character_level_breakpoints() -> None:
    attacks, _healing = _cleric_sources()
    sacred_flame = attacks["sacred_flame"]

    assert sacred_flame.damage_components[0].dice is not None
    assert sacred_flame.damage_components[0].dice.format() == "1d8"
    assert (
        attack_source_at_actor_level(sacred_flame, 5)
        .damage_components[0]
        .dice.format()
        == "2d8"
    )
    assert (
        attack_source_at_actor_level(sacred_flame, 17)
        .damage_components[0]
        .dice.format()
        == "4d8"
    )


def test_srd_healing_and_attack_spells_use_caster_ability() -> None:
    attacks, healing = _cleric_sources()

    assert (
        sum(
            modifier.value
            for modifier in attacks["inflict_wounds"].attack_roll_request.modifiers
        )
        == 5
    )
    assert healing["cure_wounds"].healing_hint == "1d8 + 3"
    assert (
        attack_source_at_cast_level(attacks["inflict_wounds"], 2)
        .damage_components[0]
        .dice.format()
        == "4d10"
    )
    assert healing_source_at_cast_level(healing["cure_wounds"], 2).healing_hint == "2d8 + 3"
