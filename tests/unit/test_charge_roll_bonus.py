"""The live mana profile replaces proficiency, without stacking charge twice."""
from dataclasses import replace

import pytest

from dnd_board_game.actors import ability_check_roll_modifiers, saving_throw_roll_modifiers
from dnd_board_game.character_creation.physical_mana import apply_physical_mana_profile
from dnd_board_game.combat.mana_charge import charge_effects, charged_check_request
from dnd_board_game.combat.scene_interactions import attack_source_with_combat_effects
from dnd_board_game.rules import (
    D20RollRequest, D20RollKind, RollModifier, RollModifierType,
    SavingThrowRequest, ability_modifier, apply_actor_d20_traits,
)
from dnd_board_game.rules.pooled_mana import charge_roll_bonus, drain, confirm_shuffle
from dnd_board_game.rules.shared_mana import sync_pool
from dnd_board_game.scenarios.pooled_mana_catalog import hero_profile
from tests.unit.test_hero_rules_consistency import heroes
from tests.unit.test_mana_charge import pool
from tests.unit.test_physical_mana import session_for


@pytest.mark.parametrize('points,bonus', [(0,0),(5,0),(6,2),(11,2),(12,4),(20,4),(21,6),(27,6)])
def test_shared_threshold_boundaries(points: int, bonus: int) -> None:
    assert charge_roll_bonus(points) == bonus


@pytest.mark.parametrize('hero', ('garran','brakka','mira','dagna','lorian','nimra','erynd'))
def test_each_hero_live_weapon_preserves_attribute_and_damage(heroes, tmp_path, hero: str) -> None:
    from dnd_board_game.combat import current_actor
    from dnd_board_game.combat.shared_mana import synchronize_shared_effects
    s = session_for(heroes[hero], tmp_path, pooled=True)
    high = max(hero_profile(hero)['values'], key=hero_profile(hero)['values'].get)
    p = pool(hero, (high,) * 3)
    s.combat_state = replace(s.combat_state, shared_mana=sync_pool(s.combat_state.shared_mana,p))
    s.combat_state,s.active_combat_effects = synchronize_shared_effects(s.combat_state,())
    actor = current_actor(s.combat_state)
    source = next(a for a in s._attack_sources_for_actor(actor) if a.source_type.value == 'weapon')
    assert not any(m.modifier_type == RollModifierType.PROFICIENCY for m in source.attack_roll_request.modifiers)
    bare = attack_source_with_combat_effects(actor,source,())
    charge = tuple(e for e in s.active_combat_effects if e.kind == 'charge_accuracy')
    full = attack_source_with_combat_effects(actor,source,charge)
    assert sum(m.value for m in full.attack_roll_request.modifiers) == sum(m.value for m in bare.attack_roll_request.modifiers) + 6
    assert full.damage_components == bare.damage_components
    assert attack_source_with_combat_effects(actor,full,charge).attack_roll_request == full.attack_roll_request
    assert attack_source_with_combat_effects(actor,full,()).attack_roll_request == bare.attack_roll_request
    payload = s.state_payload()['combat']['shared_mana']['pool_view']
    assert next(h for h in payload['hands'] if h['hero']==hero)['roll_bonus'] == 6


def test_spell_attack_charge_stacks_with_other_bonuses_and_reset_removes_it(heroes,tmp_path) -> None:
    from dnd_board_game.combat import current_actor
    s = session_for(heroes['dagna'],tmp_path,pooled=True)
    actor = current_actor(s.combat_state)
    p = pool('dagna',('B','B','B'))
    effects = charge_effects(p,{'dagna':hero_profile('dagna')})
    source = s._attack_source_by_id(actor,'guiding_bolt')
    source = replace(source,attack_roll_request=replace(source.attack_roll_request,modifiers=(
        *source.attack_roll_request.modifiers,RollModifier('Wsparcie',2,RollModifierType.SITUATIONAL,'aid'))))
    result = attack_source_with_combat_effects(actor,source,effects)
    assert sum(m.value for m in result.attack_roll_request.modifiers) == ability_modifier(actor.ability_scores.wisdom)+6+2
    empty = charge_effects(confirm_shuffle(drain(p,'test')),{'dagna':hero_profile('dagna')})
    result = attack_source_with_combat_effects(actor,result,empty)
    assert sum(m.value for m in result.attack_roll_request.modifiers) == ability_modifier(actor.ability_scores.wisdom)+2


