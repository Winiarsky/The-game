"""Color passives reach native combat rules and disappear on drain/save recovery."""
from dataclasses import replace

import pytest

from dnd_board_game.actors import Actor, ActorId, Faction, actor_has_feature
from dnd_board_game.actors.mana_passives import SOURCE, RETIRED, apply_color_features, normalize_mana_passives, reset_mana_passives
from dnd_board_game.character_creation import PLAYABLE_HERO_IDS
from dnd_board_game.character_creation.physical_mana import apply_physical_mana_profile
from dnd_board_game.combat.targets import iron_line_armor_class_bonus
from dnd_board_game.combat.shared_mana import synchronize_shared_effects, expire_deck_effects
from dnd_board_game.core.damage_types import DamageType
from dnd_board_game.inventory import effective_armor_class
from dnd_board_game.rules import D20RollKind, D20RollRequest, RollMode
from dnd_board_game.rules.d20_traits import apply_actor_d20_traits, actor_is_immune_to_effect
from dnd_board_game.rules.pooled_mana import new_mana, drain
from dnd_board_game.rules.shared_mana import sync_pool
from dnd_board_game.scenarios.pooled_mana_catalog import hero_profile
from dnd_board_game.ui.training_arena import training_hero
from dnd_board_game.world import Coordinate


def charged(hero: str, *colors: str) -> Actor:
    return apply_color_features(training_hero(hero), colors, hero_profile(hero)['color_passives'])


@pytest.mark.parametrize('hero', PLAYABLE_HERO_IDS)
def test_no_innate_bonus_and_repeated_color_does_not_stack_features(hero: str) -> None:
    base = training_hero(hero)
    assert not RETIRED.intersection(f.feature_id for f in base.features)
    assert base == apply_physical_mana_profile(base)
    assert base == normalize_mana_passives(base)
    for color in ('C','B','Z','F','N'):
        one, two = charged(hero, color), charged(hero, color, color)
        assert one == two
        assert normalize_mana_passives(one) == base
    assert any(f.feature_id.startswith('flaw_') for f in base.features)


def test_garran_white_armor_and_iron_line_only_protect_the_flanking_ally() -> None:
    garran = replace(charged('garran','B'), position=Coordinate(1,2))
    base = normalize_mana_passives(garran)
    ally = replace(training_hero('dagna'), position=Coordinate(3,2))
    enemy = Actor(ActorId('enemy'), 'Wróg', 12, 30, 0, 30, Coordinate(2,2), Faction.ENEMY)
    assert effective_armor_class(garran) == effective_armor_class(base)
    assert iron_line_armor_class_bonus(enemy, ally, (garran, ally, enemy)) == 1
    assert iron_line_armor_class_bonus(enemy, ally, (base, ally, enemy)) == 0
    assert iron_line_armor_class_bonus(enemy, garran, (garran, ally, enemy)) == 0


def test_garran_natural_19_becomes_critical_only_with_green() -> None:
    from dnd_board_game.combat.attack_flow import AttackDeclaration, resolve_attack
    from dnd_board_game.combat import ActionUse, actor_as_combat_target
    from dnd_board_game.scenarios.loader import compile_actor_combat_content
    from dnd_board_game.rules import D20RollInput, resolve_d20_roll
    enemy = Actor(ActorId('enemy'), 'Wróg', 12, 30, 0, 30, Coordinate(1,0), Faction.ENEMY)
    for colors, critical in [((),False),(('B',),False),(('Z',),True),(('Z','Z'),True)]:
        actor = charged('garran',*colors)
        source = next(s for s in compile_actor_combat_content(actor).attack_sources if s.source_item_id == 'longsword')
        declaration=AttackDeclaration(actor,actor_as_combat_target(enemy),source)
        roll=resolve_d20_roll(D20RollInput(source.attack_roll_request,19))
        assert resolve_attack(declaration,roll,ActionUse.ACTION_AVAILABLE).critical is critical


