"""Printable rune materials sharing the live game's physical panel contract."""
from __future__ import annotations

from html import escape

from .handout_maps import (
    PANEL_SYMBOLS, PRINT_SCALE, MapTile, board_svg, map_tile_svg, map_tiles,
)
from dnd_board_game.rules.runes import RESOURCE_RUNES

ACTION_MM = (60, 54)
EQUIPMENT_MM = (60, 42)


def rune_slot(name: str) -> int:
    return next(i for i, (label, _) in enumerate(PANEL_SYMBOLS) if label == name)


def panel_icon(slot: int) -> str:
    name, path = PANEL_SYMBOLS[slot]
    return (f'<svg class="glyph" viewBox="0 0 24 24" role="img" '
            f'aria-label="{escape(name)}" data-panel-slot="{slot}">'
            f'<path d="{path}"/></svg>') if path else ""
