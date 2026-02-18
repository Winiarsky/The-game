import sys
from pathlib import Path
import types

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import GameObjects.events.all_events  # noqa: F401  # rejestracja eventów
from GameObjects.events.registry import dispatch_event
from GameObjects.events.base import EventContext
from GameObjects.events.attack import base_attack_range_event
from GameObjects.events.attack import attack_range_long_bow
from GameObjects.Obstacles.simple_obstacle import SimpleObstacle


class FakeEvents:
    def __init__(self):
        self.emitted = []

    def safe_emit_action(self, **payload):
        self.emitted.append(payload)


class FakeConn:
    def __init__(self, choice=None):
        self.choice = choice

    def set_leds(self, *args, **kwargs):
        return None

    def scan_board(self, acceptable_responses=None):
        return self.choice

    def leds_off(self):
        return None


class FakeBoard:
    def __init__(self):
        self.occupants = {}
        self.blocked_edges = set()
        self.edge_objs = {}

    def occupant_at(self, pos):
        return self.occupants.get(pos)

    def interactables_at(self, pos):
        return []

    def is_blocked(self, a, b):
        return frozenset((a, b)) in self.blocked_edges

    def get_wall(self, a, b):
        return None

    def edge_interactables_between(self, a, b):
        return self.edge_objs.get(frozenset((a, b)), [])

    def remove(self, pos):
        self.occupants.pop(pos, None)


class FakeGame:
    def __init__(self):
        self.events = FakeEvents()
        self.heroes = []
        self.enemies = []
        self.board = FakeBoard()
        self.conn = FakeConn()


class Hero:
    def __init__(self, pos):
        self.position = pos
        self.statuses = []

    def add_status(self, status):
        self.statuses.append(status)

    def remove_status(self, status):
        self.statuses = [s for s in self.statuses if getattr(s, "id", s) != getattr(status, "id", status)]


class Enemy:
    def __init__(self, pos, hp=12, ac=12):
        self.position = pos
        self.hp = hp
        self.ac = ac

    def apply_damage(self, amount, dmg_type="piercing"):
        self.hp -= amount
        return self.hp, self.hp <= 0


def _ctx(game, hero):
    return EventContext(game=game, actor=hero)


def test_longbow_hits_without_cover(monkeypatch):
    hero = Hero((0, 0))
    enemy = Enemy((2, 0), hp=8, ac=10)
    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.conn.choice = enemy.position

    rolls = iter([20, 5])  # hit, dmg
    monkeypatch.setattr(base_attack_range_event, "prompt_for_roll", lambda *_, **__: next(rolls))

    result = dispatch_event("longbow", _ctx(game, hero))
    assert result.success
    assert enemy.hp == 3
    # status range_attacker nadany
    assert any(getattr(s, "id", s) == "range_attacker" for s in hero.statuses)


def test_longbow_blocked_by_wall(monkeypatch):
    hero = Hero((0, 0))
    enemy = Enemy((2, 0))
    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.board.blocked_edges.add(frozenset(((0, 0), (1, 0))))

    result = dispatch_event("longbow", _ctx(game, hero))
    assert not result.success
    assert "zasięgu" in (result.message or "") or "linia" in (result.message or "")
    assert enemy.hp == 12


def test_cover_and_range_penalty_emitted(monkeypatch):
    class ShortBow(base_attack_range_event.BaseRangeAttackEvent):
        name = "attack_short_test"
        range_increment_ft = 5
        max_range_increments = 6
        action_id_base = "attack_short_test"

    hero = Hero((0, 0))
    enemy = Enemy((6, 0), ac=12)
    obstacle = SimpleObstacle()
    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy, (1, 0): obstacle}
    game.conn.choice = enemy.position

    rolls = iter([30, 4])  # attack (>= target AC) after auto penalties, dmg
    monkeypatch.setattr(base_attack_range_event, "prompt_for_roll", lambda *_, **__: next(rolls))

    event = ShortBow()
    result = event.run(_ctx(game, hero))
    assert result.success
    emitted = game.events.emitted[-1]
    assert emitted.get("cover") == "greater"
    assert emitted.get("range_penalty") == 10  # 6 increment -> (6-1)*2
    assert enemy.hp == 8
