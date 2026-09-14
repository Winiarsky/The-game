from dataclasses import replace

import pytest

from tests.unit.test_hero_rules_consistency import heroes
from tests.unit.test_physical_mana import session_for
from dnd_board_game.combat import current_actor, ActionUse
from dnd_board_game.rules.shared_mana import ManaPhase, SharedMana
from dnd_board_game.rules.shared_mana_catalog import shared_ability
from dnd_board_game.combat.shared_mana import quote_ability
from dnd_board_game.ui.shared_mana import command
from dnd_board_game.world import Coordinate


def send(session, action, **kwargs):
    return command(session, {"command": action, "revision": session.combat_state.shared_mana.revision, **kwargs})


def test_stance_payment_precedes_effect_and_refill_waits_for_confirmation(heroes, tmp_path):
    s = session_for(heroes['garran'], tmp_path)
    assert s.combat_state.shared_mana == SharedMana(turn_actor='garran')
    s.use_combat_class_feature('defensive_stance')
    assert s.shared_mana_declaration is not None
    assert s.combat_state.turn_action.bonus_action_use == ActionUse.ACTION_AVAILABLE
    assert s.combat_state.shared_mana.market == 5
    result = send(s, 'pay')
    assert s.combat_state.shared_mana.market == 4
    assert s.combat_state.shared_mana.phase == ManaPhase.READY
    assert s.combat_state.turn_action.bonus_action_use == ActionUse.ACTION_USED
    assert next(e for e in s.active_combat_effects if e.kind == 'garran_defensive_stance_ac').duration.value == 'until_deck_refresh'
    s.finish_combat_turn()
    assert current_actor(s.combat_state).id == 'garran'
    assert s.combat_state.shared_mana.phase == ManaPhase.END_TURN
    send(s, 'refill')
    assert s.combat_state.shared_mana.deck == 19
    assert s.combat_state.shared_mana.market == 5
    assert current_actor(s.combat_state).id != 'garran'


def test_lorian_tuning_waits_for_physical_card_operation(heroes, tmp_path):
    s = session_for(heroes['lorian'], tmp_path)
    s.use_combat_class_feature('mana_tuning')
    send(s, 'pay')
    assert s.combat_state.shared_mana.market == 4
    assert s.shared_mana_declaration.stage == 'cards'
    send(s, 'cards_done')
    assert (s.combat_state.shared_mana.deck, s.combat_state.shared_mana.market, s.combat_state.shared_mana.discard) == (19, 4, 2)


@pytest.mark.parametrize('hp,expected', [(15, 0), (14, 1), (0, 1)])
def test_dagna_flaw_strictly_below_half_hp(heroes, tmp_path, hp, expected):
    s = session_for(heroes['dagna'], tmp_path)
    dagna = current_actor(s.combat_state)
    ally = replace(heroes['garran'], hp=hp, max_hp=30, position=Coordinate(dagna.position.col+1, dagna.position.row))
    state = replace(s.combat_state, actors=(*s.combat_state.actors, ally))
    ability = shared_ability('dagna', 'sacred_flame')
    quote = quote_ability(state, dagna, ability, {})
    assert len(quote.cards) == 1+expected
    assert bool(quote.reminders) == bool(expected)


def test_hymn_gives_two_bonus_actions_without_refreshing_on_reentry(heroes, tmp_path):
    from dnd_board_game.combat.session import use_bonus_action
    from dnd_board_game.combat.shared_mana import synchronize_shared_effects
    s = session_for(heroes['lorian'], tmp_path)
    s.use_combat_class_feature('victory_hymn')
    send(s, 'pay')
    assert s.combat_state.shared_mana.hymn_sources == ('lorian',)
    first = use_bonus_action(s.combat_state)
    assert first.accepted
    second = use_bonus_action(first.state)
    assert second.accepted
    updated, _ = synchronize_shared_effects(second.state, s.active_combat_effects)
    assert not use_bonus_action(updated).accepted
    assert updated.turn_action.shared_bonus_actions_used == 2


