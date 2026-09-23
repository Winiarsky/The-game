"""Build a standalone board-control prototype; leaves scenario/runtime untouched."""

from __future__ import annotations

import json
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from dnd_board_game.character_creation import PLAYABLE_HERO_IDS
from dnd_board_game.physical_cards.mana_print import build_print_hero
from dnd_board_game.physical_cards.mana_symbols import mana_symbol

OUTPUT = ROOT / "assets/maps/recruitment_arena/panel_preview"
from dnd_board_game.ui.board_panel_symbols import SYMBOLS, panel_icon as icon


def arena_svg(data: dict[str, object]) -> str:
    # Clockwise landscape view: (col,row) -> (29-row,col). No save migration.
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1240 880" role="img" aria-labelledby="arena-title">',
        '<title id="arena-title">Arena Nessy: 30 pól w dolnym panelu, 30 × 19 pól areny. Prototyp.</title>',
        "<style>.glyph{fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}.pad{cursor:pointer}.pad:hover rect{stroke:#fff;stroke-width:3}.pad:focus{outline:none}.pad:focus rect{stroke:#fff;stroke-width:3}.pad.disabled{opacity:.28;cursor:default}.pad.selected rect{stroke:#fff;stroke-width:3}.pad.selected{filter:drop-shadow(0 0 5px #f2ce75)}text{font-family:Arial,sans-serif}</style>",
        '<rect width="1240" height="880" fill="#111a1d"/>',
        '<text x="20" y="29" fill="#efd6a1" font-size="19">NESSA · ARENA REKRUTACYJNA</text>',
        '<text x="1220" y="29" text-anchor="end" fill="#a6b9b6" font-size="12">PODGLĄD PANELU · 30 × 20 PÓL</text>',
        '<g transform="translate(20 48)"><rect width="1200" height="800" fill="#ae9a77"/>',
    ]
    for x in range(31):
        parts.append(
            f'<path d="M{x*40} 0v800" stroke="#716850" stroke-opacity=".6" stroke-width=".7"/>'
        )
    for y in range(21):
        parts.append(
            f'<path d="M0 {y*40}h1200" stroke="#716850" stroke-opacity=".6" stroke-width=".7"/>'
        )
    styles = {
        "blocking_terrain": ("#4f5554", "#e3e5d8"),
        "cover": ("#805b37", "#f7dc92"),
        "difficult_terrain": ("#b47a3e", "#ffe1a1"),
    }
    for entry in data["environment"]:
        if entry["type"] not in styles:
            continue
        fill, stroke = styles[entry["type"]]
        for col, row in entry["positions"]:
            assert col != 19, "Preview panel intersects scenario terrain"
            x, y = (29 - row) * 40, col * 40
            parts.append(
                f'<g data-terrain="{escape(entry["id"])}"><title>{escape(entry["name"])}</title><rect x="{x+1}" y="{y+1}" width="38" height="38" fill="{fill}" stroke="{stroke}"/>'
            )
            if entry["type"] == "blocking_terrain":
                parts.append(
                    f'<path d="M{x+12} {y+12}l16 16m0-16-16 16" stroke="{stroke}" stroke-width="2"/>'
                )
            elif entry["type"] == "cover":
                parts.append(
                    f'<text x="{x+20}" y="{y+25}" text-anchor="middle" fill="{stroke}" font-size="15">+2</text>'
                )
            else:
                parts.append(
                    f'<path d="M{x+6} {y+28}l8-16 8 16Zm16-18 5-4 6 13Z" fill="{stroke}"/>'
                )
            parts.append("</g>")
    markers = [
        ("Nessa", 3, 18, "#72508c"),
        ("Bohater", 9, 18, "#316ca2"),
        ("Kukła", 10, 12, "#9d473f"),
        ("Pomocnik", 9, 16, "#338679"),
        ("Kukła 2", 11, 12, "#9d473f"),
        ("Kukła 3", 10, 11, "#9d473f"),
    ]
    for label, col, row, color in markers:
        x, y = (29 - row) * 40 + 20, col * 40 + 20
        marker = label[-1] if label.startswith("Kukła ") else label[0]
        caption = "" if label.startswith("Kukła ") else label
        parts.append(
            f'<g class="map-target" data-target="{label}"><circle cx="{x}" cy="{y}" r="15" fill="{color}" stroke="#f2e7c8" stroke-width="2"/><text x="{x}" y="{y+4}" text-anchor="middle" font-size="12" fill="white">{marker}</text><text x="{x}" y="{y-22}" text-anchor="middle" font-size="12" fill="#182220" stroke="#d0bd98" stroke-width="3" paint-order="stroke">{caption}</text></g>'
        )
    parts.append(
        '<rect x="0" y="757" width="1200" height="43" fill="#121a1e"/><path d="M0 759h1200" stroke="#e5bc65" stroke-width="3"/>'
    )
    for slot, (name, path) in enumerate(SYMBOLS):
        if not path:
            parts.append(f'<rect data-panel-blank="{slot}" x="{slot*40}" y="760" width="40" height="40" fill="#121a1e"><title>Puste pole</title></rect>')
            continue
        color = ("#9dcadc" if slot < 4 else "#53aeef" if slot == 24
                 else "#d6b46b" if slot < 26
                 else ["#97d4ab", "#efad9a", "#53aeef", "#efad9a"][slot - 26])
        parts.append(
            f'<g class="pad" tabindex="0" role="button" aria-label="{escape(name)}" data-slot="{slot}" data-board-col="19" data-board-row="{29-slot}" transform="translate({slot*40} 760)" style="color:{color}"><title>{escape(name)}</title><rect x="2" y="3" width="36" height="34" rx="3" fill="#1c272c" stroke="{color}" stroke-width="1"/><svg x="9" y="8" width="22" height="24" viewBox="0 0 24 24" class="glyph"><path d="{path}"/></svg></g>'
        )
    parts.append(
        '</g><text x="20" y="871" fill="#a6b9b6" font-size="12">4 akcje · przerwa · 19 run i gwiazda informacji · przerwa · + / − / zatwierdź / wróć. Panel nie jest terenem gry.</text></svg>'
    )
    return "".join(parts)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    data = json.loads(
        (ROOT / "content/scenarios/recruitment_arena_combat.json").read_text()
    )
    assert data["board"] == {"cols": 20, "rows": 30}
    assert len(SYMBOLS) == 30 and len({path for _, path in SYMBOLS if path}) == 28
    assert [slot for slot, (_, path) in enumerate(SYMBOLS) if not path] == [4, 25]
    heroes = []
    for hero_id in PLAYABLE_HERO_IDS:
        hero = build_print_hero(hero_id)
        cards = sorted(
            (c for c in hero.cards if c.timing != "R"), key=lambda c: c.panel_slot
        )
        assert len(cards) <= 20
        heroes.append(
            {
                "id": hero_id,
                "name": hero.name,
                "cards": [
                    {
                        "id": c.id,
                        "slot": c.panel_slot,
                        "name": c.name,
                        "timing": c.timing,
                        "description": c.description,
                        "mana": "".join(mana_symbol(color) for color in c.cost),
                    }
                    for c in cards
                ],
            }
        )
    svg = arena_svg(data)
    (OUTPUT / "arena-panel-v1.svg").write_text(svg)
    template = (ROOT / "scripts/arena_panel_preview.html").read_text()
    html = (
        template.replace("<!-- ARENA -->", svg)
        .replace("__HERO_DATA__", json.dumps(heroes, ensure_ascii=False))
        .replace(
            "__ICONS__", json.dumps([icon(i) for i in range(30)], ensure_ascii=False)
        )
        .replace(
            "__SYMBOL_NAMES__", json.dumps([n for n, _ in SYMBOLS], ensure_ascii=False)
        )
    )
    (OUTPUT / "index.html").write_text(html)
    (OUTPUT / "panel-manifest.json").write_text(
        json.dumps(
            {
                "preview_only": True,
                "orientation": "clockwise",
                "cells": [
                    {"slot": i, "name": n, "board_position": [19, 29 - i], "path": p, "enabled": bool(p)}
                    for i, (n, p) in enumerate(SYMBOLS)
                ],
                "heroes": heroes,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    print(
        f'Preview: {OUTPUT}/index.html; 30 cells; 7 heroes; largest repertoire {max(len(h["cards"]) for h in heroes)} runes'
    )


if __name__ == "__main__":
    main()
