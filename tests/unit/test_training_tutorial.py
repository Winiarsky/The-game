"""Personal arena content, committed progress, board notices and persistence."""
from dataclasses import replace
from pathlib import Path

import pytest

from dnd_board_game.actors import Faction
from dnd_board_game.application.recruitment_arena import HERO_ORDER, HELPER_ID
from dnd_board_game.combat import current_actor, replace_actor
from dnd_board_game.combat.scene import set_scene_flag
from dnd_board_game.hardware.board_panel import panel_position
from dnd_board_game.ui.routes import create_app
from dnd_board_game.ui.training_arena import start_training_trial, trial_won
from dnd_board_game.ui.training_tutorial import abilities, completed, record_ability, tutorial_content
from tests.unit.test_initiative_panel import Board
from tests.unit.test_recruitment_arena import arena, begin
from tests.unit.test_shared_mana_runtime import send


def test_tutorial_covers_every_current_hero_ability_and_holy_symbol() -> None:
    data = tutorial_content()
    assert sum(len(abilities(h)) for h in HERO_ORDER) == 67
    assert 'turn_undead' in data['dagna']['lessons']
    assert all(len(tip) > 40 for hero in data.values() for tip in hero['lessons'].values())


@pytest.mark.parametrize('hero', HERO_ORDER)
def test_personal_setup_keeps_terrain_and_has_legal_recipients(tmp_path: Path, hero: str) -> None:
    normal = arena(tmp_path / 'basic')
    start_training_trial(normal, hero, 'basic', 'humanoid')
    expected = normal.encounter_setup_flow.encounter
    session = arena(tmp_path / 'tutorial')
    begin(session, hero, 'tutorial')
    encounter = session._active_encounter()
    assert encounter.board == expected.board
    assert encounter.environment == expected.environment
    assert encounter.scene_objects == expected.scene_objects
    actors = session.combat_state.actors
    assert len({a.position for a in actors}) == len(actors)
    assert all(not encounter.board.terrain_at(a.position).blocks_movement for a in actors)
    assert sum(a.faction == Faction.ENEMY for a in actors) == 3
    helper = next(a for a in actors if str(a.id) == HELPER_ID)
    assert helper.hp < helper.max_hp
    assert not any(str(e.actor.id).startswith(HELPER_ID) for e in session.combat_state.initiative_order.entries)
    assert encounter.attack_sources_by_actor[HELPER_ID].damage_fixed == 2
    if hero == 'garran':
        assert sum(a.faction == Faction.ALLY for a in actors) == 3
    if hero == 'dagna':
        assert all(a.creature_type == 'undead' for a in actors if a.faction == Faction.ENEMY)
        assert any(c.actor_id == HELPER_ID for c in session.combat_state.condition_states)
        assert current_actor(session.combat_state).hp < current_actor(session.combat_state).max_hp
    if hero == 'brakka':
        assert encounter.attack_sources_by_actor['recruitment_dummy'].damage_fixed == 6
    assert session.state_payload()['training_arena']['tutorial']['completed_count'] == 0


def test_stance_counts_after_resolution_and_notice_owns_board_until_ack(tmp_path: Path) -> None:
    session = arena(tmp_path)
    begin(session, 'garran', 'tutorial')
    board = Board()
    session.attach_board_connection(board, backend='simulator')
    session.use_combat_class_feature('defensive_stance')
    assert not completed(session, 'garran')
    send(session, 'cancel')
    assert not completed(session, 'garran')
    session.use_combat_class_feature('defensive_stance')
    send(session, 'pay')
    state = session.state_payload()
    assert completed(session, 'garran') == ('defensive_stance',)
    assert state['training_arena']['tutorial']['notice']['id'] == 'defensive_stance'
    assert state['board_selection']['legal_positions'] == [[19, 1]]
    assert state['board_selection']['input_mode'] == 'single'
    assert state['board_selection']['auto_arm']
    with pytest.raises(ValueError, match='objaśnienie'):
        session._handle_board_position(panel_position(0))
    board.selected = (19, 1)
    acknowledged = session.scan_board_selection(automatic=True)
    assert acknowledged['training_arena']['tutorial']['notice'] is None
    assert [19, 29] in acknowledged['board_selection']['legal_positions']
    assert len(completed(session, 'garran')) == 1
    response = create_app(session).test_client().post('/api/training/acknowledge', json={'ability_id':'defensive_stance'})
    assert response.status_code == 400


def test_shield_bash_is_not_completed_by_payment_or_roll_preview(tmp_path: Path) -> None:
    from tests.unit.test_shield_bash_ui_flow import ready
    from dnd_board_game.ui.shield_bash import submit_shield_bash, confirm_shield_bash
    session = ready(tmp_path, pay=False)
    session.state = replace(session.state, flags=set_scene_flag(session.state.flags, 'training_mode', 'tutorial'))
    send(session, 'pay')
    assert not completed(session, 'garran')
    submit_shield_bash(session, {'attacker_roll':1})
    assert session.shield_bash_flow.stage == 'result'
    assert not completed(session, 'garran')
    confirm_shield_bash(session)
    assert completed(session, 'garran') == ('shield_bash',)
    assert session.state_payload()['training_arena']['tutorial']['notice']['name'] == 'Uderzenie tarczą'


