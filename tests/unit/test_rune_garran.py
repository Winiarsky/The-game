"""Canonical Garran card variants execute with their physical dice and costs."""
from dataclasses import replace
from types import SimpleNamespace

import pytest

from dnd_board_game.combat import current_actor, replace_actor, ActionUse
from dnd_board_game.combat.damage import apply_damage_result, resolve_damage, DamageComponentInput
from dnd_board_game.combat.targets import combat_effect_armor_class_bonus
from dnd_board_game.combat.shared_mana_features import resolve_simple_action, synchronize_bastion
from dnd_board_game.combat.runes import commit_budget
from dnd_board_game.combat.rune_dice import shield_bash_dice, second_wind_dice
from dnd_board_game.combat.session import finish_turn
from dnd_board_game.application.combat_turn_finalization import CombatTurnFinalizationService
from dnd_board_game.rules import ActiveEffect, EffectDuration
from dnd_board_game.core.damage_types import DamageType
from dnd_board_game.rules.shared_mana import pay_mana, finish_mana_action
from dnd_board_game.scenarios.rune_catalog import rune_card
from dnd_board_game.ui import shared_mana, runes
from dnd_board_game.ui.shield_bash import submit_shield_bash, confirm_shield_bash, shield_bash_payload
from dnd_board_game.world import Coordinate
from tests.unit.test_rune_combat_actions import playable, pay
from tests.unit.test_rune_resources import state_with_hand


def test_shield_bash_wildcard_is_physical_d6_plus_d4(tmp_path):
    game,_,enemy_id=playable(tmp_path,'garran',('Kotwica','Błysk','Kielich','Klucz','Wieża'))
    enemy=next(a for a in game.combat_state.actors if str(a.id)==enemy_id)
    game.start_combat_class_feature_targeting('shield_bash')
    game.select_board_position(enemy.position)
    game.confirm_combat_class_feature_targeting()
    pay(game,'boost',boost_id='damage_d4',count=1)
    pay(game)
    pay(game,'rune_choice_take',rune='Błysk')
    pay(game,'rune_choice_confirm')
    assert shield_bash_dice(game.combat_state)==(6,4)
    assert shield_bash_payload(game)['damage_die_sides']==[6,4]
    submit_shield_bash(game,{'attacker_roll':20})
    assert game.shield_bash_flow.stage=='damage'
    submit_shield_bash(game,{'damage_roll':10})
    before=game.combat_state.shared_mana.runes
    confirm_shield_bash(game)
    assert game.combat_state.shared_mana.runes==before
    assert next(a for a in game.combat_state.actors if str(a.id)==enemy_id).hp < enemy.hp
    assert game.combat_state.turn_action.action_use==ActionUse.ACTION_AVAILABLE


