"""Mira's smoke is a stationary hiding area, not movement or automatic Hide."""
from dataclasses import replace

import pytest

from dnd_board_game.application.combat_turn_finalization import CombatTurnFinalizationService
from dnd_board_game.combat import ActionUse, current_actor, hide_eligibility, replace_actor
from dnd_board_game.combat.smoke import smoke_contains, smoke_hide_request, smoke_positions
from dnd_board_game.rules import ActiveEffect, D20RollRequest, EffectDuration, EffectEvent, EffectEventType, RollMode, expire_active_effects
from dnd_board_game.save.session_snapshot import _effect_payload, _effect_from_payload
from dnd_board_game.ui.aura_preview import aura_feedback
from dnd_board_game.ui.shared_mana import gate_end_turn
from dnd_board_game.world import BoardState, BoardDimensions, Coordinate
from tests.unit.test_rune_combat_actions import playable, pay


def smoke(center=Coordinate(1, 1)):
    return ActiveEffect(id='smoke', actor_id='mira', kind='smoke_screen_area', label='Dym',
        object_id='class_feature:smoke_screen', value=0, anchor_position=center,
        source_actor_id='mira', duration=EffectDuration.UNTIL_TURN_END,
        expiration_actor_id='mira', expiration_event_count=2)


def test_smoke_square_boundaries_and_roll_modes_apply_to_every_figure():
    board=BoardState(BoardDimensions(5,5))
    effect=smoke()
    assert len(smoke_positions(board,Coordinate(1,1)))==9
    assert len(smoke_positions(board,Coordinate(0,0)))==4
    for position in smoke_positions(board,Coordinate(1,1)):
        assert smoke_contains(position,(effect,))
        assert smoke_hide_request(D20RollRequest(),position,(effect,)).mode==RollMode.ADVANTAGE
    assert not smoke_contains(Coordinate(3,1),(effect,))
    assert smoke_hide_request(D20RollRequest(),Coordinate(3,1),(effect,)).mode==RollMode.NORMAL
    assert smoke_hide_request(D20RollRequest(mode=RollMode.DISADVANTAGE),Coordinate(1,1),(effect,)).mode==RollMode.NORMAL


def test_smoke_expires_after_second_owner_turn_end_and_roundtrip_preserves_timer():
    effects=(smoke(),)
    assert _effect_from_payload(_effect_payload(effects[0]))==effects[0]
    legacy_payload=_effect_payload(effects[0])
    legacy_payload.pop('expiration_event_count')
    assert _effect_from_payload(legacy_payload).expiration_event_count==1
    for event in (EffectEvent(EffectEventType.TURN_END,actor_id='enemy'),
                  EffectEvent(EffectEventType.ROUND_ENDED),
                  EffectEvent(EffectEventType.TURN_START,actor_id='mira')):
        assert expire_active_effects(effects,event).active_effects==effects
    event=EffectEvent(EffectEventType.TURN_END,actor_id='mira')
    effects=expire_active_effects(effects,event).active_effects
    assert len(effects)==1 and effects[0].expiration_event_count==1
    assert not expire_active_effects(effects,event).active_effects
    assert not expire_active_effects((smoke(),),EffectEvent(EffectEventType.ENCOUNTER_ENDED)).active_effects


def test_preview_cancel_leaves_runic_hand_effects_and_budget_unchanged(tmp_path):
    game,_,_=playable(tmp_path,'mira',('Wieża','Rozwidlenie','Kotwica','Klucz','Kielich'))
    before=game.combat_state
    before_effects=game.active_combat_effects
    center=current_actor(before).position
    preview=aura_feedback(game,'smoke_screen','mira')
    assert set(p for f in preview.frames for p in f.positions)==set(smoke_positions(game._active_encounter().board,center))
    game.use_combat_class_feature('smoke_screen')
    assert game.active_combat_effects==before_effects
    actor=current_actor(game.combat_state)
    game.combat_state=replace_actor(game.combat_state,replace(actor,position=Coordinate(18,actor.position.row)))
    edge_preview=aura_feedback(game,'smoke_screen','mira')
    assert all(p.col<19 for frame in edge_preview.frames for p in frame.positions)
    pay(game,'cancel')
    assert game.combat_state.shared_mana.runes==before.shared_mana.runes
    assert game.combat_state.turn_action==before.turn_action
    assert game.active_combat_effects==before_effects


