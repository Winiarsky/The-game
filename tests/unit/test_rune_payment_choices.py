"""Players choose every discretionary rune; payment remains atomic."""
from collections import Counter
from dataclasses import asdict, replace
from types import SimpleNamespace

import pytest

from dnd_board_game.rules.runes import (
    available_payment_runes, card_payment_requirements, plan_card_payment,
    validate_card_payment, spend_runes,
)
from dnd_board_game.rules.shared_mana import SharedMana, pay_mana, sync_runes, finish_mana_action
from dnd_board_game.ui import shared_mana, runes
from dnd_board_game.hardware.board_panel import panel_position
from tests.unit.test_rune_resources import state_with_hand
from tests.unit.test_rune_combat_actions import playable, pay


def choose(game, rune):
    return pay(game, 'rune_choice_take', rune=rune)


def confirm(game):
    return pay(game, 'rune_choice_confirm')


def test_named_components_are_reserved_before_two_wildcards_and_boost():
    hand=('Błysk','Kotwica','Klucz','Korona')
    assert card_payment_requirements(hand,('Wieża','Błysk'))==('*','*','Błysk')
    assert available_payment_runes(hand,('Wieża','Błysk'))==('Kotwica','Klucz','Korona')
    assert plan_card_payment(hand,('Wieża','Błysk'),('Klucz','Korona'))==('Klucz','Korona','Błysk')
    with pytest.raises(ValueError):
        plan_card_payment(hand,('Wieża','Błysk'),('Błysk','Korona'))
    with pytest.raises(ValueError):
        validate_card_payment(hand,('Wieża','Błysk'),None)
    with pytest.raises(ValueError):
        validate_card_payment(hand,('Wieża','Błysk'),('Klucz','Korona','Kotwica'))


def test_direct_payment_cannot_choose_a_wildcard_or_repeat_a_copy():
    state=state_with_hand()
    mana=state.shared_mana
    with pytest.raises(ValueError,match='wybierz runy'):
        pay_mana(mana,revision=mana.revision,actor_id='garran',ability_id='shield_bash',
                 count=2,boosts=(('damage_d4',1),))
    paid=pay_mana(mana,revision=mana.revision,actor_id='garran',ability_id='shield_bash',
                  count=2,boosts=(('damage_d4',1),),rune_payment=('Kotwica','Klucz'))
    assert paid.runes.discard==('Kotwica','Klucz')
    assert 'Błysk' in paid.runes.hand('garran')
    with pytest.raises(ValueError):
        pay_mana(mana,revision=mana.revision,actor_id='garran',ability_id='shield_bash',
                 count=2,boosts=(('damage_d4',1),),rune_payment=('Kotwica','Kotwica'))
    assert SharedMana.from_payload(paid.as_payload())==paid


def _rename_first_hand(pool, hero):
    return replace(pool,heroes=(hero,*pool.heroes[1:]),hands=((hero,pool.hands[0][1]),*pool.hands[1:]))


def test_recovery_never_counts_the_newly_paid_copy_of_the_same_symbol():
    state=state_with_hand(('Romb','Romb','Romb','Klucz','Kielich'))
    pool=_rename_first_hand(state.shared_mana.runes,'lorian')
    pool=spend_runes(pool,'lorian',('Romb','Romb'))
    mana=sync_runes(state.shared_mana,pool)
    with pytest.raises(ValueError,match='sprzed zapłaty'):
        pay_mana(mana,revision=mana.revision,actor_id='lorian',ability_id='mana_recovery',count=1,
            boosts=(('recover_more',1),),rune_payment=('Romb',),rune_recovery=('Romb',)*3)
    paid=pay_mana(mana,revision=mana.revision,actor_id='lorian',ability_id='mana_recovery',count=1,
        rune_payment=('Romb',),rune_recovery=('Romb',)*2)
    assert paid.rune_recovery_available==('Romb','Romb')
    assert paid.runes.discard==('Romb','Romb','Romb')
    assert SharedMana.from_payload(paid.as_payload())==paid


def test_first_rage_free_marker_survives_save_and_next_use_requires_its_rune():
    state=state_with_hand()
    pool=_rename_first_hand(state.shared_mana.runes,'brakka')
    mana=sync_runes(state.shared_mana,pool)
    paid=pay_mana(mana,revision=mana.revision,actor_id='brakka',ability_id='rage',count=0)
    assert paid.runes.hand('brakka')==pool.hand('brakka')
    assert ('brakka','rage:free') in paid.runes.used_once
    ready=finish_mana_action(SharedMana.from_payload(paid.as_payload()),revision=paid.revision)
    with pytest.raises(ValueError,match='wybierz runy'):
        pay_mana(ready,revision=ready.revision,actor_id='brakka',ability_id='rage',count=1)
    later=pay_mana(ready,revision=ready.revision,actor_id='brakka',ability_id='rage',count=2,rune_payment=('Klucz','Kielich'))
    assert later.runes.discard==('Klucz','Kielich')


