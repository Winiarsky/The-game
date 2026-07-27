import json
from dataclasses import replace
from pathlib import Path

from dnd_board_game.actors import AbilityScores, Actor, ActorId, CreatureSize, Faction
from dnd_board_game.combat import (
    AttackKind,
    attack_source_for_actor,
    attack_source_with_positioning,
    evaluate_attack_positioning,
    legal_attack_targets,
)
from dnd_board_game.rules import RollMode
from dnd_board_game.scenarios.loader import (
    _attack_source_from_definition,
    _attacks_with_item_source,
    _item_attack_definitions,
    _parse_attack,
)
from dnd_board_game.world import BoardDimensions, BoardState, Coordinate


ITEMS = Path("content/items")


def _weapon_data(item_id: str) -> dict:
    return json.loads((ITEMS / f"{item_id}.json").read_text(encoding="utf-8"))


def _definitions(item_id: str):
    data = _weapon_data(item_id)
    attacks = _attacks_with_item_source(
        _item_attack_definitions(data),
        item_id,
        proficiency_id=item_id,
    )
    return tuple(_parse_attack(attack, f"item {item_id}") for attack in attacks)


def _actor(
    *,
    size: CreatureSize = CreatureSize.MEDIUM,
    proficiencies=(),
    strength: int = 16,
    dexterity: int = 14,
    position: Coordinate = Coordinate(0, 0),
) -> Actor:
    from dnd_board_game.actors import ProficiencyProfile

    return Actor(
        ActorId("hero"),
        "Bohater",
        14,
        20,
        0,
        30,
        position,
        Faction.ALLY,
        size=size,
        ability_scores=AbilityScores(strength=strength, dexterity=dexterity),
        proficiency_bonus=2,
        proficiencies=ProficiencyProfile(weapons=tuple(proficiencies)),
    )


def _source(item_id: str, actor: Actor, index: int = 0):
    return _attack_source_from_definition(
        _definitions(item_id)[index],
        f"weapon:{item_id}",
        actor,
    )


def test_srd_weapon_catalog_has_complete_2014_matrix() -> None:
    weapons = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in ITEMS.glob("*.json")
        if json.loads(path.read_text(encoding="utf-8")).get("kind") == "weapon"
    ]

    assert len(weapons) == 37
    assert sum(item["weapon"]["category"] == "simple" for item in weapons) == 14
    assert sum(item["weapon"]["category"] == "martial" for item in weapons) == 23
    assert all(item["source_pack_ids"] == ["srd_5_1_cc_by_4_0"] for item in weapons)
    assert all(_definitions(item["id"]) for item in weapons)


def test_weapon_damage_and_category_proficiency_are_bound_to_current_actor() -> None:
    actor = _actor(proficiencies=("martial_weapons",))
    source = attack_source_for_actor(_source("longsword", actor), actor)

    assert source.damage_components[0].formula() == "1d8 + 3"
    assert source.damage_modifier == 3
    assert source.attack_roll_request.modifiers[0].value == 3
    assert source.attack_roll_request.modifiers[1].value == 2

    weaker = replace(
        actor,
        ability_scores=replace(actor.ability_scores, strength=8),
    )
    rebound = attack_source_for_actor(source, weaker)
    assert rebound.damage_components[0].formula() == "1d8 - 1"


def test_finesse_and_thrown_generate_explicit_ability_and_range_variants() -> None:
    definitions = _definitions("dagger")

    assert [(item.attack_kind, item.ability) for item in definitions] == [
        (AttackKind.MELEE, "dexterity"),
        (AttackKind.MELEE, "strength"),
        (AttackKind.RANGED, "dexterity"),
        (AttackKind.RANGED, "strength"),
    ]
    assert definitions[2].range_feet == 20
    assert definitions[2].long_range_feet == 60


def test_long_range_is_legal_but_applies_disadvantage() -> None:
    attacker = _actor(position=Coordinate(0, 0))
    target = replace(
        _actor(position=Coordinate(40, 0)),
        id=ActorId("target"),
        faction=Faction.ENEMY,
    )
    source = attack_source_for_actor(_source("longbow", attacker), attacker)
    board = BoardState(BoardDimensions(cols=50, rows=5))

    assert [item.id for item in legal_attack_targets(board, attacker, (attacker, target), source)] == [
        "target"
    ]
    positioning = evaluate_attack_positioning(
        board,
        attacker,
        target,
        source,
        (attacker, target),
    )
    adjusted = attack_source_with_positioning(source, positioning)
    assert positioning.long_range is True
    assert adjusted.attack_roll_request.mode == RollMode.DISADVANTAGE


def test_heavy_lance_and_net_special_rules_are_typed() -> None:
    small = _actor(size=CreatureSize.SMALL)
    heavy = attack_source_for_actor(_source("heavy_crossbow", small), small)
    assert heavy.attack_roll_request.mode == RollMode.DISADVANTAGE

    lance = _source("lance", _actor())
    assert lance.reach_feet == 10
    assert lance.weapon_special_rule.value == "lance"

    net = _source("net", _actor())
    assert net.on_hit_condition == "restrained"
    assert net.limited_attacks is True
    assert net.range_feet == 5
    assert net.long_range_feet == 15
