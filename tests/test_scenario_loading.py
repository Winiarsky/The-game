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


def test_karczma_scenario_loads_trade_npcs_with_default_inventory():
    game = Game(conn=DummyConnection(), scenario="karczma")

    merchant_classes = {
        "InnkeeperNPC",
        "WeaponMerchantNPC",
        "ArmorerNPC",
        "AlchemistNPC",
        "MageNPC",
        "PriestNPC",
    }
    found: dict[str, int] = {}
    for row in range(game.board.rows):
        for col in range(game.board.cols):
            for obj in game.board.cell_at((col, row)).interactables:
                cls_name = obj.__class__.__name__
                if cls_name not in merchant_classes:
                    continue
                found[cls_name] = len(list(getattr(obj, "inventory", []) or []))

    missing = sorted(merchant_classes.difference(found.keys()))
    assert not missing, f"Brakuje handlarzy w scenariuszu karczma: {missing}"
    for cls_name, inv_count in found.items():
        assert inv_count > 0, f"{cls_name} powinien mieć domyślny asortyment (inventory)."
