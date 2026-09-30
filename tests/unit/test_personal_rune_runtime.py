"""Real session tests for token ownership, board input and atomic support."""
from collections import Counter
from dataclasses import replace
from pathlib import Path

import pytest
from dnd_board_game.rules.rune_baskets import (CATEGORIES, SYMBOLS, RuneBaskets, new_baskets,
    declare_token, confirm_category, spend_tokens)
from dnd_board_game.rules.shared_mana import SharedMana, sync_runes
from dnd_board_game.scenarios.rune_basket_catalog import load_rune_basket_catalog
from dnd_board_game.scenarios.rune_catalog import rune_card
from dnd_board_game.combat import current_actor, replace_actor
from dnd_board_game.combat.rune_baskets import quote, commit, helpers
from dnd_board_game.hardware.board_panel import panel_position
from dnd_board_game.ui.board_panel_symbols import rune_slot
from dnd_board_game.ui.shared_mana import command
from dnd_board_game.ui import rune_baskets as ui
from dnd_board_game.world import Coordinate
from tests.unit.test_mission_zero import session, start_battle


def game(tmp_path: Path):
    s=session(tmp_path,3);s.encounter_rng.seed(0);start_battle(s)
    s.configured_board_backend='none'
    return s


def filled(s):
    pool=s.combat_state.shared_mana.runes
    hands=tuple((h,tuple(r for c,n in zip(CATEGORIES,limits) for r in [SYMBOLS[CATEGORIES.index(c)][0]]*n)) for h,limits in pool.capacities)
    s.combat_state=replace(s.combat_state,shared_mana=sync_runes(s.combat_state.shared_mana,replace(pool,hands=hands,phase='ready')))


def press(s,slot):
    assert panel_position(slot) in s._current_board_scan_target().positions
    return s._handle_board_position(panel_position(slot))


def test_category_capacity_repeats_and_save_round_trip(tmp_path):
    s=game(tmp_path)
    pool=s.combat_state.shared_mana.runes
    assert isinstance(pool,RuneBaskets)
    assert pool.capacity('brakka','mobility')==3
    press(s,rune_slot('Grot'));press(s,rune_slot('Grot'))
    assert panel_position(rune_slot('Grot')) not in s._current_board_scan_target().positions
    with pytest.raises(ValueError):
        ui.command(s,dict(command='basket_take',rune='Grot',revision=s.combat_state.shared_mana.revision))
    press(s,29);press(s,rune_slot('Hak'));press(s,28)
    assert s.combat_state.shared_mana.runes.category=='defense'
    press(s,rune_slot('Wieża'))
    before=s.combat_state.shared_mana.runes
    s.save_snapshot();s.load_snapshot()
    assert s.combat_state.shared_mana.runes==before
    while s.combat_state.shared_mana.runes.phase=='allocation':
        pool=s.combat_state.shared_mana.runes
        if pool.missing(pool.actor,pool.category):press(s,rune_slot(SYMBOLS[pool.category_index][0]))
        else:press(s,28)
    assert s.combat_state.shared_mana.runes.phase=='ready'
    assert Counter(s.combat_state.shared_mana.runes.hand('garran'))['Wieża']==4


def test_every_power_uses_button_category_and_real_cross_category_resonance():
    data=load_rune_basket_catalog();pool=new_baskets({h:v['capacities'] for h,v in data['heroes'].items()})
    from dnd_board_game.rules.rune_baskets import category_of
    for h,hero in data['heroes'].items():
        for row in hero['cards']:
            card=rune_card(h,row['id'],pool=pool)
            assert card.category==category_of(card.rune)
            assert card.boosts
            assert all(category_of(b.color)!=card.category for b in card.boosts)


