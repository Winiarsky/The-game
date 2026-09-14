"""Physical scale, tiling coverage and current board/card symbol contract."""

import json
from collections import Counter
from xml.etree import ElementTree as ET

import pytest

from scripts.build_arena_print_pack import (
    ROOT,
    PAGE_ORIGIN_MM,
    PAGE_ORIGIN_Y_MM,
    PRINT_SCALE,
    guide,
    map_body,
    position,
    svg,
    tile_svg,
    tiles,
    terrain_document,
    terrain_inventory,
)
from dnd_board_game.ui.board_panel_symbols import SYMBOLS


def test_tile_cores_cover_each_board_cell_exactly_once() -> None:
    covered = Counter()
    for tile in tiles():
        assert tile.x % 25 == tile.y % 25 == tile.width % 25 == tile.height % 25 == 0
        covered.update(
            (x, y)
            for x in range(tile.x, tile.x + tile.width, 25)
            for y in range(tile.y, tile.y + tile.height, 25)
        )
    assert covered == Counter(
        {(x, y): 1 for x in range(0, 750, 25) for y in range(0, 500, 25)}
    )


def test_glue_tabs_repeat_neighbors_and_fit_printer_margins() -> None:
    all_tiles = tiles()
    for tile in all_tiles:
        assert PAGE_ORIGIN_MM - 4 * PRINT_SCALE >= 7
        assert PAGE_ORIGIN_Y_MM - 4 * PRINT_SCALE >= 5.5
        assert PAGE_ORIGIN_MM + (tile.width + tile.right + 4) * PRINT_SCALE <= 297 - 7
        assert PAGE_ORIGIN_Y_MM + (tile.height + tile.bottom + 4) * PRINT_SCALE <= 210 - 6
        if tile.right:
            neighbor = next(
                t for t in all_tiles if t.x == tile.x + tile.width and t.y == tile.y
            )
            assert tile.right == 10
            assert tile.x + tile.width + tile.right <= neighbor.x + neighbor.width
        else:
            assert tile.x + tile.width == 750
        if tile.bottom:
            neighbor = next(
                t for t in all_tiles if t.y == tile.y + tile.height and t.x == tile.x
            )
            assert tile.bottom == 10
            assert tile.y + tile.height + tile.bottom <= neighbor.y + neighbor.height
        else:
            assert tile.y + tile.height == 500


def test_clipped_map_cut_lines_and_tabs_share_calibrated_scale() -> None:
    for tile in tiles():
        page = ET.fromstring(tile_svg(tile, ""))
        assert (page.attrib["width"], page.attrib["height"]) == ("297mm", "210mm")
        layer = page.find("{http://www.w3.org/2000/svg}g")
        assert float(layer.attrib['data-print-scale']) == pytest.approx(250 / 244)
        assert layer.attrib['transform'] == f'translate({PAGE_ORIGIN_MM} {PAGE_ORIGIN_Y_MM}) scale({PRINT_SCALE:.10f})'
        viewport = layer.find("{http://www.w3.org/2000/svg}svg")
        assert viewport is not None
        x, y, w, h = map(int, viewport.attrib["viewBox"].split())
        assert (x, y) == (tile.x, tile.y)
        assert int(viewport.attrib["width"]) == w == tile.width + tile.right
        assert int(viewport.attrib["height"]) == h == tile.height + tile.bottom


def test_print_is_empty_except_for_fixed_panel_symbols() -> None:
    data = json.loads(
        (ROOT / "content/scenarios/recruitment_arena_combat.json").read_text()
    )
    body = map_body(data)
    root = ET.fromstring(svg(body, "0 0 750 500", "750mm", "500mm"))
    assert "data-terrain" not in body
    assert "data-start" not in body
    assert body == map_body({"board": data["board"]})
    icons = {
        int(el.attrib["data-panel-slot"]): el
        for el in root.iter()
        if "data-panel-slot" in el.attrib
    }
    assert set(icons) == set(range(30)) - {4}
    for slot, el in icons.items():
        assert (
            el.find("{http://www.w3.org/2000/svg}path").attrib["d"] == SYMBOLS[slot][1]
        )
    assert [position(19, 29 - slot) for slot in range(30)] == [
        (slot * 25, 475) for slot in range(30)
    ]


def test_terrain_cutouts_match_setup_inventory_and_real_cell_size() -> None:
    data = json.loads(
        (ROOT / "content/scenarios/recruitment_arena_combat.json").read_text()
    )
    inventory = terrain_inventory(data)
    html = terrain_document(data)
    root = ET.fromstring(html[html.index("<svg xmlns=") : html.rindex("</svg>") + 6])
    assert (root.attrib["width"], root.attrib["height"]) == ("210mm", "297mm")
    tokens = [e for e in root.iter() if "data-terrain-token" in e.attrib]
    assert len(tokens) == 19
    for entry in inventory:
        terrain = next(e for e in data["environment"] if e["id"] == entry["id"])
        group = [e for e in tokens if e.attrib["data-terrain-token"] == entry["id"]]
        assert len(group) == len(terrain["positions"])
        assert entry["label"] in terrain["setup_mechanics"][0]
        for token in group:
            assert float(token.attrib['data-print-scale']) * 24.4 == pytest.approx(25)
            rect = token.find("{http://www.w3.org/2000/svg}rect")
            assert (rect.attrib["width"], rect.attrib["height"]) == ("25", "25")
    assert {e.attrib["data-terrain-token"] for e in tokens} == {
        e["id"] for e in inventory
    }


def test_calibration_reference_uses_same_correction_as_map_and_tokens() -> None:
    html = guide("", [("Garran", 12, 35)])
    assert "244 → 250" in html and "Nie dodawaj jej ponownie" in html
    start = html.index('<svg xmlns=')
    root = ET.fromstring(html[start:html.index('</svg>', start) + 6])
    layer = root.find('{http://www.w3.org/2000/svg}g')
    assert float(layer.attrib['data-print-scale']) == pytest.approx(PRINT_SCALE)
    assert 48.8 * PRINT_SCALE == pytest.approx(50)
