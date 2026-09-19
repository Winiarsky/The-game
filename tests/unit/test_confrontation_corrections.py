"""Correct physical input without resetting checks, costs, or the encounter."""
import pytest

from dnd_board_game.ui import confrontation as c, exploration_mana_board as board
from dnd_board_game.rules.confrontation import Confrontation
from dnd_board_game.hardware.board_panel import panel_position
from tests.unit.test_confrontation_presentation import start, command, choose_approaches


def state(s):
    return Confrontation.from_data(c.read_store(s)['current']['state'])


def prepared(tmp_path):
    s = start(tmp_path)
    command(s, 'acknowledge'); choose_approaches(s); command(s, 'acknowledge')
    return s


def undo(s):
    view = c.payload(s)
    control = next(x for x in view['board_choices'] if x['action'] == 'undo')
    assert panel_position(control['slot']) in board.scan_target(s).positions
    return board.select_position(s, panel_position(control['slot']))


def test_approach_correction_releases_exclusive_choice_and_keeps_revision(tmp_path):
    s = start(tmp_path); command(s, 'acknowledge')
    first = c.payload(s)['actor']
    before = state(s)
    option = next(a for a in c.payload(s)['approaches'] if not a['repeatable'])
    command(s, 'approach', approach=option['id'])
    assert c.payload(s)['actor'] != first
    assert not next(a for a in c.payload(s)['approaches'] if a['id'] == option['id'])['available']
    revision = c.payload(s)['revision']
    undo(s)
    assert state(s) == before
    assert c.payload(s)['actor'] == first
    assert next(a for a in c.payload(s)['approaches'] if a['id'] == option['id'])['available']
    assert c.payload(s)['revision'] > revision
    with pytest.raises(ValueError): c.command(s, dict(action='undo', revision=revision))
    choose_approaches(s)
    assert c.payload(s)['phase'] == 'setup'
    undo(s)
    assert c.payload(s)['phase'] == 'approach'
    choose_approaches(s); command(s, 'acknowledge')
    with pytest.raises(ValueError): command(s, 'undo')


def test_correct_both_reported_colors_then_chosen_card_and_passives(tmp_path):
    s = prepared(tmp_path)
    before = state(s)
    command(s, 'color', color='B'); command(s, 'color', color='B')
    assert state(s).mana.offer == ('B', 'B')
    undo(s); undo(s)
    assert state(s) == before
    assert 'Nie dobieraj kolejnej' in c.payload(s)['correction_notice']
    command(s, 'color', color='C'); command(s, 'color', color='N')
    offer = state(s)
    command(s, 'take', index=0)
    assert state(s).mana.hand(before.actor.id) == ('C',)
    undo(s)
    assert state(s) == offer
    assert not c.payload(s)['party'][0]['passives']
    command(s, 'take', index=1)
    assert state(s).mana.offer == ('C',)
    assert state(s).mana.hand(before.actor.id) == ('N',)
    bonus = next(x['extra']['bonus'] for x in c.payload(s)['board_choices'] if x['action'] == 'test')
    command(s, 'test', bonus=bonus)
    with pytest.raises(ValueError): command(s, 'undo')


def test_correct_burn_keeps_support_and_cannot_replay_it(tmp_path):
    s = prepared(tmp_path)
    command(s, 'color', color='B'); command(s, 'color', color='N'); command(s, 'take', index=0)
    target = next(x['extra']['target'] for x in c.payload(s)['board_choices'] if x['action'] == 'support')
    command(s, 'support', target=target)
    before = state(s)
    assert dict(before.aids)[target] >= 1
    with pytest.raises(ValueError): command(s, 'undo')
    command(s, 'color', color='C')
    undo(s)
    assert state(s) == before and dict(state(s).aids)[target] == dict(before.aids)[target]
    command(s, 'color', color='Z')
    assert state(s).mana.burned == ('Z',)
    command(s, 'advance')
    with pytest.raises(ValueError): command(s, 'undo')


def test_save_resume_preserves_correction_but_requires_physical_confirmation(tmp_path):
    s = prepared(tmp_path)
    command(s, 'color', color='B')
    before = state(s)
    command(s, 'color', color='N')
    s.save_snapshot(); s.load_snapshot()
    assert c.payload(s)['needs_resume']
    assert not any(x['action']=='undo' for x in c.payload(s)['board_choices'])
    with pytest.raises(ValueError): command(s, 'undo')
    command(s, 'resume', stacks_preserved=True)
    undo(s)
    assert state(s) == before
    # Incorrect reports rejected by conservation must not erase prior corrections.
    store = c.read_store(s); previous = store['current']['corrections']
    with pytest.raises(ValueError): command(s, 'color', color='invalid')
    assert c.read_store(s)['current']['corrections'] == previous