def test_support_validates_distance_reaction_and_commits_together(tmp_path):
    s=game(tmp_path);filled(s)
    state=s.combat_state;owner=current_actor(state);assert owner.id=='garran'
    helper=next(a for a in state.actors if a.id=='brakka')
    state=replace_actor(state,replace(helper,position=Coordinate(owner.position.col+3,owner.position.row+3)))
    # Garran has no Eye; Brakka starts with Eye in Mobility.
    pool=state.shared_mana.runes
    cards=list(pool.hand('garran'));cards.remove('Oko');cards.append('Schody')
    pool=replace(pool,hands=tuple((h,tuple(cards) if h=='garran' else hand) for h,hand in pool.hands))
    state=replace(state,shared_mana=sync_runes(state.shared_mana,pool))
    assert 'brakka' in {str(a.id) for a in helpers(state,owner,'Oko')}
    updated=commit(state,owner,'shield_bash',{'push':1},('Wieża',),helper_id='brakka')
    assert len(updated.shared_mana.runes.hand('garran'))==len(pool.hand('garran'))-1
    assert len(updated.shared_mana.runes.hand('brakka'))==len(pool.hand('brakka'))-1
    assert helper.id in updated.spent_reaction_actor_ids
    assert state.shared_mana.runes==pool
    with pytest.raises(ValueError):commit(updated,owner,'shield_bash',{'push':1},('Wieża',),helper_id='brakka')
    far=replace_actor(state,replace(helper,position=Coordinate(owner.position.col+4,owner.position.row)))
    with pytest.raises(ValueError):commit(far,owner,'shield_bash',{'push':1},('Wieża',),helper_id='brakka')
    used=replace(state,spent_reaction_actor_ids=frozenset((helper.id,)))
    with pytest.raises(ValueError):commit(used,owner,'shield_bash',{'push':1},('Wieża',),helper_id='brakka')
    with pytest.raises(ValueError):commit(state,owner,'shield_bash',{},('Grot',))


def test_board_payment_cancel_then_resolve_and_recharge(tmp_path):
    s=game(tmp_path);filled(s)
    initial=s.combat_state.shared_mana.runes
    s.use_combat_class_feature('defensive_stance')
    press(s,28);press(s,rune_slot('Wieża'))
    assert ui.view(s)['phase']=='basket'
    assert s.combat_state.shared_mana.runes==initial
    press(s,29);press(s,29) # Base selection then original preview.
    command(s,dict(command='cancel',revision=s.combat_state.shared_mana.revision))
    assert s.combat_state.shared_mana.runes==initial
    s.use_combat_class_feature('defensive_stance')
    press(s,28);press(s,rune_slot('Wieża'));press(s,28);press(s,28)
    assert s.shared_mana_declaration.basket_step=='review'
    assert s.combat_state.shared_mana.runes==initial
    press(s,28)
    assert len(s.combat_state.shared_mana.runes.hand('garran'))==len(initial.hand('garran'))-1
    assert s.combat_state.turn_action.rune_special_used
    assert any(e.kind=='garran_defensive_stance_ac' for e in s.active_combat_effects)
    # Once-per-round regeneration is explicitly reported after the event.
    press(s,21);press(s,5)
    assert s.combat_state.shared_mana.runes.recharge_roll==2
    assert panel_position(29) not in s._current_board_scan_target().positions
    with pytest.raises(ValueError):
        ui.command(s,dict(command='basket_back',revision=s.combat_state.shared_mana.revision))
    press(s,26);press(s,28)
    assert s.combat_state.shared_mana.runes.phase=='recharge_review'
    press(s,28)
    assert 'Brama' in s.combat_state.shared_mana.runes.hand('garran')
    press(s,21)
    assert panel_position(5) not in s._current_board_scan_target().positions
    press(s,29)


def personal_game(tmp_path,hero):
    from tests.unit.test_rune_combat_actions import playable
    s,ally,enemy=playable(tmp_path,hero,('Wieża','Oko','Błysk','Kielich','Klucz'))
    catalog=load_rune_basket_catalog()['heroes']
    heroes=s.combat_state.shared_mana.runes.heroes
    pool=new_baskets({h:catalog[h]['capacities'] for h in heroes})
    s.combat_state=replace(s.combat_state,shared_mana=sync_runes(s.combat_state.shared_mana,pool))
    filled(s)
    return s,ally,enemy


def confirm_base(s):
    press(s,28)
    press(s,next(c['slot'] for c in ui.view(s)['choices'] if c['command']=='basket_take'))
    press(s,28);press(s,28);press(s,28)


