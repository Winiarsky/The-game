import pytest

from dnd_board_game.combat import SceneFlags, scene_flag
from dnd_board_game.exploration import (
    ExplorationState,
    apply_exploration_effect,
    challenge_state_for,
    exploration_condition_matches,
    validate_exploration_effect,
)
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


def test_apply_exploration_effect_sets_scene_flag():
    result = apply_exploration_effect(
        _state(),
        {"type": "set_flag", "parameters": {"key": "scout_calmed", "value": True}},
    )

    assert result.changed is True
    assert scene_flag(result.state.flags, "scout_calmed") is True


def test_apply_exploration_effect_grants_known_resource_and_unlock_flags():
    result = apply_exploration_effect(
        _state(),
        {"type": "grant_resource", "parameters": {"resource_id": "saw"}},
    )

    assert result.changed is True
    assert "saw" in result.state.inventory_resource_ids
    assert scene_flag(result.state.flags, "saw_found") is True


def test_apply_exploration_effect_reveals_hidden_point():
    state = _state()

    result = apply_exploration_effect(
        state,
        {"type": "reveal_point", "parameters": {"point_id": "wounded_scout"}},
    )

    assert result.changed is True
    assert exploration_condition_matches(
        result.state,
        {"type": "point_revealed", "parameters": {"point_id": "wounded_scout"}},
    )


def test_apply_exploration_effect_adds_challenge_noise():
    result = apply_exploration_effect(
        _state(),
        {"type": "add_noise", "parameters": {"challenge_id": "closed_gate", "value": 2}},
    )

    assert result.changed is True
    assert challenge_state_for(result.state, "closed_gate").noise == 2
    assert exploration_condition_matches(
        result.state,
        {"type": "challenge_noise_at_least", "parameters": {"challenge_id": "closed_gate", "value": 2}},
    )


def test_apply_exploration_effect_unlocks_option_flag():
    result = apply_exploration_effect(
        _state(),
        {"type": "unlock_option", "parameters": {"option_id": "saw_picket"}},
    )

    assert result.changed is True
    assert scene_flag(result.state.flags, "llm_unlocked_option:saw_picket") is True


def test_validate_exploration_effect_rejects_unknown_resource():
    with pytest.raises(ValueError, match="resource_id is unknown"):
        validate_exploration_effect(
            {"type": "grant_resource", "parameters": {"resource_id": "dragon_key"}},
            _state(),
        )


def test_validate_exploration_effect_rejects_negative_noise():
    with pytest.raises(ValueError, match="non-negative integer"):
        validate_exploration_effect(
            {"type": "add_noise", "parameters": {"challenge_id": "closed_gate", "value": -1}},
            _state(),
        )
