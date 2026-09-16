"""Unified tutorial navigation and independent exploration sequence progress."""
from pathlib import Path
import pytest

from dnd_board_game.application.recruitment_arena import HERO_ORDER
from dnd_board_game.scenarios.confrontation import lessons_for
from dnd_board_game.ui import training_menu as menu, confrontation as exploration
from dnd_board_game.ui.routes import create_app
from dnd_board_game.ui.exploration_app import ExplorationUiSession
from dnd_board_game.hardware.board_panel import panel_position
from tests.unit.test_recruitment_arena import arena
def send(s, action, **extra):
    return exploration.command(s, dict(action=action, revision=exploration.read_store(s)['revision'], **extra))


def prepare(s):
    send(s,'acknowledge');send(s,'acknowledge')
    draw(s)


def draw(s):
    for _ in range(4):
        p=exploration.payload(s)
        if p['mana']['phase']=='reveal':
            c=next(o for o in p['board_choices'] if o['action']=='color')
            send(s,'color',**c['extra'])
        elif p['mana']['phase']=='choose':
            own=next(h for h in p['party'] if h['id']==p['actor'])
            index=max(range(len(p['mana']['offer'])), key=lambda i: own['values'][p['mana']['offer'][i]])
            send(s,'take',index=index)
        else:return



def choose(s: ExplorationUiSession, action: str) -> dict[str, object]:
    response = create_app(s).test_client().post('/api/training/menu', json=dict(action=action, revision=menu.payload(s)['revision']))
    assert response.status_code == 200, response.json
    return response.json


def finish_simple(s: ExplorationUiSession) -> None:
    prepare(s)
    for _ in range(180):
        p=exploration.payload(s)
        if p['phase']=='result':
            assert p['completed'] and p['outcome']=='success',p
            return
        if p['mana']['phase'] in {'reveal','choose'}:draw(s)
        elif p['mana']['phase']=='burn':
            send(s,'color',**next(o['extra'] for o in p['board_choices'] if o['action']=='color'))
        elif p['phase']=='turn':send(s,'test',bonus=0)
        elif p['phase']=='check':send(s,'roll',rolls=[20])
        elif p['phase']=='impact':send(s,'roll',rolls=[p['impact_die']])
        elif p['phase']=='reaction':send(s,'react')
        else:send(s,'advance')
    raise AssertionError('Confrontation did not end')


@pytest.mark.parametrize('hero', HERO_ORDER)
def test_every_hero_has_all_exploration_cases_on_runes_and_back_at_each_menu(tmp_path: Path, hero: str) -> None:
    s = arena(tmp_path)
    choose(s, 'hero:' + hero)
    assert menu.payload(s)['view'] == 'subjects'
    choose(s, 'subject:exploration')
    assert menu.payload(s)['subject'] == 'exploration'
    choose(s, 'cases')
    found = []
    while True:
        view = menu.payload(s)
        found.extend(o['action'][5:] for o in view['options'] if o['action'].startswith('case:'))
        assert any(o['action'] == 'back' for o in view['options'])
        if view['page'] + 1 == view['pages']:
            break
        menu.select_position(s, panel_position(27))
    assert found == [lesson.id for lesson in lessons_for(hero)]
    for expected in ('modes', 'subjects', 'heroes'):
        menu.select_position(s, panel_position(29))
        assert menu.payload(s)['view'] == expected


@pytest.mark.parametrize('hero', HERO_ORDER)
def test_npc_then_object_sequence_and_single_case_do_not_share_progress(tmp_path: Path, hero: str) -> None:
    s = arena(tmp_path)
    choose(s, 'hero:' + hero)
    choose(s, 'subject:exploration')
    choose(s, 'sequence')
    assert exploration.payload(s)['lesson']['id'] == 'npc'
    finish_simple(s)
    send(s, 'next')
    assert exploration.payload(s)['lesson']['id'] == 'object'
    send(s, 'leave')
    assert menu.payload(s)['view'] == 'modes'
    choose(s, 'cases')
    choose(s, 'case:object')
    assert exploration.payload(s)['run_mode'] == 'single'
    finish_simple(s)
    assert exploration.read_store(s)['sequence_progress'][hero] == 1
    send(s, 'next')
    assert menu.payload(s)['view'] == 'cases'
    assert menu.payload(s)['subject'] == 'exploration'
    choose(s, 'back')
    choose(s, 'sequence')
    assert exploration.payload(s)['lesson']['id'] == 'object'
    assert exploration.payload(s)['run_mode'] == 'sequence'


def test_course_end_returns_to_modes_and_replay_starts_first_lesson(tmp_path: Path) -> None:
    s = arena(tmp_path)
    store = exploration.read_store(s)
    store['sequence_progress'] = {'garran': len(lessons_for('garran')) - 1}
    exploration.write(s, store)
    choose(s, 'hero:garran')
    choose(s, 'subject:exploration')
    choose(s, 'sequence')
    assert exploration.payload(s)['lesson']['id'] == 'practice_object'
    finish_simple(s)
    send(s, 'next')
    assert menu.payload(s)['view'] == 'modes'
    choose(s, 'sequence')
    assert exploration.payload(s)['lesson']['id'] == 'npc'


