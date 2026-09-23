"""Mind Break weakens one later Wisdom save, never its own first save."""
from dataclasses import replace

import pytest

from dnd_board_game.combat import (
    CombatCondition, ConditionState, ConditionSaveTiming, resolve_actor_saving_throw,
    resolve_condition_save, resolve_garran_command_halt, replace_actor,
)
from dnd_board_game.combat.conditions import condition_save_roll_request
from dnd_board_game.combat.saving_effects import MIND_BREAK_WISDOM, consume_saving_effects
from dnd_board_game.combat.spells import saving_throw_roll_request
from dnd_board_game.rules import (
    ActiveEffect, EffectDuration, EffectEvent, EffectEventType, RollMode,
    SavingThrowRequest, expire_active_effects,
)
from dnd_board_game.world import Coordinate
from tests.unit.test_garran_features import _actor, _state
from tests.unit.test_player_combat_action_flow import SequenceRng
from tests.unit.test_rune_combat_actions import playable, pay


def weakness(actor_id: str = 'enemy') -> ActiveEffect:
    return ActiveEffect(
        id=f'{MIND_BREAK_WISDOM}:{actor_id}', actor_id=actor_id,
        kind=MIND_BREAK_WISDOM, label='Załamanie woli', object_id='class_feature:nimra_mind_break',
        value=0, source_actor_id='nimra', duration=EffectDuration.UNTIL_TURN_START,
        expiration_actor_id='nimra',
    )


@pytest.mark.parametrize('ability,mode,expected', [
    ('wisdom', RollMode.NORMAL, 2),
    ('wisdom', RollMode.ADVANTAGE, 18),
    ('wisdom', RollMode.DISADVANTAGE, 2),
    ('dexterity', RollMode.NORMAL, 18),
])
def test_save_mode_matches_selected_die_and_only_wisdom_consumes(ability, mode, expected):
    target = _actor('enemy', Coordinate(1, 1))
    effects = (weakness(),)
    request = SavingThrowRequest(ability, 12, 'Test')
    preview = saving_throw_roll_request(target, request, roll_mode=mode, active_effects=effects)
    save = resolve_actor_saving_throw(target, request, natural_roll=18, natural_roll_2=2,
                                     roll_mode=mode, active_effects=effects)
    assert save.natural_roll == expected
    assert preview.mode == (RollMode.DISADVANTAGE if expected == 2 else RollMode.NORMAL)
    assert effects == (weakness(),)  # A pure preview/resolver cannot consume authoritative state.
    assert consume_saving_effects(effects, save) == (() if ability == 'wisdom' else effects)


def test_duplicate_weakness_and_other_disadvantage_do_not_stack_against_advantage():
    target = _actor('enemy', Coordinate(1, 1))
    effects = (weakness(), replace(weakness(), id='duplicate'),
               replace(weakness(), id='lorian', kind='lorian_mocked_wisdom'))
    save = resolve_actor_saving_throw(target, SavingThrowRequest('wisdom', 12, 'Test'),
                                     natural_roll=18, roll_mode=RollMode.ADVANTAGE, active_effects=effects)
    assert save.natural_roll == 18
    assert [e.kind for e in consume_saving_effects(effects, save)] == ['lorian_mocked_wisdom']


@pytest.mark.parametrize('rolls', [(18, 2), (18, 19)])
def test_command_halt_consumes_penalty_on_failure_and_success(rolls):
    from dnd_board_game.actors import Faction
    garran = _actor('garran', Coordinate(1, 1), features=('garran_command_halt',))
    target = _actor('enemy', Coordinate(2, 1), faction=Faction.ENEMY)
    result = resolve_garran_command_halt(_state(garran, target), (weakness(),), target_id='enemy',
                                       natural_roll=rolls[0], natural_roll_2=rolls[1])
    assert result.saving_throw.natural_roll == min(rolls)
    assert all(e.kind != MIND_BREAK_WISDOM for e in result.active_effects)


