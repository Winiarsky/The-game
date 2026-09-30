"""Printable rune materials sharing the live game's physical panel contract."""
from __future__ import annotations

from dataclasses import dataclass
from html import escape

from dnd_board_game.ui.board_panel_symbols import SYMBOLS
from dnd_board_game.rules.runes import RESOURCE_RUNES

PANEL_SYMBOLS: tuple[tuple[str, str], ...] = tuple(SYMBOLS)
PRINT_SCALE = (250 / 244) * 1.03
ACTION_MM = (60, 54)
EQUIPMENT_MM = (60, 42)


def rune_slot(name: str) -> int:
    return next(i for i, (label, _) in enumerate(PANEL_SYMBOLS) if label == name)


def panel_icon(slot: int) -> str:
    name, path = PANEL_SYMBOLS[slot]
    return (f'<svg class="glyph" viewBox="0 0 24 24" role="img" '
            f'aria-label="{escape(name)}" data-panel-slot="{slot}">'
            f'<path d="{path}"/></svg>') if path else ""


@dataclass(frozen=True)
class MapTile:
    label: str
    x: int
    y: int
    width: int
    height: int
    right: int
    bottom: int


def map_tiles() -> tuple[MapTile, ...]:
    """Twelve A4 cores; 6-row height keeps the enlarged cut marks printable."""
    return tuple(MapTile(f"{chr(65+r)}{c+1}", c*250, r*150, 250,
                         min(150, 500-r*150), 10 if c < 2 else 0,
                         10 if r < 3 else 0)
                 for r in range(4) for c in range(3))


def board_svg() -> str:
    lines = ''.join(f'<path d="M{x} 0V500"/>' for x in range(0, 751, 25))
    lines += ''.join(f'<path d="M0 {y}H750"/>' for y in range(0, 501, 25))
    marks = ''.join(
        f'<svg x="{i*25+5}" y="480" width="15" height="15" viewBox="0 0 24 24" '
        f'data-panel-slot="{i}" aria-label="{escape(name)}"><path d="{path}"/></svg>'
        for i, (name, path) in enumerate(PANEL_SYMBOLS) if path)
    return (f'<g fill="none" stroke="#9b9b9b" stroke-width=".2">{lines}</g>'
            f'<g fill="none" stroke="#111" stroke-width="1.5" '
            f'stroke-linecap="round" stroke-linejoin="round">{marks}</g>')


def map_tile_svg(tile: MapTile) -> str:
    w, h = tile.width+tile.right, tile.height+tile.bottom
    s = PRINT_SCALE
    marks = ''.join(f'<path d="M{x+dx} {y}h{dx*3}M{x} {y+dy}v{dy*3}"/>'
                    for x, dx in ((0, -1), (w, 1))
                    for y, dy in ((0, -1), (h, 1)))
    tabs = (f'<path d="M{tile.width} 0V{h}" stroke-dasharray="1 1"/>' if tile.right else '')
    tabs += (f'<path d="M0 {tile.height}H{w}" stroke-dasharray="1 1"/>' if tile.bottom else '')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="297mm" height="210mm" viewBox="0 0 297 210">
<text x="10" y="6" font-family="Arial" font-size="3">RUNY v0.2 · {tile.label} · A4 100% · wspólna skala +3%</text>
<g transform="translate(10 15) scale({s:.10f})" data-print-scale="{s:.10f}">
<svg width="{w}" height="{h}" viewBox="{tile.x} {tile.y} {w} {h}" overflow="hidden">{board_svg()}</svg>
<g fill="none" stroke="black" stroke-width=".2">{tabs}<rect width="{w}" height="{h}" stroke-dasharray="3 1.5"/>{marks}</g>
</g></svg>'''