def test_shared_sources_apply_boosts_idempotently(heroes, tmp_path):
    from dnd_board_game.combat.shared_mana_sources import boost_attack
    from dnd_board_game.combat.physical_mana_sources import adapt_attack
    from dnd_board_game.rules.shared_mana import pay_mana
    s = session_for(heroes['nimra'], tmp_path)
    actor = current_actor(s.combat_state)
    source = next(a for a in s._attack_sources_for_actor(actor) if a.id == 'nimra_force_wave')
    mana = pay_mana(s.combat_state.shared_mana, revision=0, actor_id='nimra', ability_id=source.id, count=5, boosts=(('damage',2),('push',1)))
    boosted = boost_attack(source, mana)
    assert [c.dice.count for c in boosted.damage_components] == [2, 2]
    assert boosted.failed_save_push_feet == 10
    assert boost_attack(adapt_attack(actor, boosted), mana) == boosted


def test_preserve_life_heals_above_half_with_forty_point_pool(heroes, tmp_path):
    from dnd_board_game.combat.class_feature_rules import PreserveLifeAllocation, preserve_life_capacity, validate_preserve_life_allocations
    s = session_for(heroes['dagna'], tmp_path)
    actor = current_actor(s.combat_state)
    target = replace(heroes['garran'], hp=20, max_hp=30)
    assert preserve_life_capacity(actor) == 40
    validate_preserve_life_allocations(actor, (target,), (PreserveLifeAllocation(str(target.id),10),))
    with pytest.raises(ValueError):
        validate_preserve_life_allocations(actor, (target,), (PreserveLifeAllocation(str(target.id),11),))


def test_mira_hidden_saving_throw_has_disadvantage(heroes, tmp_path):
    from dnd_board_game.combat.spells import resolve_actor_saving_throw
    from dnd_board_game.rules import SavingThrowRequest, ActiveEffect, EffectDuration
    s = session_for(heroes['mira'], tmp_path)
    actor = current_actor(s.combat_state)
    result = resolve_actor_saving_throw(actor, SavingThrowRequest('wisdom', 30, 'Test'), natural_roll=18, natural_roll_2=2,
        active_effects=(ActiveEffect('hidden', str(actor.id), 'shared_hidden', 'Ukrycie', 'hide', 1, duration=EffectDuration.UNTIL_DECK_REFRESH),))
    assert result.natural_roll == 2


def test_garran_command_failed_save_halves_movement_and_blocks_reaction(heroes, tmp_path):
    from dnd_board_game.combat.garran_features import resolve_garran_command_halt
    from dnd_board_game.combat.conditions import CombatCondition
    s = session_for(heroes['garran'], tmp_path)
    actor = current_actor(s.combat_state)
    enemy = next(a for a in s.combat_state.actors if a.faction != actor.faction)
    enemy = replace(enemy, position=Coordinate(actor.position.col+1, actor.position.row))
    from dnd_board_game.combat.session import replace_actor
    state = replace_actor(s.combat_state, enemy)
    resolved = resolve_garran_command_halt(state, (), target_id=str(enemy.id), natural_roll=1)
    assert any(e.kind == 'garran_command_half_movement' for e in resolved.active_effects)
    assert any(c.condition == CombatCondition.NO_REACTIONS for c in resolved.state.condition_states)


def test_arrow_rain_one_roll_respects_each_targets_ac_and_cover(heroes, tmp_path):
    from dnd_board_game.combat.shared_volley import resolve_volley
    s = session_for(heroes['erynd'], tmp_path)
    source = next(a for a in s._attack_sources_for_actor(current_actor(s.combat_state)) if a.id == 'arrow_rain')
    enemy = next(a for a in s.combat_state.actors if a.faction != current_actor(s.combat_state).faction)
    first = replace(enemy, id='first', ac=10)
    second = replace(enemy, id='second', ac=30)
    total, hits = resolve_volley(source, (first, second), {'first':2}, (), natural_roll=10)
    assert hits[0].armor_class == 12 and hits[0].hit
    assert hits[1].armor_class == 30 and not hits[1].hit
    _, misses = resolve_volley(source, (first, second), {}, (), natural_roll=1)
    assert all(not h.hit for h in misses)


