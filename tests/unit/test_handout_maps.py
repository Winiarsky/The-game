"""Both public map PDFs share calibrated vector geometry and fixed live slots."""
from collections import Counter
import importlib.util
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from dnd_board_game.physical_cards.handout_maps import (
    BOARD_COLUMNS, BOARD_ROWS, CELL_MM, FULL_HEIGHT_MM, FULL_WIDTH_MM,
    PANEL_SYMBOLS, PRINT_SCALE, full_map_svg, map_specification, map_tile_svg,
    map_tiles, render_a4_html, render_full_html,
)
from dnd_board_game.physical_cards.rune_prototype import PRINT_SCALE as LEGACY_SCALE
from dnd_board_game.ui.board_panel_symbols import SYMBOLS

ROOT = Path(__file__).resolve().parents[2]
NS = '{http://www.w3.org/2000/svg}'


def load_builder():
    spec = importlib.util.spec_from_file_location('build_handout_maps', ROOT/'scripts/build_handout_maps.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_twelve_a4_cores_cover_all_600_cells_once_at_the_current_scale() -> None:
    covered = Counter()
    assert BOARD_COLUMNS == 20 and BOARD_ROWS == 30 and CELL_MM == 25
    assert PRINT_SCALE == LEGACY_SCALE == pytest.approx((250/244)*1.03)
    for tile in map_tiles():
        covered.update((x, y) for x in range(tile.x, tile.x+tile.width, CELL_MM)
                       for y in range(tile.y, tile.y+tile.height, CELL_MM))
        assert 10+(tile.width+tile.right+4)*PRINT_SCALE <= 292
        assert 15+(tile.height+tile.bottom+4)*PRINT_SCALE <= 205
        svg = ET.fromstring(map_tile_svg(tile))
        assert (svg.attrib['width'], svg.attrib['height']) == ('297mm', '210mm')
        assert float(svg.find(NS+'g').attrib['data-print-scale']) == pytest.approx(PRINT_SCALE)
    assert len(map_tiles()) == 12
    assert covered == Counter({(x, y): 1 for x in range(0, 750, 25) for y in range(0, 500, 25)})
    assert render_a4_html().count('<section>') == 12


def test_full_page_keeps_actual_cell_pitch_and_contains_no_tile_furniture() -> None:
    full = ET.fromstring(full_map_svg())
    assert full.attrib['viewBox'] == '0 0 750 500'
    assert float(full.attrib['width'].removesuffix('mm')) == pytest.approx(750*PRINT_SCALE)
    assert float(full.attrib['height'].removesuffix('mm')) == pytest.approx(500*PRINT_SCALE)
    assert (FULL_WIDTH_MM/30, FULL_HEIGHT_MM/20) == pytest.approx((25*PRINT_SCALE, 25*PRINT_SCALE))
    assert not list(full.iter(NS+'text'))
    assert not list(full.iter(NS+'rect'))
    assert all('stroke-dasharray' not in element.attrib for element in full.iter())
    html = render_full_html()
    assert f'@page{{size:{FULL_WIDTH_MM:.10f}mm {FULL_HEIGHT_MM:.10f}mm;margin:0}}' in html
    assert '<section>' not in html and 'break-after' not in html and 'A4' not in html


def test_full_and_tiled_board_layers_have_identical_grid_and_live_glyph_geometry() -> None:
    full = ET.fromstring(full_map_svg())
    tile = ET.fromstring(map_tile_svg(map_tiles()[0]))
    board = tile.find(NS+'g').find(NS+'svg')
    assert [ET.tostring(layer) for layer in full] == [ET.tostring(layer) for layer in board]
    assert len(list(full[0].iter(NS+'path'))) == 31+21
    glyphs = [element for element in full.iter() if 'data-panel-slot' in element.attrib]
    assert len(glyphs) == 29 and PANEL_SYMBOLS == tuple(SYMBOLS)
    for glyph in glyphs:
        slot = int(glyph.attrib['data-panel-slot'])
        assert glyph.find(NS+'path').attrib['d'] == SYMBOLS[slot][1]
        assert float(glyph.attrib['x']) == slot*25+5
        assert float(glyph.attrib['y']) == 480
    spec = map_specification()
    assert spec['pdf_cell_mm'] == pytest.approx(25*PRINT_SCALE)
    assert (spec['a4_pages'], spec['full_pages']) == (12, 1)
    assert [entry['board'] for entry in spec['panel']] == [[19, 29-slot] for slot in range(30)]


def test_builder_keeps_sources_in_cache_and_publishes_only_two_pdfs(tmp_path: Path, monkeypatch) -> None:
    builder = load_builder()
    output, work = tmp_path/'handouts', tmp_path/'.cache/handouts/maps'
    operations = []
    def fake_render(html: Path, pdf: Path) -> None:
        assert html.parent == work and pdf.parent == work
        operations.append(('render', pdf.name))
        pdf.write_bytes(b'%PDF-staged')
    def fake_pages(pdf: Path) -> int:
        operations.append(('verify', pdf.name))
        return 12 if pdf.stem == 'map_a4' else 1
    def fake_publish(source: Path, destination: Path) -> Path:
        assert len([op for op in operations if op[0] == 'verify']) == 2
        operations.append(('publish', destination.name))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
        return destination
    monkeypatch.setattr(builder, 'render_pdf', fake_render)
    monkeypatch.setattr(builder, 'pdf_pages', fake_pages)
    monkeypatch.setattr(builder, 'publish_pdf', fake_publish)
    paths = builder.build_maps(output, work)
    assert paths == {'map_a4': output/'map_a4.pdf', 'map_full': output/'map_full.pdf'}
    assert {path.name for path in output.iterdir()} == {'map_a4.pdf', 'map_full.pdf'}
    assert operations == [('render', 'map_a4.pdf'), ('render', 'map_full.pdf'),
                          ('verify', 'map_a4.pdf'), ('verify', 'map_full.pdf'),
                          ('publish', 'map_a4.pdf'), ('publish', 'map_full.pdf')]
    assert json.loads((work/'map_specification.json').read_text())['full_pages'] == 1
    assert not (tmp_path/'content/scenarios/misja_0_dzwon/print/runy_v01').exists()


def test_wrong_full_page_count_cannot_publish_a_mixed_map_set(tmp_path: Path, monkeypatch) -> None:
    builder = load_builder()
    published = []
    monkeypatch.setattr(builder, 'render_pdf', lambda html, pdf: pdf.write_bytes(b'%PDF-staged'))
    monkeypatch.setattr(builder, 'pdf_pages', lambda pdf: 12 if pdf.stem == 'map_a4' else 2)
    monkeypatch.setattr(builder, 'publish_pdf', lambda source, destination: published.append(destination))
    with pytest.raises(RuntimeError, match='map_full: oczekiwano 1 stron, otrzymano 2'):
        builder.build_maps(tmp_path/'handouts', tmp_path/'.cache/maps')
    assert not published and not (tmp_path/'handouts').exists()
