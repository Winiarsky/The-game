import random

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.combat import (
    AttackSource,
    AttackSourceType,
    InitiativeEntry,
    InitiativeOrder,
    finish_turn,
    resolve_enemy_auto_attack,
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
        damage_die_sides=6,
        damage_modifier=2,
        damage_type="slashing",
    )


def _order(enemy: Actor, hero: Actor) -> InitiativeOrder:
    request = D20RollRequest()
    enemy_roll = resolve_d20_roll(D20RollInput(request, 20))
    hero_roll = resolve_d20_roll(D20RollInput(request, 10))
    return InitiativeOrder((InitiativeEntry(enemy, enemy_roll, 2, 0), InitiativeEntry(hero, hero_roll, 2, 1)))


def test_enemy_auto_attack_hits_with_deterministic_rng_and_applies_damage():
    enemy = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0), hp=20)
    state = start_combat((enemy, hero), _order(enemy, hero))

    result = resolve_enemy_auto_attack(BoardState(), state, enemy, _source(), random.Random(7))

    assert result.target is not None
    assert result.target.id == "hero"
    assert result.attack_roll is not None
    assert result.attack_roll.natural_roll == 11
    assert result.attack_roll.total == 15
    assert result.damage is not None
    assert result.damage.total_applied == 4
    updated_hero = next(actor for actor in result.state.actors if actor.id == hero.id)
    assert updated_hero.hp == 16
    assert "trafia" in result.message


def test_enemy_auto_attack_skips_when_no_legal_target():
    enemy = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(5, 5), hp=20)
    state = start_combat((enemy, hero), _order(enemy, hero))

    result = resolve_enemy_auto_attack(BoardState(), state, enemy, _source(), random.Random(7))

    assert result.target is None
    assert result.attack_roll is None
    assert result.action_used is True
    assert "nie ma legalnego celu" in result.message


def test_enemy_auto_attack_ignores_defeated_targets():
    enemy = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    defeated_hero = _actor("hero", Faction.ALLY, Coordinate(0, 0), hp=0)
    state = start_combat((enemy, defeated_hero), _order(enemy, defeated_hero))

    result = resolve_enemy_auto_attack(BoardState(), state, enemy, _source(), random.Random(7))

    assert result.target is None


def test_enemy_auto_attack_action_is_not_available_twice_in_turn():
    enemy = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0), hp=20)
    state = start_combat((enemy, hero), _order(enemy, hero))

    first = resolve_enemy_auto_attack(BoardState(), state, enemy, _source(), random.Random(7))
    second = resolve_enemy_auto_attack(BoardState(), first.state, enemy, _source(), random.Random(7))

    assert first.action_used is True
    assert second.action_used is False
    assert "już zużyta" in second.message


def test_finish_turn_after_enemy_attack_advances_to_hero():
    enemy = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0), hp=20)
    state = start_combat((enemy, hero), _order(enemy, hero))

    result = resolve_enemy_auto_attack(BoardState(), state, enemy, _source(), random.Random(7))
    next_state = finish_turn(result.state)

    assert next_state.initiative_order.current_actor.id == hero.id
