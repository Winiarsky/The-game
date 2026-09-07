"""Physical mana does not add a card ledger or remove combat legality checks."""
from dataclasses import replace
from pathlib import Path

import pytest

from tests.unit.test_hero_rules_consistency import heroes
from tests.unit.test_exploration_ui_session import _start_gate_skirmish
from dnd_board_game.actors.resources import uses_physical_mana, can_spend_actor_resource, spend_actor_resource
from dnd_board_game.character_creation.physical_mana import apply_physical_mana_profile
from dnd_board_game.combat import current_actor, ActionUse
from dnd_board_game.combat.physical_mana import declare_series, report_wave, resolve_waves, resolve_mana_support, attack_maximum
from dnd_board_game.rules.physical_mana import hero_abilities, turn_supply
from dnd_board_game.rules import EffectEvent, EffectEventType, expire_active_effects
from dnd_board_game.ui.exploration_app import ExplorationUiSession
from dnd_board_game.world import Coordinate


def session_for(hero, tmp_path):
    session = ExplorationUiSession('content/scenarios/abandoned_watchtower.json', save_dir=tmp_path/'saves', observation_dir=tmp_path/'observations')
    session.configure_custom_party((apply_physical_mana_profile(hero),))
    _start_gate_skirmish(session)
    return session


@pytest.mark.parametrize('name,count', [('garran',8),('brakka',8),('mira',8),('dagna',10),('lorian',14),('nimra',20),('erynd',9)])
def test_profile_and_full_catalog_have_no_old_resource_gates(heroes, name, count):
    old = heroes[name]
    actor = apply_physical_mana_profile(old)
    assert actor == apply_physical_mana_profile(actor)
    assert uses_physical_mana(actor) and not uses_physical_mana(old)
    assert len(hero_abilities(name)) == count
    assert not actor.spell_slots
    assert actor.attacks_per_action == 1
    assert can_spend_actor_resource(actor, 'tactics_uses', 100)
    assert spend_actor_resource(actor, 'tactics_uses', 100).actor_after == actor
    assert turn_supply(name)['draw'] == 3
    assert turn_supply(name)['keep'] == (3 if name == 'lorian' else 2)
    assert turn_supply(name, green_surge=True)['capacity'] == (7 if name == 'lorian' else 6)


def test_wave_waits_for_boundary_caps_threat_and_expires(heroes, tmp_path):
    s = session_for(heroes['garran'], tmp_path)
    state = s.combat_state
    effects = ()
    for event in (4,4,2,6,6):
        effects = report_wave(state, effects, event)
    assert not any(e.kind == 'mana_threat' for e in effects)
    resolved = resolve_waves(state, effects)
    assert next(e.value for e in resolved if e.kind == 'mana_threat') == 3
    assert sum(e.kind == 'mana_wave_4' for e in resolved) == 1
    assert next(e.value for e in resolved if e.kind == 'mana_wave_6') == 2
    assert resolve_waves(state, resolved) == resolved
    expired = expire_active_effects(resolved, EffectEvent(EffectEventType.ROUND_ENDED)).active_effects
    assert not any(e.kind in {'mana_wave_2','mana_wave_4','mana_wave_6'} for e in expired)
    assert any(e.kind == 'mana_threat' for e in expired)
    with pytest.raises(ValueError): report_wave(state, effects, True)


def test_lorian_support_consumes_time_without_card_state(heroes, tmp_path):
    s = session_for(heroes['lorian'], tmp_path)
    actor = current_actor(s.combat_state)
    after,effects,message = resolve_mana_support(s.combat_state, (), 'mana_tuning')
    assert after.turn_action.bonus_action_use == ActionUse.ACTION_USED
    assert after.turn_action.action_use == ActionUse.ACTION_AVAILABLE
    assert current_actor(after) == actor
    assert 'niebieska' in message
    with pytest.raises(ValueError): resolve_mana_support(after, effects, 'mana_transmutation')
    with pytest.raises(ValueError): resolve_mana_support(s.combat_state, (), 'mana_transfer', str(actor.id))
    s.use_combat_class_feature('mana_tuning')
    assert s.state_payload()['combat']['physical_mana']['supply']['capacity'] == 6


