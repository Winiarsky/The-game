"""Build the current monochrome PDFs in handouts/, with intermediates in .cache/."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]

from build_equipment_cards import document, mission_item_cards
from build_mission_zero_handouts import render as render_handout
from dnd_board_game.physical_cards.handout_files import (
    HANDOUT_BUILD_ROOT, HANDOUTS_ROOT, compact_pdf, pdf_pages, publish_pdf,
)
from dnd_board_game.physical_cards.mana_print_files import render_pdf
from dnd_board_game.physical_cards.handout_maps import PRINT_SCALE
from dnd_board_game.physical_cards.scenario_cutouts import build_cutouts, render_document
from dnd_board_game.scenarios.mission_pack import local_path

MISSION = ROOT / 'content/scenarios/misja_0_dzwon'


def mission_documents(pack: Path, work: Path) -> tuple[dict[str, str], dict[str, Any]]:
    """Derive current tiles, item cards and letters solely from editable sources."""
    spec = json.loads((pack / 'maps/cutouts.json').read_text(encoding='utf-8'))
    battle = json.loads((pack / 'mechanics/battle.json').read_text(encoding='utf-8'))
    tokens = build_cutouts(spec, battle)
    artwork: dict[str, str] = {}
    for token in tokens:
        if token.artwork:
            path = local_path(pack, token.artwork)
            if not path.is_file():
                raise FileNotFoundError(path)
            artwork[token.id] = path.as_uri() if path.suffix == '.png' else path.read_text(encoding='utf-8')
    tiles = render_document(tokens, spec['cell_mm'] * PRINT_SCALE, True, artwork)
    tiles = tiles.replace('Kalibracja areny 250/244; po wydruku 4 pola powinny mieć 100 mm.',
        'Skala wspólna z map_a4.pdf i map_full.pdf: (250/244) × 1,03.')
    tiles = tiles.replace('kalibracja areny 250/244', 'wspólna skala planszy +3%')
    tiles = tiles.replace('Odcinek kontrolny: 100 mm na skalibrowanym wydruku.',
        'Odcinek kontrolny: 4 pola; porównaj z planszą i czujnikami.')
    tiles = tiles.replace('svg{display:block}', 'svg{display:block}image{filter:grayscale(1)}')
    found, identified = mission_item_cards(pack, work)
    items = document([*found, identified], 'Misja 0 — przedmioty do wycięcia')
    # The test edition remains monochrome even if a source illustration is updated.
    items = items.replace('.art img{', '.art img{filter:grayscale(1);')
    letters = json.loads((pack / 'text/handouts.json').read_text(encoding='utf-8'))
    documents = dict(tiles=tiles, items=items,
                     order=render_handout(letters['order']), receipts=render_handout(letters['receipts']))
    metadata = dict(print_scale=PRINT_SCALE, cell_mm=spec['cell_mm'], pdf_cell_mm=spec['cell_mm'] * PRINT_SCALE,
                    cutout_ids=[tile.id for tile in tokens], item_cards=len(found) + 1)
    return documents, metadata


def build_mission(*, output: Path = HANDOUTS_ROOT, work: Path = HANDOUT_BUILD_ROOT / 'mission_0',
                  pack: Path = MISSION, html_only: bool = False) -> dict[str, Path]:
    work.mkdir(parents=True, exist_ok=True)
    documents, metadata = mission_documents(pack, work)
    generated: dict[str, Path] = {}
    expected = dict(tiles=7, items=1, order=1, receipts=1)
    for name, html in documents.items():
        source = work / f'{name}.html'
        source.write_text(html, encoding='utf-8')
        if html_only:
            generated[name] = source
            continue
        pdf = source.with_suffix('.pdf')
        render_pdf(source, pdf)
        if pdf_pages(pdf) != expected[name]:
            raise RuntimeError(f'{name}: oczekiwano {expected[name]} stron.')
        compact_pdf(pdf)
        generated[name] = pdf
    (work / 'manifest.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if html_only:
        return generated
    # Validate every section before replacing the public Mission 0 materials.
    return {name: publish_pdf(path, output / 'mission_0' / f'{name}.pdf', expected_pages=expected[name])
            for name, path in generated.items()}


def build(*, output: Path = HANDOUTS_ROOT, work: Path = HANDOUT_BUILD_ROOT, only: str | None = None) -> None:
    aliases = {'heroes': 'characters', 'mission': 'mission_0', 'aid': 'reference'}
    only = aliases.get(only, only)
    if only not in {None, 'characters', 'maps', 'mission_0', 'reference'}:
        raise ValueError('Nieznana część materiałów do druku.')
    if only in {None, 'maps'}:
        from build_handout_maps import build_maps
        build_maps(output=output, work=work / 'maps')
    if only in {None, 'characters'}:
        from build_rune_relations import build as build_characters
        build_characters(output=work / 'characters', publish_root=output)
    if only == 'reference':
        from build_rune_relations import build_aid
        build_aid(output=work / 'reference', publish_root=output)
    if only in {None, 'mission_0'}:
        for path in build_mission(output=output, work=work / 'mission_0').values():
            print(path.relative_to(output), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', choices=('characters', 'maps', 'mission_0', 'reference', 'heroes', 'mission', 'aid'))
    parser.add_argument('--output', type=Path, default=HANDOUTS_ROOT)
    parser.add_argument('--work', type=Path, default=HANDOUT_BUILD_ROOT)
    args = parser.parse_args()
    build(output=args.output, work=args.work, only=args.only)


if __name__ == '__main__':
    main()
