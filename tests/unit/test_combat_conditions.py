from dataclasses import replace

from dnd_board_game.actors import Actor, ActorId, Faction
from dnd_board_game.combat import (
    CombatCondition,
    ConditionState,
    InitiativeEntry,
    InitiativeOrder,
    attack_source_with_prone,
    drop_prone,
    has_condition,
    path_with_condition_cost,
    stand_up,
    start_combat,
)
from dnd_board_game.combat.attack_flow import AttackKind, AttackSource, AttackSourceType
from dnd_board_game.rules import D20RollInput, D20RollRequest, RollMode, resolve_d20_roll
from dnd_board_game.world import Coordinate, PathResult


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


def _state(hero: Actor, enemy: Actor):
    request = D20RollRequest()
    order = InitiativeOrder(
        (
            InitiativeEntry(hero, resolve_d20_roll(D20RollInput(request, 20)), 0, 0),
            InitiativeEntry(enemy, resolve_d20_roll(D20RollInput(request, 10)), 0, 1),
        )
    )
    return start_combat((hero, enemy), order)


def _source(mode: RollMode = RollMode.NORMAL) -> AttackSource:
    return AttackSource(
        "Miecz",
        AttackSourceType.WEAPON,
        5,
        D20RollRequest(mode=mode),
        attack_kind=AttackKind.MELEE,
    )


def test_drop_prone_is_free_and_standing_costs_half_base_speed() -> None:
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(2, 0))
    state = _state(hero, enemy)

    dropped = drop_prone(state, hero)
    stood = stand_up(dropped.state, hero)

    assert dropped.accepted
    assert dropped.state.turn_action == state.turn_action
    assert has_condition(dropped.state.condition_states, "hero", CombatCondition.PRONE)
    assert stood.accepted
    assert stood.movement_cost_feet == 15
    assert stood.state.turn_action.movement_used_feet == 15
    assert not has_condition(stood.state.condition_states, "hero", CombatCondition.PRONE)


def test_standing_is_rejected_without_half_speed_remaining() -> None:
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(2, 0))
    state = replace(
        _state(hero, enemy),
        condition_states=(ConditionState("hero", CombatCondition.PRONE),),
    )
    state = replace(
        state,
        turn_action=replace(state.turn_action, movement_used_feet=20),
    )

    result = stand_up(state, hero)

    assert not result.accepted
    assert "Za mało ruchu" in result.message
    assert result.state == state


def test_crawling_adds_base_distance_on_top_of_normal_or_difficult_cost() -> None:
    prone = (ConditionState("hero", CombatCondition.PRONE),)
    normal = PathResult(
        Coordinate(0, 0),
        Coordinate(2, 0),
        (Coordinate(0, 0), Coordinate(1, 0), Coordinate(2, 0)),
        10,
        True,
    )
    difficult = PathResult(
        Coordinate(0, 0),
        Coordinate(1, 0),
        (Coordinate(0, 0), Coordinate(1, 0)),
        10,
        True,
    )

    assert path_with_condition_cost(normal, prone, "hero").cost_feet == 20
    assert path_with_condition_cost(difficult, prone, "hero").cost_feet == 15
    assert not path_with_condition_cost(
        normal,
        prone,
        "hero",
        movement_budget_feet=15,
    ).valid


def test_prone_attack_factors_follow_distance_and_cancel_each_other() -> None:
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    close_enemy = _actor("enemy", Faction.ENEMY, Coordinate(1, 0))
    far_enemy = replace(close_enemy, position=Coordinate(3, 0))

    attacker_prone = attack_source_with_prone(
        _source(),
        (ConditionState("hero", CombatCondition.PRONE),),
        hero,
        close_enemy,
    )
    close_target_prone = attack_source_with_prone(
        _source(),
        (ConditionState("enemy", CombatCondition.PRONE),),
        hero,
        close_enemy,
    )
    far_target_prone = attack_source_with_prone(
        _source(mode=RollMode.ADVANTAGE),
        (ConditionState("enemy", CombatCondition.PRONE),),
        hero,
        far_enemy,
    )
    both_prone = attack_source_with_prone(
        _source(),
        (
            ConditionState("hero", CombatCondition.PRONE),
            ConditionState("enemy", CombatCondition.PRONE),
        ),
        hero,
        close_enemy,
    )

    assert attacker_prone.attack_roll_request.mode == RollMode.DISADVANTAGE
    assert close_target_prone.attack_roll_request.mode == RollMode.ADVANTAGE
    assert far_target_prone.attack_roll_request.mode == RollMode.NORMAL
    assert both_prone.attack_roll_request.mode == RollMode.NORMAL