def test_lorian_can_inspire_tutorial_helper_and_card_operation_needs_ack(tmp_path: Path) -> None:
    session = arena(tmp_path)
    begin(session, 'lorian', 'tutorial')
    session.use_combat_class_feature('mana_inspiration')
    send(session, 'parameters', target_id=HELPER_ID)
    send(session, 'pay')
    assert completed(session, 'lorian') == ('mana_inspiration',)
    from dnd_board_game.ui.training_tutorial import acknowledge
    acknowledge(session, 'mana_inspiration')
    session.use_combat_class_feature('mana_recovery')
    send(session, 'pay')
    assert 'mana_recovery' not in completed(session, 'lorian')
    assert session.shared_mana_declaration.stage == 'cards'
    send(session, 'cards_done')
    assert 'mana_recovery' in completed(session, 'lorian')


def test_killing_targets_does_not_complete_tutorial_and_progress_survives_save(tmp_path: Path) -> None:
    session = arena(tmp_path)
    begin(session, 'garran', 'tutorial')
    session.use_combat_class_feature('defensive_stance')
    send(session, 'pay')
    session.save_snapshot()
    session.load_snapshot()
    assert completed(session, 'garran') == ('defensive_stance',)
    assert session.state_payload()['training_arena']['tutorial']['notice']['id'] == 'defensive_stance'
    for enemy in session.combat_state.actors:
        if enemy.faction == Faction.ENEMY:
            session.combat_state = replace_actor(session.combat_state, replace(enemy, hp=0))
    assert not trial_won(session)
    assert 'garran' not in session.state_payload()['training_arena']['completed']
    start_training_trial(session, 'garran', 'tutorial', 'humanoid')
    assert completed(session, 'garran') == ('defensive_stance',)
    assert session.state_payload()['training_arena']['tutorial']['notice'] is None


def test_all_distinct_skills_required_no_credit_for_unknown_or_other_actor(tmp_path: Path) -> None:
    session = arena(tmp_path)
    begin(session, 'garran', 'tutorial')
    for key, actor in [('not_real','garran'), ('defensive_stance',HELPER_ID)]:
        record_ability(session, key, actor)
    assert not completed(session, 'garran')
    skills = abilities('garran')
    for ability in skills[:-1]:
        record_ability(session, ability.id, 'garran')
    assert not trial_won(session)
    record_ability(session, skills[-1].id, 'garran')
    assert trial_won(session)
    assert session.state_payload()['training_arena']['completed'] == ['garran']
    record_ability(session, skills[-1].id, 'garran')
    assert len(completed(session, 'garran')) == 9


@pytest.mark.parametrize('hero,ability', [('brakka','hard_as_rock'), ('mira','instinctive_dodge'),
                                        ('nimra','shield'), ('lorian','cutting_words')])
def test_completed_reaction_is_tracked_only_for_its_owner(tmp_path: Path, hero: str, ability: str) -> None:
    from dnd_board_game.rules.shared_mana import pay_mana
    from dnd_board_game.ui.shared_mana import complete_reaction_payment
    session = arena(tmp_path)
    begin(session, hero, 'tutorial')
    mana = session.combat_state.shared_mana
    session.combat_state = replace(session.combat_state, shared_mana=pay_mana(mana, revision=mana.revision,
        actor_id=hero, ability_id=ability, count=1))
    assert not completed(session, hero)
    complete_reaction_payment(session, ability)
    assert completed(session, hero) == (ability,)


