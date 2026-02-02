import sys
from pathlib import Path
import types

import pytest
import importlib

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

basic_melee = importlib.import_module("GameObjects.Enemies.behaviors.basic_melee")
basic_melee_flanking = importlib.import_module("GameObjects.Enemies.behaviors.basic_melee_flanking")
from GameObjects.events.base import EventResult


class FakeBoard:
    def __init__(self, hero):
        self.hero = hero

    def get_neighbors(self, pos, include_position=False, diagonal=True):
        return [(0, 0)]

    def occupant_at(self, pos):
        if pos == getattr(self.hero, "position", None):
            return self.hero
        return None

    def in_bounds(self, pos):
        return True

    def is_blocked(self, a, b):
        return False

    def edge_interactables_between(self, a, b):
        return []

    def can_enter(self, pos, allow_occupied=False):
        return True


class FakeGame:
    def __init__(self):
        self.heroes = []
        self.enemies = []
        self.board = None


def test_basic_melee_uses_events(monkeypatch):
    calls = []

    def fake_dispatch(name, ctx):
        calls.append(name)
        return EventResult(success=True, consumed_action=True)

    monkeypatch.setattr(basic_melee, "dispatch_event", fake_dispatch)

    hero = types.SimpleNamespace(position=(0, 0))
    enemy = types.SimpleNamespace(name="Enemy", position=(1, 0), move_points=3)

    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board = FakeBoard(hero)

    used = basic_melee.basic_melee(enemy, game, combat_state=None, actions_left=1)

    assert used == 1
    assert "enemy_attack_melee" in calls or "enemy_move" in calls


def test_basic_melee_flanking_uses_events(monkeypatch):
    calls = []

    def fake_dispatch(name, ctx):
        calls.append(name)
        return EventResult(success=True, consumed_action=True)

    monkeypatch.setattr(basic_melee_flanking, "dispatch_event", fake_dispatch)

    hero = types.SimpleNamespace(position=(0, 0))
    enemy = types.SimpleNamespace(name="Enemy", position=(1, 0), move_points=3)

    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board = FakeBoard(hero)

    used = basic_melee_flanking.basic_melee_flanking(enemy, game, combat_state=None, actions_left=1)

    assert used == 1
    assert calls  # at least one dispatch attempted
