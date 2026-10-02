from __future__ import annotations

import argparse
from pathlib import Path

from dnd_board_game.physical_cards.hero_card_sheet import generate_hero_card_sheet


def main() -> int:
    """Build the current monochrome handouts from the canonical catalog."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from build_rune_relations import main as build_current
    build_current()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