def test_condition_repeat_uses_same_dice_mode_as_preview():
    target = _actor('enemy', Coordinate(1, 1))
    condition = ConditionState('enemy', CombatCondition.FRIGHTENED, save_ability='wisdom',
                               save_dc=12, save_timing=ConditionSaveTiming.TURN_END)
    request = condition_save_roll_request((condition,), target, condition, active_effects=(weakness(),))
    assert request.mode == RollMode.DISADVANTAGE
    result = resolve_condition_save((condition,), target, condition, natural_roll=18, natural_roll_2=2,
                                    active_effects=(weakness(),))
    assert not result.removed
    assert result.saving_throw.natural_roll == 2


@pytest.mark.parametrize('natural,expected_damage,weakened', [(1, 6, True), (20, 3, False)])
def test_real_mind_break_keeps_damage_and_applies_only_failed_save_penalty(tmp_path, natural, expected_damage, weakened):
    game, _, enemy_id = playable(tmp_path, 'nimra', ('Węzeł', 'Oko', 'Błysk', 'Kielich', 'Klucz'))
    target = next(a for a in game.combat_state.actors if str(a.id) == enemy_id)
    game.encounter_rng = SequenceRng(natural)
    game.select_combat_attack_source('nimra_mind_break')
    game.select_player_attack_target_at_position(target.position)
    game.confirm_player_attack_target()
    pay(game)
    assert game.pending_player_attack.stage == 'damage_roll'
    assert game.pending_player_attack.saving_throws[0].natural_roll == natural
    assert not any(e.kind == MIND_BREAK_WISDOM for e in game.active_combat_effects)
    game.submit_player_damage_roll(damage=6)
    after = next(a for a in game.combat_state.actors if str(a.id) == enemy_id)
    assert target.hp - after.hp == expected_damage
    marks = tuple(e for e in game.active_combat_effects if e.kind == MIND_BREAK_WISDOM)
    assert bool(marks) == weakened
    assert not any(c.actor_id == enemy_id and c.condition == CombatCondition.NO_REACTIONS
                   for c in game.combat_state.condition_states)
    if weakened:
        assert marks[0].expiration_actor_id == 'nimra'
        assert expire_active_effects(marks, EffectEvent(EffectEventType.TURN_START, actor_id=enemy_id)).active_effects == marks
        assert not expire_active_effects(marks, EffectEvent(EffectEventType.TURN_START, actor_id='nimra')).active_effects


def test_boosted_mind_break_grants_separate_marks_after_both_saves(tmp_path):
    game, _, enemy_id = playable(tmp_path, 'nimra', ('Węzeł', 'Oko', 'Błysk', 'Kielich', 'Klucz'))
    first = next(a for a in game.combat_state.actors if str(a.id) == enemy_id)
    second = next(a for a in game.combat_state.actors if a.faction == first.faction and a.id != first.id)
    second = replace(second, position=Coordinate(first.position.col, first.position.row + 1))
    game.combat_state = replace_actor(game.combat_state, second)
    # A prior marker is consumed by the actual first save, and refreshed only after damage.
    game.active_combat_effects = (weakness(enemy_id),)
    game.encounter_rng = SequenceRng(19, 1, 1)
    game.select_combat_attack_source('nimra_mind_break')
    game.select_player_attack_target_at_position(first.position)
    game.confirm_player_attack_target()
    pay(game, 'boost', boost_id='target', count=1)
    pay(game, 'extra_target', target_id=str(second.id))
    pay(game)
    assert [s.natural_roll for s in game.pending_player_attack.saving_throws] == [1, 1]
    assert not any(e.kind == MIND_BREAK_WISDOM for e in game.active_combat_effects)
    game.submit_player_damage_roll(damage=6)
    marks = tuple(e for e in game.active_combat_effects if e.kind == MIND_BREAK_WISDOM)
    assert {e.actor_id for e in marks} == {enemy_id, str(second.id)}
    assert len(marks) == 2
    assert len(game.combat_state.shared_mana.runes.discard) == 2


