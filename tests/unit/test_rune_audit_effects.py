"""Distinct rune roles retain the real attack, area, movement and payment flows."""
from dataclasses import replace
from types import SimpleNamespace

import pytest

from dnd_board_game.combat import ActionUse, AttackKind, AttackSource, AttackSourceType, current_actor, replace_actor
from dnd_board_game.combat.attack_positioning import evaluate_attack_positioning
from dnd_board_game.combat.opportunity import opportunity_attackers_for_movement
from dnd_board_game.combat.lorian_features import is_lorian_hand_crossbow_source, validate_lorian_optical_target, lorian_attack_sources, consume_rune_optical_preparation
from dnd_board_game.combat.scene_interactions import consume_next_attack_effects
from dnd_board_game.combat.runes import quote_runes, commit_budget
from dnd_board_game.combat.shared_mana import synchronize_shared_effects
from dnd_board_game.combat.shared_mana_features import resolve_simple_action, synchronize_bastion, state_blocks_forced_movement
from dnd_board_game.rules import D20RollRequest, EffectEvent, EffectEventType, expire_active_effects
from dnd_board_game.rules.runes import spend_runes
from dnd_board_game.rules.shared_mana import pay_mana, sync_runes
from dnd_board_game.scenarios.rune_catalog import rune_card
from dnd_board_game.ui import shared_mana
from dnd_board_game.ui.aura_preview import aura_feedback
from dnd_board_game.world import BoardState, Coordinate
from tests.unit.test_rune_combat_actions import playable, pay
from tests.unit.test_rune_resources import state_with_hand


def test_bastion_membership_and_forced_movement_remain_at_cast_tile():
    state=state_with_hand()
    origin=current_actor(state).position
    state=commit_budget(state,current_actor(state),rune_card('garran','iron_bastion'))
    paid=pay_mana(state.shared_mana,revision=state.shared_mana.revision,actor_id='garran',ability_id='iron_bastion',count=1)
    state,effects=resolve_simple_action(replace(state,shared_mana=paid),(),'iron_bastion')
    state=replace_actor(state,replace(current_actor(state),position=Coordinate(10,10)))
    state,effects=synchronize_shared_effects(state,effects)
    source=next(e for e in effects if e.kind=='iron_bastion')
    assert source.anchor_position==origin
    assert 'garran' not in {e.actor_id for e in effects if e.kind=='iron_bastion_member'}
    ally=next(a for a in state.actors if str(a.id)=='mira')
    assert state_blocks_forced_movement(state,ally)
    assert not state_blocks_forced_movement(state,current_actor(state))
    session=SimpleNamespace(combat_state=state,active_combat_effects=effects,
        _active_encounter=lambda: SimpleNamespace(board=BoardState(),combat_actions_by_actor={}))
    feedback=aura_feedback(session,'iron_bastion','garran',active_only=True)
    area={p for frame in feedback.frames if frame.role.value=='area_effect' for p in frame.positions}
    assert origin in area and Coordinate(10,9) not in area


def test_feint_protects_miras_allies_from_only_the_selected_enemy_until_her_next_turn(tmp_path):
    game,ally_id,enemy_id=playable(tmp_path,'mira',(rune_card('mira','feint').rune,'Wieża','Kotwica','Błysk','Klucz'))
    ally=next(a for a in game.combat_state.actors if str(a.id)==ally_id)
    enemy=next(a for a in game.combat_state.actors if str(a.id)==enemy_id)
    source=AttackSource('Miecz',AttackSourceType.WEAPON,5,D20RollRequest(),id='sword',attack_kind=AttackKind.MELEE)
    attacks={enemy.id:source}
    destination=Coordinate(ally.position.col+2,ally.position.row)
    assert opportunity_attackers_for_movement(game.combat_state,ally,ally.position,destination,attacks)
    game.use_combat_class_feature('feint',target_id=enemy_id)
    pay(game)
    assert not opportunity_attackers_for_movement(game.combat_state,ally,ally.position,destination,attacks,game.active_combat_effects)
    expired=expire_active_effects(game.active_combat_effects,EffectEvent(EffectEventType.TURN_START,actor_id='mira')).active_effects
    assert opportunity_attackers_for_movement(game.combat_state,ally,ally.position,destination,attacks,expired)


def test_sacred_flame_area_preview_excludes_allies(tmp_path):
    card=rune_card('dagna','sacred_flame')
    game,ally_id,enemy_id=playable(tmp_path,'dagna',(card.rune,'Wieża','Kotwica','Błysk','Klucz'))
    enemy=next(a for a in game.combat_state.actors if str(a.id)==enemy_id)
    ally=next(a for a in game.combat_state.actors if str(a.id)==ally_id)
    ally=replace(ally,position=Coordinate(enemy.position.col-1,enemy.position.row))
    game.combat_state=replace_actor(game.combat_state,ally)
    game.select_combat_attack_source('sacred_flame')
    game.select_player_area_spell_at_position(enemy.position)
    assert ally.position in game.pending_area_spell.area_positions
    assert enemy_id in game.pending_area_spell.target_ids
    assert ally_id not in game.pending_area_spell.target_ids
    assert 'dagna' not in game.pending_area_spell.target_ids


