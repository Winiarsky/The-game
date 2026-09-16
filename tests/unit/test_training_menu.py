"""Independent training cases share real lessons without advancing the course."""
from dataclasses import replace
from pathlib import Path

import pytest

from dnd_board_game.application.recruitment_arena import HERO_ORDER
from dnd_board_game.application.training_walkthrough import steps
from dnd_board_game.combat.scene import scene_flag, set_scene_flag
from dnd_board_game.hardware.board_panel import panel_position
from dnd_board_game.ui import training_menu as menu, training_walkthrough as guided
from dnd_board_game.ui.routes import create_app
from dnd_board_game.ui.exploration_app import ExplorationUiSession
from tests.unit.test_recruitment_arena import arena
from tests.unit.test_training_walkthrough import prepare_pool, settle_burn
from tests.unit.test_shared_mana_runtime import send


def choose(s: ExplorationUiSession, action: str) -> dict[str, object]:
    return menu.command(s, dict(action=action, revision=menu.payload(s)['revision']))


def prepare_case(s: ExplorationUiSession) -> None:
    guided.acknowledge(s, guided.notice_id(s))
    while not s.encounter_setup_flow.completed:
        s.confirm_encounter_setup_step()
    guided.acknowledge(s, guided.notice_id(s))
    prepare_pool(s)


@pytest.mark.parametrize('hero', HERO_ORDER)
def test_all_cases_and_boosts_are_reachable_by_board_and_direct_start(tmp_path: Path, hero: str) -> None:
    s = arena(tmp_path)
    menu.select_position(s, panel_position(6 + HERO_ORDER.index(hero)))
    assert menu.payload(s)['view'] == 'subjects'
    menu.select_position(s, panel_position(6))
    assert menu.payload(s)['view'] == 'modes'
    assert s.combat_state is None and s.pending_encounter is None
    menu.select_position(s, panel_position(7))
    found = []
    while True:
        view = menu.payload(s)
        assert set(menu.board_target(s).positions) == {panel_position(o['slot']) for o in view['options']}
        found.extend(o['action'][5:] for o in view['options'] if o['action'].startswith('case:'))
        if not any(o['action'] == 'next' for o in view['options']):
            break
        menu.select_position(s, panel_position(27))
    assert found == [step.id for step in steps(hero)] + ['duel', 'trap']
    # A late boost starts directly with its required setup, without previous cases.
    case = next(step for step in reversed(steps(hero)) if step.boost_id)
    response = create_app(s).test_client().post('/api/training/start', json={'hero_id': hero, 'case_id': case.id})
    assert response.status_code == 200, response.json
    assert guided.single_case(s)
    assert guided.current_step(s).id == case.id
    assert response.json['training_arena']['tutorial']['run_mode'] == 'single'
    assert guided.flag(s, 'phase') == 'introduction'


@pytest.mark.parametrize('case_id', ['pool_draw', 'second_wind'])
def test_single_success_preserves_sequence_returns_to_same_page_and_repeats(tmp_path: Path, case_id: str) -> None:
    s = arena(tmp_path)
    s.state = replace(s.state, flags=set_scene_flag(s.state.flags, 'walkthrough_charge_progress_garran', 4))
    guided.start(s, 'garran', case_id=case_id)
    prepare_case(s)
    if case_id == 'pool_draw':
        send(s, 'pool_take', index=0)
    else:
        s.use_combat_class_feature('second_wind', natural_roll=5)
        send(s, 'pay')
        settle_burn(s)
    assert guided.flag(s, 'phase') == 'success'
    assert scene_flag(s.state.flags, 'walkthrough_charge_progress_garran', 0) == 4
    assert scene_flag(s.state.flags, 'walkthrough_charge_case_garran_' + case_id, False)
    assert s.state_payload()['training_arena']['tutorial']['notice']['button'] == '✓ Wybór ćwiczenia'
    guided.acknowledge(s, guided.notice_id(s))
    view = menu.payload(s)
    assert view['view'] == 'cases' and view['hero_id'] == 'garran'
    assert any(o['action'] == 'case:' + case_id and o['completed'] for o in view['options'])
    choose(s, 'case:' + case_id)
    assert guided.current_step(s).id == case_id
    assert guided.single_case(s)
    assert not any(step.positions for step in s.encounter_setup_flow.steps if step.kind.value == 'environment')
    guided.leave(s)
    choose(s, 'back')
    choose(s, 'sequence')
    assert not guided.single_case(s)
    assert int(guided.flag(s, 'index')) == 4


