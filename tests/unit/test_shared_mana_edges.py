"""Regression tests for committed payments, manual effects and forced movement."""
from dataclasses import replace
from unittest.mock import Mock

import pytest

from tests.unit.test_hero_rules_consistency import heroes
from tests.unit.test_physical_mana import session_for
from tests.unit.test_shared_mana_runtime import send
from dnd_board_game.combat import current_actor, ActionUse
from dnd_board_game.rules.shared_mana import ManaPhase
from dnd_board_game.world import Coordinate


def nearby_enemy(session):
    hero = current_actor(session.combat_state)
    enemy = next(a for a in session.combat_state.actors if a.faction != hero.faction)
    session.combat_state = replace(session.combat_state, actors=tuple(
        replace(a, position=Coordinate(3,3)) if a.id == hero.id else
        replace(a, position=Coordinate(4,3)) if a.id == enemy.id else a for a in session.combat_state.actors))
    return next(a for a in session.combat_state.actors if a.id == enemy.id)


def test_caring_gesture_pays_before_manual_die_and_expires_on_source_turn(heroes, tmp_path):
    from dnd_board_game.rules import EffectEvent, EffectEventType
    from dnd_board_game.combat.scene_interactions import expire_combat_effects
    s = session_for(heroes['dagna'], tmp_path)
    dagna = current_actor(s.combat_state)
    ally = replace(heroes['garran'], temp_hp=0, position=Coordinate(dagna.position.col+1, dagna.position.row))
    s.combat_state = replace(s.combat_state, actors=(*s.combat_state.actors, ally))
    s.use_combat_class_feature('caring_gesture', target_id='garran')
    send(s, 'pay')
    assert s.combat_state.shared_mana.market == 4
    assert s.shared_mana_declaration.stage == 'effect_roll'
    assert s._actor_by_string_id('garran').temp_hp == 0
    send(s, 'parameters', natural_roll=4)
    send(s, 'effect')
    from dnd_board_game.rules import ability_modifier
    assert s._actor_by_string_id('garran').temp_hp == 4 + ability_modifier(dagna.ability_scores.wisdom)
    assert s.combat_state.shared_mana.phase == ManaPhase.READY
    assert s.combat_state.turn_action.bonus_action_use == ActionUse.ACTION_USED
    s.combat_state, s.active_combat_effects, expired = expire_combat_effects(s.combat_state, s.active_combat_effects, EffectEvent(EffectEventType.TURN_START, actor_id='dagna'))
    assert expired
    assert s._actor_by_string_id('garran').temp_hp == 0


def test_aim_after_movement_cannot_take_mana(heroes, tmp_path):
    s = session_for(heroes['erynd'], tmp_path)
    s.combat_state = replace(s.combat_state, turn_action=replace(s.combat_state.turn_action, movement_used_feet=5))
    s.use_combat_class_feature('aim')
    with pytest.raises(ValueError, match='przed'):
        send(s, 'pay')
    assert s.combat_state.shared_mana.market == 5


def test_bastion_blocks_forced_movement_at_destination_boundary(heroes, tmp_path):
    from dnd_board_game.combat.magic_movement import forced_movement_destination, legal_forced_movement_targets, MagicMovementKind
    s = session_for(heroes['garran'], tmp_path)
    enemy = nearby_enemy(s)
    s.use_combat_class_feature('iron_bastion')
    send(s, 'pay')
    actor = current_actor(s.combat_state)
    board = s._active_encounter().board
    assert forced_movement_destination(board, s.combat_state, enemy, actor, kind=MagicMovementKind.PUSH, distance_feet=10) == actor.position
    assert actor.id not in {a.id for a in legal_forced_movement_targets(board, s.combat_state, enemy, kind=MagicMovementKind.PUSH, range_feet=30, distance_feet=10)}
    send(s, 'refresh')
    send(s, 'refresh_done')
    assert forced_movement_destination(board, s.combat_state, enemy, actor, kind=MagicMovementKind.PUSH, distance_feet=10) != actor.position


@pytest.mark.parametrize('roll,won', [(20, True), (1, False)])
def test_shoulder_uses_manual_contest_then_boost_damage(heroes, tmp_path, roll, won):
    s = session_for(heroes['brakka'], tmp_path)
    target = nearby_enemy(s)
    s.start_combat_class_feature_targeting('shoulder_check')
    s._handle_board_position(target.position)
    s.confirm_combat_class_feature_targeting()
    send(s, 'boost', boost_id='push', count=1)
    send(s, 'boost', boost_id='damage', count=1)
    send(s, 'pay')
    assert s.shared_mana_declaration.stage == 'effect_roll'
    s.encounter_rng = Mock(randint=Mock(return_value=10))
    send(s, 'parameters', natural_roll=roll)
    send(s, 'effect')
    if won:
        from dnd_board_game.combat.class_features import legal_shoulder_check_destinations
        legal = legal_shoulder_check_destinations(s._active_encounter().board, s.combat_state, current_actor(s.combat_state), target, distance_feet=10)
        assert legal
        s._handle_board_position(legal[-1])
        s.confirm_combat_class_feature_targeting()
        assert s.shared_mana_declaration.resume_arguments['shoulder_stage'] == 'damage'
        send(s, 'parameters', natural_roll=5)
        send(s, 'effect')
        assert s._actor_by_string_id(str(target.id)).hp == target.hp-5
    else:
        assert s._actor_by_string_id(str(target.id)).hp == target.hp
    assert s.combat_state.shared_mana.phase == ManaPhase.READY
    assert s.combat_state.shared_mana.market == 1
    assert s.combat_state.turn_action.action_use == ActionUse.ACTION_USED


