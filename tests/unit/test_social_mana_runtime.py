"""All heroes, both decisions, frozen promises and consequences through board runes."""
import json
from dataclasses import replace

import pytest

from dnd_board_game.combat.scene import set_scene_flag
from dnd_board_game.rules.exploration_mana_catalog import HEROES
from dnd_board_game.ui.exploration_mana import payload, read_store, STORE_KEY
from tests.unit.test_exploration_mana_runtime import arena, prepared, send
from tests.unit.test_exploration_mana_board import press


def pick(s, colors):
    for c in colors:
        if payload(s)['attempt']['phase'] == 'decision': press(s, 'draw')
        press(s, 'choose', color=c)


@pytest.mark.parametrize('hero', HEROES)
@pytest.mark.parametrize('kind', ['compromise','sensitive_topic','color_goal','favor'])
@pytest.mark.parametrize('take', [True, False])
def test_all_heroes_have_real_choices_and_consequences(tmp_path, hero, kind, take):
    s = prepared(arena(tmp_path), hero, 'condition_'+kind)
    if kind == 'compromise':
        pick(s, 'NCF')
        assert payload(s)['attempt']['phase'] == 'bargain'
        s.save_snapshot(); s.load_snapshot()
        if take:
            press(s, 'accept_bargain')
        else:
            press(s, 'resume')
            press(s, 'decline_bargain')
            pick(s, 'N')
    elif kind == 'sensitive_topic': pick(s, 'CCC' if take else 'NNNFB')
    elif kind == 'color_goal': pick(s, 'NNFC' if take else 'CCC')
    else:
        if take:
            pick(s, 'NNNN')
            press(s, 'draw'); press(s, 'arm_favor')
            s.save_snapshot(); s.load_snapshot(); press(s, 'resume')
            press(s, 'choose', color='C')
        else: pick(s, 'CCC')
    p = payload(s)
    assert p['attempt']['phase'] == 'result' and p['attempt']['lesson_completed']
    assert p['attempt']['outcome_kind'] == ('compromise' if kind=='compromise' and take else 'success')
    outcome = read_store(s)['outcomes'][read_store(s)['current']['token']]
    expected = 'compromise' if kind=='compromise' and take else 'sensitive_success' if kind=='sensitive_topic' and take else 'goal_success' if kind=='color_goal' and take else 'success'
    assert outcome['variant'] == expected
    ids = {f['id'] for f in p['followups']}
    if kind == 'sensitive_topic': assert ('ask_irena' in ids) != take
    if kind == 'color_goal': assert ('investigate_origin' in ids) == take
    if kind == 'favor': assert ('deliver_letter' in ids) == take
    followup = p['followups'][-1]
    press(s, 'debrief', id=followup['id'])
    assert followup['flag'] in payload(s)['attempt']['outcome_flags']
    with pytest.raises((ValueError, StopIteration)): press(s, 'debrief', id=followup['id'])
    s.save_snapshot(); s.load_snapshot()
    assert payload(s)['debrief_message'] == followup['message']
    assert len(read_store(s)['outcomes']) == 1


def test_favor_obligation_survives_failure_and_cancel_costs_nothing(tmp_path):
    s = prepared(arena(tmp_path),'garran','condition_favor')
    press(s,'arm_favor'); press(s,'cancel_favor')
    assert not read_store(s)['obligations']
    press(s,'arm_favor'); press(s,'choose',color='C')
    press(s,'stand'); send(s,'roll',rolls=[1])
    assert not payload(s)['attempt']['success'] and payload(s)['obligation']
    press(s,'debrief',id='deliver_letter')
    assert payload(s)['obligation']['fulfilled']


def test_old_store_and_frozen_promises(tmp_path, monkeypatch):
    s = prepared(arena(tmp_path),'garran','npc')
    data = read_store(s); data['version'] = 1
    data.pop('obligations'); data['current'].pop('scene_data')
    a = data['current']['attempt']; a['version'] = 1
    for key in ('condition','proposal_status','sensitive_used','favor_status'): a.pop(key)
    s.state = replace(s.state, flags=set_scene_flag(s.state.flags, STORE_KEY, json.dumps(data)))
    assert read_store(s)['version'] == 2
    assert payload(s)['condition']['kind'] == 'none'
    press(s,'choose',color='C'); press(s,'stand'); send(s,'roll',rolls=[20]); press(s,'leave')
    prepared(s,'garran','condition_sensitive_topic')
    from dnd_board_game.ui import exploration_mana as ui
    monkeypatch.setattr(ui,'scene_by_id',lambda _: (_ for _ in ()).throw(AssertionError('Promise reread from content')))
    pick(s,'CCC')
    assert 'odmawia dalszej' in payload(s)['attempt']['outcome']


def test_practice_has_three_methods_and_common_progress(tmp_path):
    s = arena(tmp_path)
    send(s,'open',hero='erynd',lesson='practice_color_goal')
    press(s,'acknowledge')
    while payload(s)['phase']=='setup': press(s,'acknowledge')
    assert len([o for o in payload(s)['options'] if o['enabled']]) == 3
    option = next(o for o in payload(s)['options'] if o['hero']=='brakka')
    press(s,'start',method=option['id']); pick(s,'NNFC')
    assert payload(s)['attempt']['actor']=='Brakka'
