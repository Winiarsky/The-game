"""The board target must lead to physical rolls and an explicit outcome."""

from dataclasses import replace
from pathlib import Path
from random import Random

import pytest

from dnd_board_game.combat import ActionUse, current_actor, replace_actor
from dnd_board_game.rules import ability_modifier
from dnd_board_game.ui.exploration_app import ExplorationUiSession
from dnd_board_game.ui.shield_bash import submit_shield_bash, confirm_shield_bash
from dnd_board_game.world import Coordinate
from tests.unit.test_recruitment_arena import arena, begin


@pytest.mark.parametrize("attack_first", [True, False])
def test_shield_bash_and_basic_attack_share_a_turn_in_either_order(
    tmp_path: Path, attack_first: bool
) -> None:
    from dnd_board_game.combat.physical_mana import is_basic_weapon

    s = ready(tmp_path, blocked=True)
    s.cancel_combat_class_feature_targeting()
    # Previous movement must not prevent using the shield or be consumed by it.
    s.combat_state = replace(
        s.combat_state,
        turn_action=replace(s.combat_state.turn_action, movement_used_feet=5),
    )

    def attack() -> None:
        actor = current_actor(s.combat_state)
        source = next(
            a for a in s._attack_sources_for_actor(actor) if is_basic_weapon(actor, a)
        )
        s.select_combat_attack_source(source.id)
        s.combat_targeting_attack_source_id = source.id
        s.select_player_attack_target_at_position(Coordinate(12, 11))
        s.confirm_player_attack_target()
        s.submit_player_attack_roll(natural_roll=1, natural_roll_2=1)

    if attack_first:
        attack()
    options = s._combat_turn_action_menu_payload()["options"]
    shield = next(o for o in options if o["action_id"] == "shield_bash")
    assert shield["shortcut"] == "E" and shield["mana_cost"] == ["C", "N"]
    s.start_combat_class_feature_targeting("shield_bash")
    s._handle_board_position(Coordinate(12, 11))
    s.confirm_combat_class_feature_targeting()
    submit_shield_bash(s, {"attacker_roll": 20})
    submit_shield_bash(s, {"damage_roll": 6})
    confirm_shield_bash(s)
    assert s.combat_state.turn_action.movement_used_feet == 5
    assert not any(
        o["action_id"] == "shield_bash"
        for o in s._combat_turn_action_menu_payload()["options"]
    )
    before, rng = s.combat_state, s.encounter_rng.getstate()
    with pytest.raises(ValueError, match="akcji dodatkowej"):
        s.start_combat_class_feature_targeting("shield_bash")
    assert s.combat_state == before and s.encounter_rng.getstate() == rng
    if not attack_first:
        attack()
    turn = s.combat_state.turn_action
    assert turn.action_use == turn.bonus_action_use == ActionUse.ACTION_USED
    assert turn.attacks_used == 1


def ready(tmp_path: Path, *, blocked: bool = False) -> ExplorationUiSession:
    s = arena(tmp_path)
    begin(s, "garran")
    hero = current_actor(s.combat_state)
    enemy = s._actor_by_string_id("recruitment_dummy")
    hero = replace(hero, position=Coordinate(11, 11) if blocked else Coordinate(9, 13))
    enemy = replace(
        enemy, position=Coordinate(12, 11) if blocked else Coordinate(10, 13)
    )
    s.combat_state = replace_actor(replace_actor(s.combat_state, hero), enemy)
    s.start_combat_class_feature_targeting("shield_bash")
    s._handle_board_position(enemy.position)
    before, rng = s.combat_state, s.encounter_rng.getstate()
    payload = s.confirm_combat_class_feature_targeting()
    assert payload["combat"]["shield_bash"]["stage"] == "contest"
    assert s.combat_state == before and s.encounter_rng.getstate() == rng
    s.encounter_rng.seed(1)  # The automatic defender d20 is 5.
    return s


