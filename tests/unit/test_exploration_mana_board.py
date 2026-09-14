"""Exercise printed runes through the real scan transport and current LED masks."""
from pathlib import Path

import pytest

from dnd_board_game.hardware.board_panel import panel_position
from dnd_board_game.rules.exploration_mana_catalog import HEROES
from dnd_board_game.ui.exploration_mana import payload, read_store
from dnd_board_game.ui.routes import create_app
from tests.unit.test_exploration_mana_runtime import prepared, send
from tests.unit.test_initiative_panel import Board
from tests.unit.test_recruitment_arena import arena


def rune(s, action: str, **extra):
    return next(c for c in payload(s)['board_choices'] if c['action'] == action
                and all(c['extra'].get(k) == v for k, v in extra.items()))


def press(s, action: str, **extra):
    return s.select_board_position(panel_position(rune(s, action, **extra)['slot']))


@pytest.mark.parametrize('hero', HEROES)
@pytest.mark.parametrize('kind', ['npc', 'object'])
def test_all_methods_colors_and_pass_via_scans(tmp_path: Path, hero: str, kind: str):
    s = arena(tmp_path)
    send(s, 'open', hero=hero, lesson=kind)
    board = Board()
    s.attach_board_connection(board, backend='simulator')
    client = create_app(s).test_client()

    def scan(action: str, **extra):
        c = rune(s, action, **extra)
        target = s._current_board_scan_target()
        assert set(target.positions) == ({panel_position(28)} if payload(s).get('attempt', {}).get('phase') == 'roll' else {panel_position(v['slot']) for v in payload(s)['board_choices']})
        assert set(p for frame in target.feedback.frames for p in frame.positions if p.col == 19) == set(target.positions)
        selection = s._board_selection_payload()
        assert selection['auto_arm']
        board.selected = panel_position(c['slot']).as_tuple()
        response = client.post('/api/board/scan', json={'revision': selection['revision'], 'automatic': True})
        assert response.status_code == 200, response.json
        return response.json

    scan('acknowledge')
    while payload(s)['phase'] == 'setup':
        scan('acknowledge')
    method = next(o for o in payload(s)['options'] if o['enabled'])
    assert rune(s, 'start', method=method['id'])['slot'] == 6 + HEROES.index(hero)
    old = s._board_selection_payload()['revision']
    scan('start', method=method['id'])
    before = read_store(s)
    scans = board.scans
    client.post('/api/board/scan', json={'revision': old, 'automatic': True})
    assert board.scans == scans and read_store(s) == before
    assert not any(c['action'] == 'stand' for c in payload(s)['board_choices'])
    with pytest.raises(ValueError):
        s.select_board_position(panel_position(19))
    scan('choose', color='C')
    assert payload(s)['attempt']['total'] == 7
    scan('stand')
    assert payload(s)['attempt']['phase'] == 'roll'
    event = scan('roll')
    assert event['panel_event'] == {'slot': 28, 'context': None}
    assert event['board_selection']['revision'] == s._board_selection_payload()['revision']
    send(s, 'roll', rolls=[20])
    scan('next')
    assert payload(s)['phase'] == 'introduction'
    scan('leave')
    assert not payload(s)['active']


def test_practice_selects_each_present_method_without_implicit_confirm(tmp_path: Path):
    s = arena(tmp_path)
    for hero in ('erynd', 'garran', 'brakka'):
        send(s, 'open', hero='erynd', lesson='practice_npc')
        press(s, 'acknowledge')
        while payload(s)['phase'] == 'setup':
            press(s, 'acknowledge')
        methods = [c for c in payload(s)['board_choices'] if c['action'] == 'start']
        assert {c['slot'] for c in methods} == {6, 7, 12}
        with pytest.raises(ValueError):
            s.select_board_position(panel_position(28))
        selected = next(o for o in payload(s)['options'] if o['hero'] == hero)
        press(s, 'start', method=selected['id'])
        assert read_store(s)['current']['attempt']['method_id'] == selected['id']
        press(s, 'choose', color='C')
        press(s, 'stand')
        send(s, 'roll', rolls=[20])
        press(s, 'leave')


