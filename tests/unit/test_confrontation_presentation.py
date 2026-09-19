"""Mission portraits, spoiler timing and physical mana rune feedback."""
from pathlib import Path
from typing import Any

import pytest

from dnd_board_game.hardware.board_panel import panel_position
from dnd_board_game.ui import confrontation as c, exploration_mana_board as board
from tests.unit.test_mission_zero import session, stage, send
from dnd_board_game.ui.exploration_app import ExplorationUiSession


def start(tmp_path: Path, count: int = 3, scene_name: str = 'nessa') -> ExplorationUiSession:
    s = session(tmp_path, count)
    stage(s, 'road' if scene_name == 'cart' else 'brief')
    send(s, 'cart' if scene_name == 'cart' else 'negotiate')
    return s


def choose_approaches(s: ExplorationUiSession, approach: str | None = None) -> None:
    while c.payload(s)['phase'] == 'approach':
        options = [a for a in c.payload(s)['approaches'] if a['available']]
        selected = approach or next((a['id'] for a in options if '*' in a['supports']), options[0]['id'])
        c.command(s, dict(action='approach', approach=selected, revision=c.payload(s)['revision']))


def command(s: ExplorationUiSession, action: str, **extra: Any) -> dict[str, Any]:
    return c.command(s, dict(action=action, revision=c.payload(s)['revision'], **extra))


@pytest.mark.parametrize('count', [3, 6])
def test_mission_portraits_and_deck_preparation_without_compromise_spoiler(tmp_path: Path, count: int):
    s = start(tmp_path, count)
    p = c.payload(s)
    assert 'nessa_portrait' in p['image_url']
    assert all(f"/{hero['id']}.png?" in hero['portrait_url'] for hero in p['party'])
    assert 'kompromis' not in p['scene']['goal'].lower()
    assert '1k8' not in p['scene']['goal']
    assert not any(option['action'] == 'compromise' for option in p['board_choices'])
    choose_approaches(s)
    command(s, 'acknowledge')
    choose_approaches(s)
    p = c.payload(s)
    assert p['mana']['copies'] == count * 2
    instruction = p['mana']['preparation']
    assert str(count * 10) in instruction
    assert all(word in instruction for word in ('czerwone:', 'białe:', 'zielone:', 'czarne:', 'niebieskie:'))
    assert 'Figurka' not in instruction and '(5,7)' not in instruction


def test_color_reporting_and_card_selection_use_mana_led_colors(tmp_path: Path):
    s = start(tmp_path)
    choose_approaches(s)
    command(s, 'acknowledge')
    choose_approaches(s)
    command(s, 'acknowledge')
    p = c.payload(s)
    assert p['mana']['phase'] == 'reveal'

    def assert_color(slot: int, color: str):
        frames = board.scan_target(s).feedback.frames
        frame = next(f for f in frames if panel_position(slot) in f.positions)
        assert frame.color == tuple(round(component * .65) for component in board.MANA_LED_COLORS[color])

    for option in p['board_choices']:
        if option['action'] == 'color':
            assert_color(option['slot'], option['extra']['color'])
    command(s, 'color', color='F')
    command(s, 'color', color='N')
    assert c.payload(s)['mana']['phase'] == 'choose'
    assert_color(6, 'F')
    assert_color(7, 'N')
    command(s, 'take', index=0)
    assert c.payload(s)['mana']['offer'] == ['N']


def test_scroll_runes_do_not_change_confrontation_or_physical_deck(tmp_path: Path):
    s = start(tmp_path)
    before = c.read_store(s)
    for slot in (26, 27):
        assert panel_position(slot) in board.scan_target(s).positions
        result = board.select_position(s, panel_position(slot))
        assert result['panel_event'] == dict(slot=slot, context=f"confrontation-scroll:{c.payload(s)['revision']}")
        assert c.read_store(s) == before