@pytest.mark.parametrize('after_effect', [False, True])
def test_restart_cancels_pending_payment_and_keeps_single_mode_and_progress(tmp_path: Path, after_effect: bool) -> None:
    s = arena(tmp_path)
    guided.start(s, 'garran', case_id='second_wind')
    prepare_case(s)
    s.use_combat_class_feature('second_wind', natural_roll=5)
    assert s.shared_mana_declaration
    if after_effect:
        send(s, 'pay')
        assert guided.flag(s, 'charge_pending_ability') == 'second_wind'
    token = guided.flag(s, 'token')
    result = create_app(s).test_client().post('/api/training/leave', json={'retry': True})
    assert result.status_code == 200, result.json
    assert s.shared_mana_declaration is None
    assert s.combat_state is None
    assert not guided.flag(s, 'charge_pending_ability')
    assert guided.single_case(s) and guided.current_step(s).id == 'second_wind'
    assert guided.flag(s, 'token') != token
    assert scene_flag(s.state.flags, 'walkthrough_charge_progress_garran', 0) == 0
    # Exit remains possible before setup has been completed too.
    result = create_app(s).test_client().post('/api/training/leave', json={'choose_case': True})
    assert result.status_code == 200
    assert result.json['training_arena']['menu']['view'] == 'cases'


def test_menu_and_single_case_survive_save_and_reject_stale_or_invalid_choices(tmp_path: Path) -> None:
    s = arena(tmp_path)
    old = menu.payload(s)['revision']
    choose(s, 'hero:lorian')
    choose(s, 'subject:combat')
    with pytest.raises(ValueError, match='aktualny'):
        menu.command(s, dict(action='sequence', revision=old))
    choose(s, 'cases')
    choose(s, 'next')
    s.save_snapshot()
    s.load_snapshot()
    assert menu.payload(s)['page'] == 1 and menu.payload(s)['hero_id'] == 'lorian'
    client = create_app(s).test_client()
    response = client.post('/api/training/start', json={'hero_id': 'lorian', 'case_id': 'shield_bash'})
    assert response.status_code == 400
    assert s.pending_encounter is None
    guided.start(s, 'lorian', case_id='mana_recovery')
    token = guided.notice_id(s)
    s.save_snapshot()
    s.load_snapshot()
    assert guided.single_case(s) and guided.notice_id(s)
    with pytest.raises(ValueError, match='aktualne'):
        guided.acknowledge(s, token)
    assert guided.current_step(s).id == 'mana_recovery'
    with pytest.raises(ValueError):
        choose(s, 'back')


def test_standalone_duel_win_does_not_complete_entire_course(tmp_path: Path) -> None:
    from dnd_board_game.actors import Faction
    from dnd_board_game.combat import replace_actor
    s = arena(tmp_path)
    guided.start(s, 'garran', case_id='duel')
    guided.acknowledge(s, guided.notice_id(s))
    while not s.encounter_setup_flow.completed:
        s.confirm_encounter_setup_step()
    guided.acknowledge(s, guided.notice_id(s))
    s.submit_encounter_initiative_roll(20)
    prepare_pool(s)
    send(s, 'pool_take', index=0)
    victim = next(a for a in s.combat_state.actors if a.faction == Faction.ENEMY)
    s.combat_state = replace_actor(s.combat_state, replace(victim, hp=0))
    result = s.state_payload()
    assert 'garran' not in result['training_arena']['completed']
    assert result['training_arena']['tutorial']['notice']['name'] == 'Pojedynek wygrany'
    guided.acknowledge(s, guided.notice_id(s))
    assert not scene_flag(s.state.flags, 'walkthrough_charge_completed_garran', False)
    assert scene_flag(s.state.flags, 'walkthrough_charge_case_garran_duel', False)
    assert menu.payload(s)['view'] == 'cases'


def test_restart_discards_unfinished_dice_and_stale_submission(tmp_path: Path) -> None:
    from dnd_board_game.ui.shield_bash import submit_shield_bash
    s = arena(tmp_path)
    guided.start(s, 'garran', case_id='shield_bash')
    prepare_case(s)
    enemy = s._actor_by_string_id('recruitment_dummy')
    s.start_combat_class_feature_targeting('shield_bash')
    s._handle_board_position(enemy.position)
    s.confirm_combat_class_feature_targeting()
    send(s, 'pay')
    assert s.shield_bash_flow is not None
    guided.leave(s, retry=True)
    assert s.shield_bash_flow is None and s.shared_mana_declaration is None
    assert guided.single_case(s) and guided.current_step(s).id == 'shield_bash'
    with pytest.raises(ValueError):
        submit_shield_bash(s, {'attacker_roll': 20})
