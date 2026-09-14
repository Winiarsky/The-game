"""Print a monochrome, true-scale A4 arena and current hero cards in one PDF."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from html import escape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dnd_board_game.character_creation import PLAYABLE_HERO_IDS
from dnd_board_game.physical_cards.mana_print import build_print_hero
from dnd_board_game.physical_cards.mana_print_files import merge_pdfs, render_pdf
from dnd_board_game.physical_cards.mana_print_html import render_hero_html
from dnd_board_game.ui.board_panel_symbols import SYMBOLS

OUTPUT = ROOT / "assets/maps/recruitment_arena/print"
CELL_MM = 25
BOARD_WIDTH_MM = 750
BOARD_HEIGHT_MM = 500
OVERLAP_MM = 10
PAGE_ORIGIN_MM = 15
PAGE_ORIGIN_Y_MM = 10
# Calibration from the reported physical print: 244 measured vs 250 intended.
# Keep design coordinates nominal; only printed map/token geometry is enlarged.
PRINT_SCALE = 250 / 244


@dataclass(frozen=True)
class Tile:
    label: str
    x: int
    y: int
    width: int
    height: int
    right: int
    bottom: int


def tiles() -> tuple[Tile, ...]:
    """Nine non-overlapping cores; tabs duplicate the next tile's map region."""
    return tuple(
        Tile(
            f"{chr(65 + row)}{col + 1}",
            col * 250,
            row * 175,
            250,
            min(175, BOARD_HEIGHT_MM - row * 175),
            OVERLAP_MM if col < 2 else 0,
            OVERLAP_MM if row < 2 else 0,
        )
        for row in range(3)
        for col in range(3)
    )


def position(col: int, row: int) -> tuple[int, int]:
    """Original hardware coordinates rotated clockwise, returned in mm."""
    return (29 - row) * CELL_MM, col * CELL_MM


def map_body(data: dict[str, Any]) -> str:
    """Reusable empty grid: all scenario scenery is placed during setup."""
    if data["board"].get("cols") not in {19, 20} or data["board"].get("rows") != 30:
        raise ValueError("Ten wydruk wymaga planszy 20 × 30.")
    parts = ['<rect width="750" height="500" fill="white"/>']
    for x in range(31):
        parts.append(
            f'<path d="M{x*25} 0v500" stroke-width="{0.3 if x % 5 == 0 else 0.12}"/>'
        )
    for y in range(21):
        parts.append(
            f'<path d="M0 {y*25}h750" stroke-width="{0.3 if y % 5 == 0 else 0.12}"/>'
        )
    parts.append(
        '<rect y="475" width="750" height="25" fill="white" stroke-width="0.5"/>'
    )
    for slot, (name, path) in enumerate(SYMBOLS):
        x = slot * CELL_MM
        parts.append(f'<path d="M{x} 475v25" stroke-width="0.25"/>')
        if path:
            parts.append(
                f'<svg data-panel-slot="{slot}" x="{x+4.5}" y="479.5" width="16" height="16" viewBox="0 0 24 24"><title>{escape(name)}</title><path d="{path}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>'
            )
    parts.append('<rect width="750" height="500" stroke-width="0.5"/>')
    return "".join(parts)


TERRAIN_LABELS = {
    "arena_screen": "ZASŁONA",
    "arena_crates": "SKRZYNIE",
    "arena_pillar": "FILAR",
    "arena_low_cover": "OSŁONA",
    "arena_rubble": "GRUZ",
}


def terrain_inventory(data: dict[str, Any]) -> list[dict[str, Any]]:
    entries = {e["id"]: e for e in data["environment"]}
    return [
        {
            "id": key,
            "name": entries[key]["name"],
            "label": label,
            "kind": entries[key]["type"],
            "count": len({tuple(p) for p in entries[key]["positions"]}),
        }
        for key, label in TERRAIN_LABELS.items()
    ]