def test_expertise_and_tool_proficiency_removed_without_changing_legacy(heroes,tmp_path) -> None:
    legacy = heroes['mira']
    actor = apply_physical_mana_profile(legacy)
    old = ability_check_roll_modifiers(legacy,'dexterity',skill='stealth',tool='thieves_tools')
    new = ability_check_roll_modifiers(actor,'dexterity',skill='stealth',tool='thieves_tools')
    assert any(m.stacking_key == 'proficiency' for m in old)
    assert not any(m.stacking_key == 'proficiency' for m in new)
    s = session_for(actor,tmp_path,pooled=True)
    p = pool('mira',('Z','Z','Z'))
    state = replace(s.combat_state,shared_mana=sync_pool(s.combat_state.shared_mana,p))
    request = charged_check_request(state,actor,D20RollRequest(modifiers=new))
    assert sum(m.value for m in request.modifiers) == ability_modifier(actor.ability_scores.dexterity)+6
    assert charged_check_request(state,actor,request)==request
    traits = apply_actor_d20_traits(actor,request,D20RollKind.ABILITY_CHECK)
    assert sum(m.value for m in traits.modifiers)==sum(m.value for m in request.modifiers)


def test_save_combines_charge_and_color_once_and_obeys_drain(heroes) -> None:
    from dnd_board_game.combat.spells import resolve_actor_saving_throw
    actor = apply_physical_mana_profile(heroes['garran'])
    effects = charge_effects(pool('garran',('B','B','F')),{'garran':hero_profile('garran')})
    request = SavingThrowRequest('constitution',15,'test')
    result = resolve_actor_saving_throw(actor,request,natural_roll=10,active_effects=effects)
    assert result.total == 10+2+4+1  # KON, 17 charge points, black passive.
    assert sum(m.value for m in saving_throw_roll_modifiers(actor,'constitution'))==2
    assert resolve_actor_saving_throw(actor,request,natural_roll=10).total==12


def test_npc_confrontation_has_no_proficiency_or_double_charge() -> None:
    from tests.unit.test_confrontation import game,charged
    from dnd_board_game.rules.confrontation import declare
    s=charged(game(),{'garran':('B','B','B')})
    assert s.actor.test_modifier==s.actor.impact_modifier==4
    assert declare(s,6).check_modifier==10
    assert declare(s,0).check_modifier==4


def test_trap_request_uses_current_pool_on_both_sides_of_drain(heroes,tmp_path) -> None:
    from dnd_board_game.combat import current_actor
    from dnd_board_game.combat.simple_traps import SimpleTrap,trap_request,resolve_trap_check
    s=session_for(heroes['garran'],tmp_path,pooled=True)
    actor=current_actor(s.combat_state)
    p=pool('garran',('B','B','B'))
    state=replace(s.combat_state,shared_mana=sync_pool(s.combat_state.shared_mana,p))
    trap=SimpleTrap('test','Pułapka',actor.position)
    request=trap_request(actor,trap,'detect',state=state)
    base=ability_modifier(actor.ability_scores.wisdom)
    assert sum(m.value for m in request.modifiers)==base+6
    assert resolve_trap_check(state,trap,'detect',10,tools_available=True).total==10+base+6
    state=replace(state,shared_mana=sync_pool(state.shared_mana,drain(p,'test')))
    assert sum(m.value for m in trap_request(actor,trap,'detect',state=state).modifiers)==base


