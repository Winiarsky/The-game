from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import GameObjects.events.all_events  # noqa: F401
from GameObjects.events.base import EventContext
from GameObjects.events.elixirs.smokestick_event import SmokestickEvent
from GameObjects.events.registry import list_events
from GameObjects.items.inventory import add_alchemical_item, has_ready_alchemical_item
from economy import item_cost_cp


class _Hero:
    def __init__(self, pos=(0, 0)):
        self.position = pos
        self.inventory = []
        self.statuses = []

    def add_status(self, status):
        self.statuses.append(status)
        return True

    def remove_status(self, status):
        sid = getattr(status, "id", status)
        self.statuses = [item for item in self.statuses if getattr(item, "id", item) != sid]
        return True


class _Enemy:
    def __init__(self, pos=(1, 0)):
        self.position = pos
        self.statuses = []

    def add_status(self, status):
        self.statuses.append(status)
        return True

    def remove_status(self, status):
        sid = getattr(status, "id", status)
        self.statuses = [item for item in self.statuses if getattr(item, "id", item) != sid]
        return True


class _Board:
    def __init__(self, hero, enemy):
        self.hero = hero
        self.enemy = enemy

    def occupant_at(self, pos):
        if tuple(pos) == tuple(self.hero.position):
            return self.hero
        if tuple(pos) == tuple(self.enemy.position):
            return self.enemy
        return None

    def get_neighbors(self, pos, include_position=False, diagonal=True):
        del include_position, diagonal
        x, y = pos
        return [
            (x + 1, y),
            (x - 1, y),
            (x, y + 1),
            (x, y - 1),
            (x + 1, y + 1),
            (x + 1, y - 1),
            (x - 1, y + 1),
            (x - 1, y - 1),
        ]


def _has_concealed(actor) -> bool:
    return any(getattr(status, "id", None) == "concealed" for status in list(getattr(actor, "statuses", []) or []))


def test_crb_alchemical_gear_core_events_are_registered():
    registered = set(list_events().keys())
    expected = {
        "acidflask",
        "alchemists_fire",
        "bottled_lightning",
        "frost_vial",
        "tanglefoot_bag",
        "thunderstone",
        "antidote",
        "antiplague",
        "elixir_of_life",
        "smokestick",
    }
    missing = sorted(expected.difference(registered))
    assert not missing, f"Brakuje eventow alchemicznych z CRB: {missing}"


def test_alchemical_gear_from_crb_has_3gp_price_in_cost_map():
    # 3 gp = 300 cp
    for item_id in (
        "acidflask",
        "alchemists_fire",
        "bottled_lightning",
        "frost_vial",
        "tanglefoot_bag",
        "thunderstone",
        "antidote",
        "antiplague",
        "elixir_of_life",
        "smokestick",
    ):
        assert item_cost_cp(item_id) == 300


def test_acid_flask_alias_maps_to_acidflask_ready_item():
    hero = _Hero()
    item = add_alchemical_item(hero, event_name="acid_flask")
    assert str(getattr(item, "event_name", "")).lower() == "acidflask"
    assert has_ready_alchemical_item(hero, "acidflask") is True
    assert has_ready_alchemical_item(hero, "acid_flask") is True


def test_smokestick_applies_concealed_in_local_area():
    hero = _Hero((0, 0))
    enemy = _Enemy((1, 0))
    board = _Board(hero, enemy)
    game = SimpleNamespace(
        board=board,
        heroes=[hero],
        enemies=[enemy],
        ui_log=lambda *_a, **_k: None,
    )
    add_alchemical_item(hero, event_name="smokestick")
    event = SmokestickEvent()
    result = event.execute(EventContext(game=game, actor=hero))
    assert result.success is True
    assert _has_concealed(hero) is True
    assert _has_concealed(enemy) is True

