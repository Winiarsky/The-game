"""Physical recovery and one-shot offers must not be skipped by normal actions."""
from dataclasses import replace
from pathlib import Path
import json

import pytest

from dnd_board_game.rules import confrontation as r
from dnd_board_game.ui import confrontation as c, exploration_mana_board as board
from dnd_board_game.hardware.board_panel import panel_position
from tests.unit.test_confrontation import charged, game, settle
from tests.unit.test_confrontation_presentation import start, choose_approaches, command


def prepared(tmp_path: Path, recovery: bool = True):
    session = start(tmp_path)
    command(session, 'acknowledge')
    choose_approaches(session)
    command(session, 'acknowledge')
    store = c.read_store(session)
    state = r.Confrontation.from_data(store['current']['state'])
    if recovery:
        state = replace(state, turn=2, mana=replace(state.mana, actor='dagna'))
        state = charged(state, {'dagna': ('Z',)}, deck_size=15)
        state = r.roll_impact(r.roll_check(r.declare(state, 0), 19), 1)
    else:
        state = charged(state, {}, deck_size=15)
        state = replace(state, stage='after_action', resistance=state.maximum // 2)
    store['current']['state'] = state.to_data()
    c.write(session, store)
    return session


def test_recovery_waits_for_physical_confirmation_and_survives_save():
    state = charged(game(('dagna', 'garran', 'brakka')), {'dagna': ('Z',)}, deck_size=0)
    state = r.roll_impact(r.roll_check(r.declare(state, 0), 19), 1)
    assert state.stage == 'recovery' and not state.outcome
    before = state.mana
    loaded = r.Confrontation.from_data(json.loads(json.dumps(state.to_data())))
    for action in (lambda: r.advance(loaded), lambda: r.report_color(loaded, 'C'),
                   lambda: r.declare(loaded, 0), lambda: r.roll_impact(loaded, 1)):
        with pytest.raises(ValueError): action()
    confirmed = r.confirm_recovery(loaded)
    assert confirmed.mana.burned == before.burned[1:]
    assert confirmed.mana.deck == (before.burned[0],)
    assert confirmed.mana.phase == 'burn'
    assert confirmed.mana.pending_count == 1
    with pytest.raises(ValueError): r.confirm_recovery(confirmed)
    assert settle(confirmed).mana.burned == (*before.burned[1:], before.burned[0])


def test_recovery_on_winning_hit_still_requires_confirmation():
    state = charged(game(('dagna', 'garran', 'brakka')), {'dagna': ('Z',)}, deck_size=0)
    state = replace(state, resistance=1)
    pending = r.roll_impact(r.roll_check(r.declare(state, 0), 19), 1)
    assert pending.stage == 'recovery' and pending.resistance == 0 and not pending.outcome
    assert settle(pending).outcome == 'success'


def test_recovery_board_and_resume_gate(tmp_path):
    session = prepared(tmp_path)
    before = c.payload(session)
    assert before['actor'] == 'dagna' and before['recovery_color']
    actions = {a['action'] for a in before['board_choices']}
    assert actions == {'confirm_recovery', 'scroll', 'leave'}
    session._exploration_mana_confirmed = ''
    with pytest.raises(ValueError): command(session, 'confirm_recovery')
    assert 'resume' in {a['action'] for a in c.payload(session)['board_choices']}
    command(session, 'resume', stacks_preserved=True)
    board.select_position(session, panel_position(28))
    after = c.payload(session)
    assert after['mana']['burned'] == before['mana']['burned'] - 1
    assert after['mana']['phase'] == 'burn'
    assert not after['recovery_color']
    with pytest.raises(ValueError): command(session, 'confirm_recovery')


@pytest.mark.parametrize('accept', [True, False])
def test_compromise_interrupts_before_next_turn_and_requires_explicit_decision(tmp_path, accept):
    session = prepared(tmp_path, recovery=False)
    before = c.payload(session)
    assert before['compromise_pending']
    assert {a['action'] for a in before['board_choices']} == {'compromise', 'decline_compromise', 'scroll', 'leave'}
    for action, extra in [('advance', {}), ('test', {'bonus': 0}), ('support', {'target': 'dagna'}), ('peek', {}), ('undo', {})]:
        with pytest.raises(ValueError, match='Najpierw'): command(session, action, **extra)
    board.select_position(session, panel_position(24 if accept else 25))
    after = c.payload(session)
    assert after['mana'] == before['mana']
    assert not after['compromise_pending']
    assert after['outcome'] == ('compromise' if accept else '')
    if not accept:
        command(session, 'advance')
        assert not c.payload(session)['compromise_pending']
        with pytest.raises(ValueError): command(session, 'compromise')


def test_offer_waits_for_test_cost_and_never_interrupts_success(tmp_path):
    session = prepared(tmp_path, recovery=False)
    store = c.read_store(session)
    state = r.Confrontation.from_data(store['current']['state'])
    from dnd_board_game.rules import pooled_mana as cards
    store['current']['state'] = replace(state, mana=cards.attack_mana(state.mana, 'deck', 1)).to_data()
    c.write(session, store)
    assert not c.payload(session)['compromise_pending']
    command(session, 'color', color=state.mana.deck[0])
    assert c.payload(session)['compromise_pending']
    assert not r.compromise_available(replace(state, resistance=0))
    assert not r.compromise_available(replace(state, resistance=state.maximum))
