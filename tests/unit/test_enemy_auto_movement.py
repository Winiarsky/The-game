import random
from dataclasses import replace

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.combat import (
    AttackSource,
    AttackSourceType,
    CombatCondition,
    ConditionState,
    InitiativeEntry,
    InitiativeOrder,
    resolve_enemy_auto_turn,
    start_combat,
)
from dnd_board_game.rules import D20RollInput, D20RollRequest, RollModifier, RollModifierType, resolve_d20_roll
from dnd_board_game.world import BoardState, Coordinate


def _actor(actor_id: str, faction: Faction, position: Coordinate, hp: int = 10) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id,
        ac=12,
        hp=hp,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=faction,
        ability_scores=AbilityScores(dexterity=14),
    )


def _source() -> AttackSource:
    return AttackSource(
        name="Szabla",
        source_type=AttackSourceType.WEAPON,
        range_feet=5,
        attack_roll_request=D20RollRequest(
            modifiers=(RollModifier("Premia ataku goblina", 4, RollModifierType.CUSTOM, stacking_key="goblin_attack"),)
        ),
        damage_fixed=1,
        damage_type="slashing",
    )


def _order(enemy: Actor, hero: Actor) -> InitiativeOrder:
    request = D20RollRequest()
    return InitiativeOrder(
        (
            InitiativeEntry(enemy, resolve_d20_roll(D20RollInput(request, 20)), 2, 0),
            InitiativeEntry(hero, resolve_d20_roll(D20RollInput(request, 10)), 2, 1),
        )
    )


def test_enemy_moves_toward_target_when_no_attack_is_available():
    enemy = _actor("goblin", Faction.ENEMY, Coordinate(0, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(4, 0), hp=20)
    state = start_combat((enemy, hero), _order(enemy, hero))

    result = resolve_enemy_auto_turn(BoardState(), state, enemy, _source(), random.Random(7))

    assert result.movement_path is not None
    assert result.movement_path.destination == Coordinate(3, 0)
    assert result.target is not None
    assert result.target.id == "hero"
    assert result.action_used is True


def test_enemy_without_reachable_target_still_moves_without_stack_trace():
    enemy = _actor("goblin", Faction.ENEMY, Coordinate(0, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(10, 0), hp=20)
    state = start_combat((enemy, hero), _order(enemy, hero))

    result = resolve_enemy_auto_turn(BoardState(), state, enemy, _source(), random.Random(7))

    assert result.movement_path is not None
    assert result.target is None
    assert result.action_used is True
    assert "nadal nie ma legalnego celu" in result.message


def test_prone_enemy_stands_before_moving_and_spends_half_speed() -> None:
    enemy = _actor("goblin", Faction.ENEMY, Coordinate(0, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(4, 0), hp=20)
    state = replace(
        start_combat((enemy, hero), _order(enemy, hero)),
        condition_states=(ConditionState("goblin", CombatCondition.PRONE),),
    )

    result = resolve_enemy_auto_turn(BoardState(), state, enemy, _source(), random.Random(7))

    assert result.movement_path is not None
    assert result.movement_path.cost_feet == 15
    assert result.state.turn_action.movement_used_feet == 30
    assert result.state.condition_states == ()
    assert "wstaje" in result.message
