from dataclasses import replace

from dnd_board_game.actors import Faction
from dnd_board_game.application import MagicMovementFlowService
from dnd_board_game.combat import (
    ActionUse,
    InitiativeEntry,
    InitiativeOrder,
    MagicMovementKind,
    current_actor,
    forced_movement_destination,
    replace_actor,
    start_combat,
)
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.scenarios import build_encounter_from_scenario, load_scenario
from dnd_board_game.world import BoardState, Coordinate


class FixedRng:
    def __init__(self, value: int) -> None:
        self.value = value

    def randint(self, _minimum: int, _maximum: int) -> int:
        return self.value


def _fixture(action_id: str):
    encounter = build_encounter_from_scenario(
        load_scenario("content/scenarios/gate_skirmish.json")
    )
    cleric = next(actor for actor in encounter.actors if str(actor.id) == "cleric")
    enemy = next(actor for actor in encounter.actors if actor.faction == Faction.ENEMY)
    roll = resolve_d20_roll(D20RollInput(D20RollRequest(), 15))
    state = start_combat(
        (cleric, enemy),
        InitiativeOrder(
            (
                InitiativeEntry(cleric, roll, 1, 0),
                InitiativeEntry(enemy, roll, 1, 1),
            )
        ),
    )
    action = next(
        action
        for action in encounter.combat_actions_by_actor[cleric.id]
        if action.id == action_id
    )
    return encounter, cleric, enemy, action, state


def test_teleport_uses_bonus_action_slot_and_does_not_spend_movement():
    encounter, cleric, _enemy, action, state = _fixture("veil_step")
    service = MagicMovementFlowService()
    slot_before = next(
        slot.remaining for slot in cleric.spell_slots if slot.level == 1
    )
    prepared = service.prepare(
        board=encounter.board,
        state=state,
        action=action,
        cast_level=1,
        scene_objects=encounter.scene_objects,
    )
    assert prepared.pending is not None
    destination = prepared.pending.legal_positions[0]

    confirmed = service.confirm(
        board=encounter.board,
        state=state,
        action=action,
        pending=prepared.pending,
        rng=FixedRng(1),
        position=destination,
        scene_objects=encounter.scene_objects,
    )

    caster_after = current_actor(confirmed.state)
    assert caster_after.position == destination
    assert confirmed.state.turn_action.bonus_action_use == ActionUse.ACTION_USED
    assert confirmed.state.turn_action.action_use == ActionUse.ACTION_AVAILABLE
    assert confirmed.state.turn_action.movement_used_feet == 0
    assert next(
        slot.remaining for slot in caster_after.spell_slots if slot.level == 1
    ) == slot_before - 1


def test_failed_strength_save_pushes_target_without_spending_target_movement():
    encounter, cleric, enemy, action, state = _fixture("repelling_pulse")
    service = MagicMovementFlowService()
    expected = forced_movement_destination(
        encounter.board,
        state,
        cleric,
        enemy,
        kind=MagicMovementKind.PUSH,
        distance_feet=10,
        scene_objects=encounter.scene_objects,
    )
    prepared = service.prepare(
        board=encounter.board,
        state=state,
        action=action,
        cast_level=1,
        scene_objects=encounter.scene_objects,
    )
    assert prepared.pending is not None
    assert str(enemy.id) in prepared.pending.legal_target_ids

    confirmed = service.confirm(
        board=encounter.board,
        state=state,
        action=action,
        pending=prepared.pending,
        rng=FixedRng(1),
        target_id=str(enemy.id),
        scene_objects=encounter.scene_objects,
    )

    enemy_after = next(
        actor for actor in confirmed.state.actors if actor.id == enemy.id
    )
    assert expected != enemy.position
    assert enemy_after.position == expected
    assert confirmed.state.turn_action.action_use == ActionUse.ACTION_USED
    assert confirmed.state.turn_action.movement_used_feet == 0


def test_successful_save_prevents_pull_but_still_consumes_cast():
    encounter, _cleric, enemy, action, state = _fixture("grasping_current")
    service = MagicMovementFlowService()
    prepared = service.prepare(
        board=encounter.board,
        state=state,
        action=action,
        cast_level=1,
        scene_objects=encounter.scene_objects,
    )
    assert prepared.pending is not None

    confirmed = service.confirm(
        board=encounter.board,
        state=state,
        action=action,
        pending=prepared.pending,
        rng=FixedRng(20),
        target_id=str(enemy.id),
        scene_objects=encounter.scene_objects,
    )

    enemy_after = next(
        actor for actor in confirmed.state.actors if actor.id == enemy.id
    )
    assert enemy_after.position == enemy.position
    assert confirmed.state.turn_action.action_use == ActionUse.ACTION_USED


def test_forced_movement_stops_at_last_tile_before_wall():
    _encounter, cleric, enemy, _action, state = _fixture("repelling_pulse")
    cleric = replace(cleric, position=Coordinate(2, 2))
    state = replace_actor(state, cleric)
    enemy = replace(enemy, position=Coordinate(3, 2))
    state = replace_actor(state, enemy)
    board = BoardState()
    board.add_wall(Coordinate(4, 2), Coordinate(5, 2))

    destination = forced_movement_destination(
        board,
        state,
        cleric,
        enemy,
        kind=MagicMovementKind.PUSH,
        distance_feet=20,
    )

    assert destination == Coordinate(4, 2)
