"""Printed commands share live availability and preserve the game LED layer."""
from dataclasses import replace
from pathlib import Path

import pytest

from dnd_board_game.application.recruitment_arena import HERO_ORDER
from dnd_board_game.hardware.board_panel import panel_feedback, panel_position
from dnd_board_game.hardware.led_feedback import LedFeedback, LedFrame, LedRole
from dnd_board_game.hardware.led_palette import LedColor
from dnd_board_game.ui.board_panel import action_economy_panel_color
from dnd_board_game.ui.board_panel_symbols import ability_panel_slot
from dnd_board_game.ui.routes import create_app
from dnd_board_game.world import Coordinate
from tests.unit.test_recruitment_arena import arena, begin as begin_trial
from tests.unit.test_initiative_panel import Board, session_at_initiative
from dnd_board_game.rules.shared_mana import SharedMana


def begin(session, hero: str, mode: str = 'basic') -> None:
    """Keep legacy arena rule regressions independent of opening deck reporting."""
    begin_trial(session, hero, mode)
    session.combat_state = replace(session.combat_state, shared_mana=SharedMana(turn_actor=hero))
    session.state_payload()


def lights(feedback: LedFeedback) -> dict[Coordinate, tuple[int, int, int]]:
    return {p: f.color for f in feedback.frames for p in f.positions}


@pytest.mark.parametrize('hero', HERO_ORDER)
def test_live_runes_match_printed_cards_and_budget(hero: str, tmp_path: Path) -> None:
    s = arena(tmp_path); begin(s, hero)
    menu = s._combat_turn_action_menu_payload()
    slots = [o['panel_slot'] for o in menu['options'] if o['panel_slot'] is not None]
    assert len(slots) == len(set(slots))
    assert {0, 3} <= set(slots)
    assert not {4, 25} & set(slots)
    for option in menu['options']:
        slot = option['panel_slot']
        if slot is not None and slot >= 5:
            ability = 'hide' if option['id'] in {'basic:hide', 'basic:end-hide'} else option['action_id'] or option['source_id']
            assert ability_panel_slot(hero, ability) == slot
    actions = s._board_panel_actions()
    assert actions == {o['panel_slot']: o['id'] for o in menu['options'] if o['panel_slot'] is not None and not o['panel_unavailable_reason']}
    target = s._current_board_scan_target()
    assert {p for p in target.positions if p.col == 19} == {panel_position(slot) for slot in (*actions, 25, 26, 27, 29)}
    for option in menu['options']:
        if option['panel_slot'] in actions:
            color = action_economy_panel_color(option['action_economy'])
            assert lights(target.feedback)[panel_position(option['panel_slot'])] == tuple(round(c * .65) for c in color)
    s.confirm_combat_turn_action('turn:move')
    target = s._current_board_scan_target()
    assert panel_position(29) in target.positions
    assert panel_position(28) not in target.positions
    assert lights(target.feedback)[panel_position(0)] == LedColor.PANEL_MOVEMENT
    assert lights(target.feedback)[panel_position(3)] == tuple(round(c * .35) for c in LedColor.PANEL_TURN_CONTROL)


def test_panel_layer_preserves_targets_and_clears_old_edge() -> None:
    target = Coordinate(8, 9)
    base = LedFeedback((LedFrame((target, panel_position(7)), LedColor.LEGAL_ATTACK_TARGET, LedRole.MARKER),))
    result = lights(panel_feedback((0, 6), base=base, control_slots=(28,)))
    assert result[target] == LedColor.LEGAL_ATTACK_TARGET
    assert panel_position(7) not in result
    assert result[panel_position(6)] == tuple(round(c * .65) for c in LedColor.PANEL_RUNE)
    assert result[panel_position(28)] == LedColor.PANEL_ACCEPT