def test_arrow_rain_ui_payment_roll_and_miss_confirmation(heroes, tmp_path):
    from dnd_board_game.ui.shared_volley import submit_volley_roll, apply_volley_damage
    s = session_for(heroes['erynd'], tmp_path)
    actor = current_actor(s.combat_state)
    enemy = next(a for a in s.combat_state.actors if a.faction != actor.faction)
    s.select_combat_attack_source('arrow_rain')
    s.select_player_area_spell_at_position(enemy.position)
    assert len(s.pending_area_spell.area_positions) == 9
    s.confirm_player_area_spell()
    send(s, 'pay')
    assert s.combat_state.shared_mana.market == 1
    assert s.pending_area_spell.stage == 'attack_roll'
    submit_volley_roll(s, 1)
    assert s.pending_area_spell.stage == 'volley_miss'
    apply_volley_damage(s, None)
    assert s.pending_area_spell is None
    assert s.combat_state.shared_mana.phase == ManaPhase.READY


def test_counterattack_command_restores_owner_budget_and_does_not_add_turns(heroes, tmp_path):
    from dnd_board_game.combat.shared_command import start_command, advance_command
    from dnd_board_game.combat.session import reaction_available_for
    s = session_for(heroes['garran'], tmp_path)
    owner = current_actor(s.combat_state)
    ally = replace(heroes['mira'], position=Coordinate(owner.position.col+1, owner.position.row))
    state = replace(s.combat_state, actors=(*s.combat_state.actors, ally))
    original = state.initiative_order
    state, effects = start_command(state, (), str(ally.id))
    assert state.shared_mana.command_step == 1
    state, effects = advance_command(state, effects)
    assert current_actor(state).id == ally.id
    assert not reaction_available_for(state, ally)
    assert len(state.initiative_order.entries) == len(original.entries)+1
    state, effects = advance_command(state, effects)
    assert state.initiative_order == original
    assert current_actor(state).id == owner.id
    assert state.turn_action.action_use == ActionUse.ACTION_USED
    assert state.turn_action.bonus_action_use == ActionUse.ACTION_AVAILABLE
    assert not effects


def test_matrix_save_is_once_per_target_turn(heroes, tmp_path):
    from dnd_board_game.combat.shared_mana_zones import resolve_matrix_save
    from dnd_board_game.rules import ActiveEffect, EffectSource, EffectSourceType, EffectDuration
    s = session_for(heroes['nimra'], tmp_path)
    actor = current_actor(s.combat_state)
    enemy = next(a for a in s.combat_state.actors if a.faction != actor.faction)
    zone = ActiveEffect('matrix', str(actor.id), 'grease_zone', 'Matryca', 'spell:nimra_sticky_matrix', 10,
        anchor_position=enemy.position, source_actor_id=str(actor.id), source=EffectSource(EffectSourceType.SPELL, 'nimra_sticky_matrix', 'Matryca'), duration=EffectDuration.UNTIL_DECK_REFRESH)
    first = resolve_matrix_save(s.combat_state, (), zone, str(enemy.id), 1)
    assert first.saving_throw is not None and not first.saving_throw.success
    second = resolve_matrix_save(first.state, first.effects, zone, str(enemy.id), 20)
    assert second.saving_throw is None
    assert second.state == first.state