def test_full_charge_has_one_test_and_support_shows_accumulated_bonus(tmp_path: Path):
    from dataclasses import replace
    from dnd_board_game.rules import confrontation as rules
    from tests.unit.test_confrontation import charged

    s = start(tmp_path)
    choose_approaches(s)
    command(s, 'acknowledge')
    choose_approaches(s)
    command(s, 'acknowledge')
    store = c.read_store(s)
    state = rules.Confrontation.from_data(store['current']['state'])
    color = max(state.mana.point_values(state.actor.id), key=state.mana.point_values(state.actor.id).get)
    state = charged(state, {state.actor.id: (color,) * 4})
    target = state.participants[1]
    state = replace(state, aids=((target.id, 3),))
    store['current']['state'] = state.to_data()
    c.write(s, store)
    options = c.payload(s)['board_choices']
    tests = [option for option in options if option['action'] == 'test']
    assert len(tests) == 1 and tests[0]['extra']['bonus'] == 6
    assert 'spal 1' in tests[0]['label']
    help_choice = next(option for option in options if option['action'] == 'support' and option['extra']['target'] == target.id)
    expected = 3 + rules.support_bonus(state)
    assert f'razem +{expected}' in help_choice['label']
    command(s, 'support', target=target.id)
    payload = c.payload(s)
    assert next(hero for hero in payload['party'] if hero['id'] == target.id)['aid'] == expected
    assert payload['mana']['phase'] == 'burn' and payload['mana']['pending'] == 1
    assert not any(option['action'] == 'advance' for option in payload['board_choices'])


def test_assignment_save_and_directed_help_use_board_runes(tmp_path: Path):
    s = start(tmp_path)
    command(s, 'acknowledge')
    assert c.payload(s)['phase'] == 'approach'
    choices = [o for o in c.payload(s)['board_choices'] if o['action'] == 'approach']
    assert [o['slot'] for o in choices] == [6, 7, 8, 9, 10, 11]
    target = board.scan_target(s)
    assert all(panel_position(slot) not in target.positions for slot in range(6))
    assert all(panel_position(o['slot']) in target.positions for o in choices)
    for index, approach in enumerate(('compliments','logic','demands')):
        payload = c.payload(s)
        assert payload['actor'] == payload['party'][index]['id']
        assert not payload['needs_resume']
        choice = next(o for o in payload['board_choices'] if o['action']=='approach' and o['extra']['approach']==approach)
        board.select_position(s, panel_position(choice['slot']))
        if index == 0:
            s.save_snapshot();s.load_snapshot()
            assert c.payload(s)['party'][0]['assigned']
            assert not next(a for a in c.payload(s)['approaches'] if a['id']=='compliments')['available']
            assert all(o['slot'] != 6 for o in c.payload(s)['board_choices'])
            assert panel_position(6) not in board.scan_target(s).positions
            with pytest.raises(ValueError):command(s, 'approach', approach='compliments')
    assert c.payload(s)['phase']=='setup'
    command(s,'acknowledge')
    command(s,'color',color='C');command(s,'color',color='B');command(s,'take',index=0)
    payload = c.payload(s)
    supports = [o for o in payload['board_choices'] if o['action']=='support']
    assert [o['extra']['target'] for o in supports] == [payload['party'][1]['id']]
    with pytest.raises(ValueError):command(s,'support',target=payload['party'][2]['id'])
    assert any(o['action']=='peek' for o in payload['board_choices'])


def test_untouched_old_save_gets_approach_preparation_without_resetting_active_play(tmp_path: Path):
    s = start(tmp_path)
    store = c.read_store(s)
    store['current']['state'].pop('approach_options')
    store['current']['state'].pop('approach_selection_version', None)
    store['current']['state']['stage'] = 'setup'
    store['current']['scene'].pop('approaches')
    c.write(s, store)
    migrated = c.read_store(s)
    assert migrated['current']['state']['stage'] == 'introduction'
    assert migrated['current']['state']['approach_options']
    assert migrated['current']['scene']['approaches']
    command(s, 'acknowledge')
    choose_approaches(s)
    command(s, 'acknowledge')
    command(s, 'color', color='C')
    store = c.read_store(s)
    before = store['current']['state']['mana']
    store['current']['state'].pop('approach_options')
    store['current']['state'].pop('approach_selection_version', None)
    c.write(s, store)
    assert c.read_store(s)['current']['state']['mana'] == before
    assert c.payload(s)['phase'] == 'turn'


