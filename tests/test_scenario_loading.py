from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.game import Game


class DummyConnection:
    """Minimalny stub połączenia – bez ruchu po sieci."""

    def set_leds(self, *_args, **_kwargs):
        return None

    def leds_off(self, *_args, **_kwargs):
        return None

    def scan_board(self, *_args, **_kwargs):
        return (0, 0)

    def read_card(self, *_args, **_kwargs):
        return "DECLINE"


def test_karczma_scenario_loads_with_simple_wall():
    game = Game(conn=DummyConnection(), scenario="karczma")
    assert game.board.walls, "Powinny zostać wczytane ściany ze scenariusza karczma"