def test_optical_scope_prepares_ordinary_attack_without_firing_or_spending_a(tmp_path):
    game,_,enemy_id=playable(tmp_path,'lorian',('Błysk','Brama','Kotwica','Kielich','Klucz'))
    actor=current_actor(game.combat_state)
    ordinary=next(s for s in game._attack_sources_for_actor(actor) if is_lorian_hand_crossbow_source(s))
    game.use_combat_class_feature('optical_scope')
    assert game.shared_mana_declaration.ability_id=='optical_scope'
    pay(game)
    assert game.pending_player_attack is None and game.combat_targeting_attack_source_id is None
    assert game.combat_state.turn_action.movement_action_used
    assert game.combat_state.turn_action.rune_special_used
    assert game.combat_state.turn_action.action_use==ActionUse.ACTION_AVAILABLE
    prepared=next(s for s in game._attack_sources_for_actor(actor) if s.id==ordinary.id)
    assert sum(m.value for m in prepared.attack_roll_request.modifiers)==sum(m.value for m in ordinary.attack_roll_request.modifiers)+2
    other=replace(ordinary,id='mocking_shot')
    assert lorian_attack_sources(actor,(other,),game.active_combat_effects)[0].attack_roll_request==other.attack_roll_request
    retained=consume_next_attack_effects(game.active_combat_effects,str(actor.id))
    retained=consume_rune_optical_preparation(retained,str(actor.id),other)
    assert any(e.kind=='rune_optical_prepared' for e in retained)
    assert not any(e.kind=='rune_optical_prepared' for e in expire_active_effects(retained,
        EffectEvent(EffectEventType.TURN_END,actor_id=str(actor.id))).active_effects)
    enemy=next(a for a in game.combat_state.actors if str(a.id)==enemy_id)
    cover_actor=next(a for a in game.combat_state.actors if a.id!=actor.id and a.faction==actor.faction)
    positioned=(replace(actor,position=Coordinate(0,0)),replace(enemy,position=Coordinate(4,0)),
                replace(cover_actor,position=Coordinate(2,0)))
    cover_board=BoardState()
    assert evaluate_attack_positioning(cover_board,positioned[0],positioned[1],ordinary,positioned).cover_bonus>0
    assert evaluate_attack_positioning(cover_board,positioned[0],positioned[1],prepared,positioned).cover_bonus==0
    cover_board.add_wall(Coordinate(1,0),Coordinate(2,0))
    assert evaluate_attack_positioning(cover_board,positioned[0],positioned[1],prepared,positioned).total_cover
    game.select_combat_attack_source(ordinary.id)
    game.select_player_attack_target_at_position(enemy.position)
    game.confirm_player_attack_target()
    game.submit_player_attack_roll(natural_roll=1,natural_roll_2=1)
    assert game.combat_state.turn_action.action_use==ActionUse.ACTION_USED
    assert len(game.combat_state.shared_mana.runes.discard)==1
    assert not any(e.kind=='rune_optical_prepared' for e in game.active_combat_effects)


def test_optical_scope_second_shot_requires_a_and_locks_same_target(tmp_path):
    game,_,enemy_id=playable(tmp_path,'lorian',('Błysk','Brama','Kotwica','Kielich','Klucz'))
    before=game.combat_state
    exhausted=replace(before,turn_action=replace(before.turn_action,action_use=ActionUse.ACTION_USED))
    with pytest.raises(ValueError,match='ataku'):
        quote_runes(exhausted,current_actor(exhausted),'optical_scope',{'shot':1})
    game.use_combat_class_feature('optical_scope')
    pay(game,'boost',boost_id='shot',count=1)
    pay(game)
    assert game.combat_state.turn_action.action_use==ActionUse.ACTION_USED
    enemy=next(a for a in game.combat_state.actors if str(a.id)==enemy_id)
    for index in range(2):
        game.select_player_attack_target_at_position(enemy.position)
        game.confirm_player_attack_target()
        game.submit_player_attack_roll(natural_roll=1,natural_roll_2=1)
        if index==0:
            assert game.combat_state.turn_action.attacks_used==1
            assert game.combat_state.turn_action.attacks_maximum==2
            source=next(s for s in game._attack_sources_for_actor(current_actor(game.combat_state)) if s.id=='optical_scope')
            with pytest.raises(ValueError,match='ten sam cel'):
                validate_lorian_optical_target(game.active_combat_effects,attacker_id='lorian',target_id='different',source=source)
    assert len(game.combat_state.shared_mana.runes.discard)==2
    assert game.combat_state.turn_action.action_use==ActionUse.ACTION_USED


def test_double_shot_cannot_be_added_after_weapon_attack(tmp_path):
    card=rune_card('erynd','double_shot')
    game,_,_=playable(tmp_path,'erynd',(card.rune,'Wieża','Kotwica','Błysk','Klucz'))
    state=game.combat_state
    state=replace(state,turn_action=replace(state.turn_action,action_use=ActionUse.ACTION_USED))
    with pytest.raises(ValueError,match='ataku'):
        quote_runes(state,current_actor(state),'double_shot',{})


def test_first_rage_is_available_with_an_empty_rune_hand(tmp_path):
    game,_,_=playable(tmp_path,'brakka',('Oko','Wieża','Kotwica','Błysk','Klucz'))
    state=game.combat_state
    pool=state.shared_mana.runes
    pool=spend_runes(pool,'brakka',pool.hand('brakka'))
    game.combat_state=replace(state,shared_mana=sync_runes(state.shared_mana,pool))
    assert any(option.action_id=='rage' for option in game._available_turn_options(game._combat_turn_action_options()))
    game.use_combat_class_feature('rage')
    assert not shared_mana.payload(game)['declaration']['error']
    assert shared_mana.payload(game)['declaration']['cost']==[]
    pay(game)
    assert any(e.kind=='rage' for e in game.active_combat_effects)
    assert game.combat_state.shared_mana.runes.hand('brakka')==()
    assert game.combat_state.turn_action.rune_special_used
