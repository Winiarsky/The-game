from pathlib import Path
import sys
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.Interactables.loot_pile import LootPile
from combat.damage_utils import cleanup_defeated_enemies, remove_defeated_enemy


class BoardStub:
    def __init__(self):
        self.occupants = {}
        self.interactables = {}
        self.removed = []

    def occupant_at(self, pos):
        return self.occupants.get(pos)

    def remove(self, pos):
        self.removed.append(pos)
        self.occupants.pop(pos, None)

    def add_interactable(self, interactable, position):
        self.interactables.setdefault(position, []).append(interactable)
        setter = getattr(interactable, "set_position", None)
        if callable(setter):
            setter(position)

    def interactables_at(self, position):
        return list(self.interactables.get(position, []))


class EnemyStub:
    def __init__(self, *, pos=(1, 1), hp=0, loot_items=None, loot_cp=0):
        self.position = pos
        self.hp = hp
        self.loot_items = list(loot_items or [])
        self.loot_cp = int(loot_cp)
        self.inventory = []
        self.coin_pouch = {}
        self.statuses = []

    def has_status(self, status_id):
        return False


def test_remove_defeated_enemy_drops_loot_pile_and_removes_enemy():
    board = BoardStub()
    item = SimpleNamespace(name="Sztylet", item_id="dagger", category="weapon")
    enemy = EnemyStub(loot_items=[item], loot_cp=35)
    board.occupants[enemy.position] = enemy
    logs = []
    game = SimpleNamespace(board=board, enemies=[enemy], heroes=[], ui_log=lambda message, **kwargs: logs.append((message, kwargs)))

    result = remove_defeated_enemy(game, enemy, source="test")

    assert result["removed_from_list"] is True
    assert result["removed_from_board"] is True
    assert result["loot_dropped"] == 2
    assert enemy not in game.enemies
    assert enemy.position is None
    assert (1, 1) in board.removed
    piles = [obj for obj in board.interactables_at((1, 1)) if isinstance(obj, LootPile)]
    assert len(piles) == 1
    loot_ids = {getattr(item, "item_id", None) for item in piles[0].loot_items}
    assert "dagger" in loot_ids
    currency_entries = [
        entry
        for entry in piles[0].loot_items
        if isinstance(entry, dict) and str(entry.get("kind", "")).lower() == "currency_cp"
    ]
    assert currency_entries and int(currency_entries[0].get("amount_cp", 0) or 0) == 35
    assert logs
    message, kwargs = logs[-1]
    assert "zostaje loot" in message.lower()
    communication = kwargs.get("communication") or {}
    assert "Jak zebrać loot" in str(communication.get("details_markdown") or "")


def test_cleanup_defeated_enemies_removes_only_dead_targets():
    board = BoardStub()
    dead_enemy = EnemyStub(pos=(1, 1), hp=0, loot_cp=10)
    live_enemy = EnemyStub(pos=(2, 2), hp=6)
    board.occupants[(1, 1)] = dead_enemy
    board.occupants[(2, 2)] = live_enemy
    game = SimpleNamespace(board=board, enemies=[dead_enemy, live_enemy], heroes=[])

    removed = cleanup_defeated_enemies(game, source="cleanup:test")

    assert removed == 1
    assert dead_enemy not in game.enemies
    assert live_enemy in game.enemies
    piles = [obj for obj in board.interactables_at((1, 1)) if isinstance(obj, LootPile)]
    assert len(piles) == 1
