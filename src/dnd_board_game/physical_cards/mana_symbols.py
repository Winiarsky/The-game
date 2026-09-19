"""Print-safe mana symbols matching the combat UI; no bitmap dependency."""

from html import escape
import re

from dnd_board_game.rules.physical_mana import COLORS

PATHS = {
    "C": "M12 2C14 8 20 8 20 15a8 8 0 0 1-16 0c0-3 2-6 5-8-1 5 2 6 3 4 2-3 1-6 0-9Z",
    "N": "M12 2C10 6 5 11 5 15a7 7 0 0 0 14 0c0-4-5-9-7-13ZM8 15c0 2 1 3 3 3",
    "Z": "M9 22h6M10 22v-7H6a3 3 0 0 1-1-6 4 4 0 0 1 4-6 4 4 0 0 1 7 1 4 4 0 0 1 4 5 3 3 0 0 1-2 6h-4v7M10 16l-2-3M14 17l3-4",
    "B": "M16 12a4 4 0 1 0-8 0 4 4 0 1 0 8 0M12 1v4M12 19v4M1 12h4M19 12h4M4 4l3 3M17 17l3 3M4 20l3-3M17 7l3-3",
    "F": "M8 21v-4C2 16 2 3 12 3s10 13 4 14v4ZM9 21v-3M12 21v-3M15 21v-3M9 11a1.5 1.5 0 1 0-3 0 1.5 1.5 0 1 0 3 0M18 11a1.5 1.5 0 1 0-3 0 1.5 1.5 0 1 0 3 0M11 15l1-2 1 2Z",
    "*": "M22 12a10 10 0 1 0-20 0 10 10 0 1 0 20 0M9 9l3-3v12M9 18h6",
}


def mana_symbol(color: str) -> str:
    label = f"1 mana {COLORS[color]}"
    return (
        f'<svg class="mana-symbol" data-mana="{color}" viewBox="0 0 24 24" '
        f'role="img" aria-label="{escape(label)}"><title>{escape(label)}</title>'
        f'<path d="{PATHS[color]}"/></svg>'
    )


def passive_mana_symbol(color: str, stackable: bool) -> str:
    label = 'Kumuluje się' if stackable else 'Nie kumuluje się'
    border = '3px' if stackable else '1px'
    return (f'<span class="mana-passive-symbol" data-stackable="{str(stackable).lower()}" '
            f'title="{label}" style="border:{border} solid currentColor">{mana_symbol(color)}</span>')


def mana_text(text: str) -> str:
    """Replace only explicit color markers, preserving escaped readable prose."""
    return re.sub(r"\(([CNZBF*])\)", lambda m: mana_symbol(m[1]), escape(text))
