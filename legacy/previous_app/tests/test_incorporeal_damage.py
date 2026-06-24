import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.events.attack import basic_melee_attack_event
from GameObjects.events.base import EventContext
from statuses.base import Status
from statuses.classes.barbarian.instincts.spirit_instinct import SpiritInstinctActiveStatus
from damage_types import DamageType


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

    def occupant_at(self, pos):
        return self.occupants.get(pos)

    def get_neighbors(self, pos, include_position=False, diagonal=True):
        del diagonal
        neighbors = [
            (pos[0] + 1, pos[1]),
            (pos[0] - 1, pos[1]),
            (pos[0], pos[1] + 1),
            (pos[0], pos[1] - 1),
        ]
        if include_position:
            neighbors.append(pos)
        return neighbors

    def in_bounds(self, _pos):
        return True

    def remove(self, pos):
        self.occupants.pop(pos, None)


class FakeGame:
    def __init__(self):
        self.heroes = []
        self.enemies = []
        self.board = FakeBoard()
        self.conn = FakeConn()
        self.ui_log = lambda *_a, **_k: None
        self.events = type("Evt", (), {"safe_emit_action": lambda *a, **k: None})()


class Hero:
    def __init__(self, pos):
        self.position = pos
        self.statuses = []

    def remove_status(self, status):
        self.statuses = [s for s in self.statuses if getattr(s, "id", s) != getattr(status, "id", status)]


class IncorporealEnemy:
    def __init__(self, pos, hp=30, ac=5):
        self.position = pos
        self.hp = hp
        self.ac = ac
        self.tags = ["incorporeal"]
        self.last_damage_amount = None
        self.last_damage_type = None

    def apply_damage(self, amount, dmg_type=""):
        self.last_damage_amount = amount
        self.last_damage_type = dmg_type
        self.hp -= amount
        return self.hp, self.hp <= 0


def _ctx(game, hero):
    return EventContext(game=game, actor=hero)


def test_incorporeal_halves_physical_damage(monkeypatch):
    hero = Hero((0, 0))
    enemy = IncorporealEnemy((1, 0), hp=30, ac=5)
    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.conn.choice = enemy.position

    rolls = iter([12, 10])  # hit (no crit), dmg
    monkeypatch.setattr(basic_melee_attack_event, "prompt_for_roll", lambda *_, **__: next(rolls))
    monkeypatch.setattr(basic_melee_attack_event, "refresh_flanking_statuses", lambda *_a, **_k: None)

    result = basic_melee_attack_event.BasicMeleeAttackEvent().execute(_ctx(game, hero))
    assert result.success
    assert enemy.last_damage_type == DamageType.SLASHING.value
    assert enemy.last_damage_amount == 5


def test_incorporeal_ignores_crit_and_precision(monkeypatch):
    class PrecisionAttack(basic_melee_attack_event.BasicMeleeAttackEvent):
        name = "precision_attack"
        default_tags = ["attack_melee", "precision"]
        damage_prompt = "1k4 + STR"

    hero = Hero((0, 0))
    enemy = IncorporealEnemy((1, 0), hp=30, ac=5)
    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.conn.choice = enemy.position

    rolls = iter([30, 8])  # critical, dmg
    monkeypatch.setattr(basic_melee_attack_event, "prompt_for_roll", lambda *_, **__: next(rolls))
    monkeypatch.setattr(basic_melee_attack_event, "refresh_flanking_statuses", lambda *_a, **_k: None)

    event = PrecisionAttack()
    result = event.execute(_ctx(game, hero))
    assert result.success
    assert enemy.last_damage_amount == 0


def test_spirit_instinct_ignores_incorporeal(monkeypatch):
    hero = Hero((0, 0))
    enemy = IncorporealEnemy((1, 0), hp=30, ac=5)
    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.conn.choice = enemy.position

    hero.statuses.append(Status(id="rage"))
    hero.statuses.append(SpiritInstinctActiveStatus(spirit_type="weapon", duration=10))

    rolls = iter([12, 10])  # hit (no crit), dmg
    monkeypatch.setattr(basic_melee_attack_event, "prompt_for_roll", lambda *_, **__: next(rolls))
    monkeypatch.setattr(basic_melee_attack_event, "refresh_flanking_statuses", lambda *_a, **_k: None)

    result = basic_melee_attack_event.BasicMeleeAttackEvent().execute(_ctx(game, hero))
    assert result.success
    assert enemy.last_damage_amount == 13
