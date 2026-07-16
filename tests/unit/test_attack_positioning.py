from dataclasses import replace

from dnd_board_game.actors import Actor, ActorId, Faction
from dnd_board_game.combat import (
    AttackKind,
    AttackSource,
    AttackSourceType,
    CoverLevel,
    SceneObject,
    attack_source_with_positioning,
    dexterity_save_cover_modifiers,
    evaluate_attack_positioning,
)
from dnd_board_game.combat.setup import SetupVisibility
from dnd_board_game.rules import D20RollRequest, RollMode
from dnd_board_game.world import BLOCKING_TERRAIN, BoardState, Coordinate


def _actor(actor_id: str, faction: Faction, position: Coordinate) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id,
        ac=12,
        hp=10,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=faction,
    )


def _source(*, kind: AttackKind = AttackKind.RANGED, mode: RollMode = RollMode.NORMAL) -> AttackSource:
    return AttackSource(
        "Kusza" if kind == AttackKind.RANGED else "Miecz",
        AttackSourceType.WEAPON,
        80 if kind == AttackKind.RANGED else 5,
        D20RollRequest(mode=mode),
        attack_kind=kind,
    )


def _cover(name: str, position: Coordinate, bonus: int) -> SceneObject:
    return SceneObject(
        name.lower(),
        name,
        (position,),
        "",
        visibility=SetupVisibility.VISIBLE,
        projectile_cover_bonus=bonus,
    )


def test_intervening_scene_object_grants_half_cover() -> None:
    attacker = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    target = _actor("goblin", Faction.ENEMY, Coordinate(4, 0))

    positioning = evaluate_attack_positioning(
        BoardState(),
        attacker,
        target,
        _source(),
        (attacker, target),
        (_cover("Wóz", Coordinate(2, 0), 2),),
    )

    assert positioning.cover_level == CoverLevel.HALF
    assert positioning.cover_bonus == 2
    assert positioning.cover_sources == ("Wóz",)


def test_three_quarters_cover_wins_without_stacking_with_half_cover() -> None:
    attacker = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    target = _actor("goblin", Faction.ENEMY, Coordinate(5, 0))

    positioning = evaluate_attack_positioning(
        BoardState(),
        attacker,
        target,
        _source(),
        (attacker, target),
        (
            _cover("Wóz", Coordinate(2, 0), 2),
            _cover("Blanki", Coordinate(3, 0), 5),
        ),
    )

    assert positioning.cover_level == CoverLevel.THREE_QUARTERS
    assert positioning.cover_bonus == 5
    assert positioning.cover_sources == ("Blanki",)


def test_cover_bonus_applies_only_to_dexterity_saving_throws() -> None:
    attacker = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    target = _actor("goblin", Faction.ENEMY, Coordinate(4, 0))
    source = AttackSource(
        "Płomień",
        AttackSourceType.SPELL,
        60,
        D20RollRequest(),
        save_ability="dexterity",
        attack_kind=AttackKind.RANGED,
    )
    positioning = evaluate_attack_positioning(
        BoardState(),
        attacker,
        target,
        source,
        (attacker, target),
        (_cover("Blanki", Coordinate(2, 0), 5),),
    )

    dexterity = dexterity_save_cover_modifiers("dexterity", positioning)

    assert positioning.cover_level == CoverLevel.THREE_QUARTERS
    assert [(modifier.label, modifier.value) for modifier in dexterity] == [
        ("3/4 osłony", 5)
    ]
    assert dexterity_save_cover_modifiers("constitution", positioning) == ()


def test_intervening_living_creature_grants_half_cover() -> None:
    attacker = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    target = _actor("goblin", Faction.ENEMY, Coordinate(4, 0))
    bystander = _actor("cleric", Faction.ALLY, Coordinate(2, 0))

    positioning = evaluate_attack_positioning(
        BoardState(), attacker, target, _source(), (attacker, target, bystander)
    )

    assert positioning.cover_level == CoverLevel.HALF
    assert positioning.cover_bonus == 2
    assert positioning.cover_sources == ("cleric",)


def test_blocked_line_of_sight_is_total_cover() -> None:
    board = BoardState()
    board.set_terrain(Coordinate(2, 0), BLOCKING_TERRAIN)
    attacker = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    target = _actor("goblin", Faction.ENEMY, Coordinate(4, 0))

    positioning = evaluate_attack_positioning(
        board, attacker, target, _source(), (attacker, target)
    )

    assert positioning.cover_level == CoverLevel.TOTAL
    assert positioning.total_cover is True


def test_ranged_attack_in_melee_has_disadvantage_and_cancels_advantage() -> None:
    attacker = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    target = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    positioning = evaluate_attack_positioning(
        BoardState(), attacker, target, _source(), (attacker, target)
    )

    normal = attack_source_with_positioning(_source(), positioning)
    with_advantage = attack_source_with_positioning(
        _source(mode=RollMode.ADVANTAGE), positioning
    )

    assert positioning.ranged_threat_actor_ids == ("goblin",)
    assert normal.attack_roll_request.mode == RollMode.DISADVANTAGE
    assert with_advantage.attack_roll_request.mode == RollMode.NORMAL
    assert normal.attack_roll_request.modifiers[-1].label == "Atak dystansowy w zwarciu"