def terrain_document(data: dict[str, Any]) -> str:
    page = '<text x="16" y="20" font-size="7" font-weight="bold">Teren areny · wytnij i ułóż</text>'
    page += '<text x="16" y="29" font-size="3.4">Każdy kwadrat: 25 × 25 mm. Wytnij po zewnętrznym obrysie.</text>'
    page += '<text x="16" y="35" font-size="3.4">Układaj na podświetlonych polach podczas setupu; nie przyklejaj do mapy.</text>'
    descriptions = {
        "blocking_terrain": "Blokuje ruch i widoczność",
        "cover": "Ruch dozwolony · osłona +2 KP",
        "difficult_terrain": "Ruch ×2 · bez osłony",
    }
    for row, entry in enumerate(terrain_inventory(data)):
        y = 49 + row * 41
        count = entry["count"]
        if count > (8 if row == 4 else 6):
            raise ValueError("Nowy układ terenu wymaga większego arkusza znaczników.")
        page += f'<text x="16" y="{y-4}" font-size="3.6" font-weight="bold">{escape(entry["name"])} · {count} szt.</text>'
        # Rule captions below the group leave all token edges accessible for cutting.
        for i in range(count):
            columns = 4 if count > 6 else 6
            x, ty = 16 + (i % columns) * 29, y + (i // columns) * 28
            page += f'<g data-terrain-token="{entry["id"]}" data-print-scale="{PRINT_SCALE:.10f}" transform="translate({x} {ty}) scale({PRINT_SCALE:.10f})">'
            page += '<rect width="25" height="25" fill="white" stroke-width="0.25"/>'
            kind = entry["kind"]
            if kind == "blocking_terrain":
                page += '<rect x="1.5" y="1.5" width="22" height="16" fill="url(#blocked)" stroke-width="0.35"/><path d="M8 5l9 9m0-9-9 9" stroke-width="0.65"/>'
            elif kind == "cover":
                page += '<rect x="2" y="2" width="21" height="16" stroke-width="0.45"/><text x="12.5" y="14" font-size="8" text-anchor="middle">+2</text>'
            else:
                page += '<path d="M4 7l4-3 3 4-5 3Zm10 3 5-5 3 7-6 4ZM3 15l4-3 3 5Z" stroke-width="0.45"/>'
            page += f'<text x="12.5" y="22" font-size="2.6" text-anchor="middle" font-weight="bold">{entry["label"]}</text></g>'
        bottom = y + (28 if count > 6 else 0) + 25
        page += f'<text x="16" y="{bottom+5}" font-size="2.8">{descriptions[entry["kind"]]}</text>'
    page += '<text x="16" y="282" font-size="3">Bohatera, Nessę i kukły reprezentują figurki. Ten arkusz zawiera tylko teren.</text>'
    return document(svg(page, "0 0 210 297", "210mm", "297mm"), "portrait")


def svg(body: str, viewbox: str, width: str, height: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}" width="{width}" height="{height}" '
        'fill="none" stroke="black" font-family="Arial,sans-serif">'
        '<defs><pattern id="blocked" width="4" height="4" patternUnits="userSpaceOnUse">'
        '<path d="M-1 1l2-2M0 4l4-4M3 5l2-2" stroke="black" stroke-width="0.15"/></pattern></defs>'
        "<style>text{fill:black;stroke:none}</style>" + body + "</svg>"
    )


