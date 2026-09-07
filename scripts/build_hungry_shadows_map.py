"""Build exact playable SVG and printable HTML from the encounter's terrain.

The generated illustration is a background; cell outlines come exclusively from
runtime content. Run after changing terrain or replacing the v6 illustration.
"""

from __future__ import annotations

import base64
import json
from collections import Counter
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "assets/maps/ostatni_transport_01"
SCENARIO = ROOT / "content/scenarios/ostatni_transport_01_glodne_cienie.json"


def boundary(positions: list[list[int]]) -> str:
    edges: Counter[tuple[tuple[int, int], tuple[int, int]]] = Counter()
    for x, y in sorted(set(map(tuple, positions))):
        corners = [(x, y), (x + 1, y), (x + 1, y + 1), (x, y + 1)]
        for first, second in zip(corners, corners[1:] + corners[:1]):
            edges[tuple(sorted((first, second)))] += 1
    return " ".join(
        f"M {a[0]*50},{a[1]*50} L {b[0]*50},{b[1]*50}"
        for (a, b), count in edges.items()
        if count == 1
    )


def main() -> None:
    data = json.loads(SCENARIO.read_text())
    encoded = base64.b64encode(
        (DEST / "glodne_cienie_illustration_v6.png").read_bytes()
    ).decode("ascii")
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="1500" viewBox="0 0 1000 1500">',
        "<title>Głodne Cienie — plansza 20 × 30</title>",
        "<desc>Czerwony ciągły obrys: blokada ruchu i widoczności. Złoty przerywany: osłona kierunkowa. Niebieski kropkowany: trudny teren. Pozostałe pola są przechodnie.</desc>",
        f'<image width="1000" height="1500" preserveAspectRatio="none" href="data:image/png;base64,{encoded}"/>',
    ]
    for x in range(21):
        parts.append(
            f'<path d="M{x*50},0 V1500" stroke="white" stroke-opacity=".22" stroke-width="1"/>'
        )
    for y in range(31):
        parts.append(
            f'<path d="M0,{y*50} H1000" stroke="white" stroke-opacity=".22" stroke-width="1"/>'
        )
    colors = {
        "blocking_terrain": ("#ef8074", ""),
        "cover": ("#ffe094", "10 5"),
        "difficult_terrain": ("#a4dcef", "3 5"),
    }
    zones = []
    for entry in data["environment"]:
        if entry["type"] not in colors:
            continue
        color, dash = colors[entry["type"]]
        parts.append(
            f'<g id="{escape(entry["id"])}"><title>{escape(entry["name"])}</title>'
        )
        parts.append(
            f'<path d="{boundary(entry["positions"])}" fill="none" stroke="#171917" stroke-width="5"/>'
        )
        parts.append(
            f'<path d="{boundary(entry["positions"])}" fill="none" stroke="{color}" stroke-width="3" stroke-dasharray="{dash}"/></g>'
        )
        zones.append({key: entry[key] for key in ("id", "name", "type", "positions")})
    for x in range(20):
        parts.append(
            f'<text x="{x*50+25}" y="17" text-anchor="middle" font-family="sans-serif" font-size="12" fill="white" stroke="#111" stroke-width="3" paint-order="stroke">{x}</text>'
        )
    for y in range(30):
        parts.append(
            f'<text x="5" y="{y*50+30}" font-family="sans-serif" font-size="12" fill="white" stroke="#111" stroke-width="3" paint-order="stroke">{y}</text>'
        )
    parts.append("</svg>")
    svg = "".join(parts)
    (DEST / "glodne_cienie_battlemap_v6.svg").write_text(svg)
    (DEST / "glodne_cienie_print_v6.html").write_text(
        '<!doctype html><html lang="pl"><meta charset="utf-8"><title>Głodne Cienie — wydruk 50 × 75 cm</title><style>@page{size:50cm 75cm;margin:0}html,body{margin:0;padding:0}svg{display:block;width:50cm;height:75cm}</style>'
        + svg
        + "</html>"
    )
    layout = {
        "id": "glodne_cienie_tactical_layout_v6",
        "board": data["board"],
        "map_asset": data["encounter_map_asset"],
        "player_start_zones": data["player_start_zones"],
        "party_size_variants": data["encounter_party_size_variants"],
        "actors": [{k: a[k] for k in ("id", "position")} for a in data["actors"]],
        "zones": zones,
    }
    (DEST / "glodne_cienie_tactical_layout_v6.json").write_text(
        json.dumps(layout, ensure_ascii=False, indent=2) + "\n"
    )
    print("Generated v6 SVG, print HTML and layout from runtime content.")


if __name__ == "__main__":
    main()
