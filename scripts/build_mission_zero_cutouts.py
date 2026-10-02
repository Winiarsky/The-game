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
    """Keep the old command while using the current Mission 0 print source."""
    from build_handouts import build_mission
    from dnd_board_game.physical_cards.handout_files import HANDOUTS_ROOT, HANDOUT_BUILD_ROOT
    parser = argparse.ArgumentParser(description="Aktualne materiały Misji 0 w handouts/mission_0.")
    parser.add_argument('--html-only', action='store_true')
    parser.add_argument('--output', type=Path, default=HANDOUTS_ROOT)
    parser.add_argument('--work', type=Path, default=HANDOUT_BUILD_ROOT / 'mission_0')
    args = parser.parse_args()
    for path in build_mission(output=args.output, work=args.work, html_only=args.html_only).values():
        print(path, flush=True)


if __name__=='__main__':
    main()