def test_series_beyond_hand_capacity_resolves_separate_misses_and_targets(heroes, tmp_path):
    s = session_for(heroes['lorian'], tmp_path)
    hero = current_actor(s.combat_state)
    enemies = [a for a in s.combat_state.actors if a.faction != hero.faction]
    positions = {str(hero.id): Coordinate(3,3), str(enemies[0].id): Coordinate(3,4), str(enemies[1].id): Coordinate(4,3)}
    s.combat_state = replace(s.combat_state, actors=tuple(replace(a, position=positions.get(str(a.id), a.position)) for a in s.combat_state.actors))
    source = next(a for a in s._attack_sources_for_actor(current_actor(s.combat_state)) if 'crossbow' in (a.source_item_id or ''))
    s.select_combat_attack_source(source.id)
    s.combat_targeting_attack_source_id = source.id
    assert s.state_payload()['combat']['physical_mana']['needs_attack_count']
    for invalid in (0,-1,True,1.5):
        with pytest.raises(ValueError): declare_series(s.combat_state, (), invalid)
    s.declare_physical_attack_series(8)
    for enemy in enemies[:2]:
        s.select_player_attack_target_at_position(positions[str(enemy.id)])
        s.confirm_player_attack_target()
        s.submit_player_attack_roll(natural_roll=1, natural_roll_2=1)
    assert s.combat_state.turn_action.attacks_used == 2
    assert s.combat_state.turn_action.attacks_maximum == 8
    assert s.combat_state.turn_action.action_use == ActionUse.ACTION_USED
    with pytest.raises(ValueError): s.declare_physical_attack_series(9)
    s.save_snapshot()
    s.load_snapshot()
    assert s.combat_state.turn_action.attacks_used == 2
    assert s.state_payload()['combat']['physical_mana']['series']['declared'] == 8


def test_double_shot_has_two_independent_attacks_and_fixed_price(heroes, tmp_path):
    s = session_for(heroes['erynd'], tmp_path)
    hero = current_actor(s.combat_state)
    enemies = [a for a in s.combat_state.actors if a.faction != hero.faction]
    positions = {str(hero.id): Coordinate(3,3), str(enemies[0].id): Coordinate(3,6), str(enemies[1].id): Coordinate(5,6)}
    s.combat_state = replace(s.combat_state, actors=tuple(replace(a, position=positions.get(str(a.id),a.position)) for a in s.combat_state.actors))
    s.use_combat_class_feature('double_shot')
    assert not s.state_payload()['combat']['physical_mana']['needs_attack_count']
    for enemy in enemies[:2]:
        s.select_player_attack_target_at_position(positions[str(enemy.id)])
        s.confirm_player_attack_target()
        s.submit_player_attack_roll(natural_roll=1)
    assert s.combat_state.turn_action.attacks_used == 2
    assert s.combat_state.turn_action.attacks_maximum == 2


def test_adapted_healing_aura_and_summon_use_new_timing(heroes):
    from dnd_board_game.scenarios.loader import compile_actor_combat_content
    from dnd_board_game.combat.class_features import apply_life_domain_to_healing_source
    from dnd_board_game.combat.action_economy import ActionEconomyCost
    actor = apply_physical_mana_profile(heroes['dagna'])
    compiled = compile_actor_combat_content(actor)
    word = apply_life_domain_to_healing_source(actor, next(s for s in compiled.healing_sources if s.id == 'healing_word'))
    assert word.action_cost == ActionEconomyCost.ACTION
    assert word.healing_modifier == 7
    actions = {a.id:a for a in compiled.combat_actions}
    assert actions['spiritual_weapon'].action_cost == ActionEconomyCost.ACTION
    assert actions['spiritual_weapon'].duration_rounds == 3
    assert actions['bless'].duration_rounds == 3
    assert actions['healing_grace_aura'].bonus_modifier_ability is None


