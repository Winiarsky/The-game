import pytest

from dnd_board_game.actors import Actor, ActorId, Faction
from dnd_board_game.combat import (
    AttackActionStatus,
    AttackSource,
    AttackSourceType,
    attack_declaration_from_state,
    cancel_attack_action,
    select_attack_target,
    start_attack_action,
)
from dnd_board_game.rules import D20RollRequest
from dnd_board_game.world import BoardState, Coordinate


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


def _source() -> AttackSource:
    return AttackSource("Miecz", AttackSourceType.WEAPON, 5, D20RollRequest(), "1d6 slashing")


def test_start_attack_action_collects_legal_targets():
    board = BoardState()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))

    state = start_attack_action(board, hero, (hero, goblin), _source())

    assert state.status == AttackActionStatus.SELECTING_TARGET
    assert [target.id for target in state.legal_targets] == ["goblin"]


def test_select_attack_target_by_id_and_position():
    board = BoardState()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    state = start_attack_action(board, hero, (hero, goblin), _source())

    selected_by_id = select_attack_target(state, target_id="goblin")
    selected_by_position = select_attack_target(state, position=Coordinate(1, 0))

    assert selected_by_id.selected_target.id == "goblin"
    assert selected_by_id.status == AttackActionStatus.TARGET_SELECTED
    assert selected_by_position.selected_target.id == "goblin"
    assert attack_declaration_from_state(selected_by_id).target.id == "goblin"


def test_select_illegal_target_is_rejected_and_cancel_works():
    board = BoardState()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    state = start_attack_action(board, hero, (hero, goblin), _source())

    with pytest.raises(ValueError):
        select_attack_target(state, target_id="missing")

    cancelled = cancel_attack_action(state)
    assert cancelled.status == AttackActionStatus.CANCELLED
    assert cancelled.selected_target is None
