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


def test_bandit_cave_entrance_loads_with_closed_top_right_and_bottom_walls():
    game = Game(conn=DummyConnection(), scenario="bandit_cave_cave_entrance")

    assert game.board.get_wall((0, 3), (0, 4)) is not None
    assert game.board.get_wall((9, 3), (9, 4)) is not None
    assert game.board.get_wall((18, 3), (18, 4)) is not None
    assert game.board.get_wall((18, 4), (19, 4)) is not None
    assert game.board.get_wall((18, 9), (19, 9)) is not None
    assert game.board.get_wall((18, 13), (19, 13)) is not None
    assert game.board.get_wall((0, 13), (0, 14)) is not None
    assert game.board.get_wall((9, 13), (9, 14)) is not None
    assert game.board.get_wall((18, 13), (18, 14)) is not None


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


def _assert_goblin_pack(game, *, expected_positions: dict[str, tuple[int, int]]) -> None:
    enemy_types = sorted(enemy.__class__.__name__ for enemy in game.enemies)
    assert enemy_types == ["GoblinCommando", "GoblinDog", "GoblinWarrior", "GoblinWarrior"]

    enemy_positions = {getattr(enemy, "name", ""): getattr(enemy, "position", None) for enemy in game.enemies}
    assert enemy_positions == expected_positions


def test_goblin_skirmish_scenario_loads_enemy_objects_and_cover_layout():
    game = Game(conn=DummyConnection(), scenario="goblin_skirmish")

    assert game.scenario["starting_positions"] == [
        [1, 11],
        [2, 11],
        [3, 11],
        [1, 12],
        [2, 12],
        [3, 12],
    ]

    _assert_goblin_pack(
        game,
        expected_positions={
            "Goblin Commando": (14, 3),
            "Goblin Dog": (18, 10),
            "Goblin Warrior A": (10, 11),
            "Goblin Warrior B": (16, 8),
        },
    )

    assert game.board.cell_at((6, 5)).field.walkable is False
    forest = game.board.cell_at((14, 3)).field
    assert forest.__class__.__name__ == "ForestTerrain"
    assert getattr(forest, "cover_type", None) == "standard"
    assert int(getattr(game.board.cell_at((17, 9)).field, "move_cost_bonus_feet", 0) or 0) == 5
    assert game.board.occupant_at((4, 6)).__class__.__name__ == "SimpleObstacle"
    assert game.board.get_wall((5, 6), (6, 6)) is not None
    assert game.board.get_wall((10, 11), (10, 12)) is not None


def test_goblin_skirmish_arena_loads_with_open_cover_islands():
    game = Game(conn=DummyConnection(), scenario="goblin_skirmish_arena")

    assert game.scenario["starting_positions"] == [
        [1, 12],
        [2, 12],
        [3, 12],
        [1, 13],
        [2, 13],
        [3, 13],
    ]

    _assert_goblin_pack(
        game,
        expected_positions={
            "Goblin Commando": (10, 2),
            "Goblin Dog": (18, 7),
            "Goblin Warrior A": (8, 7),
            "Goblin Warrior B": (13, 7),
        },
    )

    assert game.board.cell_at((6, 4)).field.walkable is False
    north_cover = game.board.cell_at((10, 2)).field
    assert north_cover.__class__.__name__ == "ForestTerrain"
    assert int(getattr(game.board.cell_at((17, 7)).field, "move_cost_bonus_feet", 0) or 0) == 5
    assert game.board.occupant_at((3, 5)).__class__.__name__ == "SimpleObstacle"
    assert game.board.get_wall((10, 2), (10, 3)) is not None