def tile_svg(tile: Tile, body: str) -> str:
    w, h = tile.width + tile.right, tile.height + tile.bottom
    origin = 0
    header = f'<text x="22" y="6" font-size="4" font-weight="bold">ARENA NESSY · {tile.label}</text>'
    header += '<text x="280" y="6" text-anchor="end" font-size="2.7">A4 · 100% · korekta 250/244 · pole docelowo 25 mm</text>'
    page = ""
    # Clip in nominal coordinates; scale the complete map/cut/glue layer together.
    page += f'<svg x="{origin}" y="{origin}" width="{w}" height="{h}" viewBox="{tile.x} {tile.y} {w} {h}">{body}</svg>'
    if tile.right:
        next_label = f"{tile.label[0]}{int(tile.label[1])+1}"
        cx, cy = origin + tile.width + OVERLAP_MM / 2, origin + tile.height / 2
        page += f'<path d="M{origin+tile.width} {origin}v{h}" stroke-width="0.3" stroke-dasharray="0.5 1"/>'
        page += f'<g transform="translate({cx} {cy}) rotate(-90)"><rect x="-54" y="-2.5" width="108" height="5" fill="white" stroke="none"/><text text-anchor="middle" font-size="2.8" y="1">ZAKŁADKA 10 mm · KLEJ / TAŚMA · POD {next_label}</text></g>'
    if tile.bottom:
        next_label = f"{chr(ord(tile.label[0])+1)}{tile.label[1]}"
        cy = origin + tile.height + OVERLAP_MM / 2
        page += f'<path d="M{origin} {origin+tile.height}h{w}" stroke-width="0.3" stroke-dasharray="0.5 1"/>'
        page += f'<rect x="{origin+60}" y="{cy-2.5}" width="130" height="5" fill="white" stroke="none"/><text x="{origin+125}" y="{cy+1}" text-anchor="middle" font-size="2.8">ZAKŁADKA 10 mm · KLEJ / TAŚMA · POD {next_label}</text>'
    # Outer boundary is the only cut line. Do not cut the dotted join boundaries.
    page += f'<rect x="{origin}" y="{origin}" width="{w}" height="{h}" stroke-width="0.3" stroke-dasharray="3 1.5"/>'
    for x in (origin, origin + w):
        for y in (origin, origin + h):
            dx, dy = (-1 if x == origin else 1), (-1 if y == origin else 1)
            page += (
                f'<path d="M{x+dx} {y}h{dx*3}M{x} {y+dy}v{dy*3}" stroke-width="0.2"/>'
            )
    corrected = (
        f'<g data-print-scale="{PRINT_SCALE:.10f}" '
        f'transform="translate({PAGE_ORIGIN_MM} {PAGE_ORIGIN_Y_MM}) scale({PRINT_SCALE:.10f})">'
        f'{page}</g>'
    )
    return svg(header + corrected, "0 0 297 210", "297mm", "210mm")


def document(body: str, orientation: str) -> str:
    return f"""<!doctype html><html lang="pl"><meta charset="utf-8"><title>Arena i karty — druk A4</title>
<style>@page{{size:A4 {orientation};margin:0}}*{{box-sizing:border-box}}body{{margin:0;color:#000;background:#fff;font:10pt Arial,sans-serif}}
.sheet{{break-after:page;width:297mm;height:210mm;overflow:hidden}}.sheet:last-child{{break-after:auto}}svg{{display:block}}
.guide{{padding:14mm 16mm;width:210mm;height:297mm;overflow:hidden;font-size:9.5pt}}h1{{font-size:23pt;margin:0 0 3mm}}h2{{font-size:12pt;margin:4mm 0 2mm}}
p{{margin:2mm 0;line-height:1.35}}ol{{padding-left:5mm;line-height:1.4;margin:2mm 0}}li{{margin-bottom:1.5mm}}.small{{font-size:8.5pt}}table{{width:100%;border-collapse:collapse}}td{{padding:1.4mm 2mm;border-bottom:0.2mm solid #000}}.two{{display:grid;grid-template-columns:1fr 1fr;gap:6mm}}.note{{border:0.3mm solid black;padding:2.5mm;margin:3mm 0}}</style>{body}</html>"""