def test_case_save_retry_during_roll_and_return_from_setup(tmp_path: Path) -> None:
    s = arena(tmp_path)
    exploration.start_course(s, 'brakka', case_id='npc')
    prepare(s)
    send(s, 'test', bonus=0)
    old = exploration.read_store(s)['revision']
    s.save_snapshot()
    s.load_snapshot()
    assert exploration.payload(s)['run_mode'] == 'single'
    response = create_app(s).test_client().post('/api/exploration-mana', json=dict(action='retry', revision=exploration.read_store(s)['revision']))
    assert response.status_code == 200, response.json
    assert exploration.read_store(s)['current']['state']['stage']=='introduction'
    assert exploration.payload(s)['run_mode'] == 'single'
    with pytest.raises(ValueError):
        exploration.command(s, dict(action='roll', revision=old, rolls=[20]))
    send(s, 'acknowledge')
    send(s, 'leave')
    assert menu.payload(s)['view'] == 'cases'
    assert menu.payload(s)['hero_id'] == 'brakka'


def test_leaving_unfinished_roll_preserves_sequence_and_clears_active_lesson(tmp_path: Path) -> None:
    s = arena(tmp_path)
    exploration.start_course(s, 'brakka')
    prepare(s)
    send(s, 'test', bonus=0)
    send(s, 'leave')
    assert not exploration.active(s)
    assert menu.payload(s)['view'] == 'modes'
    choose(s, 'sequence')
    assert exploration.payload(s)['lesson']['id'] == 'npc'
    assert exploration.read_store(s)['current']['state']['stage']=='introduction'


def test_party_composition_and_progress_survive_retry_and_save(tmp_path):
    s=arena(tmp_path)
    choose(s,'hero:lorian');choose(s,'subject:exploration');choose(s,'party')
    initial=exploration.selected_party(s,'lorian')
    for h in HERO_ORDER:
        if h not in initial and len(exploration.selected_party(s,'lorian'))<5:choose(s,'member:'+h)
    assert len(exploration.selected_party(s,'lorian'))==5
    choose(s,'back');choose(s,'cases');choose(s,'case:object')
    prepare(s)
    assert len(exploration.payload(s)['party'])==5
    assert len({a.position for a in s.custom_party})==1
    assert s.state.party_position.marker_position.col==9 and s.state.party_position.marker_position.row==18
    send(s,'support',target='garran')
    s.save_snapshot();s.load_snapshot()
    assert exploration.payload(s)['needs_resume']
    with pytest.raises(ValueError):send(s,'advance')
    send(s,'resume',stacks_preserved=True)
    assert not exploration.payload(s)['needs_resume']
    send(s,'leave')
    assert len(exploration.selected_party(s,'lorian'))==5


def test_old_save_is_separate_from_new_party_course(tmp_path):
    from dnd_board_game.ui import exploration_mana as legacy
    s=arena(tmp_path)
    old=legacy.read_store(s)
    old['completed']=['garran:npc'];old['sequence_progress']={'garran':9}
    legacy.write_store(s,old)
    exploration.start_course(s,'garran')
    assert exploration.payload(s)['lesson']['id']=='npc'
    assert not exploration.read_store(s)['completed']


@pytest.mark.parametrize('case,phase',[('charge','turn'),('reaction','reaction'),('drain','turn')])
def test_targeted_cases_start_at_edge_condition_and_can_leave_on_rune(tmp_path,case,phase):
    from dnd_board_game.ui.exploration_mana_board import select_position
    s=arena(tmp_path)
    exploration.start_course(s,'lorian',case_id=case)
    send(s,'acknowledge')
    assert exploration.payload(s)['setup']['preparation']
    send(s,'acknowledge')
    assert exploration.payload(s)['phase']==phase
    if case=='charge':
        assert exploration.payload(s)['mana']['points']==14
        send(s,'take',index=0)
        assert exploration.payload(s)['mana']['points']==21
    elif case=='drain':assert exploration.payload(s)['mana']['deck']==3
    else:send(s,'react')
    select_position(s,panel_position(29))
    assert not exploration.active(s) and menu.payload(s)['view']=='cases'


def test_resume_preserves_influence_roll_and_rejects_old_revision(tmp_path):
    s=arena(tmp_path)
    exploration.start_course(s,'erynd',case_id='object')
    prepare(s)
    send(s,'test',bonus=0);send(s,'roll',rolls=[20])
    before=exploration.payload(s)
    assert before['phase']=='impact'
    s.save_snapshot();s.load_snapshot()
    assert exploration.payload(s)['needs_resume']
    with pytest.raises(ValueError):send(s,'roll',rolls=[4])
    send(s,'resume',stacks_preserved=True)
    with pytest.raises(ValueError):exploration.command(s,dict(action='roll',rolls=[4],revision=before['revision']))
    restored=exploration.payload(s)
    assert restored['attempt']['modifier_total']==before['attempt']['modifier_total']
    send(s,'roll',rolls=[4])
    assert exploration.payload(s)['last_impact']==4+before['attempt']['modifier_total']


def test_favor_obligation_survives_leave_and_new_case(tmp_path):
    s=arena(tmp_path)
    exploration.start_course(s,'erynd',case_id='favor')
    prepare(s);send(s,'test',bonus=0);send(s,'roll',rolls=[1])
    p=exploration.payload(s)
    send(s,'color',**next(o['extra'] for o in p['board_choices'] if o['action']=='color'))
    send(s,'advance');draw(s)
    send(s,'favor')
    assert exploration.payload(s)['obligation']
    obligations=exploration.read_store(s)['obligations']
    send(s,'leave')
    exploration.start_course(s,'erynd',case_id='object')
    assert exploration.read_store(s)['obligations']==obligations