@pytest.mark.parametrize('width', [390, 1100])
def test_browser_tutorial_notice_symbols_and_confirmation(tmp_path: Path, width: int) -> None:
    import json
    import shutil
    import subprocess
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        pytest.skip('Chrome is needed for tutorial presentation')
    session = arena(tmp_path)
    begin(session, 'garran', 'tutorial')
    session.use_combat_class_feature('defensive_stance')
    send(session, 'pay')
    state = session.state_payload()
    static = Path('src/dnd_board_game/ui/static')
    scripts = '\n'.join((static / name).read_text() for name in ('physical_mana.js','board_panel.js','training_arena.js'))
    source = (static / 'exploration.js').read_text()
    initialize = source[source.index('function initializeKeyboardRollWizard()'):source.index('function keyboardRollStepPrompt(')]
    css = '\n'.join((static / name).read_text() for name in ('exploration.css','physical_mana.css','training_arena.css'))
    harness = r'''
let busy=false, keyboardRollWizard=null, call=null;
function esc(text) {return String(text ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');}
function api(path,body) {call={path,body};}
function check(ok,message) {if(!ok) throw new Error(message);}
try {
 renderTrainingArena();
 const notice=document.getElementById('training-notice');
 check(notice?.getAttribute('role')==='dialog', 'missing explanation dialog');
 check(notice.innerText.includes('Pozycja obronna'), 'wrong ability');
 check(notice.querySelector('.mana-B'), 'missing white mana symbol');
 check(document.querySelectorAll('.training-lesson').length===9, 'missing checklist abilities');
 check(document.querySelectorAll('.training-lesson.completed').length===1, 'wrong completed count');
 check(!initializeKeyboardRollWizard(), 'dice overlay stole tutorial input');
 check(desiredBoardPanel()===null, 'browser overrides server tutorial mask');
 notice.querySelector('button').click();
 check(call.path==='/api/training/acknowledge' && call.body.ability_id==='defensive_stance', 'wrong acknowledgement');
 state.training_arena.tutorial.notice=null;
 renderTrainingArena();
 check(!document.getElementById('training-notice'), 'notice remains after acknowledgement');
 check(document.documentElement.scrollWidth<=innerWidth, 'horizontal overflow');
 document.getElementById('result').textContent='PASS';
} catch(error) {document.getElementById('result').textContent='FAIL: '+error.stack;}
'''
    page = tmp_path / 'tutorial.html'
    page.write_text('<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                   + '<style>' + css + '</style><div id="training-arena-panel"></div><pre id="result">PENDING</pre>'
                   + '<script>let state=' + json.dumps(state).replace('</','<\\/') + ';'
                   + 'new Function(' + json.dumps(source).replace('</','<\\/') + ');'
                   + scripts + initialize + harness + '</script>')
    result = subprocess.run([chrome,'--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage',
                             '--no-first-run','--disable-background-networking','--no-proxy-server',
                             f'--user-data-dir={tmp_path / "chrome"}',f'--window-size={width},1000',
                             '--dump-dom',page.as_uri()],capture_output=True,text=True,timeout=20)
    assert result.returncode == 0, result.stderr[-1000:]
    assert '<pre id="result">PASS</pre>' in result.stdout, result.stdout[-3000:]


def test_garran_command_requires_both_attacks_with_real_tutorial_helper(tmp_path: Path) -> None:
    from dnd_board_game.world import Coordinate
    session = arena(tmp_path)
    begin(session, 'garran', 'tutorial')
    hero = current_actor(session.combat_state)
    session.combat_state = replace_actor(session.combat_state, replace(hero, position=Coordinate(10, 17)))
    session.use_combat_class_feature('counterattack_command')
    send(session, 'parameters', target_id=HELPER_ID)
    send(session, 'pay')
    assert not completed(session, 'garran')
    for expected in ('garran', HELPER_ID):
        actor = current_actor(session.combat_state)
        assert str(actor.id) == expected
        assert any(source.id == 'counterattack_command' for source in session._attack_sources_for_actor(actor))
        session.select_combat_attack_source('counterattack_command')
        session.combat_targeting_attack_source_id = 'counterattack_command'
        enemy = session._actor_by_string_id('recruitment_dummy')
        session.select_player_attack_target_at_position(enemy.position)
        session.confirm_player_attack_target()
        session.submit_player_attack_roll(natural_roll=1, natural_roll_2=1)
        if expected == 'garran':
            assert not completed(session, 'garran')
    assert completed(session, 'garran') == ('counterattack_command',)
    assert str(current_actor(session.combat_state).id) == 'garran'


def test_garran_setup_offers_guard_and_defers_notice_until_attack_finishes(tmp_path: Path) -> None:
    session = arena(tmp_path)
    begin(session, 'garran', 'tutorial')
    order = session.combat_state.initiative_order
    index = next(i for i, entry in enumerate(order.entries) if str(entry.actor.id) == 'recruitment_dummy')
    session.combat_state = replace(session.combat_state, initiative_order=replace(order, current_index=index))
    session.resolve_enemy_turn()
    assert session.pending_enemy_turn_intent.target.id == HELPER_ID
    assert session.shared_mana_declaration.ability_id == 'garran_guard_companion'
    assert not completed(session, 'garran')
    send(session, 'pay')
    assert completed(session, 'garran') == ('garran_guard_companion',)
    assert session.state_payload()['training_arena']['tutorial']['notice'] is None
    session._commit_pending_enemy_turn()
    session.confirm_enemy_turn_result()
    assert session.state_payload()['training_arena']['tutorial']['notice']['id'] == 'garran_guard_companion'


def test_mira_can_practise_dodge_without_being_hidden(tmp_path: Path) -> None:
    from dnd_board_game.world import Coordinate
    session = arena(tmp_path)
    begin(session, 'mira', 'tutorial')
    order = session.combat_state.initiative_order
    index = next(i for i, entry in enumerate(order.entries) if str(entry.actor.id) == 'recruitment_dummy')
    session.combat_state = replace(session.combat_state, initiative_order=replace(order, current_index=index))
    enemy = session._actor_by_string_id('recruitment_dummy')
    session.combat_state = replace_actor(session.combat_state, replace(enemy, position=Coordinate(10, 18)))
    assert not session.combat_state.hidden_states
    session.resolve_enemy_turn()
    assert session.pending_reaction_window.current_option.effect_id == 'instinctive_dodge'
    session.use_instinctive_dodge_reaction()
    assert not completed(session, 'mira')
    send(session, 'pay')
    assert completed(session, 'mira') == ('instinctive_dodge',)