def test_wildcard_choice_undo_led_and_final_commit(tmp_path):
    game,_,_=playable(tmp_path,'garran',('Wieża','Kotwica','Błysk','Kielich','Klucz'))
    game.use_combat_class_feature('defensive_stance')
    pay(game,'boost',boost_id='temp_hp',count=1)
    before=game.combat_state.shared_mana.runes
    pay(game)
    assert game.shared_mana_declaration.stage=='rune_choices'
    assert panel_position(28) not in runes.scan_target(game).positions
    assert panel_position(runes.RUNE_SLOTS['Wieża']) not in runes.scan_target(game).positions
    choose(game,'Klucz')
    assert panel_position(28) in runes.scan_target(game).positions
    assert game.combat_state.shared_mana.runes==before
    pay(game,'rune_choice_back')
    assert panel_position(28) not in runes.scan_target(game).positions
    choose(game,'Kielich')
    old_revision=game.combat_state.shared_mana.revision
    confirm(game)
    after=game.combat_state.shared_mana.runes
    assert Counter(after.discard)==Counter(('Wieża','Kielich'))
    assert 'Klucz' in after.hand('garran')
    with pytest.raises(ValueError,match='Nieaktualny'):
        shared_mana.command(game,dict(command='rune_choice_confirm',revision=old_revision))
    assert game.combat_state.shared_mana.runes==after


def test_two_substitute_runes_preserve_named_booster(tmp_path):
    game,_,_=playable(tmp_path,'garran',('Kotwica','Błysk','Kielich','Klucz','Korona'))
    game.use_combat_class_feature('defensive_stance')
    pay(game,'boost',boost_id='anchor',count=1)
    before=game.combat_state.shared_mana.runes
    pay(game)
    assert runes.view(game)['reserved']==['Kotwica']
    with pytest.raises(ValueError):choose(game,'Kotwica')
    choose(game,'Klucz')
    assert not runes.view(game)['can_confirm']
    choose(game,'Korona')
    assert game.combat_state.shared_mana.runes==before
    confirm(game)
    assert Counter(game.combat_state.shared_mana.runes.discard)==Counter(('Kotwica','Klucz','Korona'))


def test_tuning_selects_exchange_after_cost_and_back_clears_later_choice(tmp_path):
    game,_,_=playable(tmp_path,'lorian',('Kotwica','Błysk','Kielich','Klucz','Korona'))
    game.use_combat_class_feature('mana_tuning')
    before=game.combat_state.shared_mana.runes
    pay(game)
    choose(game,'Kotwica'); choose(game,'Błysk'); confirm(game)
    assert game.shared_mana_declaration.rune_choice_step=='exchange'
    choose(game,'Klucz')
    pay(game,'rune_choice_back')
    pay(game,'rune_choice_back')
    assert game.shared_mana_declaration.rune_choice_step=='payment'
    assert 'exchange' not in game.shared_mana_declaration.rune_choices
    choose(game,'Klucz'); confirm(game)
    assert 'Klucz' not in [c.get('rune') for c in runes.view(game)['choices']]
    choose(game,'Korona')
    assert game.combat_state.shared_mana.runes==before
    confirm(game)
    after=game.combat_state.shared_mana.runes
    assert Counter(after.hand('lorian'))==Counter(('Błysk','Kielich',before.deck[0]))
    assert Counter(after.discard)==Counter(('Kotwica','Klucz','Korona'))


def _add_discard(game, cards):
    state=game.combat_state
    pool=state.shared_mana.runes
    deck=list(pool.deck)
    for rune in cards:deck.remove(rune)
    pool=replace(pool,deck=tuple(deck),discard=(*pool.discard,*cards))
    game.combat_state=replace(state,shared_mana=sync_runes(state.shared_mana,pool))


def test_recovery_selects_duplicates_from_old_discard_and_is_once(tmp_path):
    game,_,_=playable(tmp_path,'lorian',('Romb','Wieża','Kielich','Kotwica','Klucz'))
    _add_discard(game,('Błysk','Błysk','Oko'))
    game.use_combat_class_feature('mana_recovery')
    pay(game,'boost',boost_id='recover_more',count=1)
    before=game.combat_state.shared_mana.runes
    pay(game)
    assert runes.view(game)['maximum']==3
    with pytest.raises(ValueError):choose(game,'Romb')
    choose(game,'Błysk'); choose(game,'Błysk'); choose(game,'Oko')
    assert game.combat_state.shared_mana.runes==before
    confirm(game)
    after=game.combat_state.shared_mana.runes
    assert len(after.hand('lorian'))==7
    assert after.hand('lorian').count('Błysk')==2
    assert after.discard==('Romb',)
    assert ('lorian','mana_recovery') in after.used_once
    from dnd_board_game.combat import ActionUse
    assert game.combat_state.turn_action.action_use==ActionUse.ACTION_USED


def test_recovery_with_empty_old_discard_cannot_pay(tmp_path):
    game,_,_=playable(tmp_path,'lorian',('Romb','Wieża','Kielich','Kotwica','Klucz'))
    before=game.combat_state.shared_mana.runes
    with pytest.raises(ValueError,match='przed zapłatą'):
        game.use_combat_class_feature('mana_recovery')
    assert game.combat_state.shared_mana.runes==before