def guide(body: str, hero_pages: list[tuple[str, int, int]]) -> str:
    overview = body
    for tile in tiles():
        overview += f'<rect x="{tile.x}" y="{tile.y}" width="{tile.width}" height="{tile.height}" stroke-width="2" stroke-dasharray="9 5"/><rect x="{tile.x+6}" y="{tile.y+6}" width="42" height="25" fill="white" stroke="none"/><text x="{tile.x+11}" y="{tile.y+25}" font-size="20" font-weight="bold">{tile.label}</text>'
    overview_svg = svg(overview, "-2 -2 754 504", "88mm", "59mm")
    rows = "".join(
        f"<tr><td>{escape(name)}</td><td>{start}–{start+count-1}</td></tr>"
        for name, start, count in hero_pages
    )
    return document(
        f"""<main class="guide">
<h1>Arena Nessy + karty postaci</h1><p>Czarno-biały komplet do testów · A4 · 7 bohaterów · 77 zdolności</p>
<div class="note"><b>Drukuj jednostronnie, w skali 100% / „rzeczywisty rozmiar”.</b><br>
Wyłącz „dopasuj do strony”. Papier A4, automatyczny obrót stron, druk czarno-biały.
Mapa: poziomo. Instrukcja, teren i karty: pionowo.<br><b>Korekta pomiaru 244 → 250: +2,46% jest już w pliku.</b> Nie dodawaj jej ponownie w ustawieniach druku.</div>
<h2>Najpierw sprawdź skalę</h2><p>Wydrukuj tę stronę i zmierz odcinek: musi mieć <b>50 mm</b>.
Kwadrat ma bok <b>25 mm</b> — tyle samo co pole planszy. Dopiero wtedy drukuj resztę.</p>
{svg(f'<g data-print-scale="{PRINT_SCALE:.10f}" transform="scale({PRINT_SCALE:.10f})"><path d="M2 7h50M2 4v6M52 4v6" stroke-width="0.3"/><text x="27" y="14" text-anchor="middle" font-size="3.5">50 mm</text><rect x="65" y="1" width="25" height="25" stroke-width="0.2"/></g><text x="100" y="10" font-size="3.5">Gotowa plansza: 750 × 500 mm</text><text x="100" y="16" font-size="3.5">30 × 20 pól; dolne runy nieaktywne.</text>', '0 0 178 28', '178mm', '28mm')}
<h2>Składanie mapy · strony 2–10</h2>
<div class="two"><div>{overview_svg}<p class="small">Układ arkuszy: A1–A3 u góry, B1–B3 w środku, C1–C3 na dole. Panel znajduje się na dolnym brzegu.</p></div>
<div><ol><li>Wytnij każdy arkusz po <b>przerywanym obwodzie</b>. Zachowaj podpisane pasy zakładki.</li>
<li>Linia z <b>drobnych kropek</b> wyznacza miejsce przyłożenia następnej części. <b>Nie przecinaj jej.</b></li>
<li>Najpierw sklej rzędy: A1 → A2 → A3; analogicznie B i C. Potem nałóż rząd B na A, a C na B.</li>
<li>Posmaruj zakładkę klejem lub użyj taśmy dwustronnej. Następny arkusz przykrywa cały pas 10 mm.</li></ol></div></div>
<p class="small">Zakładka powtarza fragment sąsiedniej części. Dopasuj linie siatki; napisy o kleju mają zniknąć pod następnym arkuszem. Zwykłą taśmę można przykleić od spodu po spasowaniu części. Nie dodawaj zakładek do wymiaru gotowej mapy.</p>
<h2>Teren do wycięcia · strona 11</h2>
<p class="small">Wytnij osobne znaczniki 25 × 25 mm. Podczas setupu połóż wskazany rodzaj na podświetlonych polach: zasłonę, skrzynie, filar, niską osłonę lub gruz. Nie przyklejaj ich do planszy.</p>
<p class="small">Plansza jest pusta. Bohatera, Nessę, kukły i ewentualnego pomocnika ustawiaj jako figurki zgodnie z setupem w aplikacji. Na mapie nie ma ich stałych pozycji.</p>
<h2>Karty do wycięcia · strony {hero_pages[0][1]}–{hero_pages[-1][1]+hero_pages[-1][2]-1}</h2>
<div class="two"><table><tr><td><b>Bohater</b></td><td><b>Strony PDF</b></td></tr>{rows}</table><div>
<p class="small">Każdy zestaw zawiera statystyki, pasywy, skazę, pełny repertuar zdolności oraz zasady many. Tnij karty po ich obrysach; arkusze informacyjne zostaw w całości. Bez rewersów.</p>
<p class="small">Symbole na kartach odpowiadają panelowi: ruch, atak, zmiana broni, przedmiot, puste pole, koniec tury; dalej 20 run oraz − / + / zatwierdź / wróć.</p>
<p class="small">Wydruk panelu służy do testów układu. Podłączenie całej obsługi aplikacji do panelu jest osobnym etapem wdrożenia.</p></div></div>
</main>""",
        "portrait",
    )