def test_mira_hidden_and_flanking_damage_requires_red() -> None:
    from tests.unit.test_mira_features import _state
    from dnd_board_game.combat import plan_sneak_attack, attack_source_with_hidden_advantage
    from dnd_board_game.scenarios.loader import compile_actor_combat_content
    from dnd_board_game.rules import RollModifier, RollModifierType
    enemy=Actor(ActorId('enemy'),'Wróg',12,30,0,30,Coordinate(1,0),Faction.ENEMY)
    for colors, count in [((),0),(('C',),1),(('Z',),2),(('C','Z'),3),(('C','C','Z'),3)]:
        actor=charged('mira',*colors)
        source=next(s for s in compile_actor_combat_content(actor).attack_sources if s.source_item_id=='rapier')
        source=attack_source_with_hidden_advantage(source,True)
        source=replace(source,attack_roll_request=replace(source.attack_roll_request,modifiers=(
            *source.attack_roll_request.modifiers,RollModifier('Flanka',0,RollModifierType.CUSTOM,'flanking_advantage'))))
        state=replace(_state(actor,enemy),actors=(actor,enemy))
        plan=plan_sneak_attack(state=state,active_effects=(),attacker=actor,target=enemy,
                               source=source,roll_mode=source.attack_roll_request.mode)
        assert plan.eligible == bool(count)
        if count:
            assert next(c.dice.count for c in plan.source.damage_components if c.id=='sneak_attack') == count


def test_brakka_survival_returns_only_after_drain_and_reunlock() -> None:
    from dnd_board_game.combat import DamageComponentInput, apply_damage, resolve_damage
    base=replace(charged('brakka'),hp=2)
    active=replace(charged('brakka','F'),hp=2)
    hit=resolve_damage((DamageComponentInput(3,DamageType.SLASHING),))
    assert apply_damage(base,hit).hp == 0
    saved=apply_damage(active,hit)
    assert saved.hp == 1
    unlocked=apply_color_features(normalize_mana_passives(saved),('F',),hero_profile('brakka')['color_passives'])
    assert apply_damage(unlocked,hit).hp == 0
    drained = reset_mana_passives(saved)
    assert apply_damage(drained,hit).hp == 0
    unlocked = apply_color_features(drained,('F',),hero_profile('brakka')['color_passives'])
    assert apply_damage(unlocked,hit).hp == 1


def test_brakka_armor_and_nimra_magic_save_are_color_dependent() -> None:
    assert effective_armor_class(charged('brakka','B')) == 14
    assert effective_armor_class(charged('brakka')) == 11
    request = D20RollRequest(ability='intelligence')
    assert apply_actor_d20_traits(charged('nimra'), request, D20RollKind.SAVING_THROW,
                                 effect_tags=('magic',)).mode == RollMode.NORMAL
    assert apply_actor_d20_traits(charged('nimra','F'), request, D20RollKind.SAVING_THROW,
                                 effect_tags=('magic',)).mode == RollMode.ADVANTAGE
    assert apply_actor_d20_traits(charged('nimra','F'), request, D20RollKind.SAVING_THROW).mode == RollMode.NORMAL


def test_mira_luck_dagna_poison_and_lorian_sleep_are_no_longer_innate() -> None:
    for colors, enabled in [((),False),(('N',),True)]:
        assert apply_actor_d20_traits(charged('mira',*colors),D20RollRequest(),D20RollKind.ATTACK).reroll_natural_ones is enabled
        assert actor_is_immune_to_effect(charged('lorian',*colors),'magical_sleep') is enabled
    assert DamageType.POISON not in charged('dagna').damage_affinities.resistances
    assert DamageType.POISON in charged('dagna','F').damage_affinities.resistances
    assert charged('dagna').max_hp == 27


def test_erynd_archery_changes_actual_attack_and_first_blood_needs_red() -> None:
    from dnd_board_game.scenarios.loader import compile_actor_combat_content
    from dnd_board_game.combat.attack_flow import attack_source_for_actor
    from dnd_board_game.combat.erynd_features import first_blood_damage
    base, blue = charged('erynd'), charged('erynd','N')
    source = next(s for s in compile_actor_combat_content(base).attack_sources if s.source_item_id == 'longbow')
    before = attack_source_for_actor(source, base)
    after = attack_source_for_actor(source, blue)
    assert sum(m.value for m in after.attack_roll_request.modifiers) == sum(m.value for m in before.attack_roll_request.modifiers) + 2
    enemy = Actor(ActorId('enemy'), 'Wróg', 12, 30, 0, 30, Coordinate(2,2), Faction.ENEMY)
    assert first_blood_damage(base,enemy,DamageType.PIERCING) is None
    assert first_blood_damage(charged('erynd','C'),enemy,DamageType.PIERCING).dice.count == 1


