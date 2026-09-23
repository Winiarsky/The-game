"""The new paper/controller contract must fit real slots and match the playable interface."""
from collections import Counter
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from dnd_board_game.physical_cards.rune_prototype import (
    ACTION_MM, EQUIPMENT_MM, PANEL_SYMBOLS, PRINT_SCALE, board_svg,
    map_tile_svg, map_tiles, rune_slot,
)
from dnd_board_game.ui.board_panel_symbols import SYMBOLS as LIVE_SYMBOLS

ROOT = Path(__file__).resolve().parents[2]


def test_new_panel_layout_has_both_gaps_and_matches_the_live_contract() -> None:
    assert len(PANEL_SYMBOLS) == 30
    assert [n for n,_ in PANEL_SYMBOLS[:4]] == ['Ruch','Atak','Przedmiot','Koniec tury']
    assert [i for i,(_,p) in enumerate(PANEL_SYMBOLS) if not p] == [4,25]
    assert [n for n,_ in PANEL_SYMBOLS[26:]] == ['Zwiększ','Zmniejsz','Zatwierdź','Wróć']
    assert 'Zmiana broni' not in [n for n,_ in PANEL_SYMBOLS]
    assert tuple(LIVE_SYMBOLS) == PANEL_SYMBOLS
    assert LIVE_SYMBOLS[5][0] == PANEL_SYMBOLS[5][0] == 'Rozwidlenie'


def test_enlarged_tiles_cover_all_cells_once_with_printable_cut_marks() -> None:
    counts = Counter()
    for tile in map_tiles():
        counts.update((x,y) for x in range(tile.x,tile.x+tile.width,25)
                      for y in range(tile.y,tile.y+tile.height,25))
        assert 10-4*PRINT_SCALE >= 5
        assert 15-4*PRINT_SCALE >= 5
        assert 10+(tile.width+tile.right+4)*PRINT_SCALE <= 292
        assert 15+(tile.height+tile.bottom+4)*PRINT_SCALE <= 205
        root = ET.fromstring(map_tile_svg(tile))
        assert root.attrib['width'] == '297mm'
        layer = root.find('{http://www.w3.org/2000/svg}g')
        assert float(layer.attrib['data-print-scale']) == pytest.approx((250/244)*1.03)
    assert counts == Counter({(x,y):1 for x in range(0,750,25) for y in range(0,500,25)})
    assert len(map_tiles()) == 12


def test_printed_glyphs_use_the_same_fixed_slots_as_the_mockup_data() -> None:
    root = ET.fromstring('<svg>'+board_svg()+'</svg>')
    glyphs = [g for g in root.iter() if 'data-panel-slot' in g.attrib]
    assert len(glyphs) == 28
    for g in glyphs:
        i = int(g.attrib['data-panel-slot'])
        assert g.find('path').attrib['d'] == PANEL_SYMBOLS[i][1]
        assert float(g.attrib['x']) == 25*i+5


def test_all_seven_modular_sets_fit_twelve_replaceable_ability_slots() -> None:
    cards = json.loads((ROOT/'content/print/runes_v01/action_cards.json').read_text())
    assert set(cards) == {'garran','brakka','mira','dagna','lorian','nimra','erynd'}
    for key, entries in cards.items():
        assert 1 <= len(entries) <= 12
        assert len({c['slot'] for c in entries}) == len(entries)
        assert len({c['id'] for c in entries}) == len(entries)
        for card in entries:
            assert card['slot'] != rune_slot('Gwiazda')
            assert 5 <= card['slot'] < 24
            assert card['rune'] != 'Gwiazda'
            assert card['rune'] == PANEL_SYMBOLS[card['slot']][0]
            assert len(card['boosts']) <= 3
            assert card['status'] in {'prototype', 'ready'}
            assert card['description']
            assert card['budget'] in {'S', 'M+S', 'A+S', 'M+A+S', 'R'}
    assert ACTION_MM == (60,54)
    assert EQUIPMENT_MM == (60,42)


def test_exported_mockup_and_paper_share_card_costs_and_panel_positions() -> None:
    path = ROOT/'docs/ui/rune-prototype-data.js'
    raw = path.read_text().split('window.RUNE_DATA = ',1)[1].removesuffix(';\n')
    data = json.loads(raw)
    source = json.loads((ROOT/'content/print/runes_v01/action_cards.json').read_text())
    assert [(p['name'],p['path']) for p in data['panel']] == list(PANEL_SYMBOLS)
    assert {h['id']:h['cards'] for h in data['heroes']} == source
    assert 'Gwiazda' not in data['resourceRunes']
    assert 'Klucz' in data['resourceRunes']
    from dnd_board_game.rules.runes import RESOURCE_RUNES
    assert tuple(data['resourceRunes']) == RESOURCE_RUNES
    bastion = next(c for c in source['garran'] if c['id'] == 'iron_bastion')
    assert bastion['rune'] == 'Klucz' and bastion['slot'] == 23
    for hero in data['heroes']:
        from dnd_board_game.scenarios.rune_traits import rune_flaw
        flaw = rune_flaw(hero['id'])
        assert hero['flaw'] == [flaw.name, flaw.body]
        assert (ROOT/'docs/ui'/hero['portrait']).is_file()
        from dnd_board_game.character_creation.runes import apply_rune_profile
        from dnd_board_game.ui.training_arena import training_hero
        actor = apply_rune_profile(training_hero(hero['id']))
        assert {i['id'] for i in hero['equipment']} == {i.id for i in actor.inventory}
        assert sum(i.kind == 'weapon' for i in actor.inventory) == 1