def pdf_pages(path: Path) -> int:
    info = subprocess.run(
        ["pdfinfo", str(path)], capture_output=True, text=True, check=True, timeout=15
    ).stdout
    return int(
        next(
            line.split(":")[1]
            for line in info.splitlines()
            if line.startswith("Pages:")
        )
    )


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    parts = OUTPUT / "parts"
    parts.mkdir(exist_ok=True)
    data = json.loads(
        (ROOT / "content/scenarios/recruitment_arena_combat.json").read_text()
    )
    body = map_body(data)
    (OUTPUT / "arena_bw_750x500mm.svg").write_text(
        svg(body, "0 0 750 500", "750mm", "500mm")
    )
    map_html = parts / "arena_A4.html"
    map_html.write_text(
        document(
            "".join(
                f'<section class="sheet">{tile_svg(t, body)}</section>' for t in tiles()
            ),
            "landscape",
        )
    )
    map_pdf = parts / "arena_A4.pdf"
    render_pdf(map_html, map_pdf)
    if pdf_pages(map_pdf) != 9:
        raise RuntimeError("Mapa musi mieć dokładnie 9 stron.")
    print("Arena: 9 arkuszy A4, zakładki 10 mm", flush=True)
    hero_pdfs = []
    hero_pages = []
    terrain_html, terrain_pdf = parts / "teren.html", parts / "teren.pdf"
    terrain_html.write_text(terrain_document(data))
    render_pdf(terrain_html, terrain_pdf)
    if pdf_pages(terrain_pdf) != 1:
        raise RuntimeError("Znaczniki terenu muszą zmieścić się na jednej stronie.")
    next_page = 12
    for hero_id in PLAYABLE_HERO_IDS:
        hero = build_print_hero(hero_id)
        html, pdf = parts / f"{hero_id}.html", parts / f"{hero_id}.pdf"
        html.write_text(render_hero_html(hero, "bw_test"))
        render_pdf(html, pdf)
        count = pdf_pages(pdf)
        hero_pages.append((hero.name, next_page, count))
        next_page += count
        hero_pdfs.append(pdf)
        print(f"{hero.name}: {count} stron", flush=True)
    guide_html, guide_pdf = parts / "instrukcja.html", parts / "instrukcja.pdf"
    guide_html.write_text(guide(body, hero_pages))
    render_pdf(guide_html, guide_pdf)
    if pdf_pages(guide_pdf) != 1:
        raise RuntimeError("Instrukcja musi zmieścić się na jednej stronie.")
    destination = OUTPUT / "arena_i_karty_A4_czarno_biale.pdf"
    merge_pdfs([guide_pdf, map_pdf, terrain_pdf, *hero_pdfs], destination)
    if pdf_pages(destination) != next_page - 1:
        raise RuntimeError("Nieprawidłowa liczba stron pakietu.")
    (OUTPUT / "manifest.json").write_text(
        json.dumps(
            {
                "pdf": destination.name,
                "pages": next_page - 1,
                "cell_mm": CELL_MM,
                "print_scale": PRINT_SCALE,
                "pdf_cell_mm": CELL_MM * PRINT_SCALE,
                "calibration": {"measured": 244, "target": 250},
                "tile_origin_mm": [PAGE_ORIGIN_MM, PAGE_ORIGIN_Y_MM],
                "board_mm": [BOARD_WIDTH_MM, BOARD_HEIGHT_MM],
                "overlap_mm": OVERLAP_MM,
                "orientation": "clockwise",
                "panel_blank_slot": 4,
                "blank_map": True,
                "terrain_page": 11,
                "terrain_tokens": terrain_inventory(data),
                "tiles": [asdict(t) for t in tiles()],
                "heroes": [
                    {"name": n, "first_page": p, "pages": c} for n, p, c in hero_pages
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    print(f"Gotowe: {destination} ({next_page-1} stron)", flush=True)


if __name__ == "__main__":
    main()
