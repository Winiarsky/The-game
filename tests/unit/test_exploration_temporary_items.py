from dnd_board_game.combat import SceneFlags
from dnd_board_game.exploration import (
    CraftingComponentSelection,
    CraftingDraft,
    ExplorationState,
    build_crafting_source_registry,
    craft_temporary_item,
    matching_resources,
    use_temporary_item,
)
from dnd_board_game.scenarios import build_exploration_from_scenario, load_scenario


def _state_and_gate():
    exploration = build_exploration_from_scenario(load_scenario("content/scenarios/abandoned_watchtower.json"))
    state = ExplorationState(
        exploration.zones,
        exploration.points,
        exploration.party_position,
        SceneFlags(),
        challenges=exploration.challenges,
        resources=exploration.resources,
        inventory_resource_ids=exploration.initial_resource_ids,
    )
    challenge = next(item for item in exploration.challenges if item.id == "closed_gate")
    option = next(item for item in challenge.options if item.id == "force_gate")
    draft = CraftingDraft(
        label="Prowizoryczny taran",
        description="Długa deska obciążona kamieniem.",
        purpose_id="heavy_force",
        components=(
            CraftingComponentSelection("zone:gate:item:gate_rotten_planks"),
            CraftingComponentSelection("zone:gate:item:gate_loose_stones"),
        ),
    )
    state, item = craft_temporary_item(
        state,
        draft,
        build_crafting_source_registry(state, exploration.actors),
        exploration.crafting_policy,
    )
    return state, item, option


def test_temporary_item_is_available_only_for_its_matching_scene_approach():
    state, item, option = _state_and_gate()

    assert item.id == "temporary:crafted:1"
    assert item.uses_remaining == 2
    assert [resource.id for resource in matching_resources(state, option)] == [item.id]


def test_temporary_item_tracks_uses_and_becomes_unavailable():
    state, item, option = _state_and_gate()

    state, first_use = use_temporary_item(state, item.id)
    state, final_use = use_temporary_item(state, item.id)

    assert first_use.uses_remaining == 1
    assert final_use.uses_remaining == 0
    assert matching_resources(state, option) == ()
