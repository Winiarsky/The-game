from dataclasses import replace

from dnd_board_game.combat import SceneFlags, scene_flag
from dnd_board_game.exploration import (
    ExplorationState,
    active_option_bonuses_for_actor,
    actors_matching_challenge_option,
    available_challenge_options,
    available_challenge_options_for_actors,
    challenge_state_for,
    option_roll_modifiers_for_actor,
    reveal_exploration_points,
    resolve_challenge_option,
    visible_exploration_points,
)
from dnd_board_game.inventory import break_inventory_item
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


def test_force_success_clears_both_gate_blockers_and_completes_challenge():
    state = _state()
    challenge = state.challenges[0]
    option = next(item for item in challenge.options if item.id == "force_gate")

    result = resolve_challenge_option(state, challenge, option, _roll(16))

    updated = challenge_state_for(result.state, challenge.id)
    assert result.success is True
    assert updated.current_progress == 0
    assert updated.completed is True
    assert scene_flag(result.state.flags, "gate_passed") is True
    assert scene_flag(result.state.flags, "gate_lock_cleared") is True
    assert scene_flag(result.state.flags, "gate_bolt_cleared") is True
    assert updated.noise == 2
    assert updated.attempts[-1].option_id == "force_gate"
    assert updated.attempts[-1].progress_added == 0
    assert updated.attempts[-1].success is True


def test_vault_failure_adds_complication_without_fake_gate_progress():
    state = _state()
    challenge = state.challenges[0]
    option = next(item for item in challenge.options if item.id == "vault_gate")

    result = resolve_challenge_option(state, challenge, option, _roll(2))

    updated = challenge_state_for(result.state, challenge.id)
    assert result.success is False
    assert result.progress_added == 0
    assert updated.current_progress == 0
    assert scene_flag(result.state.flags, "gate_bolt_cleared") is not True
    assert "ryzyko_upadku" in updated.complications
    assert updated.attempts[-1].option_id == "vault_gate"
    assert updated.attempts[-1].success is False
    assert updated.attempts[-1].complications_added == ("ryzyko_upadku",)


def test_failed_force_attempt_can_be_retried_and_alert_is_capped():
    state = _state()
    challenge = state.challenges[0]
    option = next(item for item in challenge.options if item.id == "force_gate")

    first = resolve_challenge_option(state, challenge, option, _roll(10))
    second = resolve_challenge_option(first.state, challenge, option, _roll(16))

    updated = challenge_state_for(second.state, challenge.id)
    assert [attempt.option_id for attempt in updated.attempts] == ["force_gate", "force_gate"]
    assert [attempt.total for attempt in updated.attempts] == [10, 16]
    assert updated.current_progress == 0
    assert updated.noise == 3
    assert updated.completed is True
    assert scene_flag(second.state.flags, "gate_lock_cleared") is True
    assert scene_flag(second.state.flags, "gate_bolt_cleared") is True
    assert scene_flag(second.state.flags, "gate_goblin_ambush_prepared") is True


def test_critical_failure_uses_critical_complication():
    state = _state()
    challenge = state.challenges[0]
    option = next(item for item in challenge.options if item.id == "force_gate")

    result = resolve_challenge_option(state, challenge, option, _roll(1))

    updated = challenge_state_for(result.state, challenge.id)
    assert result.critical_failure is True
    assert result.noise_added == 3
    assert updated.completed is False
    assert scene_flag(result.state.flags, "gate_lock_cleared") is not True
    assert scene_flag(result.state.flags, "gate_bolt_cleared") is not True
    assert scene_flag(result.state.flags, "gate_goblin_ambush_prepared") is True
    assert "alarm_w_strażnicy" in updated.complications


def test_force_gate_is_quiet_only_on_natural_20():
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
    assert scene_flag(natural_20.state.flags, "gate_critical_breach") is True
    assert high_margin.noise_added == 2


def test_opened_lock_hides_lockpicking_but_does_not_complete_gate():
    state = _state()
    challenge = state.challenges[0]
    option = next(item for item in challenge.options if item.id == "lockpick_gate")

    result = resolve_challenge_option(state, challenge, option, _roll(16))

    updated = challenge_state_for(result.state, challenge.id)
    available_ids = {item.id for item in available_challenge_options(result.state, challenge)}
    assert updated.completed is False
    assert scene_flag(result.state.flags, "gate_lock_cleared") is True
    assert scene_flag(result.state.flags, "gate_bolt_cleared") is not True
    assert "lockpick_gate" not in available_ids
    assert "force_gate" in available_ids


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