def test_weapon_activation_resumes_owner_without_free_initiative_turn(heroes, tmp_path):
    from dnd_board_game.combat.summoning import SummonedCreatureState, summon_actor, add_summoned_creature
    from dnd_board_game.combat.physical_mana_summon import activate_weapon, finish_weapon_activation
    from dnd_board_game.scenarios.loader import compile_actor_combat_content
    from dnd_board_game.actors import ActorId
    s = session_for(heroes['dagna'], tmp_path)
    owner = current_actor(s.combat_state)
    definition = next(a.summon for a in compile_actor_combat_content(owner).combat_actions if a.id == 'spiritual_weapon')
    actor = summon_actor(definition, actor_id=ActorId('summon:test'), owner=owner, position=Coordinate(4,4))
    summon = SummonedCreatureState(actor.id, owner.id, 'spiritual_weapon', definition, 'summon:test:duration')
    state = add_summoned_creature(s.combat_state, summon, actor)
    assert actor.id not in {e.actor.id for e in state.initiative_order.entries}
    active,effects = activate_weapon(state, ())
    assert current_actor(active).id == actor.id
    restored,effects = finish_weapon_activation(active,effects)
    assert current_actor(restored).id == owner.id
    assert restored.round_number == state.round_number
    assert restored.turn_action.bonus_action_use == ActionUse.ACTION_USED
    assert restored.turn_action.action_use == state.turn_action.action_use
    assert actor.id not in {e.actor.id for e in restored.initiative_order.entries}
    with pytest.raises(ValueError): activate_weapon(restored,effects)


def test_wave_affects_ac_speed_and_flat_enemy_damage_without_stacking(heroes, tmp_path):
    from dnd_board_game.combat.targets import combat_armor_class
    from dnd_board_game.combat.conditions import effective_movement_speed
    from dnd_board_game.combat.scene_interactions import attack_source_with_combat_effects
    s = session_for(heroes['garran'], tmp_path)
    actor = current_actor(s.combat_state)
    enemy = next(a for a in s.combat_state.actors if a.faction != actor.faction)
    effects = ()
    for event in (1,2,4): effects = report_wave(s.combat_state,effects,event)
    effects = resolve_waves(s.combat_state,effects)
    assert combat_armor_class(actor,effects) == combat_armor_class(actor) + 1
    assert effective_movement_speed(actor,(),effects) == max(5,effective_movement_speed(actor,())-10)
    source = s._attack_sources_for_actor(enemy)[0]
    modified = attack_source_with_combat_effects(enemy,source,effects)
    assert modified.damage_components[0].modifier == source.damage_components[0].modifier + 4
    assert len(modified.damage_components) == len(source.damage_components)
    again = attack_source_with_combat_effects(enemy,modified,effects)
    assert again.damage_components == modified.damage_components


def test_new_bonus_menu_does_not_hide_main_action_healing(heroes, tmp_path):
    s = session_for(heroes['garran'], tmp_path)
    s.use_combat_class_feature('action_surge')
    assert s.combat_state.turn_action.action_use == ActionUse.ACTION_AVAILABLE
    assert s.combat_state.turn_action.bonus_action_use == ActionUse.ACTION_USED
    ids = {o.action_id for o in s._combat_turn_action_options()}
    assert 'second_wind' in ids
    assert 'defensive_stance' not in ids
    assert 'action_surge' not in ids


