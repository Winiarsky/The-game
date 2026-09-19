"""Print footprints match playable terrain, interaction points and A4 geometry."""
from dataclasses import replace
import json
from pathlib import Path
import re
import pytest
from dnd_board_game.physical_cards.scenario_cutouts import build_cutouts, arrange, render_document, tile_svg
from dnd_board_game.scenarios.loader import load_scenario, build_encounter_from_scenario, encounter_for_party_size
from dnd_board_game.world import Coordinate
from dnd_board_game.world.movement import movement_cost
from dnd_board_game.combat.attack_positioning import evaluate_attack_positioning, evaluate_cover_from_origin

PACK=Path('content/scenarios/misja_0_dzwon')

def inputs():
    return (json.loads((PACK/'maps/cutouts.json').read_text()),json.loads((PACK/'mechanics/battle.json').read_text()))

@pytest.mark.parametrize('scale',[1,250/244])
def test_print_preserves_every_footprint_and_fits_a4_without_overlaps(scale):
    spec,battle=inputs();tokens=build_cutouts(spec,battle)
    placements=arrange(tokens,25*scale)
    assert len(tokens)==len(placements)==18
    for p in placements:
        assert p.width==pytest.approx(p.token.size[0]*25*scale)
        assert p.height==pytest.approx(p.token.size[1]*25*scale)
        assert p.x>=10 and p.x+p.width<=200
        assert p.y>=30 and p.y+p.height<=279
        for q in placements:
            if q==p or q.page!=p.page:continue
            assert p.x+p.width<=q.x or q.x+q.width<=p.x or p.y+p.height<=q.y or q.y+q.height<=p.y
    html=render_document(tokens,25*scale,scale!=1)
    assert html.count('<section>')==7
    assert len(re.findall('data-cutout=',html))==18
    for t in tokens:assert f'data-cutout="{t.id}"' in html


def test_interaction_points_match_mission_and_small_bell_marker_is_on_left_cell():
    tokens=build_cutouts(*inputs())
    points=json.loads((PACK/'flow.json').read_text())['point_positions']
    for t in tokens:
        if t.environment_id in {'armory','quarters','store','bell'}:
            key='load' if t.environment_id=='bell' else t.environment_id
            assert t.interaction==tuple(points[key])
    bell=next(t for t in tokens if t.environment_id=='bell')
    assert '<circle cx="21" cy="4"' in tile_svg(bell,25)


def test_disconnected_or_missing_terrain_is_not_silently_printed_as_rectangle():
    spec,battle=inputs()
    battle['environment'][0]['positions']=[[9,16],[11,16]]
    with pytest.raises(ValueError,match='prostokątem'):build_cutouts(spec,battle)
    spec,battle=inputs();spec['items']=spec['items'][1:]
    with pytest.raises(ValueError,match='Każdy'):build_cutouts(spec,battle)

@pytest.mark.parametrize('count',[3,4,5,6])
def test_terrain_rules_and_all_start_positions_agree_with_print(count):
    tokens=build_cutouts(*inputs())
    enc=encounter_for_party_size(build_encounter_from_scenario(load_scenario(PACK/'mechanics/battle.json')),count)
    actor=enc.actors[0]
    for a in enc.actors:assert not enc.board.terrain_at(a.position).blocks_movement
    for zone in enc.player_start_zones:
        for pos in zone:assert movement_cost(enc.board,actor,(),pos)==5
    for t in tokens:
        if not t.environment_id:continue
        for c,r in t.positions:
            cost=movement_cost(enc.board,actor,(),Coordinate(c,r))
            assert cost==({'blocking_terrain':None,'difficult_terrain':10,'cover':5}[t.kind])
    attacker=replace(actor,position=Coordinate(6,19))
    target=replace(enc.actors[1],position=Coordinate(6,18))
    source=enc.attack_sources_by_actor[actor.id]
    positioning=evaluate_attack_positioning(enc.board,attacker,target,source,(attacker,target),enc.scene_objects)
    assert positioning.cover_bonus==2
    target=replace(target,position=Coordinate(6,17))
    assert evaluate_cover_from_origin(enc.board,attacker.position,target,(target,),enc.scene_objects).cover_bonus==2
