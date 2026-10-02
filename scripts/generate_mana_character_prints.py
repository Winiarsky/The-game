"""Generate the current profile's colored and low-ink character materials."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dnd_board_game.physical_cards.mana_print_files import main

def main() -> int:
    """Build the current monochrome handouts from the canonical catalog."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from build_rune_relations import main as build_current
    build_current()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