def test_volley_uses_aim_and_consumes_it_on_one_shared_roll(heroes, tmp_path):
    from dnd_board_game.application.player_area_healing_flow import PendingAreaSpell
    from dnd_board_game.ui.shared_volley import submit_volley_roll
    s = session_for(heroes['erynd'], tmp_path)
    target = nearby_enemy(s)
    s.use_combat_class_feature('aim')
    send(s, 'pay')
    actor = current_actor(s.combat_state)
    s.pending_area_spell = PendingAreaSpell(caster_id=str(actor.id), source_id='arrow_rain', origin=actor.position, anchor=target.position, area_positions=(target.position,), target_ids=(str(target.id),), stage='attack_roll')
    submit_volley_roll(s, natural_roll=1, natural_roll_2=20)
    assert s.pending_area_spell.volley_hits[0].critical
    assert not any(e.kind == 'erynd_aim_advantage' for e in s.active_combat_effects)


def test_rage_has_no_round_timer_and_refresh_expires_both_markers(heroes, tmp_path):
    from dnd_board_game.rules import EffectDuration, EffectEvent, EffectEventType, expire_active_effects
    s = session_for(heroes['brakka'], tmp_path)
    s.use_combat_class_feature('rage')
    send(s, 'pay')
    rage = tuple(e for e in s.active_combat_effects if e.kind in {'rage', 'rage_duration'})
    assert len(rage) == 2
    assert all(e.duration == EffectDuration.UNTIL_DECK_REFRESH and e.remaining_rounds is None for e in rage)
    for _ in range(12):
        rage = expire_active_effects(rage, EffectEvent(EffectEventType.ROUND_ENDED)).active_effects
    assert len(rage) == 2
    send(s, 'refresh')
    send(s, 'refresh_done')
    assert not any(e.kind in {'rage', 'rage_duration'} for e in s.active_combat_effects)


def test_hidden_mira_save_ui_requests_two_dice(heroes, tmp_path):
    from dnd_board_game.application.enemy_turn_flow import PendingEnemySavingThrow
    from dnd_board_game.ui.exploration_app import _pending_enemy_saving_throw_payload
    from dnd_board_game.rules import SavingThrowRequest
    from dnd_board_game.combat.physical_mana import effect
    s = session_for(heroes['mira'], tmp_path)
    pending = PendingEnemySavingThrow('mira', 'enemy_spell', SavingThrowRequest('wisdom', 14, 'Wróg'))
    payload = _pending_enemy_saving_throw_payload(pending, s.combat_state, (effect('mira', 'shared_hidden', 'Ukrycie'),))
    assert payload['roll_mode'] == 'disadvantage'


def test_force_wave_boost_applies_damage_and_push_without_losing_payment(heroes, tmp_path):
    s = session_for(heroes['nimra'], tmp_path)
    target = nearby_enemy(s)
    s.select_combat_attack_source('nimra_force_wave')
    s.select_player_area_spell_at_position(Coordinate(4,3))
    s.confirm_player_area_spell()
    send(s, 'boost', boost_id='damage', count=1)
    send(s, 'boost', boost_id='push', count=1)
    s.encounter_rng = Mock(randint=Mock(return_value=1))
    send(s, 'pay')
    assert s.pending_area_spell.stage == 'damage_roll'
    source = s._attack_source_by_id(current_actor(s.combat_state), 'nimra_force_wave')
    totals = {c.id: c.dice.count for c in source.damage_components}
    s.submit_player_area_spell_damage(component_totals=totals)
    updated = s._actor_by_string_id(str(target.id))
    assert updated.hp < target.hp
    assert updated.position != target.position
    assert s.combat_state.shared_mana.market == 1
    assert s.combat_state.shared_mana.phase == ManaPhase.READY


def test_lightning_path_jumps_twice_without_repeating_targets(heroes, tmp_path):
    s = session_for(heroes['nimra'], tmp_path)
    first = nearby_enemy(s)
    second = replace(first, id='second', position=Coordinate(5,3))
    third = replace(first, id='third', position=Coordinate(6,3))
    s.combat_state = replace(s.combat_state, actors=(*s.combat_state.actors, second, third))
    s.select_combat_attack_source('nimra_lightning_path')
    s.select_player_attack_target_at_position(first.position)
    assert s.pending_player_attack.shared_target_ids == ('second', 'third')
    s.confirm_player_attack_target()
    s.encounter_rng = Mock(randint=Mock(return_value=1))
    send(s, 'pay')
    assert len(s.pending_player_attack.saving_throws) == 3
    source = s._attack_source_by_id(current_actor(s.combat_state), 'nimra_lightning_path')
    s.submit_player_damage_roll(component_totals={c.id: c.dice.count for c in source.damage_components})
    assert all(s._actor_by_string_id(str(a.id)).hp < a.hp for a in (first, second, third))
    assert s.combat_state.shared_mana.phase == ManaPhase.READY