def test_saved_confrontation_drops_old_proficiency_without_resetting_cards() -> None:
    import json
    from types import SimpleNamespace
    from dnd_board_game.combat.scene import SceneFlags
    from dnd_board_game.ui.confrontation import KEY,read_store
    from dnd_board_game.ui.training_arena import training_hero
    from dnd_board_game.scenarios.confrontation import scene_by_id
    from tests.unit.test_confrontation import game,charged
    from dnd_board_game.rules.confrontation import declare
    state=declare(charged(game(),{'garran':('B','B','B')}),6).to_data()
    state['participants'][0]['test_modifier']+=2
    state['check_modifier']+=2
    current={'state':state,'scene':scene_by_id('nessa_raise')}
    raw=json.dumps({'version':1,'current':current,'active':True})
    session=SimpleNamespace(state=SimpleNamespace(flags=SceneFlags(((KEY,raw),))),
        exploration=SimpleNamespace(actors=tuple(training_hero(h) for h in ('garran','brakka','dagna'))))
    result=read_store(session)['current']
    assert result['roll_rules_version']==2
    assert result['state']['check_modifier']==10
    assert result['state']['participants'][0]['test_modifier']==4
    assert result['state']['mana']['pools']==json.loads(raw)['current']['state']['mana']['pools']


def test_concentration_and_its_preview_share_charge_and_color(heroes,tmp_path) -> None:
    from dnd_board_game.combat import current_actor
    from dnd_board_game.application.player_combat_resource_flow import PlayerCombatResourceFlowService,PendingConcentrationCheck
    from dnd_board_game.ui.exploration_app import _pending_concentration_check_payload
    s=session_for(heroes['garran'],tmp_path,pooled=True)
    actor=current_actor(s.combat_state)
    effects=charge_effects(pool('garran',('B','B','F')),{'garran':hero_profile('garran')})
    result=PlayerCombatResourceFlowService().resolve_concentration_check(
        state=s.combat_state,active_effects=effects,actor_id=str(actor.id),effect_ids=(),
        damage=10,dc=15,natural_roll=10)
    assert dict(result.event_payload)['total']==17
    pending=PendingConcentrationCheck(actor_id=str(actor.id),effect_ids=(),damage=10,dc=15)
    assert _pending_concentration_check_payload(pending,s.combat_state,effects)['modifier']==7


def test_shield_bash_charge_changes_contest_but_not_damage(heroes,tmp_path) -> None:
    from dnd_board_game.combat import current_actor
    from dnd_board_game.combat.garran_features import resolve_shield_bash
    from dnd_board_game.world import Coordinate
    s=session_for(heroes['garran'],tmp_path,pooled=True)
    actor=current_actor(s.combat_state)
    enemy=next(a for a in s.combat_state.actors if a.faction != actor.faction)
    enemy=replace(enemy,position=Coordinate(actor.position.col+1,actor.position.row))
    p=pool('garran',('B','B','F'))
    state=replace(s.combat_state,actors=tuple(enemy if a.id==enemy.id else a for a in s.combat_state.actors),
        shared_mana=sync_pool(s.combat_state.shared_mana,p))
    result=resolve_shield_bash(state,board=s._active_encounter().board,target_id=str(enemy.id),
        attacker_roll=10,defender_roll=1,damage_roll=3)
    assert result.attacker_total==18
    assert result.defender_total==1+ability_modifier(enemy.ability_scores.strength)
    assert result.damage.damage.total_applied==7


@pytest.mark.parametrize('bonus', (0,2,4,6))
def test_spiritual_weapon_uses_owners_charge_without_damage_bonus(heroes,bonus: int) -> None:
    from dnd_board_game.combat.summoning import summon_attack_source
    from tests.unit.test_summoning_flow import _fixture
    definition=replace(_fixture()[3].summon,id='spiritual_weapon')
    actor=apply_physical_mana_profile(heroes['dagna'])
    source=summon_attack_source(definition,actor,charge_bonus=bonus)
    base=ability_modifier(actor.ability_scores.wisdom)
    assert sum(m.value for m in source.attack_roll_request.modifiers)==base+bonus
    assert source.damage_modifier==base
