"""Choosing a pending reaction preserves the window, resources and actor identity."""
from dataclasses import replace
from types import SimpleNamespace

import pytest

from dnd_board_game.combat.reactions import ReactionKind, ReactionOption, ReactionStage, ReactionWindow, advance_reaction_window
from dnd_board_game.hardware.board_panel import panel_position
from dnd_board_game.ui.reaction_choices import select_option, choose, view, select_position, scan_target
from dnd_board_game.world import Coordinate


def option(key,actor='garran',kind=ReactionKind.OPPORTUNITY_ATTACK):
    return ReactionOption(key,kind,actor,'enemy','leaves_reach',label=key)


def test_select_different_reaction_preserves_history_and_remaining_options():
    spent,one,two,other=option('spent'),option('one'),option('two'),option('other','mira')
    window=ReactionWindow('enemy','leaves_reach',(spent,one,two,other),current_index=1)
    selected=select_option(window,'two')
    assert selected.current_option==two
    assert selected.options==(spent,two,one,other)
    assert window.current_option==one
    assert selected.current_index==1 and selected.stage==ReactionStage.CHOICE
    assert select_option(selected,'one').options==window.options
    with pytest.raises(ValueError):select_option(window,'spent')


def test_selection_cannot_change_reaction_after_roll_starts():
    window=ReactionWindow('enemy','leaves_reach',(option('one'),option('two')),stage=ReactionStage.ATTACK_ROLL)
    with pytest.raises(ValueError):select_option(window,'two')


def test_reactors_with_same_weapon_button_choose_by_figure_field(monkeypatch):
    from dnd_board_game.ui import reaction_choices as module
    garran=SimpleNamespace(id='garran',name='Garran',position=Coordinate(4,4))
    mira=SimpleNamespace(id='mira',name='Mira',position=Coordinate(7,4))
    s=SimpleNamespace(combat_state=SimpleNamespace(actors=(garran,mira)),
                      pending_reaction_window=ReactionWindow('enemy','leaves_reach',(option('garran-oa'),option('mira-oa','mira'))),
                      board_selection_revision=10,board_panel_context=None)
    monkeypatch.setattr(module,'_available',lambda current:current.pending_reaction_window.remaining_options)
    events=[]
    s._activate_current_reaction_option=lambda:events.append('activate')
    s._record=lambda kind,data:events.append((kind,data))
    s._sync_board_leds=lambda:events.append('leds')
    s.state_payload=lambda:{'selected':s.pending_reaction_window.current_option.id}
    p=view(s)
    assert p['actor_name']=='Garran' and p['choices'][0]['slot']==1 and p['choices'][0]['cost']==[]
    target=scan_target(s)
    assert garran.position in target.positions and mira.position in target.positions
    assert panel_position(28) in target.positions
    assert select_position(s,mira.position)=={'selected':'mira-oa'}
    assert view(s)['actor_name']=='Mira' and view(s)['choices'][0]['slot']==1
    assert s.board_selection_revision==11
    assert select_position(s,panel_position(28))=={'selected':'mira-oa'}
    assert s.pending_reaction_window.choice_confirmed
    assert len(s.pending_reaction_window.options)==2
    with pytest.raises(ValueError):choose(s,'garran-oa',revision=10)


def test_same_actor_ready_and_opportunity_attack_have_distinct_buttons(monkeypatch):
    from dnd_board_game.ui import reaction_choices as module
    actor=SimpleNamespace(id='garran',name='Garran',position=Coordinate(4,4))
    s=SimpleNamespace(combat_state=SimpleNamespace(actors=(actor,)),board_selection_revision=1,
                      pending_reaction_window=ReactionWindow('enemy','moves',(option('ready',kind=ReactionKind.READY_ATTACK),option('oa'))))
    monkeypatch.setattr(module,'_available',lambda current:current.pending_reaction_window.remaining_options)
    choices=view(s)['choices']
    assert len({choice['slot'] for choice in choices})==2
    assert next(choice for choice in choices if choice['id']=='oa')['slot']==1


def test_new_window_and_next_actor_require_fresh_choice():
    window=ReactionWindow('enemy','moves',(option('one'),option('two','mira')))
    assert not window.choice_confirmed
    next_window=advance_reaction_window(replace(window,choice_confirmed=True),available_reactor_ids=('mira',))
    assert next_window.current_option.id=='two' and not next_window.choice_confirmed


def test_real_reaction_budget_and_hand_gate_paid_option_but_not_weapon():
    from dnd_board_game.ui.reaction_choices import _available
    from dnd_board_game.rules.shared_mana import sync_runes
    from tests.unit.test_rune_resources import state_with_hand
    state=state_with_hand()
    shield=ReactionOption('shield',ReactionKind.DEFENSIVE_SPELL,'nimra','nimra','attack',effect_id='shield')
    s=SimpleNamespace(combat_state=state,shared_mana_declaration=None,
                      pending_reaction_window=ReactionWindow('enemy','attack',(option('weapon'),shield)))
    assert [o.id for o in _available(s)]==['weapon']
    pool=state.shared_mana.runes
    hand=list(pool.hand('garran'));hand.remove('Wieża')
    pool=replace(pool,hands=(('garran',tuple(hand)),('mira',()),('nimra',('Wieża',))))
    s.combat_state=replace(state,shared_mana=sync_runes(state.shared_mana,pool))
    assert [o.id for o in _available(s)]==['weapon','shield']
    s.pending_reaction_window=replace(s.pending_reaction_window,choice_confirmed=True)
    assert _available(s)==()
