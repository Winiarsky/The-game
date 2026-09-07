"""Generate the current profile's colored and low-ink character materials."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dnd_board_game.physical_cards.mana_print_files import main

if __name__ == "__main__":
    raise SystemExit(main())