def test_goblin_skirmish_ambush_loads_with_chokepoint_and_flank_route():
    game = Game(conn=DummyConnection(), scenario="goblin_skirmish_ambush")

    assert game.scenario["starting_positions"] == [
        [0, 8],
        [1, 8],
        [2, 8],
        [0, 9],
        [1, 9],
        [2, 9],
    ]

    _assert_goblin_pack(
        game,
        expected_positions={
            "Goblin Commando": (15, 3),
            "Goblin Dog": (18, 5),
            "Goblin Warrior A": (7, 8),
            "Goblin Warrior B": (13, 6),
        },
    )

    assert game.board.cell_at((6, 4)).field.walkable is False
    ambush_cover = game.board.cell_at((15, 3)).field
    assert ambush_cover.__class__.__name__ == "ForestTerrain"
    assert int(getattr(game.board.cell_at((17, 4)).field, "move_cost_bonus_feet", 0) or 0) == 5
    assert game.board.occupant_at((12, 5)).__class__.__name__ == "SimpleObstacle"
    assert game.board.get_wall((15, 3), (15, 4)) is not None


def test_goblin_skirmish_flank_lab_loads_with_split_lanes_for_ai_debug():
    game = Game(conn=DummyConnection(), scenario="goblin_skirmish_flank_lab")

    assert game.scenario["starting_positions"] == [
        [0, 6],
        [1, 6],
        [2, 6],
        [0, 7],
        [1, 7],
        [2, 7],
    ]

    _assert_goblin_pack(
        game,
        expected_positions={
            "Goblin Commando": (16, 2),
            "Goblin Dog": (18, 11),
            "Goblin Warrior A": (7, 8),
            "Goblin Warrior B": (12, 7),
        },
    )

    assert game.board.cell_at((8, 5)).field.walkable is False
    perch_cover = game.board.cell_at((16, 2)).field
    assert perch_cover.__class__.__name__ == "ForestTerrain"
    assert int(getattr(game.board.cell_at((17, 10)).field, "move_cost_bonus_feet", 0) or 0) == 5
    assert game.board.occupant_at((6, 4)).__class__.__name__ == "SimpleObstacle"
    assert game.board.get_wall((15, 3), (16, 3)) is not None


def test_goblin_skirmish_dense_ruins_loads_with_fragmented_cover_layout():
    game = Game(conn=DummyConnection(), scenario="goblin_skirmish_dense_ruins")

    assert game.scenario["starting_positions"] == [
        [0, 11],
        [1, 11],
        [2, 11],
        [0, 12],
        [1, 12],
        [2, 12],
    ]

    _assert_goblin_pack(
        game,
        expected_positions={
            "Goblin Commando": (16, 3),
            "Goblin Dog": (18, 10),
            "Goblin Warrior A": (7, 9),
            "Goblin Warrior B": (14, 7),
        },
    )

    assert game.board.cell_at((4, 4)).field.walkable is False
    dense_cover = game.board.cell_at((12, 3)).field
    assert dense_cover.__class__.__name__ == "ForestTerrain"
    assert int(getattr(game.board.cell_at((16, 10)).field, "move_cost_bonus_feet", 0) or 0) == 5
    assert game.board.occupant_at((11, 5)).__class__.__name__ == "SimpleObstacle"
    assert game.board.get_wall((16, 3), (16, 4)) is not None


def test_goblin_skirmish_tight_chokepoints_loads_with_forced_corridors():
    game = Game(conn=DummyConnection(), scenario="goblin_skirmish_tight_chokepoints")

    assert game.scenario["starting_positions"] == [
        [0, 7],
        [1, 7],
        [2, 7],
        [0, 8],
        [1, 8],
        [2, 8],
    ]

    _assert_goblin_pack(
        game,
        expected_positions={
            "Goblin Commando": (17, 4),
            "Goblin Dog": (18, 12),
            "Goblin Warrior A": (7, 8),
            "Goblin Warrior B": (13, 7),
        },
    )

    assert game.board.cell_at((5, 3)).field.walkable is False
    corridor_cover = game.board.cell_at((17, 5)).field
    assert corridor_cover.__class__.__name__ == "ForestTerrain"
    assert int(getattr(game.board.cell_at((13, 8)).field, "move_cost_bonus_feet", 0) or 0) == 5
    assert game.board.occupant_at((16, 6)).__class__.__name__ == "SimpleObstacle"
    assert game.board.get_wall((17, 4), (17, 5)) is not None