def test_melee_attack_is_not_penalized_by_adjacent_enemy() -> None:
    attacker = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    target = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    positioning = evaluate_attack_positioning(
        BoardState(), attacker, target, _source(kind=AttackKind.MELEE), (attacker, target)
    )

    assert positioning.ranged_threat_actor_ids == ()
    assert attack_source_with_positioning(
        _source(kind=AttackKind.MELEE), positioning
    ).attack_roll_request.mode == RollMode.NORMAL


def test_melee_attacker_flanks_with_living_ally_on_opposite_side_by_default() -> None:
    attacker = _actor("hero", Faction.ALLY, Coordinate(1, 2))
    target = _actor("goblin", Faction.ENEMY, Coordinate(2, 2))
    ally = _actor("rogue", Faction.ALLY, Coordinate(3, 2))

    positioning = evaluate_attack_positioning(
        BoardState(),
        attacker,
        target,
        _source(kind=AttackKind.MELEE),
        (attacker, target, ally),
    )
    effective = attack_source_with_positioning(
        _source(kind=AttackKind.MELEE), positioning
    )

    assert positioning.flanking_ally_ids == ("rogue",)
    assert effective.attack_roll_request.mode == RollMode.ADVANTAGE
    assert effective.attack_roll_request.modifiers[-1].label == "Flankowanie"


def test_diagonal_opposite_corners_also_flank() -> None:
    attacker = _actor("hero", Faction.ALLY, Coordinate(1, 1))
    target = _actor("goblin", Faction.ENEMY, Coordinate(2, 2))
    ally = _actor("rogue", Faction.ALLY, Coordinate(3, 3))

    positioning = evaluate_attack_positioning(
        BoardState(),
        attacker,
        target,
        _source(kind=AttackKind.MELEE),
        (attacker, target, ally),
    )

    assert positioning.flanking_ally_ids == ("rogue",)


def test_adjacent_ally_not_on_opposite_side_does_not_flank() -> None:
    attacker = _actor("hero", Faction.ALLY, Coordinate(1, 2))
    target = _actor("goblin", Faction.ENEMY, Coordinate(2, 2))
    ally = _actor("rogue", Faction.ALLY, Coordinate(2, 3))

    positioning = evaluate_attack_positioning(
        BoardState(),
        attacker,
        target,
        _source(kind=AttackKind.MELEE),
        (attacker, target, ally),
    )

    assert positioning.flanking_ally_ids == ()


def test_ranged_attack_does_not_gain_flanking_advantage() -> None:
    attacker = _actor("hero", Faction.ALLY, Coordinate(1, 2))
    target = _actor("goblin", Faction.ENEMY, Coordinate(2, 2))
    ally = _actor("rogue", Faction.ALLY, Coordinate(3, 2))

    positioning = evaluate_attack_positioning(
        BoardState(), attacker, target, _source(), (attacker, target, ally)
    )

    assert positioning.flanking_ally_ids == ()


def test_flanking_can_be_explicitly_disabled() -> None:
    attacker = _actor("hero", Faction.ALLY, Coordinate(1, 2))
    target = _actor("goblin", Faction.ENEMY, Coordinate(2, 2))
    ally = _actor("rogue", Faction.ALLY, Coordinate(3, 2))

    positioning = evaluate_attack_positioning(
        BoardState(),
        attacker,
        target,
        _source(kind=AttackKind.MELEE),
        (attacker, target, ally),
        flanking_enabled=False,
    )

    assert positioning.flanking_ally_ids == ()


def test_defeated_ally_does_not_provide_flanking() -> None:
    attacker = _actor("hero", Faction.ALLY, Coordinate(1, 2))
    target = _actor("goblin", Faction.ENEMY, Coordinate(2, 2))
    ally = replace(_actor("rogue", Faction.ALLY, Coordinate(3, 2)), hp=0)

    positioning = evaluate_attack_positioning(
        BoardState(),
        attacker,
        target,
        _source(kind=AttackKind.MELEE),
        (attacker, target, ally),
    )

    assert positioning.flanking_ally_ids == ()


def test_flanking_advantage_cancels_existing_disadvantage() -> None:
    attacker = _actor("hero", Faction.ALLY, Coordinate(1, 2))
    target = _actor("goblin", Faction.ENEMY, Coordinate(2, 2))
    ally = _actor("rogue", Faction.ALLY, Coordinate(3, 2))
    source = _source(kind=AttackKind.MELEE, mode=RollMode.DISADVANTAGE)
    positioning = evaluate_attack_positioning(
        BoardState(), attacker, target, source, (attacker, target, ally)
    )

    effective = attack_source_with_positioning(source, positioning)

    assert effective.attack_roll_request.mode == RollMode.NORMAL
