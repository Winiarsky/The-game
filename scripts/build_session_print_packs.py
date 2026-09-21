"""Build Mission 0 A4 packs: scenery/handouts, hero sheets, rules, and markers."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from build_equipment_cards import document, mission_item_cards
from build_mission_zero_handouts import render as render_handout
from dnd_board_game.physical_cards.mana_print_files import merge_pdfs, render_pdf
from dnd_board_game.physical_cards.scenario_cutouts import build_cutouts, render_document
from dnd_board_game.scenarios.mission_pack import local_path

MISSION = ROOT / 'content/scenarios/misja_0_dzwon'


def pdf_pages(path: Path) -> int:
    info = subprocess.run(['pdfinfo', str(path)], check=True, capture_output=True,
                          text=True, timeout=15).stdout
    return int(next(line.split(':', 1)[1] for line in info.splitlines()
                    if line.startswith('Pages:')))


def write_part(folder: Path, name: str, html: str) -> Path:
    source = folder / f'{name}.html'
    source.write_text(html, encoding='utf-8')
    target = source.with_suffix('.pdf')
    render_pdf(source, target)
    return target


def assemble(destination: Path, parts: list[tuple[str, Path]], **metadata: Any) -> None:
    sections = []
    next_page = 1
    for title, path in parts:
        count = pdf_pages(path)
        sections.append(dict(title=title, first_page=next_page,
                             last_page=next_page + count - 1, pages=count))
        next_page += count
    merge_pdfs([path for _, path in parts], destination)
    if pdf_pages(destination) != next_page - 1:
        raise RuntimeError('Nieprawidłowa liczba stron kompletnego pakietu.')
    # Use the same 300 dpi print optimization as hero sheets; preserve page
    # geometry and calibration while making the publishable map packs smaller.
    from build_hero_mats import compact_pdf
    compact_pdf(destination)
    manifest = dict(pdf=destination.name, pages=next_page - 1, sections=sections, **metadata)
    destination.with_suffix('.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = [f'# {destination.stem}', '', 'A4 · jednostronnie · skala 100%, bez dopasowania.', '',
             '| Zawartość | Strony PDF |', '| --- | --- |']
    lines += [f'| {s["title"]} | {s["first_page"]}–{s["last_page"]} |' for s in sections]
    destination.with_suffix('.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'{destination}: {next_page - 1} stron', flush=True)


def build_mission(*, nominal: bool = False) -> Path:
    output = MISSION / 'print'
    output.mkdir(parents=True, exist_ok=True)
    destination = output / ('misja_0_komplet_A4_25mm.pdf' if nominal else 'misja_0_komplet_A4.pdf')
    spec = json.loads((MISSION / 'maps/cutouts.json').read_text())
    battle = json.loads((MISSION / 'mechanics/battle.json').read_text())
    tokens = build_cutouts(spec, battle)
    scale = 1 if nominal else spec['print_scale']
    artwork = {}
    for token in tokens:
        if token.artwork:
            path = local_path(MISSION, token.artwork)
            if not path.is_file():
                raise FileNotFoundError(path)
            artwork[token.id] = path.as_uri() if path.suffix == '.png' else path.read_text()
    handouts = json.loads((MISSION / 'print/handouts.json').read_text())
    with TemporaryDirectory(prefix='session-print-') as temporary:
        folder = Path(temporary)
        parts = [('Elementy planszy — instrukcja, rozmieszczenie i kafle', write_part(
            folder, 'kafle', render_document(tokens, spec['cell_mm'] * scale, scale != 1, artwork)))]
        for key, title in [('order', 'Handout — rozkaz Nessy'), ('receipts', 'Handout — pokwitowania Boruta')]:
            parts.append((title, write_part(folder, key, render_handout(handouts[key]))))
        found, identified = mission_item_cards(MISSION, folder)
        parts.append(('Handouty — przedmioty, medalik i obie karty pierścienia', write_part(
            folder, 'przedmioty', document([*found, identified], 'Misja 0 · przedmioty do wycięcia'))))
        assemble(destination, parts, print_scale=scale, cell_mm=spec['cell_mm'],
                 tile_ids=[t.id for t in tokens], item_cards=7)
    return destination


def build_heroes() -> Path:
    from build_hero_mats import build_pack
    return build_pack()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', choices=('mission', 'heroes', 'aid'))
    parser.add_argument('--nominal', action='store_true', help='Kafle 25 mm bez korekty drukarki.')
    args = parser.parse_args()
    if args.only in (None, 'mission'):
        build_mission(nominal=args.nominal)
    if args.only in (None, 'heroes'):
        build_heroes()
    if args.only == 'aid':
        from build_hero_mats import build_player_aid
        build_player_aid()


if __name__ == '__main__':
    main()
