import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.events.base import EventContext  # noqa: E402
from GameObjects.events.attack.basic_melee_attack_event import BasicMeleeAttackEvent  # noqa: E402


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

    def occupant_at(self, pos):
        return self.occupants.get(pos)

    def get_neighbors(self, pos, *, include_position=False, diagonal=True):
        x, y = pos
        deltas = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        if diagonal:
            deltas += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        neighbors = [(x + dx, y + dy) for dx, dy in deltas]
        if include_position:
            neighbors.insert(0, pos)
        return neighbors

    def remove(self, pos):
        self.occupants.pop(pos, None)


class FakeGame:
    def __init__(self):
        self.events = FakeEvents()
        self.heroes = []
        self.enemies = []
        self.board = FakeBoard()
        self.conn = FakeConn()
        self.ui_log = lambda *a, **k: None


class Hero:
    def __init__(self, pos=(0, 0)):
        self.position = pos
        self.statuses = []
        self.bonuses = []
        self.object_id = "hero-1"

    def remove_status(self, *_args, **_kwargs):
        return None


class Enemy:
    def __init__(self, pos=(1, 0), hp=30, ac=10):
        self.position = pos
        self.hp = hp
        self.ac = ac

    def apply_damage(self, amount, dmg_type="slashing"):
        self.hp -= amount
        return self.hp, self.hp <= 0


def _ctx(game, hero):
    return EventContext(game=game, actor=hero)


def _setup_game():
    hero = Hero((0, 0))
    enemy = Enemy((1, 0))
    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.conn.choice = enemy.position
    return game, hero, enemy


def _prompt_recorder(attack_rolls, damage_rolls, recorded):
    def _prompt(*_args, **kwargs):
        if kwargs.get("layout") == "test":
            recorded.append(kwargs.get("modifiers"))
            return next(attack_rolls)
        return next(damage_rolls)

    return _prompt


def _map_value(mod_grid):
    if not mod_grid:
        return None
    for entry in mod_grid.get("penCirc", []):
        if entry.get("label", "").startswith("MAP"):
            return entry.get("value")
    return None


def test_map_penalty_standard_second_and_third_attack(monkeypatch):
    game, hero, _enemy = _setup_game()
    recorded = []
    rolls = iter([20, 1, 20, 1, 20, 1])
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.prompt_for_roll",
        _prompt_recorder(rolls, rolls, recorded),
    )
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.refresh_flanking_statuses",
        lambda *_: None,
    )

    event = BasicMeleeAttackEvent()
    event.run(_ctx(game, hero))
    event.run(_ctx(game, hero))
    event.run(_ctx(game, hero))

    assert _map_value(recorded[0]) is None
    assert _map_value(recorded[1]) == 5
    assert _map_value(recorded[2]) == 10


def test_map_penalty_agile_second_and_third_attack(monkeypatch):
    game, hero, _enemy = _setup_game()
    recorded = []
    rolls = iter([20, 1, 20, 1, 20, 1])
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.prompt_for_roll",
        _prompt_recorder(rolls, rolls, recorded),
    )
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.refresh_flanking_statuses",
        lambda *_: None,
    )

    class AgileMelee(BasicMeleeAttackEvent):
        default_tags = ["attack_melee", "agile"]

    event = AgileMelee()
    event.run(_ctx(game, hero))
    event.run(_ctx(game, hero))
    event.run(_ctx(game, hero))

    assert _map_value(recorded[0]) is None
    assert _map_value(recorded[1]) == 4
    assert _map_value(recorded[2]) == 8