@pytest.mark.parametrize('hero_id', ['garran', 'brakka', 'mira', 'dagna', 'lorian', 'nimra', 'erynd'])
def test_all_shared_abilities_have_runtime_sources_or_features(heroes, tmp_path, hero_id):
    from dnd_board_game.rules.shared_mana_catalog import CATALOG
    from dnd_board_game.combat.physical_mana import effect
    s = session_for(heroes[hero_id], tmp_path)
    s.active_combat_effects = (effect(hero_id, 'rage', 'Szał'),)
    actor = current_actor(s.combat_state)
    sources = {a.id for a in s._attack_sources_for_actor(actor)}
    options = s._combat_turn_action_options()
    available = sources | {o.action_id for o in options} | {o.source_id for o in options}
    s.active_combat_effects = ()
    available |= {o.action_id for o in s._combat_turn_action_options()}
    # Reactions are offered by interrupts and Hide has its dedicated basic menu action.
    special = {'hide', 'counterattack_command', 'garran_shield_wall', 'garran_rally'}
    expected = {a.id for a in CATALOG if a.hero_id == hero_id and a.timing != 'R'} - special
    assert expected <= available, expected - available


def test_technique_movement_preserves_ordinary_budget_and_rejects_repeat_targets(heroes, tmp_path):
    from dnd_board_game.rules.shared_mana import pay_mana
    from dnd_board_game.combat.session import movement_remaining, use_movement
    from dnd_board_game.combat.shared_mana_techniques import validate_technique_target
    from dnd_board_game.world import PathResult
    s = session_for(heroes['mira'], tmp_path)
    actor = current_actor(s.combat_state)
    mana = pay_mana(s.combat_state.shared_mana, revision=0, actor_id='mira', ability_id='blade_dance', count=4)
    state = replace(s.combat_state, shared_mana=mana)
    assert movement_remaining(state, actor) == 15
    destination = Coordinate(actor.position.col+1, actor.position.row)
    path = PathResult(actor.position, destination, (actor.position, destination), 5, True)
    moved = use_movement(state, actor, path)
    assert moved.accepted and moved.state.turn_action.movement_used_feet == 0
    assert moved.state.shared_mana.technique_movement == 10
    state = replace(moved.state, shared_mana=replace(moved.state.shared_mana, attack_targets=('enemy',)))
    with pytest.raises(ValueError, match='innego'):
        validate_technique_target(state, 'blade_dance', 'enemy')


def test_paid_action_cannot_be_cancelled_before_its_roll(heroes, tmp_path):
    s = session_for(heroes['garran'], tmp_path)
    s.use_combat_class_feature('second_wind')
    send(s, 'pay')
    assert s.pending_physical_feature_action_id == "second_wind"
    with pytest.raises(ValueError, match='Koszt'):
        s.cancel_physical_feature_prompt()
    assert s.combat_state.shared_mana.market == 4


def test_end_effects_are_resolved_before_refill(heroes, tmp_path):
    from dnd_board_game.combat.physical_mana import effect
    s = session_for(heroes['garran'], tmp_path)
    s.active_combat_effects = (effect('garran', 'shared_offensive_used', 'Ofensywa', 1),)
    s.finish_combat_turn()
    assert s.combat_state.shared_mana.phase == ManaPhase.END_TURN
    assert s.combat_state.shared_mana.end_effects_applied
    assert not s.active_combat_effects
    send(s, 'refill')
    assert not s.combat_state.shared_mana.end_effects_applied


def test_two_reactions_can_share_one_attack_without_counting_as_own_mana(heroes, tmp_path):
    from dnd_board_game.rules.shared_mana import pay_mana
    from dnd_board_game.ui.shared_mana import complete_reaction_payment
    s = session_for(heroes['garran'], tmp_path)
    for actor, ability in [('lorian', 'cutting_words'), ('nimra', 'shield')]:
        mana = s.combat_state.shared_mana
        s.combat_state = replace(s.combat_state, shared_mana=pay_mana(mana, revision=mana.revision, actor_id=actor, ability_id=ability, count=1))
        complete_reaction_payment(s, ability)
        assert s.combat_state.shared_mana.phase == ManaPhase.READY
    assert s.combat_state.shared_mana.market == 3
    assert s.combat_state.shared_mana.spent_this_turn == 0