@pytest.mark.parametrize('hero,ability,target,effect',[
    ('brakka','rage','', 'rage'),('mira','feint','enemy','feint'),
    ('dagna','caring_gesture','ally','temporary_hit_points'),
    ('lorian','mana_inspiration','ally','bardic_inspiration'),('erynd','aim','','erynd_aim_advantage'),
])
def test_hero_power_spends_one_category_token_and_keeps_attack(tmp_path,hero,ability,target,effect):
    from dnd_board_game.combat import ActionUse
    s,ally,enemy=personal_game(tmp_path,hero)
    before=s.combat_state.shared_mana.runes
    s.use_combat_class_feature(ability,target_id=ally if target=='ally' else enemy if target=='enemy' else '',natural_roll=3 if hero=='dagna' else None)
    confirm_base(s)
    assert len(s.combat_state.shared_mana.runes.hand(hero))==len(before.hand(hero))-1
    assert s.combat_state.turn_action.action_use==ActionUse.ACTION_AVAILABLE
    assert any(e.kind==effect for e in s.active_combat_effects)


def test_nimra_spell_and_echo_surcharge_use_own_tokens(tmp_path):
    from dnd_board_game.combat import ActionUse
    s,ally,enemy=personal_game(tmp_path,'nimra')
    s.combat_state=replace(s.combat_state,turn_action=replace(s.combat_state.turn_action,action_use=ActionUse.ACTION_USED))
    target=next(a for a in s.combat_state.actors if str(a.id)==enemy)
    s.select_combat_attack_source('nimra_frost_pulse');s.select_player_attack_target_at_position(target.position);s.confirm_player_attack_target()
    confirm_base(s)
    if s.pending_player_attack and s.pending_player_attack.stage=='damage_roll':s.submit_player_damage_roll(damage=4)
    assert s.combat_state.turn_action.rune_special_used
    assert len(s.combat_state.shared_mana.runes.charged('nimra','mobility'))==1
    assert s.combat_state.shared_mana.echo_spell=='nimra_frost_pulse'


def test_shield_bash_helper_board_flow_and_automatic_enemy_die(tmp_path):
    from dnd_board_game.ui.shield_bash import submit_shield_bash,confirm_shield_bash
    from dnd_board_game.combat import ActionUse
    s,ally,enemy=personal_game(tmp_path,'garran')
    pool=s.combat_state.shared_mana.runes
    hand=list(pool.hand('garran'));hand.remove('Oko');hand.append('Schody')
    pool=replace(pool,hands=tuple((h,tuple(hand) if h=='garran' else cards) for h,cards in pool.hands))
    s.combat_state=replace(s.combat_state,shared_mana=sync_runes(s.combat_state.shared_mana,pool))
    target=next(a for a in s.combat_state.actors if str(a.id)==enemy)
    helper=next(a for a in s.combat_state.actors if str(a.id)==ally)
    s.start_combat_class_feature_targeting('shield_bash');s.select_board_position(target.position);s.confirm_combat_class_feature_targeting()
    press(s,28);press(s,rune_slot('Wieża'));press(s,rune_slot('Oko'))
    assert s.shared_mana_declaration.basket_step=='helper'
    assert helper.position in s._current_board_scan_target().positions
    s._handle_board_position(helper.position)
    assert s.shared_mana_declaration.basket_step=='helper_confirm'
    press(s,28);press(s,28)
    assert s.combat_state.shared_mana.runes==pool
    assert helper.id not in s.combat_state.spent_reaction_actor_ids
    press(s,28)
    assert helper.id in s.combat_state.spent_reaction_actor_ids
    assert len(s.combat_state.shared_mana.runes.hand(ally))==len(pool.hand(ally))-1
    assert s.shield_bash_flow.stage=='contest'
    submit_shield_bash(s,{'attacker_roll':20})
    assert s.shield_bash_flow.defender_roll in range(1,21)
    if s.shield_bash_flow.stage=='damage':submit_shield_bash(s,{'damage_roll':6})
    confirm_shield_bash(s)
    assert s.combat_state.turn_action.action_use==ActionUse.ACTION_AVAILABLE


