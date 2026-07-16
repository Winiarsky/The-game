from dnd_board_game.combat import SceneFlags
from dnd_board_game.exploration import (
    ExplorationState,
    ExplorationTrapAction,
    ExplorationTrapStatus,
    resolve_trap_action,
    match_revealed_trap_action,
    reveal_trap,
    trap_state_for,
)
from dnd_board_game.scenarios import build_exploration_from_scenario, load_scenario


def _state() -> ExplorationState:
    exploration = build_exploration_from_scenario(
        load_scenario("content/scenarios/abandoned_watchtower.json")
    )
    return ExplorationState(
        exploration.zones,
        exploration.points,
        exploration.party_position,
        SceneFlags(),
        challenges=exploration.challenges,
        resources=exploration.resources,
        inventory_resource_ids=exploration.initial_resource_ids,
        traps=exploration.traps,
    )


def test_trap_is_hidden_until_revealed() -> None:
    state = _state()

    revealed = reveal_trap(state, "gate_alarm_wire")

    assert trap_state_for(state, "gate_alarm_wire").status == ExplorationTrapStatus.HIDDEN
    assert trap_state_for(revealed, "gate_alarm_wire").status == ExplorationTrapStatus.REVEALED


def test_successful_disarm_and_bypass_prevent_trigger() -> None:
    state = reveal_trap(_state(), "gate_alarm_wire")
    trap = state.traps[0]

    disarmed = resolve_trap_action(
        state,
        trap,
        ExplorationTrapAction.DISARM,
        total=12,
    )
    bypassed = resolve_trap_action(
        state,
        trap,
        ExplorationTrapAction.BYPASS,
        total=10,
    )

    assert disarmed.success is True
    assert disarmed.triggered is False
    assert trap_state_for(disarmed.state, trap.id).status == ExplorationTrapStatus.DISARMED
    assert bypassed.success is True
    assert trap_state_for(bypassed.state, trap.id).status == ExplorationTrapStatus.BYPASSED


def test_failed_disarm_triggers_trap() -> None:
    state = reveal_trap(_state(), "gate_alarm_wire")
    trap = state.traps[0]

    result = resolve_trap_action(
        state,
        trap,
        ExplorationTrapAction.DISARM,
        total=11,
    )

    assert result.success is False
    assert result.triggered is True
    assert trap_state_for(result.state, trap.id).status == ExplorationTrapStatus.TRIGGERED


def test_revealed_trap_actions_are_matched_from_authored_examples() -> None:
    state = reveal_trap(_state(), "gate_alarm_wire")

    matched = match_revealed_trap_action(
        state,
        "chcę ostrożnie ominąć tę linkę",
        zone_id="gate",
    )

    assert matched is not None
    trap, action = matched
    assert trap.id == "gate_alarm_wire"
    assert action == ExplorationTrapAction.BYPASS