def test_guided_mask_bust_and_resume_only_allow_current_decisions(tmp_path: Path):
    s = prepared(arena(tmp_path), 'garran', 'bust')
    for i, color in enumerate('CCNF'):
        if i:
            assert not any(c['action'] == 'stand' for c in payload(s)['board_choices'])
            press(s, 'draw')
        assert [c['extra']['color'] for c in payload(s)['board_choices'] if c['action'] == 'choose'] == [color]
        press(s, 'choose', color=color)
    assert payload(s)['attempt']['dice_count'] == 2
    assert {c['action'] for c in payload(s)['board_choices']} == {'roll', 'leave'}
    send(s, 'roll', rolls=[20, 1])
    press(s, 'leave')
    prepared(s, 'erynd', 'object')
    press(s, 'choose', color='B')
    s.save_snapshot()
    s.load_snapshot()
    assert {c['action'] for c in payload(s)['board_choices']} == {'resume', 'retry', 'leave'}
    press(s, 'resume')
    assert {c['action'] for c in payload(s)['board_choices']} == {'draw', 'stand', 'retry', 'leave'}
    press(s, 'draw')
    assert rune(s, 'empty')['slot'] == 22
    press(s, 'empty')
    assert payload(s)['attempt']['end_reason'] == 'empty'


def test_lorian_reroll_rune_and_retry_mask(tmp_path: Path):
    s = prepared(arena(tmp_path), 'lorian', 'lorian_reroll')
    press(s, 'choose', color='C')
    press(s, 'draw')
    press(s, 'choose', color='N')
    assert not any(c['action'] == 'draw' for c in payload(s)['board_choices'])
    press(s, 'stand')
    send(s, 'roll', rolls=[1])
    assert {c['action'] for c in payload(s)['board_choices']} == {'reroll', 'leave'}
    press(s, 'reroll')
    send(s, 'roll', rolls=[20])
    press(s, 'retry')
    assert payload(s)['phase'] == 'introduction'


@pytest.mark.parametrize('kind', ['object', 'bust', 'trap'])
def test_browser_dice_panel_owns_scan_mask_stream_and_review(tmp_path: Path, kind: str):
    if kind == 'trap':
        from dnd_board_game.ui import simple_traps
        from dnd_board_game.ui.training_arena import start_training_trial
        from dnd_board_game.ui.training_tutorial import acknowledge, notice_id
        from tests.unit.test_simple_combat_traps import hero_turn
        s = arena(tmp_path)
        start_training_trial(s, 'garran', 'traps', 'humanoid')
        acknowledge(s, notice_id(s))
        while not s.encounter_setup_flow.completed:
            s.confirm_encounter_setup_step()
        s.start_encounter_initiative()
        s.submit_encounter_initiative_roll(20)
        hero_turn(s, 'garran')
        simple_traps.command(s, dict(action='detect', revision=simple_traps.read(s)['revision']))
    else:
        s = prepared(arena(tmp_path), 'garran', kind)
        for i, color in enumerate('CCNF' if kind == 'bust' else 'C'):
            if i:
                press(s, 'draw')
            press(s, 'choose', color=color)
        if kind == 'object':
            press(s, 'stand')
    assert s._board_panel_enabled()
    board = Board()
    s.attach_board_connection(board, backend='simulator')
    client = create_app(s).test_client()
    for index, slots, mode in ((0, [26, 27, 28], 'stream'), (1, [26, 27, 28, 29], 'stream'),
                                (2, [28, 29], 'single')):
        context = f'dice:test:{index}'
        s.configure_board_panel(context, slots, True)
        before = s.state
        target = s._current_board_scan_target()
        assert set(target.positions) == {panel_position(slot) for slot in slots}
        assert s._board_selection_payload()['input_mode'] == mode
        assert s._board_selection_payload()['auto_arm']
        for slot in slots:
            board.selected = panel_position(slot).as_tuple()
            response = client.post('/api/board/scan', json={'revision': s._board_selection_payload()['revision']})
            assert response.status_code == 200, response.json
            assert response.json['panel_event'] == {'slot': slot, 'context': context}
            assert s.state == before  # Individual dice never resolve the test.
        with pytest.raises(ValueError):
            s.select_board_position(panel_position(6))
    with pytest.raises(ValueError):
        s.configure_board_panel('decision:old', [28, 29], False)
    if kind == 'trap':
        simple_traps.command(s, dict(action='roll', roll=20, revision=simple_traps.read(s)['revision']))
    else:
        send(s, 'roll', rolls=[20, 1] if kind == 'bust' else [20])
    assert s.board_panel_context is None