def test_runtime_sync_drain_and_reload_restore_only_colors_in_saved_pool(tmp_path) -> None:
    from tests.unit.test_physical_mana import session_for
    s = session_for(training_hero('garran'), tmp_path, pooled=True)
    p = new_mana(('garran',), 'garran', values={'garran':hero_profile('garran')['values']})
    p = replace(p, phase='ready', deck=(None,)*23, pools=(('garran',('B','Z')),), draw_due=False)
    s.combat_state=replace(s.combat_state, shared_mana=sync_pool(s.combat_state.shared_mana,p))
    s.combat_state,s.active_combat_effects=synchronize_shared_effects(s.combat_state,())
    a=s._actor_by_string_id('garran')
    assert actor_has_feature(a,'iron_line') and actor_has_feature(a,'improved_critical')
    assert any(e.kind=='charge_feature' and 'Ulepszony krytyk' in e.label for e in s.active_combat_effects)
    expired,_=expire_deck_effects(s.combat_state,s.active_combat_effects)
    assert not any(f.source_ref==SOURCE for a in expired.actors for f in a.features)
    s.save_snapshot()
    s.load_snapshot()
    assert actor_has_feature(s._actor_by_string_id('garran'),'improved_critical')
    p=s.combat_state.shared_mana.pooled
    s.combat_state=replace(s.combat_state,shared_mana=sync_pool(s.combat_state.shared_mana,drain(p,'test')))
    s.state_payload()
    assert not actor_has_feature(s._actor_by_string_id('garran'),'improved_critical')
    assert not any(e.kind.startswith('charge_') for e in s.active_combat_effects)


def test_exploration_has_no_hidden_free_lorian_or_erynd_bonus() -> None:
    from dnd_board_game.application.exploration_mana_flow import method_modifiers
    from dnd_board_game.rules.exploration_mana_catalog import hero_methods
    for hero in ('lorian','erynd'):
        for method in hero_methods(hero):
            assert len(method_modifiers(training_hero(hero),method)) == 1


def test_garran_blue_protects_self_white_only_ally_and_borders_match_stacking() -> None:
    from dnd_board_game.combat.targets import combat_armor_class
    from dnd_board_game.combat.mana_charge import charge_effects
    from tests.unit.test_mana_charge import pool
    from dnd_board_game.physical_cards.mana_print import build_print_hero
    from dnd_board_game.physical_cards.mana_print_html import render_hero_html
    base = charged('garran')
    for colors, expected in [(('B',),0),(('N',),1),(('N','N'),1),(('B','N'),1)]:
        p=pool('garran',colors)
        effects=charge_effects(p,{'garran':hero_profile('garran')})
        assert combat_armor_class(base,effects)==effective_armor_class(base)+expected
    hero=build_print_hero('garran')
    assert hero.stacking_mana_colors==('C','F')
    assert hero.stacking_exploration_colors==('C',)
    html=render_hero_html(hero,'bw_test')
    assert 'data-stackable="true"' in html and 'data-stackable="false"' in html


def test_mira_passives_ignore_spent_turn_markers_and_work_outside_own_turn() -> None:
    from tests.unit.test_mira_features import _state
    from dnd_board_game.combat import plan_sneak_attack, commit_sneak_attack_hit
    from dnd_board_game.scenarios.loader import compile_actor_combat_content
    from dnd_board_game.rules import RollModifier, RollModifierType
    actor=charged('mira','Z')
    enemy=Actor(ActorId('enemy'),'Wróg',12,30,0,30,Coordinate(1,0),Faction.ENEMY)
    state=replace(_state(enemy,actor),actors=(enemy,actor))
    source=next(s for s in compile_actor_combat_content(actor).attack_sources if s.source_item_id=='rapier')
    source=replace(source,attack_roll_request=replace(source.attack_roll_request,modifiers=(RollModifier('Flanka',0,RollModifierType.CUSTOM,'flanking_advantage'),)))
    for _ in range(2):
        plan=plan_sneak_attack(state=state,active_effects=commit_sneak_attack_hit((),'mira'),attacker=actor,target=enemy,source=source,roll_mode=RollMode.DISADVANTAGE)
        assert plan.eligible
        assert next(c for c in plan.source.damage_components if c.id=='sneak_attack').dice.count==2