def test_keyboard_preview_requests_count_and_cancel_clears_uncommitted_series(heroes, tmp_path):
    s = session_for(heroes['lorian'], tmp_path)
    hero = current_actor(s.combat_state)
    enemy = next(a for a in s.combat_state.actors if a.faction != hero.faction)
    s.combat_state = replace(s.combat_state, actors=tuple(replace(a,position=Coordinate(3,3)) if a.id == hero.id
                            else replace(a,position=Coordinate(3,4)) if a.id == enemy.id else a for a in s.combat_state.actors))
    option = next(o for o in s._combat_turn_action_options() if o.action.value == 'select_attack_source' and o.source_id and 'crossbow' in o.source_id)
    assert s.confirm_combat_turn_action(option.id)['combat']['physical_mana']['needs_attack_count']
    s.declare_physical_attack_series(3)
    assert s.state_payload()['combat']['physical_mana']['series']['remaining'] == 3
    with pytest.raises(ValueError): s.declare_physical_attack_series(4)
    s.cancel_combat_turn_action_preview()
    assert s.combat_state.turn_action.action_use == ActionUse.ACTION_AVAILABLE
    assert s.state_payload()['combat']['physical_mana']['series']['declared'] is None


def test_printable_catalog_and_mana_routes_are_readable(heroes, tmp_path):
    from dnd_board_game.ui.routes import create_app
    s = session_for(heroes['garran'], tmp_path)
    client = create_app(s).test_client()
    page = client.get('/rules/physical-mana')
    assert page.status_code == 200
    assert page.get_data(as_text=True).count('class="card"') == 77
    assert 'Inspiracja barw' in page.get_data(as_text=True)
    assert client.post('/api/combat/mana-wave', json={'event':True}).status_code == 400
    assert client.post('/api/combat/mana-wave', json={'event':2}).status_code == 200
    assert not any(e.kind == 'mana_wave_2' for e in s.active_combat_effects)
    assert any(e.kind == 'mana_wave_pending' for e in s.active_combat_effects)


@pytest.mark.parametrize('margin,prevented', [(2,True),(3,False)])
def test_physical_shield_is_three_ac_for_one_attack_without_a_slot(heroes, margin, prevented):
    from tests.unit.test_combat_reaction_flow import _state, _actor
    from dnd_board_game.actors import Faction
    from dnd_board_game.application import DefensiveSpellReactionFlowService
    from dnd_board_game.combat import (actor_as_combat_target, AttackSource, AttackSourceType, AttackDeclaration,
        resolve_attack, resolve_damage, DamageComponentInput, DamageType, apply_damage_result, replace_actor, EnemyAutoTurnResult)
    from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
    from dnd_board_game.scenarios.loader import compile_actor_combat_content
    target_actor = apply_physical_mana_profile(heroes['nimra'])
    enemy = _actor('enemy', Faction.ENEMY, Coordinate(2,2))
    state = _state(enemy,target_actor)
    target = actor_as_combat_target(target_actor)
    source = AttackSource('Atak',AttackSourceType.WEAPON,5,D20RollRequest(),damage_fixed=4)
    roll = resolve_d20_roll(D20RollInput(source.attack_roll_request,target.ac+margin))
    attack = resolve_attack(AttackDeclaration(enemy,target,source),roll,ActionUse.ACTION_AVAILABLE)
    damage = resolve_damage((DamageComponentInput(4,DamageType.SLASHING),))
    applied = apply_damage_result(target_actor,damage)
    result = EnemyAutoTurnResult(state=replace_actor(state,applied.actor_after),enemy=enemy,target=target,
             message='Trafienie',attack_roll=roll,attack_resolution=attack,damage=damage,applied_damage=applied,
             updated_target=applied.actor_after,action_used=True,source=source)
    actions = {target_actor.id:compile_actor_combat_content(target_actor).combat_actions}
    service=DefensiveSpellReactionFlowService()
    option=service.option(state=state,enemy_result=result,actions_by_actor=actions)
    assert option is not None
    resolution=service.cast(state=state,enemy_result=result,active_effects=(),option=option,actions_by_actor=actions)
    assert resolution.prevented_hit == prevented
    assert not any(e.kind == 'spell_ac_bonus' for e in resolution.active_effects)
    assert next(a for a in resolution.state.actors if a.id == target_actor.id).spell_slots == ()