def test_real_scan_selects_action_and_rejects_blank_or_stale_input(tmp_path: Path) -> None:
    s = arena(tmp_path); begin(s, 'garran')
    board = Board(); s.attach_board_connection(board, backend='simulator')
    client = create_app(s, character_dir=tmp_path/'characters').test_client()
    selection = s._board_selection_payload()
    assert selection['auto_arm']
    before = s.combat_state
    board.selected = panel_position(0).as_tuple()
    response = client.post('/api/board/scan', json={'revision': selection['revision'], 'automatic': True})
    assert response.status_code == 200
    assert response.json['combat']['turn_action_menu']['preview_option_id'] == 'turn:move'
    assert s.combat_state == before
    assert response.json['board_selection']['auto_arm']
    assert board.leds[board.selected] == LedColor.PANEL_MOVEMENT
    client.post('/api/board/scan', json={'revision': selection['revision']})
    assert board.scans == 1
    blank = panel_position(4)
    assert client.post('/api/board/select', json={'col': blank.col, 'row': blank.row}).status_code == 400


def test_finishing_initiative_lights_and_arms_first_action_menu(tmp_path: Path) -> None:
    s = session_at_initiative(tmp_path)
    board = Board(); s.attach_board_connection(board, backend='simulator')
    s.update_initiative_panel('accept', value=20)
    board.selected = panel_position(28).as_tuple()
    result = s.scan_board_selection(automatic=True)
    # Legacy arena starts with deck preparation; the opening-rune flow is tested
    # separately with a real Mission 0 party.
    assert s.combat_state.shared_mana.pooled.phase == 'setup'
    s.combat_state = replace(s.combat_state, shared_mana=SharedMana(turn_actor='garran'))
    result = s.state_payload()
    s._sync_board_leds()
    assert result['combat']['turn_action_menu']['actor_id'] == 'garran'
    assert result['board_selection']['auto_arm']
    assert [19, 29] in result['board_selection']['legal_positions']
    assert board.leds[(19, 29)] == tuple(round(c * .65) for c in LedColor.PANEL_MOVEMENT)
    board.selected = (19, 29)
    result = s.scan_board_selection(expected_revision=result['board_selection']['revision'], automatic=True)
    assert result['combat']['turn_action_menu']['preview_option_id'] == 'turn:move'


def test_mana_payment_locks_actions_and_cancellation_restores_them(tmp_path: Path) -> None:
    s = arena(tmp_path); begin(s, 'garran')
    board = Board(); s.attach_board_connection(board, backend='simulator')
    client = create_app(s).test_client()
    before = s.combat_state
    s.use_combat_class_feature('defensive_stance')
    assert s.shared_mana_declaration is not None
    assert s._board_panel_actions() == {}
    assert set(s._current_board_scan_target().positions) == {panel_position(28), panel_position(29)}
    # A stale browser registration cannot replace the server-owned payment mask.
    s.configure_board_panel('mana:payment', [26, 27, 28, 29], True)
    assert set(p for p in board.leds if p[0] == 19) == {(19, 1), (19, 0)}
    response = client.post('/api/combat/shared-mana', json={
        'command': 'cancel', 'revision': s.combat_state.shared_mana.revision,
    })
    assert response.status_code == 200
    assert s.combat_state == replace(before, shared_mana=replace(
        before.shared_mana, revision=before.shared_mana.revision + 1,
    ))
    assert s._board_panel_actions()[0] == 'turn:move'
    assert s._board_selection_payload()['auto_arm']
    assert (19, 29) in board.leds


