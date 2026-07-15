import pytest

from dnd_board_game.combat import SceneFlags
from dnd_board_game.exploration import (
    ExplorationState,
    FixtureOperation,
    apply_fixture_action,
    build_crafting_source_registry,
    plan_fixture_action,
)
from dnd_board_game.scenarios import build_exploration_from_scenario, load_scenario


def _state_and_actors():
    exploration = build_exploration_from_scenario(
        load_scenario("content/scenarios/abandoned_watchtower.json")
    )
    state = ExplorationState(
        exploration.zones,
        exploration.points,
        exploration.party_position,
        SceneFlags(),
        challenges=exploration.challenges,
        resources=exploration.resources,
        inventory_resource_ids=exploration.initial_resource_ids,
    )
    return state, exploration.actors


def test_detach_fixture_changes_runtime_state_and_releases_authored_items() -> None:
    state, actors = _state_and_actors()
    source_id = "zone:gate:fixture:gate_corroded_hinges"
    plan = plan_fixture_action(state, source_id=source_id, operation=FixtureOperation.DETACH)

    result = apply_fixture_action(state, plan, success=True)

    assert result.changed is True
    assert result.released_item_ids == ("detached_gate_metal",)
    runtime = result.state.fixture_states[0]
    assert runtime.condition == "detached"
    assert runtime.detached is True
    registry = build_crafting_source_registry(result.state, actors)
    assert registry.source_by_id(source_id).usable is False
    metal = registry.source_by_id("zone:gate:item:detached_gate_metal")
    assert metal is not None and metal.usable is True and metal.quantity == 2


def test_failed_fixture_action_does_not_change_fixture_state() -> None:
    state, _actors = _state_and_actors()
    plan = plan_fixture_action(
        state,
        source_id="zone:gate:fixture:gate_corroded_hinges",
        operation=FixtureOperation.DETACH,
    )

    result = apply_fixture_action(state, plan, success=False)

    assert result.changed is False
    assert result.state == state


def test_fixture_operation_must_be_authored_for_target() -> None:
    state, _actors = _state_and_actors()

    with pytest.raises(ValueError, match="nie jest dozwolona"):
        plan_fixture_action(
            state,
            source_id="zone:gate:fixture:gate_corroded_hinges",
            operation=FixtureOperation.OPEN,
        )


def test_completed_detachment_cannot_be_repeated() -> None:
    state, _actors = _state_and_actors()
    plan = plan_fixture_action(
        state,
        source_id="zone:gate:fixture:gate_corroded_hinges",
        operation=FixtureOperation.DETACH,
    )
    changed = apply_fixture_action(state, plan, success=True)

    with pytest.raises(ValueError, match="nie jest już dostępny"):
        plan_fixture_action(
            changed.state,
            source_id=plan.source_id,
            operation=FixtureOperation.DETACH,
        )