def test_erynd_volley_applies_one_bonus_to_each_fresh_target_without_duplicate_dice() -> None:
    from tests.unit.test_mira_features import _state
    from dnd_board_game.combat.shared_volley import VolleyHit, volley_bonuses, volley_damage_specs
    from dnd_board_game.combat.erynd_features import commit_first_blood_hit
    from dnd_board_game.scenarios.loader import compile_actor_combat_content
    actor=charged('erynd','C')
    targets=tuple(Actor(ActorId(f'e{i}'),'Wróg',12,30 if i!=2 else 29,0,30,Coordinate(i+2,0),Faction.ENEMY,max_hp=30) for i in range(4))
    state=replace(_state(actor,*targets),actors=(actor,*targets))
    source=next(s for s in compile_actor_combat_content(actor).attack_sources if s.source_item_id=='longbow')
    hits=tuple(VolleyHit(str(a.id),12,0,i!=3,False) for i,a in enumerate(targets))
    bonuses=volley_bonuses(state,source,hits,commit_first_blood_hit((),'erynd'))
    assert [(c.id,t) for c,t in bonuses]==[('first_blood','e0'),('first_blood','e1')]
    assert [c.id for c in volley_damage_specs(source,bonuses)].count('first_blood')==1


def test_brakka_used_status_survives_save_and_real_drain_renews_it(tmp_path) -> None:
    from tests.unit.test_physical_mana import session_for
    from tests.unit.test_pooled_mana_runtime import send
    from tests.unit.test_mana_charge import pool
    from dnd_board_game.combat import DamageComponentInput, apply_damage, resolve_damage
    from dnd_board_game.actors.mana_passives import color_passive_status
    s=session_for(training_hero('brakka'),tmp_path,pooled=True)
    p=pool('brakka',('F',))
    s.combat_state=replace(s.combat_state,shared_mana=sync_pool(s.combat_state.shared_mana,p))
    s.state_payload()
    a=s._actor_by_string_id('brakka')
    used=apply_damage(replace(a,hp=2),resolve_damage((DamageComponentInput(3,DamageType.SLASHING),)))
    s.combat_state=replace(s.combat_state,actors=tuple(used if a.id==used.id else a for a in s.combat_state.actors))
    assert used.hp==1
    s.save_snapshot();s.load_snapshot()
    view=s.state_payload()['combat']['shared_mana']['pool_view']
    assert 'Zużyte' in view['hands'][0]['color_passives']['F']['status']
    assert any('Zużyte' in e.label for e in s.active_combat_effects)
    s.combat_state=replace(s.combat_state,shared_mana=sync_pool(s.combat_state.shared_mana,drain(s.combat_state.shared_mana.pooled,'test')))
    s.state_payload();send(s,'pool_shuffle')
    restored=s._actor_by_string_id('brakka')
    assert 'Gotowe' in color_passive_status(restored,hero_profile('brakka')['color_passives']['F'])
    assert not actor_has_feature(restored,'relentless_endurance')