def test_dice_controls_lock_runes_use_colors_and_forward_one_event(tmp_path: Path) -> None:
    s = arena(tmp_path); begin(s, 'garran')
    board = Board(); s.attach_board_connection(board, backend='simulator')
    client = create_app(s, character_dir=tmp_path/'characters').test_client()
    response = client.post('/api/board/panel', json={'context': 'dice:1', 'slots': [26,27,28], 'exclusive': True})
    assert response.status_code == 200
    selection = response.json['board_selection']
    assert selection['auto_arm']
    assert set(map(tuple, selection['legal_positions'])) == {(19,3),(19,2),(19,1)}
    assert board.leds[(19,3)] == LedColor.PANEL_PLUS
    assert board.leds[(19,2)] == LedColor.PANEL_MINUS
    assert board.leds[(19,1)] == LedColor.PANEL_ACCEPT
    assert not any(p[0] == 19 and p[1] > 3 for p in board.leds)
    board.selected = (19,2)
    result = client.post('/api/board/scan', json={'revision': selection['revision']})
    assert result.json['panel_event'] == {'slot': 27, 'context': 'dice:1'}
    client.post('/api/board/scan', json={'revision': selection['revision']})
    assert board.scans == 1
    assert client.post('/api/board/select', json={'col':19,'row':29}).status_code == 400
    client.post('/api/board/panel', json={'context':'review:1','slots':[28,29],'exclusive':True})
    assert set(p for p in board.leds if p[0] == 19) == {(19,1),(19,0)}
    assert client.post('/api/board/panel', json={'context':'bad','slots':[4],'exclusive':True}).status_code == 400


def test_panel_strip_is_outside_playable_arena(tmp_path: Path) -> None:
    s = arena(tmp_path); begin(s, 'nimra', 'area')
    board = s._active_encounter().board
    assert board.dimensions.cols == 19
    assert all(not board.in_bounds(panel_position(slot)) for slot in range(30))


def test_targeted_feature_preview_is_selected_on_screen_without_cost(tmp_path: Path) -> None:
    s = arena(tmp_path); begin(s, 'garran')
    from dnd_board_game.combat import current_actor, replace_actor
    actor = current_actor(s.combat_state)
    enemy = s._actor_by_string_id('recruitment_dummy')
    s.combat_state = replace_actor(s.combat_state, replace(enemy, position=Coordinate(actor.position.col+1, actor.position.row)))
    before = s.combat_state
    s.start_combat_class_feature_targeting('shield_bash')
    assert s.combat_targeting_class_feature_action_id == 'shield_bash'
    s.cancel_combat_class_feature_targeting()
    assert s.combat_state == before
    assert s._board_panel_actions()[0] == 'turn:move'


def test_weapon_icon_survives_spell_preview_and_corner_has_back(tmp_path: Path) -> None:
    s = arena(tmp_path); begin(s, 'nimra', 'area')
    s.confirm_combat_turn_action('attack-source:nimra_frost_pulse')
    assert any(o['panel_slot'] == 1 for o in s._combat_turn_action_menu_payload()['options'])
    assert panel_position(29) in s._current_board_scan_target().positions
    assert s._board_panel_actions()[0] == 'turn:move'


def test_stale_browser_registration_does_not_override_new_decision(tmp_path: Path) -> None:
    s = arena(tmp_path); begin(s, 'garran')
    revision = s._board_selection_payload()['revision']
    s.confirm_combat_turn_action('turn:move')
    s.configure_board_panel('old-dice', [26, 27, 28], True, expected_revision=revision)
    assert s.board_panel_context is None
    assert panel_position(28) not in s._current_board_scan_target().positions


def test_spent_bonus_runes_remain_disabled(tmp_path: Path) -> None:
    from dnd_board_game.combat.session import use_bonus_action
    s = arena(tmp_path); begin(s, 'garran')
    spent = use_bonus_action(s.combat_state)
    assert spent.accepted
    s.combat_state = spent.state
    assert s._board_panel_actions()[0] == 'turn:move'
    assert 'class-feature:shield_bash' not in s._board_panel_actions().values()
    assert panel_position(18) not in lights(s._current_board_scan_target().feedback)
    client = create_app(s).test_client()
    assert client.post('/api/board/select', json={'col': 19, 'row': 11}).status_code == 400


