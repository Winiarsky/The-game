from dnd_board_game.combat import SceneFlags
from dnd_board_game.exploration import (
    ExplorationState,
    create_temporary_item,
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
    template = challenge.llm_policy.temporary_item_templates[0]
    option = next(item for item in challenge.options if item.id == "force_gate")
    return state, template, option


def test_temporary_item_is_available_only_for_its_matching_scene_approach():
    state, template, option = _state_and_gate()

    state, item = create_temporary_item(
        state,
        template,
        zone_id="gate",
        source_materials=("stare deski", "metalowe okucia"),
    )

    assert item.id == "temporary:improvised_battering_ram"
    assert item.uses_remaining == 2
    assert [resource.id for resource in matching_resources(state, option)] == [item.id]


def test_temporary_item_tracks_uses_and_becomes_unavailable():
    state, template, option = _state_and_gate()
    state, item = create_temporary_item(
        state,
        template,
        zone_id="gate",
        source_materials=("stare deski", "metalowe okucia"),
    )

    state, first_use = use_temporary_item(state, item.id)
    state, final_use = use_temporary_item(state, item.id)

    assert first_use.uses_remaining == 1
    assert final_use.uses_remaining == 0
    assert matching_resources(state, option) == ()