def test_second_wind_boost_adds_d4_and_constitution_once(tmp_path):
    game,_,_=playable(tmp_path,'garran',('Kielich','Błysk','Kotwica','Klucz','Wieża'))
    actor=current_actor(game.combat_state)
    game.combat_state=replace_actor(game.combat_state,replace(actor,hp=1))
    game.use_combat_class_feature('second_wind',natural_roll=14)
    pay(game,'boost',boost_id='heal_d4',count=1)
    pay(game)
    pay(game,'rune_choice_take',rune='Błysk')
    pay(game,'rune_choice_confirm')
    assert current_actor(game.combat_state).hp==min(actor.max_hp,1+14+(actor.ability_scores.constitution-10)//2)
    assert len(game.combat_state.shared_mana.runes.discard)==2
    assert ('garran','second_wind') in game.combat_state.shared_mana.runes.used_once


def test_stance_temp_hp_and_nonstacking_aura(tmp_path):
    game,_,_=playable(tmp_path,'garran',('Wieża','Błysk','Kotwica','Klucz','Kielich'))
    game.use_combat_class_feature('defensive_stance')
    pay(game,'boost',boost_id='temp_hp',count=1)
    pay(game)
    pay(game,'rune_choice_take',rune='Błysk')
    pay(game,'rune_choice_confirm')
    actor=current_actor(game.combat_state)
    assert actor.temp_hp==5
    bastion=ActiveEffect(id='bastion',actor_id='garran',kind='iron_bastion_member',label='Bastion',object_id='test',value=1)
    assert combat_effect_armor_class_bonus(actor,(*game.active_combat_effects,bastion))==2


@pytest.mark.parametrize('boost', ['', 'armor', 'radius'])
def test_bastion_upkeep_after_round_keeps_hand_without_new_draw(boost):
    state=state_with_hand(('Kotwica','Błysk','Brama','Wieża','Klucz'))
    outer=next(actor for actor in state.actors if actor.id=='nimra')
    state=replace_actor(state,replace(outer,position=Coordinate(3,2)))
    card=rune_card('garran','iron_bastion')
    state=commit_budget(state,current_actor(state),card)
    mana=pay_mana(state.shared_mana,revision=state.shared_mana.revision,actor_id='garran',ability_id='iron_bastion',
                  count=2 if boost else 1,boosts=((boost,1),) if boost else ())
    state,effects=resolve_simple_action(replace(state,shared_mana=mana),(),'iron_bastion')
    effects=synchronize_bastion(state.actors,effects)
    source=next(e for e in effects if e.kind=='iron_bastion')
    assert source.value==(2 if boost=='armor' else 1)
    assert source.radius_feet==(15 if boost=='radius' else 10)
    assert source.duration==EffectDuration.UNTIL_ENCOUNTER_END
    assert any(e.kind=='iron_bastion_member' and e.actor_id=='nimra' for e in effects)==(boost=='radius')
    state=replace(state,shared_mana=finish_mana_action(state.shared_mana,revision=state.shared_mana.revision))
    before=state.shared_mana.runes
    service=CombatTurnFinalizationService()
    for _ in range(4):
        result=service.finish_active_turn(state=state,active_effects=effects)
        state,effects=result.state,result.active_effects
    assert not state.shared_mana.rune_upkeep_actor
    assert state.shared_mana.runes==before
    for _ in range(4):
        result=service.finish_active_turn(state=state,active_effects=effects)
        state,effects=result.state,result.active_effects
    assert state.shared_mana.rune_upkeep_actor=='garran'
    assert state.shared_mana.runes==before
    session=SimpleNamespace(combat_state=state,active_combat_effects=effects,board_panel_context=None,shared_mana_declaration=None,
        _record=lambda *a:None,_sync_board_leds=lambda:None,state_payload=lambda:{})
    upkeep=runes.view(session)
    assert upkeep['upkeep_rune']==''
    assert not any(c['command']=='rune_upkeep_pay' for c in upkeep['choices'])
    runes.command(session,dict(command='rune_upkeep_take',rune='Kotwica',revision=session.combat_state.shared_mana.revision))
    assert session.combat_state.shared_mana.runes==before
    upkeep=runes.view(session)
    assert upkeep['upkeep_rune']=='Kotwica'
    assert 'Kotwica' in upkeep['instruction'] and '+1 KP' in upkeep['instruction'] and '2 pól' in upkeep['instruction']
    assert 'Kotwica' in next(c['label'] for c in upkeep['choices'] if c['command']=='rune_upkeep_pay')
    runes.command(session,dict(command='rune_upkeep_pay',revision=session.combat_state.shared_mana.revision))
    assert len(session.combat_state.shared_mana.runes.hand('garran'))==len(before.hand('garran'))-1
    assert not session.combat_state.shared_mana.rune_upkeep_actor
    assert not session.combat_state.turn_action.rune_special_used
    assert session.combat_state.shared_mana.runes.discard[-1]=='Kotwica'
    assert session.combat_state.shared_mana.runes.deck==before.deck
    renewed=next(e for e in session.active_combat_effects if e.kind=='iron_bastion')
    assert renewed.value==1 and renewed.radius_feet==10
    assert not any(e.kind=='iron_bastion_member' and e.actor_id=='nimra' for e in session.active_combat_effects)
    session.combat_state=state
    runes.command(session,dict(command='rune_upkeep_end',revision=state.shared_mana.revision))
    assert not any(e.kind.startswith('iron_bastion') for e in session.active_combat_effects)
    assert session.combat_state.shared_mana.runes==before


def test_counterattack_quote_explains_the_companions_own_rune_selection():
    state=state_with_hand()
    pool=state.shared_mana.runes
    hands=tuple((hero, cards[:-1] if hero=='garran' else ('Klucz',) if hero=='mira' else cards)
                for hero,cards in pool.hands)
    state=replace(state,shared_mana=replace(state.shared_mana,runes=replace(pool,hands=hands)))
    session=SimpleNamespace(combat_state=state)
    declaration=shared_mana.ManaDeclaration('counterattack_command','garran','',resume_arguments={'target_id':'mira'})
    before=state.shared_mana.runes
    quote=shared_mana._quote(session,declaration)
    assert quote.cards==('Błysk',)
    assert any('mira' in note and 'wybierze własną runę' in note and 'reakcję' in note for note in quote.reminders)
    assert session.combat_state.shared_mana.runes==before


def test_guard_reduction_is_applied_to_total_damage():
    state=state_with_hand()
    actor=current_actor(state)
    reduction=ActiveEffect(id='guard',actor_id='garran',kind='rune_guard_reduction',label='Osłona',object_id='test',value=6)
    applied=apply_damage_result(actor,resolve_damage((DamageComponentInput(4,DamageType.SLASHING),DamageComponentInput(4,DamageType.FIRE))),active_effects=(reduction,))
    assert applied.damage.total_applied==2
    assert sum(c.amount_applied for c in applied.damage.resolved_components)==2


def test_halt_boost_targets_two_enemies_and_pays_once(tmp_path):
    game,_,enemy_id=playable(tmp_path,'garran',('Klepsydra','Korona','Kotwica','Klucz','Kielich'))
    first=next(a for a in game.combat_state.actors if str(a.id)==enemy_id)
    second=next(a for a in game.combat_state.actors if a.faction==first.faction and a.id!=first.id)
    second=replace(second,position=Coordinate(first.position.col,first.position.row+1))
    game.combat_state=replace_actor(game.combat_state,second)
    game.start_combat_class_feature_targeting('garran_command_halt')
    game.select_board_position(first.position)
    game.confirm_combat_class_feature_targeting()
    pay(game,'boost',boost_id='target',count=1)
    pay(game,'target',target_id=str(second.id))
    pay(game)
    assert len(game.combat_state.shared_mana.runes.discard)==2
    assert first.name in game.board_message and second.name in game.board_message
    assert game.combat_state.turn_action.action_use==ActionUse.ACTION_AVAILABLE


def test_rally_one_target_or_two_selected_with_one_wildcard(tmp_path):
    game,ally,_=playable(tmp_path,'garran',('Korona','Wieża','Kotwica','Klucz','Kielich'))
    game.use_combat_class_feature('garran_rally')
    pay(game,'boost',boost_id='second',count=1)
    pay(game,'target',target_id='garran')
    pay(game,'target',target_id=ally)
    pay(game)
    pay(game,'rune_choice_take',rune='Wieża')
    pay(game,'rune_choice_confirm')
    targets={e.actor_id for e in game.active_combat_effects if e.kind=='garran_rally_advantage'}
    assert targets=={'garran',ally}
    assert len(game.combat_state.shared_mana.runes.discard)==2