@pytest.mark.parametrize('on_panel', [False, True])
def test_load_arena_save_preserves_play_area_or_rejects_panel_occupant(
    tmp_path: Path, on_panel: bool,
) -> None:
    from dnd_board_game.combat import current_actor, replace_actor
    s = arena(tmp_path); begin(s, 'garran')
    if on_panel:
        # Reproduce a save made before the printed edge was reserved.
        board = s._active_encounter().board
        board.dimensions = replace(board.dimensions, cols=20)
        actor = current_actor(s.combat_state)
        s.combat_state = replace_actor(s.combat_state, replace(actor, position=panel_position(0)))
    s.save_snapshot()
    if on_panel:
        with pytest.raises(ValueError, match='pasie panelu'):
            s.load_snapshot()
    else:
        s.load_snapshot()
        assert s._active_encounter().board.dimensions.cols == 19
        assert s._board_panel_actions()[0] == 'turn:move'


def test_board_transmits_actions_and_corner_controls_after_screen_preview(tmp_path: Path) -> None:
    s = arena(tmp_path); begin(s, 'garran')
    board = Board(); s.attach_board_connection(board, backend='simulator')
    s._sync_board_leds()
    assert board.leds[panel_position(0).as_tuple()] == tuple(round(c * .65) for c in LedColor.PANEL_MOVEMENT)
    s.confirm_combat_turn_action('turn:move')
    assert panel_position(28).as_tuple() not in board.leds
    assert board.leds[panel_position(0).as_tuple()] == LedColor.PANEL_MOVEMENT


def test_sword_damage_returns_menu_and_allows_shield_selection(tmp_path: Path) -> None:
    from dnd_board_game.combat import current_actor, replace_actor

    s = arena(tmp_path)
    begin(s, 'garran')
    hero = replace(current_actor(s.combat_state), position=Coordinate(13, 15))
    enemy = replace(s._actor_by_string_id('recruitment_dummy'), position=Coordinate(12, 14))
    s.combat_state = replace_actor(replace_actor(s.combat_state, hero), enemy)
    s.select_combat_attack_source('longsword_slash')
    s.combat_targeting_attack_source_id = 'longsword_slash'
    s.select_player_attack_target_at_position(enemy.position)
    s.confirm_player_attack_target()
    s.submit_player_attack_roll(natural_roll=14)
    client = create_app(s).test_client()
    response = client.post('/api/combat/player-damage', json={'components': {'base': 11}})
    assert response.status_code == 200
    payload = response.get_json()
    assert s._actor_by_string_id('recruitment_dummy').hp == 39
    assert s.pending_player_attack is None
    assert payload['combat']['turn_action_menu'] is not None
    assert [19, 11] in payload['board_selection']['legal_positions']
    response = client.post('/api/board/select', json={'col': 19, 'row': 11})
    assert response.status_code == 200
    assert s.combat_targeting_class_feature_action_id == 'shield_bash'


def test_action_labels_do_not_recompute_movement_paths(tmp_path: Path, monkeypatch) -> None:
    import dnd_board_game.ui.exploration_app as module

    s = arena(tmp_path)
    begin(s, 'garran')
    monkeypatch.setattr(module, '_remaining_movement_range', lambda *args: pytest.fail('Action labels do not need pathfinding'))
    options = s._combat_turn_action_options()
    move = next(option for option in options if option.id == 'turn:move')
    assert '30 ft' in move.description
    assert any(option.id == 'class-feature:shield_bash' for option in options)


def test_selection_reuses_fresh_target_with_the_same_revision(tmp_path: Path, monkeypatch) -> None:
    s = arena(tmp_path)
    begin(s, 'garran')
    target = s._current_board_scan_target()
    expected = s._board_selection_payload()
    monkeypatch.setattr(s, '_current_board_scan_target', lambda: pytest.fail('Fresh target must be reused'))
    assert s._board_selection_payload(target=target) == expected
