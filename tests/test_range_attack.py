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
from bonuses import BonusEffect, BonusType
from GameObjects.items.shield import create_shield


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
        self.bonuses = []
        self.equipped_shield = None

    def add_status(self, status):
        self.statuses.append(status)

    def remove_status(self, status):
        self.statuses = [s for s in self.statuses if getattr(s, "id", s) != getattr(status, "id", status)]

    def has_status(self, status_id):
        return any(getattr(s, "id", s) == status_id for s in self.statuses)


class Enemy:
    def __init__(self, pos, hp=12, ac=12):
        self.position = pos
        self.hp = hp
        self.ac = ac
        self.statuses = []
        self.bonuses = []

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

    rolls = iter([15, 5])  # hit, dmg
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


def test_longbow_wrong_square_against_undetected_target_still_counts_as_attack():
    hero = Hero((0, 0))
    enemy = Enemy((2, 0), hp=8, ac=10)
    enemy.statuses.append(types.SimpleNamespace(id="undetected"))
    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.conn.choice = (1, 1)

    result = dispatch_event("longbow", _ctx(game, hero))

    assert result.success is True
    assert bool((result.data or {}).get("hit", True)) is False
    assert (result.data or {}).get("target") is None
    assert (result.data or {}).get("guessed_target_square") == (1, 1)
    assert enemy.hp == 8
    assert getattr(hero, "_attack_trait_state", {}).get("attacks_this_turn") == 1
    assert any(getattr(s, "id", s) == "range_attacker" for s in hero.statuses)


def test_analyze_shot_raised_tower_shield_in_line_grants_standard_cover():
    shooter = Hero((0, 0))
    blocker = Hero((1, 0))
    target = Enemy((2, 0), ac=12)
    tower = create_shield("tower_shield")
    assert tower is not None
    blocker.equipped_shield = tower
    blocker.bonuses.append(
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=2,
            tag="ac",
            source="raise_shield:round1",
            label="tarcza w gorze",
        )
    )
    game = FakeGame()
    game.heroes = [shooter, blocker]
    game.enemies = [target]
    game.board.occupants = {
        shooter.position: shooter,
        blocker.position: blocker,
        target.position: target,
    }

    event = attack_range_long_bow.LongBowAttackEvent()
    analyzed = event._analyze_shot(game, shooter.position, target.position, target=target)

    assert analyzed.get("cover_type") == "standard"
    assert analyzed.get("blocked") is False


def test_analyze_shot_tower_shield_without_raise_does_not_grant_cover():
    shooter = Hero((0, 0))
    blocker = Hero((1, 0))
    target = Enemy((2, 0), ac=12)
    tower = create_shield("tower_shield")
    assert tower is not None
    blocker.equipped_shield = tower
    game = FakeGame()
    game.heroes = [shooter, blocker]
    game.enemies = [target]
    game.board.occupants = {
        shooter.position: shooter,
        blocker.position: blocker,
        target.position: target,
    }

    event = attack_range_long_bow.LongBowAttackEvent()
    analyzed = event._analyze_shot(game, shooter.position, target.position, target=target)

    assert analyzed.get("cover_type") == "none"