def test_dagna_aura_waits_for_payment_and_applies_both_boosts(heroes, tmp_path):
    s = session_for(heroes['dagna'], tmp_path)
    nearby_enemy(s)
    s.start_combat_concentration_action('divine_care_aura')
    assert s.shared_mana_declaration is not None
    assert not any(e.kind == 'divine_care_aura_source' for e in s.active_combat_effects)
    send(s, 'boost', boost_id='radius', count=1)
    send(s, 'boost', boost_id='reduction', count=1)
    send(s, 'pay')
    source = next(e for e in s.active_combat_effects if e.kind == 'divine_care_aura_source')
    assert source.radius_feet == 10
    assert source.value == 2
    assert source.modifier == -2
    assert s.combat_state.shared_mana.market == 1
    assert s.combat_state.shared_mana.phase == ManaPhase.READY


def test_matrix_can_be_placed_on_empty_ground_without_initial_save(heroes, tmp_path):
    s = session_for(heroes['nimra'], tmp_path)
    nearby_enemy(s)
    s.start_combat_concentration_action('nimra_sticky_matrix')
    s._handle_board_position(Coordinate(5,5))
    assert s.pending_concentration_action.selected_target_ids == ()
    s.confirm_combat_concentration_action()
    s.encounter_rng = Mock(randint=Mock(return_value=1))
    send(s, 'pay')
    assert s.combat_state.shared_mana.phase == ManaPhase.READY
    assert s.combat_state.shared_mana.market == 3
    assert sum(e.kind == 'grease_zone' for e in s.active_combat_effects) == 1
    assert not s.combat_state.condition_states
    s.encounter_rng.randint.assert_not_called()


def test_guard_payment_uses_reaction_and_redirects_one_attack(heroes, tmp_path):
    from dnd_board_game.ui.shared_guard import offer_guard
    from dnd_board_game.combat.enemy_ai import EnemyTurnPlan
    from dnd_board_game.combat import actor_as_combat_target
    from dnd_board_game.combat.session import reaction_available_for
    from dnd_board_game.combat.garran_features import redirect_guarded_single_target
    s = session_for(heroes['garran'], tmp_path)
    enemy = nearby_enemy(s)
    ally = replace(heroes['mira'], position=Coordinate(3,4))
    s.combat_state = replace(s.combat_state, actors=(*s.combat_state.actors, ally), shared_mana=replace(s.combat_state.shared_mana, turn_actor=str(enemy.id)))
    source = s._active_encounter().attack_sources_by_actor[enemy.id]
    s.pending_enemy_turn_intent = EnemyTurnPlan(s.combat_state, enemy, actor_as_combat_target(ally), 'Atak', source_id=source.id)
    assert offer_guard(s)
    s.resolve_enemy_turn = Mock(side_effect=lambda: s.state_payload())
    send(s, 'pay')
    assert not reaction_available_for(s.combat_state, current_actor(s.combat_state))
    assert s.combat_state.shared_mana.market == 4
    assert s.combat_state.shared_mana.spent_this_turn == 0
    redirect = redirect_guarded_single_target(s.combat_state, s.active_combat_effects, 'mira')
    assert redirect.target.id == 'garran'
    assert not any(e.kind == 'garran_guard_companion' for e in redirect.active_effects)


def test_rider_keeps_early_use_expiration_and_source_turn_boundary(heroes, tmp_path):
    from dnd_board_game.rules import ActiveEffect, EffectDuration, AdditionalEffectExpiration, EffectEvent, EffectEventType, expire_active_effects
    from dnd_board_game.combat.shared_mana import synchronize_shared_effects
    s = session_for(heroes['lorian'], tmp_path)
    target = nearby_enemy(s)
    mark = ActiveEffect('mocked', str(target.id), 'lorian_mocked_attack', 'Ostrzał', 'class_feature:mocking_shot', 1,
        source_actor_id='lorian', target_actor_id=str(target.id), duration=EffectDuration.UNTIL_NEXT_ATTACK,
        expiration_actor_id=str(target.id), additional_expirations=(AdditionalEffectExpiration(EffectDuration.UNTIL_TURN_END, actor_id=str(target.id)),))
    state, effects = synchronize_shared_effects(s.combat_state, (mark,))
    assert effects[0].duration == EffectDuration.UNTIL_TURN_START
    assert effects[0].expiration_actor_id == 'lorian'
    assert synchronize_shared_effects(state, effects) == (state, effects)
    assert expire_active_effects(effects, EffectEvent(EffectEventType.TURN_END, actor_id=str(target.id))).active_effects == effects
    assert not expire_active_effects(effects, EffectEvent(EffectEventType.ATTACK_RESOLVED, actor_id=str(target.id), target_actor_id='lorian')).active_effects