def test_paid_smoke_has_no_free_hide_movement_or_disengage_and_stationary_leds(tmp_path):
    game,_,enemy_id=playable(tmp_path,'mira',('Wieża','Rozwidlenie','Kotwica','Klucz','Kielich'))
    before=game.combat_state
    actor=current_actor(before)
    enemy=next(a for a in before.actors if str(a.id)==enemy_id)
    board=game._active_encounter().board
    assert not hide_eligibility(board,actor,before.actors).allowed
    game.use_combat_class_feature('smoke_screen')
    pay(game)
    assert current_actor(game.combat_state).position==actor.position
    assert game.combat_state.turn_action.movement_used_feet==0
    assert not game.combat_state.turn_action.movement_action_used
    assert game.combat_state.turn_action.action_use==ActionUse.ACTION_AVAILABLE
    assert game.combat_state.turn_action.rune_special_used
    assert len(game.combat_state.shared_mana.runes.discard)==1
    assert not game.combat_state.hidden_states
    assert game.pending_combat_skill_check is None
    assert not any(e.kind in {'smoke_screen_hide_pending','movement_speed_cap','disengage_until_turn_end'} for e in game.active_combat_effects)
    assert hide_eligibility(board,actor,game.combat_state.actors,active_effects=game.active_combat_effects).allowed
    assert hide_eligibility(board,enemy,game.combat_state.actors,active_effects=game.active_combat_effects).allowed
    assert smoke_hide_request(D20RollRequest(),enemy.position,game.active_combat_effects).mode==RollMode.ADVANTAGE
    with pytest.raises(ValueError):game.use_combat_class_feature('hide')
    game.combat_state=replace_actor(game.combat_state,replace(actor,position=Coordinate(actor.position.col+3,actor.position.row)))
    actual=aura_feedback(game,'smoke_screen','mira',active_only=True)
    assert set(p for f in actual.frames for p in f.positions)==set(smoke_positions(board,actor.position))


def test_next_turn_hide_is_separate_paid_card_with_advantage_and_smoke_expires(tmp_path):
    game,_,_=playable(tmp_path,'mira',('Wieża','Rozwidlenie','Kotwica','Klucz','Kielich'))
    game.use_combat_class_feature('smoke_screen')
    pay(game)
    service=CombatTurnFinalizationService()
    assert not gate_end_turn(game)
    assert next(e for e in game.active_combat_effects if e.kind=='smoke_screen_area').expiration_event_count==1
    for _ in game.combat_state.initiative_order.entries:
        result=service.finish_active_turn(state=game.combat_state,active_effects=game.active_combat_effects)
        game.combat_state,game.active_combat_effects=result.state,result.active_effects
    assert str(current_actor(game.combat_state).id)=='mira'
    assert next(e for e in game.active_combat_effects if e.kind=='smoke_screen_area').expiration_event_count==1
    before=game.combat_state.shared_mana.runes
    hide_options=[option for option in game._combat_turn_action_options()
                  if option.action_id=='hide' or option.action.value=='hide']
    assert len(hide_options)==1 and hide_options[0].id=='class-feature:hide'
    game.use_combat_class_feature('hide')
    assert game.shared_mana_declaration.ability_id=='hide'
    assert game.combat_state.shared_mana.runes==before
    pay(game)
    assert game.pending_combat_skill_check.roll_mode=='advantage'
    assert len(game.combat_state.shared_mana.runes.discard)==2
    game.submit_combat_skill_check(natural_roll=1,natural_roll_2=20)
    assert game.combat_state.hidden_states
    assert game.combat_state.turn_action.action_use==ActionUse.ACTION_AVAILABLE
    result=service.finish_active_turn(state=game.combat_state,active_effects=game.active_combat_effects)
    assert not any(e.kind=='smoke_screen_area' for e in result.active_effects)