def test_retired_great_tuning_cannot_bypass_rune_payment(tmp_path):
    game,_,_=playable(tmp_path,'lorian',('Romb','Wieża','Kielich','Kotwica','Klucz'))
    before=game.combat_state.shared_mana.runes
    with pytest.raises(ValueError):
        game.use_combat_class_feature('mana_great_tuning')
    assert game.combat_state.shared_mana.runes==before


def test_partner_selects_own_rune_and_cancel_preserves_both_hands(tmp_path):
    game,ally,_=playable(tmp_path,'garran',('Błysk','Kielich','Wieża','Kotwica','Klucz'))
    state=game.combat_state
    pool=state.shared_mana.runes
    pool=replace(pool,hands=tuple((h,('Błysk','Kielich','Wieża') if h=='garran' else
        ('Kotwica','Klucz') if h==ally else cards) for h,cards in pool.hands))
    game.combat_state=replace(state,shared_mana=sync_runes(state.shared_mana,pool))
    for cancel in (True,False):
        game.use_combat_class_feature('counterattack_command',target_id=ally)
        pay(game,'boost',boost_id='move',count=1)
        pay(game); choose(game,'Kielich'); confirm(game)
        assert game.shared_mana_declaration.rune_choice_step=='partner'
        assert runes.view(game)['actor']==ally
        assert game.combat_state.shared_mana.runes==pool
        choose(game,'Klucz')
        if cancel:
            pay(game,'cancel')
            assert game.combat_state.shared_mana.runes==pool
        else:
            confirm(game)
            after=game.combat_state.shared_mana.runes
            assert after.hand(ally)==('Kotwica',)
            assert after.hand('garran')==('Wieża',)
            assert Counter(after.discard)==Counter(('Błysk','Kielich','Klucz'))


def test_partner_cannot_change_after_rune_selection_even_with_same_rune(tmp_path):
    from dnd_board_game.combat import current_actor, replace_actor
    from dnd_board_game.world import Coordinate
    game,ally,_=playable(tmp_path,'garran',('Błysk','Kielich','Wieża','Klucz','Klucz'))
    state=game.combat_state
    pool=state.shared_mana.runes
    other=next(h for h in pool.heroes if h not in ('garran',ally))
    owner=current_actor(state)
    target=next(a for a in state.actors if str(a.id)==other)
    state=replace_actor(state,replace(target,position=Coordinate(owner.position.col+1,owner.position.row+1)))
    pool=replace(pool,hands=tuple((h,('Błysk','Kielich','Wieża') if h=='garran' else ('Klucz',)) for h,_ in pool.hands))
    game.combat_state=replace(state,shared_mana=sync_runes(state.shared_mana,pool))
    game.use_combat_class_feature('counterattack_command',target_id=ally)
    pay(game)
    choose(game,'Klucz')
    before=game.combat_state
    declaration=asdict(game.shared_mana_declaration)
    for command, arguments in (
        ('target',dict(target_id=other)),
        ('clear_targets',{}),
        ('parameters',dict(target_id=other,natural_roll=20)),
        ('mode',dict(mode='dash')),
        ('boost',dict(boost_id='move',count=1)),
        ('pay',{}),
    ):
        with pytest.raises(ValueError,match='W trakcie wyboru run'):
            pay(game,command,**arguments)
        assert game.combat_state==before
        assert asdict(game.shared_mana_declaration)==declaration
    confirm(game)
    paid=game.combat_state.shared_mana.runes
    assert paid.hand(ally)==()
    assert paid.hand(other)==('Klucz',)
    assert paid.hand('garran')==('Kielich','Wieża')


def test_upkeep_choice_survives_snapshot_and_never_auto_pays():
    state=state_with_hand()
    state=replace(state,shared_mana=replace(state.shared_mana,rune_upkeep_actor='garran'))
    game=SimpleNamespace(combat_state=state,shared_mana_declaration=None,active_combat_effects=(),board_panel_context=None,
        _record=lambda *a:None,_sync_board_leds=lambda:None,state_payload=lambda:{})
    before=state.shared_mana.runes
    with pytest.raises(ValueError,match='wybierz runę'):
        runes.command(game,dict(command='rune_upkeep_pay',revision=state.shared_mana.revision))
    runes.command(game,dict(command='rune_upkeep_take',rune='Klucz',revision=game.combat_state.shared_mana.revision))
    assert game.combat_state.shared_mana.runes==before
    restored=SharedMana.from_payload(game.combat_state.shared_mana.as_payload())
    assert restored.rune_upkeep_selected=='Klucz'
    game.combat_state=replace(game.combat_state,shared_mana=restored)
    runes.command(game,dict(command='rune_upkeep_pay',revision=restored.revision))
    assert game.combat_state.shared_mana.runes.discard==('Klucz',)
    assert 'Kotwica' in game.combat_state.shared_mana.runes.hand('garran')