def test_mira_reaction_keeps_hidden_and_flank_dice_between_roll_and_damage() -> None:
    from tests.unit.test_mira_features import _state
    from dnd_board_game.application.combat_reaction_flow import PlayerReactionFlowService
    from dnd_board_game.combat.stealth import HiddenState
    from dnd_board_game.scenarios.loader import compile_actor_combat_content
    from dnd_board_game.world import BoardState
    actor=replace(charged('mira','C','Z'),position=Coordinate(1,2))
    ally=replace(charged('garran'),position=Coordinate(3,2))
    enemy=Actor(ActorId('enemy'),'Wróg',12,50,0,30,Coordinate(2,2),Faction.ENEMY)
    state=replace(_state(enemy,actor,ally),actors=(enemy,actor,ally),hidden_states=(HiddenState(actor_id='mira',hidden_from_actor_ids=('enemy',),stealth_total=20),))
    source=next(s for s in compile_actor_combat_content(actor).attack_sources if s.source_item_id=='rapier')
    sources={actor.id:source}; service=PlayerReactionFlowService()
    result=service.resolve_attack_roll(state=state,attacker_id='mira',target_id='enemy',attack_sources_by_actor=sources,active_effects=(),natural_roll=15,natural_roll_2=15,board=BoardState())
    bonus=next(c for c in result.source.damage_components if c.id=='sneak_attack')
    assert bonus.dice.count==3 and result.hit
    assert not result.state.hidden_states
    damage=service.apply_damage(state=result.state,attacker_id='mira',target_id='enemy',attack_sources_by_actor=sources,active_effects=result.active_effects,component_totals={source.damage_components[0].id:1,'sneak_attack':6})
    assert damage.applied_damage.applied_to_hp==1+source.damage_components[0].modifier+6
    assert not any(e.kind=='saturation_reaction_damage' for e in damage.active_effects)


def test_mira_damage_resolution_applies_flank_bonus_on_each_hit_in_same_turn() -> None:
    from tests.unit.test_mira_features import _state
    from dnd_board_game.application.player_combat_action_flow import PlayerCombatActionFlowService, PendingPlayerAttack
    from dnd_board_game.scenarios.loader import compile_actor_combat_content
    from dnd_board_game.world import BoardState
    actor=replace(charged('mira','Z'),position=Coordinate(1,2))
    ally=replace(charged('garran'),position=Coordinate(3,2))
    enemy=Actor(ActorId('enemy'),'Wróg',12,100,0,30,Coordinate(2,2),Faction.ENEMY)
    state=replace(_state(actor,enemy,ally),actors=(actor,enemy,ally))
    source=next(s for s in compile_actor_combat_content(actor).attack_sources if s.source_item_id=='rapier')
    service=PlayerCombatActionFlowService();effects=()
    initial_turn=state.turn_action
    for _ in range(2):
        state=replace(state,turn_action=initial_turn)
        rolled=service.submit_attack_roll(state=state,board=BoardState(),source=source,pending=PendingPlayerAttack('mira','enemy',source.id,'attack_roll'),active_effects=effects,natural_roll=15,natural_roll_2=15)
        assert rolled.pending.sneak_attack_dice==2
        before=next(a for a in rolled.state.actors if str(a.id)=='enemy').hp
        resolved=service.submit_damage(state=rolled.state,source=source,pending=rolled.pending,active_effects=rolled.active_effects,component_totals={source.damage_components[0].id:1,'sneak_attack':4})
        state,effects=resolved.state,resolved.active_effects
        after=next(a for a in state.actors if str(a.id)=='enemy').hp
        assert before-after==1+source.damage_components[0].modifier+4
        assert not any(e.kind=='sneak_attack_used' for e in effects)


def test_dagna_and_mira_steps_have_no_once_per_turn_marker(tmp_path) -> None:
    from tests.unit.test_physical_mana import session_for
    from dnd_board_game.combat.shared_mana_passives import apply_hit_passive
    from dnd_board_game.scenarios.loader import compile_actor_combat_content
    s=session_for(training_hero('dagna'),tmp_path,pooled=True)
    dagna=replace(charged('dagna','N'),position=Coordinate(2,2))
    ally=replace(charged('garran'),position=Coordinate(3,2),hp=5)
    before=replace(s.combat_state,actors=(dagna,ally))
    for hp in (6,7):
        s.combat_state=replace(before,actors=(dagna,replace(ally,hp=hp)))
        s._offer_field_medic_step(healer_id='dagna',target_ids=('garran',),state_before=before)
        assert s.pending_magic_movement is not None
        assert not any(e.kind=='field_medic_step_used' for e in s.active_combat_effects)
        s.pending_magic_movement=None
    mira=charged('mira','F')
    from tests.unit.test_mira_features import _state
    state=replace(_state(mira),actors=(mira,))
    knife=next(a for a in compile_actor_combat_content(mira).attack_sources if a.source_item_id=='throwing_knife')
    for _ in range(2):
        state,effects,offered=apply_hit_passive(state,(),knife)
        assert offered and not effects