def test_old_partial_draft_preserves_unique_prefix_and_adds_missing_options(tmp_path: Path):
    s=start(tmp_path,6)
    command(s,'acknowledge')
    command(s,'approach',approach='compliments')
    store=c.read_store(s)
    old=store['current']['state']
    old.pop('approach_selection_version')
    old['approach_options']=[options[:5] for options in old['approach_options']]
    old['participants'][1]=old['approach_options'][1][0]
    old['turn']=2
    c.write(s,store)
    migrated=c.read_store(s)['current']['state']
    assert migrated['turn']==1
    assert migrated['participants'][0]['approach_id']=='compliments'
    assert not migrated['participants'][1]['approach_id']
    assert len(migrated['approach_options'][0])==6
    choose_approaches(s)
    assert c.payload(s)['phase']=='setup'


def test_repeatable_choice_keeps_same_rune_after_selection_and_reload(tmp_path: Path):
    s=start(tmp_path)
    command(s,'acknowledge')
    choice=next(a for a in c.payload(s)['approaches'] if a['id']=='logic')
    assert choice['repeatable']
    board.select_position(s,panel_position(choice['slot']))
    s.save_snapshot();s.load_snapshot()
    assert next(a for a in c.payload(s)['approaches'] if a['id']=='logic')['available']
    assert panel_position(choice['slot']) in board.scan_target(s).positions
    board.select_position(s,panel_position(choice['slot']))
    assert [h['method'] for h in c.payload(s)['party'][:2]]==['Logiczne argumenty']*2
    # Migrate an unstarted version-2 draft without losing its assignments.
    store=c.read_store(s)
    store['current']['state']['approach_selection_version']=2
    c.write(s,store)
    state=c.read_store(s)['current']['state']
    assert state['approach_selection_version']==3
    assert state['turn']==2
    assert all(p['repeatable'] for p in state['participants'][:2])


def test_cart_mixed_approaches_for_six_heroes_and_old_preparation(tmp_path: Path):
    s=start(tmp_path,6,scene_name='cart')
    store=c.read_store(s)
    store['current']['state'].pop('approach_options')
    store['current']['state'].pop('approach_selection_version')
    store['current']['state']['stage']='setup'
    c.write(s,store)
    assert c.payload(s)['phase']=='introduction'
    command(s,'acknowledge')
    p=c.payload(s)
    assert p['effect_name']=='Postęp'
    assert 'P02' not in p['scene']['description'] and 'Zbierz elementy' not in p['scene']['description']
    assert {a['id'] for a in p['approaches'] if a['repeatable']}=={'lift','unload'}
    for approach in ('lash','lift','lift','unload','unload','ground'):
        p=c.payload(s)
        chosen=next(a for a in p['approaches'] if a['id']==approach)
        assert chosen['available']
        board.select_position(s,panel_position(chosen['slot']))
        if c.payload(s)['phase']=='approach':
            after=next(a for a in c.payload(s)['approaches'] if a['id']==approach)
            assert after['available']==chosen['repeatable']
            assert (panel_position(chosen['slot']) in board.scan_target(s).positions)==chosen['repeatable']
    assert c.payload(s)['phase']=='setup'
    s.save_snapshot();s.load_snapshot()
    assert c.payload(s)['phase']=='setup'
    assert [h['method'] for h in c.payload(s)['party']].count('Uniesienie wozu')==2
    command(s,'acknowledge')
    assert c.payload(s)['phase']=='turn'


def test_saved_peek_skips_color_reporting_and_uses_only_position_runes(tmp_path: Path):
    s=start(tmp_path)
    command(s,'acknowledge');choose_approaches(s);command(s,'acknowledge')
    command(s,'color',color='C');command(s,'color',color='B');command(s,'take',index=0)
    command(s,'peek')
    store=c.read_store(s);before=store['current']['state']['mana']
    store['current']['state']['stage']='peek_color'
    c.write(s,store);s.save_snapshot();s.load_snapshot()
    if c.payload(s)['needs_resume']:command(s,'resume',stacks_preserved=True)
    p=c.payload(s)
    assert p['phase']=='peek_choice' and 'peek_color' not in p
    choices=[o for o in p['board_choices'] if o['action']=='peek_finish']
    assert [(o['slot'],o['extra']['move_top']) for o in choices]==[(18,False),(19,True)]
    assert not any(o['action'] in {'color','peek_color'} for o in p['board_choices'])
    with pytest.raises(ValueError):command(s,'peek_color',color='N')
    board.select_position(s,panel_position(19))
    after=c.read_store(s)['current']['state']
    assert after['stage']=='after_action'
    assert after['mana']['deck']==[before['deck'][-1],*before['deck'][:-1]]
    assert after['mana']['burned']==before['burned']
