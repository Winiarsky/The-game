from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.events.attack.basic_melee_attack_event import BasicMeleeAttackEvent
from GameObjects.events.base import EventContext
from states.combat import Combat
from statuses.base import Status


class FakeEvents:
    def safe_emit_action(self, **_payload):
        return None


class FakeConn:
    def __init__(self, choice=None):
        self.choice = choice

    def set_leds(self, *_args, **_kwargs):
        return None

    def scan_board(self, _acceptable_responses=None):
        return self.choice

    def leds_off(self):
        return None


class FakeBoard:
    def __init__(self):
        self.occupants = {}

    def occupant_at(self, pos):
        return self.occupants.get(pos)

    def get_neighbors(self, pos, *, include_position=False, diagonal=True):
        _ = diagonal
        x, y = pos
        out = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        if include_position:
            out.append(pos)
        return out

    def remove(self, pos):
        self.occupants.pop(pos, None)


class FakeGame:
    def __init__(self):
        self.events = FakeEvents()
        self.heroes = []
        self.enemies = []
        self.board = FakeBoard()
        self.conn = FakeConn()
        self.ui_log = lambda *_a, **_k: None
        self.state = None


@dataclass
class Hero:
    object_id: str = "hero-1"
    position: tuple[int, int] | None = (0, 0)
    statuses: list[Status] = field(default_factory=list)
    bonuses: list = field(default_factory=list)

    def has_status(self, status_id: str) -> bool:
        return any(getattr(s, "id", s) == status_id for s in self.statuses)

    def add_status(self, status):
        self.statuses.append(status)

    def remove_status(self, status):
        sid = getattr(status, "id", status)
        self.statuses = [s for s in self.statuses if getattr(s, "id", s) != sid]


@dataclass
class Enemy:
    object_id: str = "enemy-1"
    position: tuple[int, int] | None = (1, 0)
    hp: int = 40
    ac: int = 10

    def apply_damage(self, amount, _dmg_type=""):
        self.hp -= int(amount)
        return self.hp, self.hp <= 0


def _map_value(mod_grid):
    if not mod_grid:
        return None
    for entry in mod_grid.get("penCirc", []):
        if entry.get("label", "").startswith("MAP"):
            return entry.get("value")
    return None


def test_ranger_flurry_map_against_hunted_prey(monkeypatch):
    hero = Hero()
    enemy = Enemy()
    hero.statuses.append(
        Status(
            id="ranger",
            data={
                "ranger_setup": {
                    "hunter_edge": "flurry",
                    "hunted_prey_target_id": enemy.object_id,
                }
            },
        )
    )

    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.conn.choice = enemy.position

    recorded = []
    rolls = iter([20, 1, 20, 1, 20, 1])

    def _prompt(*_args, **kwargs):
        if kwargs.get("layout") == "test":
            recorded.append(kwargs.get("modifiers"))
        return next(rolls)

    monkeypatch.setattr("GameObjects.events.attack.basic_melee_attack_event.prompt_for_roll", _prompt)
    monkeypatch.setattr("GameObjects.events.attack.basic_melee_attack_event.refresh_flanking_statuses", lambda *_a, **_k: None)

    event = BasicMeleeAttackEvent()
    event.run(EventContext(game=game, actor=hero))
    event.run(EventContext(game=game, actor=hero))
    event.run(EventContext(game=game, actor=hero))

    assert _map_value(recorded[0]) is None
    assert _map_value(recorded[1]) == 3
    assert _map_value(recorded[2]) == 6


def test_ranger_precision_applies_once_per_round(monkeypatch):
    hero = Hero(object_id="hero-precision")
    enemy = Enemy(object_id="enemy-precision", hp=30)
    hero.statuses.append(
        Status(
            id="ranger",
            data={
                "ranger_setup": {
                    "hunter_edge": "precision",
                    "hunted_prey_target_id": enemy.object_id,
                }
            },
        )
    )

    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.conn.choice = enemy.position
    game.state = Combat(game)

    precision_calls = {"count": 0}

    def _prompt(*args, **kwargs):
        prompt = str(args[0]) if args else ""
        if kwargs.get("layout") == "test":
            return 20
        if "Hunter's Edge (Precision)" in prompt:
            precision_calls["count"] += 1
            return 4
        return 6

    monkeypatch.setattr("GameObjects.events.attack.basic_melee_attack_event.prompt_for_roll", _prompt)
    monkeypatch.setattr("GameObjects.events.attack.basic_melee_attack_event.refresh_flanking_statuses", lambda *_a, **_k: None)

    event = BasicMeleeAttackEvent()
    event.run(EventContext(game=game, actor=hero))
    event.run(EventContext(game=game, actor=hero))

    assert precision_calls["count"] == 1
    assert enemy.hp == 14


def test_ranger_precision_skips_precision_immune_targets(monkeypatch):
    hero = Hero(object_id="hero-precision-immune")
    enemy = Enemy(object_id="enemy-undead", hp=30)
    enemy.tags = ["undead"]
    hero.statuses.append(
        Status(
            id="ranger",
            data={
                "ranger_setup": {
                    "hunter_edge": "precision",
                    "hunted_prey_target_id": enemy.object_id,
                }
            },
        )
    )

    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.conn.choice = enemy.position
    game.state = Combat(game)

    precision_calls = {"count": 0}

    def _prompt(*args, **kwargs):
        prompt = str(args[0]) if args else ""
        if kwargs.get("layout") == "test":
            return 20
        if "Hunter's Edge (Precision)" in prompt:
            precision_calls["count"] += 1
            return 4
        return 6

    monkeypatch.setattr("GameObjects.events.attack.basic_melee_attack_event.prompt_for_roll", _prompt)
    monkeypatch.setattr("GameObjects.events.attack.basic_melee_attack_event.refresh_flanking_statuses", lambda *_a, **_k: None)

    event = BasicMeleeAttackEvent()
    event.run(EventContext(game=game, actor=hero))

    assert precision_calls["count"] == 0