def test_actor_requirements_hide_option_when_no_actor_matches():
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
    challenge = next(item for item in state.challenges if item.id == "closed_gate")
    lockpick = next(item for item in challenge.options if item.id == "lockpick_gate")

    assert lockpick.requires_item_ids == ("thieves_tools",)
    assert [actor.name for actor in actors_matching_challenge_option(exploration.actors, lockpick)] == ["Łotrzyca"]

    actors_without_tools = tuple(actor for actor in exploration.actors if str(actor.id) != "rogue")

    assert "lockpick_gate" not in {
        option.id for option in available_challenge_options_for_actors(state, challenge, actors_without_tools)
    }


def test_gate_challenge_item_bonus_is_active_only_for_unbroken_item():
    exploration = build_exploration_from_scenario(load_scenario("content/scenarios/abandoned_watchtower"))
    challenge = next(item for item in exploration.challenges if item.id == "closed_gate")
    lockpick = next(item for item in challenge.options if item.id == "lockpick_gate")
    rogue = next(actor for actor in exploration.actors if str(actor.id) == "rogue")

    bonuses = active_option_bonuses_for_actor(rogue, lockpick)
    modifiers = option_roll_modifiers_for_actor(rogue, lockpick)

    assert [bonus.source_id for bonus in bonuses] == ["thieves_tools"]
    assert modifiers == ()  # biegłość narzędzia jest częścią check request, nie item bonusem

    broken_rogue = break_inventory_item(rogue, "thieves_tools")

    assert active_option_bonuses_for_actor(broken_rogue, lockpick) == ()
    assert option_roll_modifiers_for_actor(broken_rogue, lockpick) == ()


def test_spell_option_bonus_requires_slot_for_leveled_spell():
    exploration = build_exploration_from_scenario(load_scenario("content/scenarios/abandoned_watchtower"))
    challenge = next(item for item in exploration.challenges if item.id == "closed_gate")
    flame = next(item for item in challenge.options if item.id == "reveal_bolt_with_flame")
    cleric = next(actor for actor in exploration.actors if str(actor.id) == "cleric")
    leveled_flame = replace(
        flame,
        requires_spell_ids=("healing_word",),
        bonuses=(
            replace(
                flame.bonuses[0],
                source_id="healing_word",
                spell_level=1,
            ),
        ),
    )

    assert active_option_bonuses_for_actor(cleric, flame)[0].spell_level == 0
    assert actors_matching_challenge_option((cleric,), leveled_flame) == (cleric,)

    spent_cleric = replace(cleric, spell_slots=tuple(replace(slot, remaining=0) for slot in cleric.spell_slots))

    assert actors_matching_challenge_option((spent_cleric,), leveled_flame) == ()
    assert active_option_bonuses_for_actor(spent_cleric, leveled_flame) == ()


def test_spell_option_bonus_requires_leveled_spell_to_be_prepared():
    exploration = build_exploration_from_scenario(load_scenario("content/scenarios/abandoned_watchtower"))
    challenge = next(item for item in exploration.challenges if item.id == "closed_gate")
    flame = next(item for item in challenge.options if item.id == "reveal_bolt_with_flame")
    cleric = next(actor for actor in exploration.actors if str(actor.id) == "cleric")
    unprepared_spell_option = replace(
        flame,
        requires_spell_ids=("radiant_line",),
        bonuses=(
            replace(
                flame.bonuses[0],
                source_id="radiant_line",
                spell_level=1,
            ),
        ),
    )

    assert actors_matching_challenge_option((cleric,), unprepared_spell_option) == ()
    assert active_option_bonuses_for_actor(cleric, unprepared_spell_option) == ()


def test_gate_challenge_does_not_reveal_hidden_npc_before_encounter_is_won():
    state = _state()
    challenge = next(item for item in state.challenges if item.id == "closed_gate")
    option = next(item for item in challenge.options if item.id == "force_gate")

    result = resolve_challenge_option(state, challenge, option, _roll(16))
    revealed_state, revealed = reveal_exploration_points(result.state, challenge.reveals_on_complete)

    updated = challenge_state_for(result.state, challenge.id)
    assert updated.completed is True
    assert challenge.reveals_on_complete == ()
    assert revealed == ()
    assert "wounded_scout" not in {point.id for point in visible_exploration_points(revealed_state.points)}