@pytest.mark.parametrize("blocked", [False, True])
def test_win_uses_one_automatic_enemy_roll_and_manual_hero_dice(
    tmp_path: Path, blocked: bool
) -> None:
    s = ready(tmp_path, blocked=blocked)
    before = s.combat_state
    target = s._actor_by_string_id("recruitment_dummy")
    expected_rng = Random()
    expected_rng.setstate(s.encounter_rng.getstate())
    expected_defender_roll = expected_rng.randint(1, 20)
    payload = submit_shield_bash(s, {"attacker_roll": 15})
    assert payload["combat"]["shield_bash"]["defender_roll"] == expected_defender_roll
    assert s.encounter_rng.getstate() == expected_rng.getstate()
    rng = s.encounter_rng.getstate()
    assert payload["combat"]["shield_bash"]["stage"] == "damage"
    assert s.combat_state == before
    payload = submit_shield_bash(s, {"damage_roll": 6})
    preview = payload["combat"]["shield_bash"]
    assert preview["stage"] == "result" and preview["succeeded"]
    assert preview["damage"] == 6 + ability_modifier(
        current_actor(before).ability_scores.strength
    )
    assert (preview["destination"] is None) == blocked
    assert s.combat_state == before and s.encounter_rng.getstate() == rng
    assert not payload["combat"]["turn_action_menu"]
    assert not s._current_board_scan_target().positions
    with pytest.raises(ValueError):
        s.cancel_combat_class_feature_targeting()
    confirm_shield_bash(s)
    assert s.combat_state.turn_action.bonus_action_use == ActionUse.ACTION_USED
    assert s.combat_state.turn_action.movement_used_feet == 0
    assert s.combat_state.turn_action.action_use == ActionUse.ACTION_AVAILABLE
    assert (
        s._actor_by_string_id("recruitment_dummy").hp == target.hp - preview["damage"]
    )
    assert s.shield_bash_flow is None
    if blocked:
        assert s._actor_by_string_id("recruitment_dummy").position == target.position
    else:
        assert s._actor_by_string_id("recruitment_dummy").position == Coordinate(11, 13)
    with pytest.raises(ValueError):
        confirm_shield_bash(s)


def test_tie_goes_straight_to_result_without_damage_roll(tmp_path: Path) -> None:
    s = ready(tmp_path)
    before = s.combat_state
    bonus = ability_modifier(current_actor(before).ability_scores.strength)
    payload = submit_shield_bash(s, {"attacker_roll": 1})
    assert payload["combat"]["shield_bash"]["defender_roll"] == 1 + bonus
    preview = payload["combat"]["shield_bash"]
    assert preview["stage"] == "result" and not preview["succeeded"]
    assert preview["damage"] == 0 and preview["destination"] is None
    assert s.combat_state == before
    confirm_shield_bash(s)
    assert s.combat_state.actors == before.actors
    assert s.combat_state.turn_action.bonus_action_use == ActionUse.ACTION_USED


def test_bad_rolls_and_cancel_do_not_spend_action_or_change_target(
    tmp_path: Path,
) -> None:
    s = ready(tmp_path)
    before, pending = s.combat_state, s.shield_bash_flow
    rng = s.encounter_rng.getstate()
    for value in (0, 21, True, None, 1.5):
        with pytest.raises(ValueError):
            submit_shield_bash(s, {"attacker_roll": value})
        assert s.combat_state == before and s.shield_bash_flow == pending
        assert s.encounter_rng.getstate() == rng
    s._handle_board_position(Coordinate(1, 1))
    assert s.shield_bash_flow == pending
    s.cancel_combat_class_feature_targeting()
    assert s.shield_bash_flow is None and s.combat_state == before


def test_shield_bash_routes_use_same_pending_flow(tmp_path: Path) -> None:
    from dnd_board_game.ui.routes import create_app

    s = ready(tmp_path)
    client = create_app(s, character_dir=tmp_path / "characters").test_client()
    assert client.post("/api/combat/shield-bash/confirm").status_code == 400
    assert (
        client.post(
            "/api/combat/shield-bash/rolls",
            json={"attacker_roll": 20, "defender_roll": 99},
        ).status_code
        == 200
    )
    assert (
        s.shield_bash_flow.defender_roll == 5
    )  # Client-supplied enemy rolls are ignored.
    rng = s.encounter_rng.getstate()
    assert (
        client.post(
            "/api/combat/shield-bash/rolls", json={"attacker_roll": 20}
        ).status_code
        == 400
    )
    assert s.encounter_rng.getstate() == rng
    assert (
        client.post(
            "/api/combat/shield-bash/rolls", json={"damage_roll": 7}
        ).status_code
        == 400
    )
    response = client.post("/api/combat/shield-bash/rolls", json={"damage_roll": 2})
    assert response.json["combat"]["shield_bash"]["stage"] == "result"
    assert client.post("/api/combat/shield-bash/confirm").status_code == 200


def test_pending_shield_bash_cannot_be_saved_or_survive_loading_another_state(
    tmp_path: Path,
) -> None:
    s = ready(tmp_path)
    with pytest.raises(ValueError):
        s.save_snapshot()
    s.cancel_combat_class_feature_targeting()
    s.save_snapshot()
    s.start_combat_class_feature_targeting("shield_bash")
    s._handle_board_position(s._actor_by_string_id("recruitment_dummy").position)
    s.confirm_combat_class_feature_targeting()
    submit_shield_bash(s, {"attacker_roll": 20})
    submit_shield_bash(s, {"damage_roll": 6})
    s.load_snapshot()
    assert s.shield_bash_flow is None
    assert s.combat_targeting_class_feature_action_id is None
    with pytest.raises(ValueError):
        confirm_shield_bash(s)
