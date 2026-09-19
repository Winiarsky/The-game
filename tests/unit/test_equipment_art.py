"""Equipment artwork is local, complete and served through a bounded asset route."""
from pathlib import Path
from urllib.parse import unquote
import re

from dnd_board_game.physical_cards.equipment_art import ART_NAMES, artwork_path, item_art, motif
from dnd_board_game.ui.exploration_app import create_app
from dnd_board_game.ui.training_arena import training_hero
from tests.unit.test_mission_recovery import party


def test_art_route_and_invalid_asset_names(tmp_path):
    client=create_app(party(tmp_path)).test_client()
    response=client.get('/equipment-art/sword.png')
    assert response.status_code==200 and response.mimetype=='image/png'
    assert response.data[:8]==b'\x89PNG\r\n\x1a\n'
    assert client.get('/equipment-art/not-an-item.png').status_code==404
    assert client.get('/equipment-art/../scenario.json').status_code==404
    assert client.get('/equipment-art/sword.png',headers={'If-None-Match':response.headers['ETag']}).status_code==304


def test_complete_art_catalog_and_portable_print_references(tmp_path):
    for name in ART_NAMES:
        assert artwork_path(name).read_bytes()[:8]==b'\x89PNG\r\n\x1a\n',name
    for hero in ('garran','brakka','erynd','dagna','nimra','mira','lorian'):
        for item in training_hero(hero).inventory:
            html=item_art(item,print_root=tmp_path)
            source=unquote(re.search(r'src="([^"]+)"',html).group(1))
            assert (tmp_path/source).resolve()==artwork_path(motif(item)).resolve()
            assert '<svg' not in html and '<img' in html
    assert motif(next(i for i in training_hero('garran').inventory if i.id=='chain_mail')) != motif(next(i for i in training_hero('dagna').inventory if i.id=='scale_mail'))
