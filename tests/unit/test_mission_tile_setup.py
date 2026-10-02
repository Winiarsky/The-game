"""Whole cutouts, deliberate batches and physical accept-only setup."""
from pathlib import Path
from dataclasses import replace

import pytest

from dnd_board_game.combat.setup import SetupStep, SetupStepKind
from dnd_board_game.hardware.board_panel import panel_position
from dnd_board_game.hardware.led_palette import LedColor
from dnd_board_game.ui import mission_setup, mission_zero
from dnd_board_game.scenarios.mission_pack import read_json
from dnd_board_game.world import Coordinate
from tests.unit.test_mission_zero import PACK, session, stage, send
from dnd_board_game.physical_cards.scenario_cutouts import Cutout, tile_svg


def test_guild_rotates_existing_prints_towards_runes_without_moving_interactions() -> None:
    catalog = mission_setup.tiles(PACK)
    office, arena = catalog['G01'], catalog['G02']
    assert office.size == (5, 7) and office.board_size == (7, 5)
    assert arena.size == (5, 9) and arena.board_size == (9, 5)
    assert office.origin == (2, 5) and arena.origin == (10, 6)
    assert office.interaction == (5, 7) and arena.interaction == (14, 8)
    for tile, old_origin in ((office, (3, 4)), (arena, (12, 4))):
        assert tile.board_rotation == -90
        # Existing paper tiles retain their exact art, caption and I marker.
        old = replace(tile, origin=old_origin, board_rotation=0)
        assert tile_svg(tile, 25) == tile_svg(old, 25)
    assert not set(office.positions) & set(arena.positions)
    assert all(col < 19 for tile in (office, arena) for col, _ in tile.positions)
    specs = read_json(PACK, 'maps/setup.json')['guild_setup']
    for spec in specs[:3]:
        p = mission_setup.prepare(PACK, spec)
        tile = catalog[spec['cutout_ids'][0]]
        assert {tuple(pos) for pos in p['positions']} == set(tile.positions)
        assert p['focus_positions'] == [list(tile.interaction)]
        assert 'ku runom' in p['body']


def test_outpost_rotates_every_tile_and_preserves_existing_paper() -> None:
    catalog = mission_setup.tiles(PACK)
    previous = {
        'P01': ((9, 16), (2, 1)), 'P02': ((9, 24), (2, 1)),
        'P03': ((7, 17), (1, 1)), 'P04': ((12, 17), (1, 1)),
        'P05': ((2, 3), (6, 8)), 'P06': ((12, 3), (6, 8)),
        'P07': ((2, 13), (4, 5)), 'P08': ((6, 18), (2, 1)),
        'P09': ((12, 18), (2, 1)), 'P10': ((8, 13), (1, 1)),
        'P11': ((6, 16), (2, 1)), 'P12': ((11, 19), (3, 1)),
        'P13': ((4, 20), (1, 1)), 'P14': ((15, 16), (1, 1)),
        'P15': ((9, 12), (1, 1)),
    }
    for key, (origin, size) in previous.items():
        tile = catalog[key]
        assert tile.board_rotation == -90
        assert tile.size == size and tile.board_size == size[::-1]
        assert tile_svg(tile, 25) == tile_svg(replace(tile, origin=origin, board_rotation=0), 25)
    specs = read_json(PACK, 'maps/setup.json')['battle_setup']
    assert all('ku runom' in spec['body'] for spec in specs)


@pytest.mark.parametrize('rotation,board_cell', [(0, (1, 0)), (90, (2, 1)), (180, (0, 2)), (-90, (0, 0))])
def test_rotated_interaction_cell_maps_back_to_paper(rotation: int, board_cell: tuple[int, int]) -> None:
    tile = Cutout('test', 'Test', 'guild', (3, 4), (2, 3), 'place',
                  interaction=(3+board_cell[0], 4+board_cell[1]), board_rotation=rotation)
    assert tile.interaction_offset == (1, 0)
    assert tile.interaction in tile.positions


def test_battle_batches_cover_every_tile_once_before_figures() -> None:
    actor=SetupStep(SetupStepKind.ACTORS,'Bohater',(Coordinate(9,20),),(0,220,255),'Ustaw bohatera.')
    legacy=SetupStep(SetupStepKind.ENVIRONMENT,'Stary teren',(),(0,0,0),'Stary setup.')
    steps=mission_setup.battle_steps(PACK,(actor,legacy))
    assert len(steps)==9 and steps[-1]==actor
    assert [s.cutout_ids for s in steps[:3]]==[('P05',),('P06',),('P07',)]
    ids=[key for step in steps for key in step.cutout_ids]
    catalog=mission_setup.tiles(PACK)
    assert len(ids)==len(set(ids))==14
    assert set(ids)=={t.id for t in catalog.values() if t.environment_id}
    assert any(len(s.cutout_ids)==3 for s in steps)
    for step in steps[:-1]:
        expected={Coordinate(*p) for key in step.cutout_ids for p in catalog[key].positions}
        assert set(step.positions)==expected
        assert step.color==LedColor.SETUP_FOOTPRINT
        assert set(step.focus_positions)<=expected


def test_real_battle_accepts_each_terrain_batch_then_places_heroes(tmp_path: Path) -> None:
    s=session(tmp_path)
    stage(s,'arrival')
    send(s,'battle')
    specs=read_json(PACK,'maps/setup.json')['battle_setup']
    for spec in specs:
        flow=s.encounter_setup_flow
        step=flow.current_step
        assert list(step.cutout_ids)==spec['cutout_ids']
        payload=s.state_payload()['encounter_setup']['current_step']
        assert [t['id'] for t in payload['tiles']]==spec['cutout_ids']
        assert flow.can_confirm
        # Physical selection is confirmation, never any of the footprint cells.
        target=s._current_board_scan_target()
        assert target.positions == ((panel_position(28), panel_position(29))
                                    if flow.can_back else (panel_position(28),))
        s.confirm_encounter_setup_step()
    assert s.encounter_setup_flow.is_player_start_step
    assert not s.encounter_setup_flow.current_step.cutout_ids
    assert mission_zero.read(s)['stage']=='battle'


@pytest.mark.parametrize('setup_stage', ['guild_setup', 'post_setup'])
def test_mission_setup_back_keeps_rewards_and_reopens_previous_tile(tmp_path: Path, setup_stage: str) -> None:
    s = session(tmp_path)
    stage(s, setup_stage, index=0)
    before = (s.exploration.actors, s.state.party_loot)
    assert not any(c['action'] == 'setup_back' for c in mission_zero.payload(s)['choices'])
    with pytest.raises(ValueError):
        send(s, 'setup_back')
    send(s, 'next')
    # The first post-battle instruction places the fixed party marker. Going
    # back reopens that instruction; it does not move the marker elsewhere.
    position_before_back = s.state.party_position
    previous = mission_zero.read(s)['revision']
    p = mission_zero.select_position(s, panel_position(29))['mission']
    assert mission_zero.read(s)['index'] == 0
    expected = read_json(PACK, 'maps/setup.json')[setup_stage][0]
    assert p['setup']['title'] == expected['title']
    assert p['setup'].get('cutout_ids', []) == expected.get('cutout_ids', [])
    assert (s.exploration.actors, s.state.party_loot) == before
    assert s.state.party_position == position_before_back
    with pytest.raises(ValueError, match='Nieaktualny'):
        mission_zero.command(s, dict(action='next', revision=previous))
