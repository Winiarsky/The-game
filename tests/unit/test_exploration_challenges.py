from dnd_board_game.combat import SceneFlags, scene_flag
from dnd_board_game.exploration import (
    ExplorationState,
    available_challenge_options,
    challenge_state_for,
    reveal_exploration_points,
    resolve_challenge_option,
    visible_exploration_points,
)
from dnd_board_game.rules import D20RollInput, D20RollRequest, RollModifier, RollModifierType, resolve_d20_roll
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


def _roll(total_roll: int):
    return resolve_d20_roll(D20RollInput(D20RollRequest(), total_roll))


def test_success_adds_progress_and_completes_gate_challenge():
    state = _state()
    challenge = state.challenges[0]
    option = next(item for item in challenge.options if item.id == "force_gate")

    result = resolve_challenge_option(state, challenge, option, _roll(12))

    updated = challenge_state_for(result.state, challenge.id)
    assert result.success is True
    assert updated.current_progress == 3
    assert updated.completed is True
    assert scene_flag(result.state.flags, "gate_passed") is True
    assert updated.attempts[-1].option_id == "force_gate"
    assert updated.attempts[-1].progress_added == 3
    assert updated.attempts[-1].success is True


def test_failure_still_adds_fail_forward_progress_and_complication():
    state = _state()
    challenge = state.challenges[0]
    option = next(item for item in challenge.options if item.id == "vault_gate")

    result = resolve_challenge_option(state, challenge, option, _roll(2))

    updated = challenge_state_for(result.state, challenge.id)
    assert result.success is False
    assert result.progress_added == 1
    assert updated.current_progress == 1
    assert "ryzyko_upadku" in updated.complications
    assert updated.attempts[-1].option_id == "vault_gate"
    assert updated.attempts[-1].success is False
    assert updated.attempts[-1].complications_added == ("ryzyko_upadku",)


def test_repeated_challenge_attempts_keep_history_order():
    state = _state()
    challenge = state.challenges[0]
    option = next(item for item in challenge.options if item.id == "break_picket")

    first = resolve_challenge_option(state, challenge, option, _roll(2))
    second = resolve_challenge_option(first.state, challenge, option, _roll(10))

    updated = challenge_state_for(second.state, challenge.id)
    assert [attempt.option_id for attempt in updated.attempts] == ["break_picket", "break_picket"]
    assert [attempt.total for attempt in updated.attempts] == [2, 10]
    assert updated.current_progress == 2


def test_critical_failure_uses_critical_complication():
    state = _state()
    challenge = state.challenges[0]
    option = next(item for item in challenge.options if item.id == "force_gate")

    result = resolve_challenge_option(state, challenge, option, _roll(1))

    updated = challenge_state_for(result.state, challenge.id)
    assert result.critical_failure is True
    assert result.noise_added == 3
    assert "alarm_w_strażnicy" in updated.complications


def test_force_gate_can_be_quiet_on_natural_20_or_success_margin():
    state = _state()
    challenge = state.challenges[0]
    option = next(item for item in challenge.options if item.id == "force_gate")

    natural_20 = resolve_challenge_option(state, challenge, option, _roll(20))
    high_margin_roll = resolve_d20_roll(
        D20RollInput(
            D20RollRequest(modifiers=(RollModifier("Test bonus", 10, RollModifierType.CUSTOM),)),
            12,
        )
    )
    high_margin = resolve_challenge_option(state, challenge, option, high_margin_roll)

    assert natural_20.noise_added == 0
    assert high_margin.noise_added == 0


def test_resource_locked_option_is_hidden_until_resource_is_owned():
    state = _state()
    challenge = state.challenges[0]

    assert "saw_picket" not in {option.id for option in available_challenge_options(state, challenge)}

    with_saw = ExplorationState(
        state.zones,
        state.points,
        state.party_position,
        state.flags,
        challenges=state.challenges,
        resources=state.resources,
        inventory_resource_ids=(*state.inventory_resource_ids, "saw"),
    )

    assert "saw_picket" in {option.id for option in available_challenge_options(with_saw, challenge)}


def test_courtyard_challenge_reveals_hidden_npc_after_completion():
    state = _state()
    challenge = next(item for item in state.challenges if item.id == "courtyard_search")
    option = next(item for item in challenge.options if item.id == "inspect_tracks_courtyard")

    result = resolve_challenge_option(state, challenge, option, _roll(12))
    revealed_state, revealed = reveal_exploration_points(result.state, challenge.reveals_on_complete)

    updated = challenge_state_for(result.state, challenge.id)
    assert updated.completed is True
    assert challenge.reveals_on_complete == ("wounded_scout",)
    assert [point.id for point in revealed] == ["wounded_scout"]
    assert "wounded_scout" in {point.id for point in visible_exploration_points(revealed_state.points)}
