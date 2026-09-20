"""Distinct combat passives affect actual attacks, damage, recipients and movement."""
from dataclasses import replace
import pytest
from dnd_board_game.combat.mana_charge import charge_effects, picked_color, damage_bonus
from dnd_board_game.scenarios.pooled_mana_catalog import hero_profile, load_catalog
from dnd_board_game.actors.mana_passives import apply_color_features
from dnd_board_game.combat.damage import apply_damage_result, resolve_damage, DamageComponentInput
from dnd_board_game.core.damage_types import DamageType
from dnd_board_game.world import Coordinate
from tests.unit.test_mana_charge import pool
from tests.unit.test_hero_rules_consistency import heroes
from tests.unit.test_physical_mana import session_for
from tests.unit.test_pooled_mana_runtime import prepare


def effects(hero, hand, actors=()):
    return charge_effects(pool(hero,hand), {hero:hero_profile(hero)}, actors)


def test_combat_passives_have_distinct_names_and_rule_combinations():
    items=[v for p in load_catalog()['heroes'].values() for v in p['color_passives'].values()]
    assert len(items)==35
    assert len({v['display']['name'] for v in items})==35
    assert len({(v['kind'],tuple(v.get('features',()))) for v in items})==35


def test_brakka_last_anger_requires_wounds_and_melee_weapon(heroes,tmp_path):
    actor=heroes['brakka']; s=session_for(actor,tmp_path,pooled=True)
    source=next(x for x in s._attack_sources_for_actor(actor) if x.source_type.value=='weapon' and x.attack_kind.value=='melee')
    statuses=effects('brakka',('N','N'))
    assert damage_bonus(actor,source,statuses)==0
    wounded=replace(actor,hp=actor.max_hp//2)
    assert damage_bonus(wounded,source,statuses)==2
    assert damage_bonus(wounded,source,())==0


def test_nimra_full_pool_means_six_physical_cards_and_blue_stacks(heroes,tmp_path):
    actor=heroes['nimra'];s=session_for(actor,tmp_path,pooled=True)
    source=s._attack_source_by_id(actor,'nimra_frost_pulse')
    assert damage_bonus(actor,source,effects('nimra',('N','N','N','C')))==3
    assert damage_bonus(actor,source,effects('nimra',('N','N','N','C','B','F')))==6
    assert damage_bonus(actor,source,())==0


def test_dagna_sacred_ember_only_adds_to_radiant_spell_damage(heroes,tmp_path):
    actor=heroes['dagna'];s=session_for(actor,tmp_path,pooled=True)
    spells=[x for x in s._attack_sources_for_actor(actor) if x.source_type.value=='spell' and x.damage_components]
    radiant=next(x for x in spells if x.damage_components[0].damage_type==DamageType.RADIANT)
    statuses=effects('dagna',('C','C','C','C'))
    assert damage_bonus(actor,radiant,statuses)==3
    other=replace(radiant,damage_type='fire',damage_components=(replace(radiant.damage_components[0],damage_type=DamageType.FIRE),))
    assert damage_bonus(actor,other,statuses)==0


def test_lorian_protects_only_closest_conscious_ally_within_ten_feet(heroes):
    from dnd_board_game.combat.targets import combat_armor_class
    from dnd_board_game.inventory import effective_armor_class
    lorian=replace(heroes['lorian'],position=Coordinate(2,2))
    close=replace(heroes['garran'],position=Coordinate(3,2))
    far=replace(heroes['brakka'],position=Coordinate(4,2))
    statuses=effects('lorian',('B','B'),(lorian,far,close))
    for actor,bonus in ((lorian,0),(close,1),(far,0)):
        assert combat_armor_class(actor,statuses)==effective_armor_class(actor)+bonus
    moved=replace(close,position=Coordinate(9,9))
    statuses=effects('lorian',('B',),(lorian,far,moved))
    assert combat_armor_class(far,statuses)==effective_armor_class(far)+1
    assert not any(e.kind=='charge_ac' for e in effects('lorian',('B',),(lorian,moved)))
    assert not any(e.kind=='charge_ac' for e in effects('lorian',('B',),(replace(lorian,hp=0),close)))


@pytest.mark.parametrize('kind,expected', [(DamageType.FIRE,4),(DamageType.COLD,4),(DamageType.LIGHTNING,4),(DamageType.SLASHING,9)])
def test_nimra_ward_reduces_actual_damage_without_double_resistance(heroes,kind,expected):
    actor=heroes['nimra'];damage=resolve_damage((DamageComponentInput(9,kind),))
    statuses=effects('nimra',('B','B'))
    assert apply_damage_result(actor,damage,active_effects=statuses).damage.total_applied==expected
    if expected==4:
        actor=replace(actor,damage_affinities=replace(actor.damage_affinities,resistances=(kind,)))
        assert apply_damage_result(actor,damage,active_effects=statuses).damage.total_applied==4
    assert apply_damage_result(heroes['nimra'],damage).damage.total_applied==9


def test_nimra_pick_grants_temp_hp_once_without_healing_or_stacking(heroes,tmp_path):
    actor=replace(heroes['nimra'],hp=5)
    s=session_for(actor,tmp_path,pooled=True)
    prepare(s,'Z','C')
    assert s._actor_by_string_id('nimra').temp_hp==4
    s.state_payload();s.state_payload()
    changed=s._actor_by_string_id('nimra')
    assert changed.hp==5 and changed.temp_hp==4
    passive=hero_profile('nimra')['color_passives']['Z']
    assert picked_color((replace(actor,temp_hp=7),),'nimra',passive)[0].temp_hp==7
    assert picked_color((replace(actor,temp_hp=2),),'nimra',passive)[0].temp_hp==4


def test_erynd_pathfinder_changes_terrain_cost_but_not_occupied_tile(heroes):
    from dnd_board_game.world.board_state import BoardState
    from dnd_board_game.world.terrain import DIFFICULT_TERRAIN
    from dnd_board_game.world.movement import movement_cost
    board=BoardState();tile=Coordinate(1,0);board.set_terrain(tile,DIFFICULT_TERRAIN)
    from dnd_board_game.character_creation.physical_mana import apply_physical_mana_profile
    actor=apply_physical_mana_profile(heroes['erynd']);profile=hero_profile('erynd')['color_passives']
    plain=apply_color_features(actor,(),profile);active=apply_color_features(actor,('B',),profile)
    assert movement_cost(board,plain,(plain,),tile)==10
    assert movement_cost(board,active,(active,),tile)==5
    ally=replace(heroes['garran'],position=tile)
    assert movement_cost(board,active,(active,ally),tile)==10
    assert movement_cost(board,apply_color_features(active,(),profile),(),tile)==10