def test_focus_recharges_two_slots_and_preserves_declared_category(tmp_path):
    s=game(tmp_path);filled(s)
    pool=spend_tokens(s.combat_state.shared_mana.runes,{'garran':('Wieża','Wieża')})
    s.combat_state=replace(s.combat_state,shared_mana=sync_runes(s.combat_state.shared_mana,pool))
    press(s,19);press(s,28)
    for expected in (1,0):
        press(s,rune_slot('Wieża'));press(s,28);press(s,28)
        assert s.combat_state.shared_mana.runes.recharge_remaining==expected
    assert s.combat_state.shared_mana.runes.charged('garran','defense').count('Kotwica')==2
    assert s.combat_state.turn_action.rune_special_used


def test_erynd_late_surcharge_does_not_pay_base_or_action_twice(tmp_path):
    from dnd_board_game.ui.shared_mana import ManaDeclaration
    s,ally,enemy=personal_game(tmp_path,'erynd')
    actor=current_actor(s.combat_state)
    s.combat_state=commit(s.combat_state,actor,'double_shot',{},('Grot',))
    target=next(a for a in s.combat_state.actors if str(a.id)==enemy)
    friend=next(a for a in s.combat_state.actors if str(a.id)==ally)
    s.combat_state=replace_actor(s.combat_state,replace(friend,position=Coordinate(target.position.col,target.position.row+1)))
    before=s.combat_state.shared_mana.runes
    turn=s.combat_state.turn_action
    s.combat_targeting_attack_source_id='double_shot'
    s.shared_mana_declaration=ManaDeclaration('double_shot','erynd','state_payload',selected_target_ids=(enemy,),rune_flaw_only=True)
    press(s,28);press(s,rune_slot('Grot'))
    assert s.shared_mana_declaration.basket_step=='review'
    press(s,29)
    assert s.shared_mana_declaration.basket_step=='surcharge'
    press(s,rune_slot('Grot'));press(s,28)
    assert len(s.combat_state.shared_mana.runes.hand('erynd'))==len(before.hand('erynd'))-1
    assert s.combat_state.shared_mana.rune_flaw_paid
    assert s.combat_state.turn_action.action_use==turn.action_use
    assert s.combat_state.turn_action.shared_bonus_actions_used==turn.shared_bonus_actions_used
    assert s.combat_state.turn_action.rune_special_used==turn.rune_special_used


def test_support_reaction_stays_spent_through_own_turn_until_new_round(tmp_path):
    from dnd_board_game.combat.session import finish_turn, use_actor_reaction, reaction_available_for
    s=game(tmp_path);filled(s)
    state=s.combat_state
    helper=next(a for a in state.actors if a.id=='brakka')
    order=state.initiative_order
    entry=next(e for e in order.entries if e.actor.id==helper.id)
    state=replace(state,initiative_order=replace(order,entries=(order.entries[0],entry,*(e for e in order.entries[1:] if e!=entry))))
    state=use_actor_reaction(state,helper).state
    started=state.round_number
    state=finish_turn(state)
    assert current_actor(state).id==helper.id
    assert not reaction_available_for(state,helper)
    while state.round_number==started:state=finish_turn(state)
    assert reaction_available_for(state,helper)


@pytest.mark.parametrize('initial_hp,expected_hp',[(0,3),(8,8)])
def test_concrete_guard_resonance_spends_second_token_without_stacking_temp_hp(tmp_path,initial_hp,expected_hp):
    s,_,_=personal_game(tmp_path,'brakka')
    actor=current_actor(s.combat_state)
    s.combat_state=replace_actor(s.combat_state,replace(actor,temp_hp=initial_hp))
    pool=s.combat_state.shared_mana.runes
    s.use_combat_class_feature('rage')
    press(s,28);press(s,rune_slot('Oko'));press(s,rune_slot('Wieża'));press(s,28)
    assert s.combat_state.shared_mana.runes==pool
    assert current_actor(s.combat_state).temp_hp==initial_hp
    press(s,28)
    assert len(s.combat_state.shared_mana.runes.hand('brakka'))==len(pool.hand('brakka'))-2
    assert current_actor(s.combat_state).temp_hp==expected_hp
