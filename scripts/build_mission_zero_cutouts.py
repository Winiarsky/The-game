"""Build framed Mission 0 cutouts from local illustrations and scenario terrain."""
from __future__ import annotations

import argparse
import os
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from dnd_board_game.physical_cards.scenario_cutouts import build_cutouts, render_document
from dnd_board_game.physical_cards.mana_print_files import render_pdf
from dnd_board_game.scenarios.mission_pack import local_path


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--html-only', action='store_true')
    args=parser.parse_args()
    pack=ROOT/'content/scenarios/misja_0_dzwon'
    spec=json.loads((pack/'maps/cutouts.json').read_text())
    battle=json.loads((pack/'mechanics/battle.json').read_text())
    tokens=build_cutouts(spec,battle)
    output=pack/'maps/print'
    artworks={}
    for t in tokens:
        if t.artwork:
            path=local_path(pack,t.artwork)
            artworks[t.id]=(os.path.relpath(path,output) if path.suffix=='.png' else path.read_text())
            if not path.is_file():
                raise FileNotFoundError(path)
    output=pack/'maps/print'
    output.mkdir(parents=True, exist_ok=True)
    for name,scale in [('elements_A4',spec['print_scale']),('elements_A4_25mm',1)]:
        path=output/f'{name}.html'
        path.write_text(render_document(tokens,spec['cell_mm']*scale,scale!=1,artworks))
        if not args.html_only:render_pdf(path,path.with_suffix('.pdf'))
        print(path.with_suffix('.html' if args.html_only else '.pdf'),flush=True)


if __name__=='__main__':
    main()