def test_smoke_has_its_own_movement_after_ordinary_movement(heroes, tmp_path):
    from dnd_board_game.combat.session import movement_remaining, use_movement
    from dnd_board_game.world import PathResult
    s = session_for(heroes['mira'], tmp_path)
    s.combat_state = replace(s.combat_state, turn_action=replace(s.combat_state.turn_action, movement_used_feet=25))
    s.use_combat_class_feature('smoke_screen')
    send(s, 'boost', boost_id='move', count=1)
    send(s, 'pay')
    actor = current_actor(s.combat_state)
    assert movement_remaining(s.combat_state, actor, s.active_combat_effects) == 15
    dest = Coordinate(actor.position.col+1, actor.position.row)
    move = use_movement(s.combat_state, actor, PathResult(actor.position, dest, (actor.position, dest), 5, True), s.active_combat_effects)
    assert move.accepted
    assert move.state.turn_action.movement_used_feet == 25
    assert move.state.shared_mana.smoke_movement == 10


def test_paid_dance_can_finish_without_attacking_and_keeps_cost(heroes, tmp_path):
    s = session_for(heroes['mira'], tmp_path)
    s.select_combat_attack_source('blade_dance')
    send(s, 'pay')
    s.finish_combat_turn()
    assert s.combat_state.shared_mana.market == 1
    assert s.combat_state.shared_mana.phase == ManaPhase.END_TURN
    assert s.combat_state.turn_action.action_use == ActionUse.ACTION_USED


def test_inspiration_rejects_missing_target_before_payment(heroes, tmp_path):
    from dnd_board_game.character_creation.physical_mana import apply_physical_mana_profile
    s = session_for(heroes['lorian'], tmp_path)
    owner = current_actor(s.combat_state)
    ally = replace(apply_physical_mana_profile(heroes['garran']), position=Coordinate(owner.position.col+1, owner.position.row))
    s.combat_state = replace(s.combat_state, actors=(*s.combat_state.actors, ally))
    s.use_combat_class_feature('mana_inspiration')
    with pytest.raises(ValueError, match='bohatera'):
        send(s, 'pay')
    assert s.combat_state.shared_mana.market == 5
    assert 'garran' in {a['id'] for a in s.state_payload()['combat']['shared_mana']['declaration']['targets']}
    send(s, 'parameters', target_id='garran')
    send(s, 'pay')
    assert s.combat_state.shared_mana.market == 4
    assert any(e.kind == 'bardic_inspiration' and e.actor_id == 'garran' for e in s.active_combat_effects)


def test_erynd_technique_quotes_adjacent_ally_flaw_before_payment(heroes, tmp_path):
    s = session_for(heroes['erynd'], tmp_path)
    owner = current_actor(s.combat_state)
    target = next(a for a in s.combat_state.actors if a.faction != owner.faction)
    ally = replace(heroes['garran'], position=Coordinate(4,6))
    s.combat_state = replace(s.combat_state, actors=tuple(replace(a, position=Coordinate(3,3)) if a.id == owner.id else replace(a, position=Coordinate(3,6)) if a.id == target.id else a for a in s.combat_state.actors)+(ally,))
    s.use_combat_class_feature('double_shot')
    assert s.shared_mana_declaration is None
    s.select_player_attack_target_at_position(Coordinate(3,6))
    s.confirm_player_attack_target()
    assert len(s.state_payload()['combat']['shared_mana']['declaration']['cost']) == 4
    send(s, 'pay')
    assert s.combat_state.shared_mana.market == 1


def test_shared_mana_snapshot_roundtrip_preserves_cycle_and_echo(heroes, tmp_path):
    s = session_for(heroes['nimra'], tmp_path)
    s.combat_state = replace(s.combat_state, shared_mana=SharedMana(deck=7, market=4, discard=14, cycle=3, echo_spell='nimra_frost_pulse', echo_count=2, turn_actor='nimra'))
    expected = s.combat_state.shared_mana
    s.save_snapshot()
    s.load_snapshot()
    assert s.combat_state.shared_mana == expected
