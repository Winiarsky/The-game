"""Shared vector geometry for the calibrated board and its twelve A4 tiles.

The paper board is the live 20-column, 30-row board rotated clockwise: its
panel column becomes the bottom row, with slot 0 at the left edge.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from html import escape
from typing import Any

from dnd_board_game.ui.board_panel_symbols import SYMBOLS

PANEL_SYMBOLS: tuple[tuple[str, str], ...] = tuple(SYMBOLS)
BOARD_COLUMNS = 20
BOARD_ROWS = 30
CELL_MM = 25
PRINT_SCALE = (250 / 244) * 1.03
SOURCE_WIDTH_MM = BOARD_ROWS * CELL_MM
SOURCE_HEIGHT_MM = BOARD_COLUMNS * CELL_MM
PAGE_WIDTH_MM = 297
PAGE_HEIGHT_MM = 210
TILE_MARGIN_LEFT_MM = 10
TILE_MARGIN_TOP_MM = 15
FULL_WIDTH_MM = SOURCE_WIDTH_MM * PRINT_SCALE
FULL_HEIGHT_MM = SOURCE_HEIGHT_MM * PRINT_SCALE


@dataclass(frozen=True, slots=True)
class MapTile:
    label: str
    x: int
    y: int
    width: int
    height: int
    right: int
    bottom: int


def map_tiles() -> tuple[MapTile, ...]:
    """Twelve non-overlapping cores with right/bottom assembly tabs."""
    return tuple(
        MapTile(f"{chr(65+row)}{column+1}", column*250, row*150, 250,
                min(150, SOURCE_HEIGHT_MM-row*150),
                10 if column < 2 else 0, 10 if row < 3 else 0)
        for row in range(4) for column in range(3)
    )


def board_svg() -> str:
    """One authoritative grid and the same glyph paths as the live panel."""
    lines = ''.join(f'<path d="M{x} 0V{SOURCE_HEIGHT_MM}"/>'
                    for x in range(0, SOURCE_WIDTH_MM+1, CELL_MM))
    lines += ''.join(f'<path d="M0 {y}H{SOURCE_WIDTH_MM}"/>'
                     for y in range(0, SOURCE_HEIGHT_MM+1, CELL_MM))
    marks = ''.join(
        f'<svg x="{slot*CELL_MM+5}" y="{SOURCE_HEIGHT_MM-20}" width="15" height="15" viewBox="0 0 24 24" '
        f'data-panel-slot="{slot}" aria-label="{escape(name)}"><path d="{path}"/></svg>'
        for slot, (name, path) in enumerate(PANEL_SYMBOLS) if path
    )
    return (f'<g fill="none" stroke="#9b9b9b" stroke-width=".2">{lines}</g>'
            f'<g fill="none" stroke="#111" stroke-width="1.5" '
            f'stroke-linecap="round" stroke-linejoin="round">{marks}</g>')


def map_tile_svg(tile: MapTile) -> str:
    width, height = tile.width+tile.right, tile.height+tile.bottom
    marks = ''.join(
        f'<path d="M{x+dx} {y}h{dx*3}M{x} {y+dy}v{dy*3}"/>'
        for x, dx in ((0, -1), (width, 1))
        for y, dy in ((0, -1), (height, 1))
    )
    tabs = f'<path d="M{tile.width} 0V{height}" stroke-dasharray="1 1"/>' if tile.right else ''
    if tile.bottom:
        tabs += f'<path d="M0 {tile.height}H{width}" stroke-dasharray="1 1"/>'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{PAGE_WIDTH_MM}mm" height="{PAGE_HEIGHT_MM}mm" viewBox="0 0 {PAGE_WIDTH_MM} {PAGE_HEIGHT_MM}">
<text x="10" y="6" font-family="Arial" font-size="3">PLANSZA · {tile.label} · A4 100% · kalibracja +3%</text>
<g transform="translate({TILE_MARGIN_LEFT_MM} {TILE_MARGIN_TOP_MM}) scale({PRINT_SCALE:.10f})" data-print-scale="{PRINT_SCALE:.10f}">
<svg width="{width}" height="{height}" viewBox="{tile.x} {tile.y} {width} {height}" overflow="hidden">{board_svg()}</svg>
<g fill="none" stroke="black" stroke-width=".2">{tabs}<rect width="{width}" height="{height}" stroke-dasharray="3 1.5"/>{marks}</g>
</g></svg>'''


def full_map_svg() -> str:
    """Exactly the complete board, without assembly furniture or tile labels."""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{FULL_WIDTH_MM:.10f}mm" height="{FULL_HEIGHT_MM:.10f}mm" '
            f'viewBox="0 0 {SOURCE_WIDTH_MM} {SOURCE_HEIGHT_MM}" '
            f'data-print-scale="{PRINT_SCALE:.10f}">{board_svg()}</svg>')


def render_a4_html() -> str:
    sheets = ''.join('<section>'+map_tile_svg(tile)+'</section>' for tile in map_tiles())
    return ('<!doctype html><html lang="pl"><head><meta charset="utf-8"><title>Plansza A4</title>'
            '<style>@page{size:A4 landscape;margin:0}html,body{margin:0;padding:0}'
            f'section{{width:{PAGE_WIDTH_MM}mm;height:{PAGE_HEIGHT_MM}mm;break-after:page;break-inside:avoid}}'
            'section:last-child{break-after:auto}svg{display:block}</style></head><body>'
            +sheets+'</body></html>')


def render_full_html() -> str:
    return ('<!doctype html><html lang="pl"><head><meta charset="utf-8"><title>Plansza pełna</title>'
            f'<style>@page{{size:{FULL_WIDTH_MM:.10f}mm {FULL_HEIGHT_MM:.10f}mm;margin:0}}'
            'html,body{margin:0;padding:0}svg{display:block}</style></head><body>'
            +full_map_svg()+'</body></html>')


def map_specification() -> dict[str, Any]:
    """Physical page sizes and logical mapping for export verification."""
    return dict(
        board_columns=BOARD_COLUMNS, board_rows=BOARD_ROWS, nominal_cell_mm=CELL_MM,
        print_scale=PRINT_SCALE, relative_scale=1.03, pdf_cell_mm=CELL_MM*PRINT_SCALE,
        orientation="clockwise", full_width_mm=FULL_WIDTH_MM, full_height_mm=FULL_HEIGHT_MM,
        a4_pages=12, full_pages=1, a4_page_mm=[PAGE_WIDTH_MM, PAGE_HEIGHT_MM],
        tiles=[asdict(tile) for tile in map_tiles()],
        panel=[dict(slot=slot, name=name, path=path, board=[BOARD_COLUMNS-1, BOARD_ROWS-1-slot])
               for slot, (name, path) in enumerate(PANEL_SYMBOLS)],
    )
