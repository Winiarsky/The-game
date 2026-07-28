from dnd_board_game.combat import SceneFlags, scene_flag
from dnd_board_game.exploration import (
    ExplorationState,
    grant_resource,
    matching_resources,
    remove_resource,
    resolve_challenge_option,
)
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.scenarios import build_exploration_from_scenario, load_scenario


def _state():
    exploration = build_exploration_from_scenario(load_scenario("content/scenarios/abandoned_watchtower.json"))
    return ExplorationState(
        exploration.zones,
        exploration.points,
        exploration.party_position,
        SceneFlags(),
        challenges=exploration.challenges,
        resources=exploration.resources,
        inventory_resource_ids=exploration.initial_resource_ids,
    )


def _roll(natural: int):
    return resolve_d20_roll(D20RollInput(D20RollRequest(), natural))


def test_matching_resources_only_returns_owned_items_with_matching_tags():
    state = _state()
    challenge = state.challenges[0]
    vault = next(option for option in challenge.options if option.id == "vault_gate")
    force = next(option for option in challenge.options if option.id == "force_gate")

    assert [resource.id for resource in matching_resources(state, vault)] == ["rope", "wedge"]
    assert matching_resources(state, force) == ()


def test_resource_can_mitigate_failure_noise_and_complication():
    state = _state()
    challenge = state.challenges[0]
    option = next(item for item in challenge.options if item.id == "lever_gate")
    wedge = next(resource for resource in state.resources if resource.id == "wedge")

    result = resolve_challenge_option(state, challenge, option, _roll(2), wedge)

    assert result.noise_added == 1
    assert "jammed_gate" not in result.complications_added


def test_granting_saw_adds_resource_and_unlock_flag():
    state = _state()

    updated = grant_resource(state, "saw")

    assert "saw" in updated.inventory_resource_ids
    assert scene_flag(updated.flags, "saw_found") is True


def test_exploration_resource_exposes_item_roll_modifier_and_consumption_policy():
    state = _state()
    rope = next(resource for resource in state.resources if resource.id == "rope")
    wedge = next(resource for resource in state.resources if resource.id == "wedge")

    modifier = rope.as_roll_modifier()

    assert modifier is not None
    assert modifier.value == 2
    assert modifier.modifier_type.value == "item"
    assert rope.consume_on_use is False
    assert wedge.consume_on_use is True


def test_removing_owned_resource_preserves_other_resources():
    state = _state()

    updated = remove_resource(state, "wedge")

    assert updated.inventory_resource_ids == ("rope",)
