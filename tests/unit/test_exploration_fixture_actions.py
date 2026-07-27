import pytest

from dnd_board_game.combat import SceneFlags
from dnd_board_game.exploration import (
    ExplorationState,
    FixtureOperation,
    apply_fixture_damage,
    apply_fixture_action,
    build_crafting_source_registry,
    fixture_runtime_state,
    fixture_scene_objects,
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


def test_locked_door_projects_blocking_total_cover_until_opened() -> None:
    state, _actors = _state_and_actors()
    gate = state.zones[0].fixtures[0]

    closed = fixture_scene_objects(state, zone_id="gate")
    gate_object = next(item for item in closed if item.name == "Stara brama")

    assert fixture_runtime_state(
        state,
        zone_id="gate",
        fixture=gate,
    ).locked is True
    assert gate_object.blocks_movement is True
    assert gate_object.projectile_cover_bonus == 5

    unlocked = apply_fixture_action(
        state,
        plan_fixture_action(
            state,
            source_id="zone:gate:fixture:watchtower_gate",
            operation=FixtureOperation.UNLOCK,
        ),
        success=True,
    )
    opened = apply_fixture_action(
        unlocked.state,
        plan_fixture_action(
            unlocked.state,
            source_id="zone:gate:fixture:watchtower_gate",
            operation=FixtureOperation.OPEN,
        ),
        success=True,
    )
    open_object = next(
        item
        for item in fixture_scene_objects(opened.state, zone_id="gate")
        if item.name == "Stara brama"
    )

    assert open_object.blocks_movement is False
    assert open_object.projectile_cover_bonus == 0


def test_container_unlock_open_and_loot_releases_contents_once() -> None:
    state, _actors = _state_and_actors()
    source_id = "zone:gate:fixture:gate_supply_chest"

    unlocked = apply_fixture_action(
        state,
        plan_fixture_action(
            state,
            source_id=source_id,
            operation=FixtureOperation.UNLOCK,
        ),
        success=True,
    )
    opened = apply_fixture_action(
        unlocked.state,
        plan_fixture_action(
            unlocked.state,
            source_id=source_id,
            operation=FixtureOperation.OPEN,
        ),
        success=True,
    )
    looted = apply_fixture_action(
        opened.state,
        plan_fixture_action(
            opened.state,
            source_id=source_id,
            operation=FixtureOperation.LOOT,
        ),
        success=True,
    )

    assert looted.released_item_ids == ("gate_chest_arrows",)
    runtime = next(
        item
        for item in looted.state.fixture_states
        if item.fixture_id == "gate_supply_chest"
    )
    assert runtime.opened is True
    assert runtime.locked is False
    assert runtime.looted is True
    with pytest.raises(ValueError, match="już opróżniony"):
        plan_fixture_action(
            looted.state,
            source_id=source_id,
            operation=FixtureOperation.LOOT,
        )


def test_fixture_damage_threshold_and_destruction_remove_combat_projection() -> None:
    state, _actors = _state_and_actors()
    source_id = "zone:gate:fixture:gate_supply_chest"

    resisted = apply_fixture_damage(state, source_id=source_id, raw_damage=2)
    destroyed = apply_fixture_damage(
        resisted.state,
        source_id=source_id,
        raw_damage=10,
    )

    assert resisted.applied_damage == 0
    assert resisted.current_hit_points == 10
    assert destroyed.destroyed is True
    assert destroyed.released_item_ids == ("gate_chest_arrows",)
    assert all(
        item.name != "Skrzynia strażnicza"
        for item in fixture_scene_objects(destroyed.state, zone_id="gate")
    )
