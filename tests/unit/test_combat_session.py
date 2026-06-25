from dataclasses import replace

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.combat import (
    CombatStatus,
    InitiativeEntry,
    InitiativeOrder,
    current_actor,
    finish_turn,
    replace_actor,
    start_combat,
    use_turn_action,
)
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.world import Coordinate


def _actor(actor_id: str, faction: Faction, col: int, hp: int = 10) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id,
        ac=12,
        hp=hp,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(col, 0),
        faction=faction,
        ability_scores=AbilityScores(dexterity=14),
    )


def _order(*actors: Actor) -> InitiativeOrder:
    request = D20RollRequest()
    entries = []
    for index, actor in enumerate(actors):
        roll = resolve_d20_roll(D20RollInput(request, 20 - index))
        entries.append(InitiativeEntry(actor, roll, 2, index))
    return InitiativeOrder(tuple(entries))


def test_start_combat_selects_first_initiative_actor():
    hero = _actor("hero", Faction.ALLY, 0)
    goblin = _actor("goblin", Faction.ENEMY, 1)

    state = start_combat((hero, goblin), _order(hero, goblin))

    assert current_actor(state).id == hero.id
    assert state.round_number == 1


def test_turn_action_can_only_be_used_once():
    hero = _actor("hero", Faction.ALLY, 0)
    goblin = _actor("goblin", Faction.ENEMY, 1)
    state = start_combat((hero, goblin), _order(hero, goblin))

    first = use_turn_action(state)
    second = use_turn_action(first.state)

    assert first.accepted is True
    assert second.accepted is False
    assert "już zużyta" in second.message


def test_finish_turn_advances_actor_and_resets_action():
    hero = _actor("hero", Faction.ALLY, 0)
    goblin = _actor("goblin", Faction.ENEMY, 1)
    state = use_turn_action(start_combat((hero, goblin), _order(hero, goblin))).state

    state = finish_turn(state)

    assert current_actor(state).id == goblin.id
    assert use_turn_action(state).accepted is True


def test_finish_turn_wraps_to_next_round():
    hero = _actor("hero", Faction.ALLY, 0)
    goblin = _actor("goblin", Faction.ENEMY, 1)
    state = start_combat((hero, goblin), _order(hero, goblin))

    state = finish_turn(finish_turn(state))

    assert current_actor(state).id == hero.id
    assert state.round_number == 2


def test_defeated_side_finishes_combat():
    hero = _actor("hero", Faction.ALLY, 0)
    goblin = _actor("goblin", Faction.ENEMY, 1)
    state = start_combat((hero, goblin), _order(hero, goblin))

    state = replace_actor(state, replace(goblin, hp=0))

    assert state.status == CombatStatus.FINISHED
    assert state.winner == Faction.ALLY