def test_mind_break_damage_boost_stays_two_d6(tmp_path):
    from dnd_board_game.combat import current_actor
    game, _, enemy_id = playable(tmp_path, 'nimra', ('Węzeł', 'Oko', 'Błysk', 'Kielich', 'Klucz'))
    target = next(a for a in game.combat_state.actors if str(a.id) == enemy_id)
    game.encounter_rng = SequenceRng(1)
    game.select_combat_attack_source('nimra_mind_break')
    game.select_player_attack_target_at_position(target.position)
    game.confirm_player_attack_target()
    pay(game, 'boost', boost_id='damage', count=1)
    pay(game)
    source = game._attack_source_by_id(current_actor(game.combat_state), 'nimra_mind_break')
    effective = game._effective_attack_source(current_actor(game.combat_state), source, target)
    assert sum(c.dice.count for c in effective.damage_components if c.dice) == 2
    assert all(c.dice.sides == 6 for c in effective.damage_components if c.dice)
    game.submit_player_damage_roll(component_totals={c.id: 4 for c in effective.damage_components})
    assert len(game.combat_state.shared_mana.runes.discard) == 2
    assert any(e.kind == MIND_BREAK_WISDOM for e in game.active_combat_effects)


def test_marked_save_keeps_advantage_cancelled_even_with_exhaustion():
    target = replace(_actor('enemy', Coordinate(1, 1)), exhaustion_level=3)
    result = resolve_actor_saving_throw(target, SavingThrowRequest('wisdom', 12, 'Test'),
        natural_roll=18, roll_mode=RollMode.ADVANTAGE, active_effects=(weakness(),))
    assert result.natural_roll == 18


def test_debuff_consumes_wisdom_penalty_only_after_confirmation():
    from dnd_board_game.application import SpellDebuffFlowService
    from tests.unit.test_spell_debuff_flow import _fixture
    encounter, _, enemy, action, state = _fixture('weakening_miasma')
    action = replace(action, save_ability='wisdom')
    effects = (weakness(str(enemy.id)),)
    service = SpellDebuffFlowService()
    prepared = service.prepare(board=encounter.board, state=state, action=action, cast_level=1,
                               active_effects=effects)
    assert prepared.active_effects is None
    cancelled = service.cancel(state=state, pending=prepared.pending)
    assert cancelled.active_effects is None
    result = service.confirm(board=encounter.board, state=state, action=action,
        pending=prepared.pending, target_id=str(enemy.id), rng=SequenceRng(18, 2), active_effects=effects)
    assert result.active_effects == ()
    assert dict(result.event_payload)['save']['natural_roll'] == 2


def test_channel_turn_uses_and_consumes_the_same_wisdom_penalty():
    from dnd_board_game.actors import ActorResourcePool, FeatureGrant, FeatureSourceKind, RecoveryPeriod
    from dnd_board_game.combat.class_features import resolve_channel_turn
    from tests.unit.test_spell_debuff_flow import _fixture
    encounter, cleric, enemy, _, state = _fixture('weakening_miasma')
    cleric = replace(cleric, features=(*cleric.features, FeatureGrant('turn_undead', 'Odpędzanie', FeatureSourceKind.SCENARIO, 'test')),
        resource_pools=(*cleric.resource_pools, ActorResourcePool('channel_divinity_uses', 'Boska moc', 1, 1, RecoveryPeriod.LONG_REST)))
    enemy = replace(enemy, creature_type='undead', position=Coordinate(cleric.position.col + 1, cleric.position.row))
    state = replace_actor(replace_actor(state, cleric), enemy)
    result = resolve_channel_turn(state, action_id='turn_undead', board=encounter.board,
        saving_rolls={str(enemy.id): 18}, saving_rolls_2={str(enemy.id): 2}, active_effects=(weakness(str(enemy.id)),))
    assert result.turned_target_ids == (str(enemy.id),)
    assert result.active_effects == ()


def test_enemy_save_preview_uses_the_same_mode_without_consuming():
    from dnd_board_game.application.enemy_turn_flow import PendingEnemySavingThrow
    from dnd_board_game.ui.exploration_app import _pending_enemy_saving_throw_payload
    actor = _actor('enemy', Coordinate(1, 1))
    effects = (weakness(),)
    state = _state(actor)
    pending = PendingEnemySavingThrow('enemy', 'test', SavingThrowRequest('wisdom', 12, 'Test'))
    payload = _pending_enemy_saving_throw_payload(pending, state, effects)
    assert payload['roll_mode'] == 'disadvantage'
    assert effects == (weakness(),)
