from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import GameObjects.events.all_events  # noqa: F401
from GameObjects.events.base import EventContext
from GameObjects.events.registry import dispatch_event
from GameObjects.events.attack import basic_melee_attack_event, base_attack_range_event
from statuses import Status


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
        _ = acceptable_responses
        return self.choice

    def leds_off(self):
        return None


class FakeBoard:
    def __init__(self):
        self.occupants = {}

    def occupant_at(self, pos):
        return self.occupants.get(pos)

    def get_neighbors(self, pos, include_position=False, diagonal=True):
        _ = diagonal
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

    def interactables_at(self, _pos):
        return []

    def is_blocked(self, _a, _b):
        return False

    def edge_interactables_between(self, _a, _b):
        return []


class FakeGame:
    def __init__(self):
        self.events = FakeEvents()
        self.heroes = []
        self.enemies = []
        self.board = FakeBoard()
        self.conn = FakeConn()
        self.ui_log = lambda *_a, **_k: None


class Hero:
    def __init__(self, pos):
        self.position = pos
        self.statuses = []
        self.bonuses = []

    def add_status(self, status):
        self.statuses.append(status)

    def has_status(self, status_id: str) -> bool:
        return any(getattr(s, "id", s) == status_id for s in self.statuses)

    def remove_status(self, status):
        sid = getattr(status, "id", status)
        self.statuses = [s for s in self.statuses if getattr(s, "id", s) != sid]


class Enemy:
    def __init__(self, pos, hp=12, ac=10):
        self.position = pos
        self.hp = hp
        self.ac = ac

    def apply_damage(self, amount, _dmg_type=""):
        self.hp -= int(amount)
        return self.hp, self.hp <= 0


def _ctx(game, hero, metadata=None):
    return EventContext(game=game, actor=hero, metadata=dict(metadata or {}))


def test_exacting_strike_metadata_does_not_increase_map_on_miss(monkeypatch):
    hero = Hero((0, 0))
    enemy = Enemy((1, 0), hp=20, ac=30)
    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.conn.choice = enemy.position

    hero._attack_trait_state = {"attacks_this_turn": 1, "weapon_counts": {"attack_sword": 1}}

    monkeypatch.setattr(basic_melee_attack_event, "prompt_for_roll", lambda *_a, **_k: 1)
    monkeypatch.setattr(basic_melee_attack_event, "refresh_flanking_statuses", lambda *_a, **_k: None)

    result = dispatch_event("sword", _ctx(game, hero, {"exacting_strike_press": True}))

    assert result.success is True
    assert "map bez zmian" in str(result.message or "").lower()
    assert int(hero._attack_trait_state.get("attacks_this_turn", 0) or 0) == 1


def test_map_attack_count_metadata_counts_as_two_attacks(monkeypatch):
    hero = Hero((0, 0))
    enemy = Enemy((1, 0), hp=20, ac=30)
    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.conn.choice = enemy.position

    hero._attack_trait_state = {"attacks_this_turn": 0, "weapon_counts": {"attack_sword": 0}}

    monkeypatch.setattr(basic_melee_attack_event, "prompt_for_roll", lambda *_a, **_k: 1)
    monkeypatch.setattr(basic_melee_attack_event, "refresh_flanking_statuses", lambda *_a, **_k: None)

    result = dispatch_event("sword", _ctx(game, hero, {"map_attack_count": 2}))

    assert result.success is True
    assert int(hero._attack_trait_state.get("attacks_this_turn", 0) or 0) == 2


def test_point_blank_shot_stance_ignores_volley_penalty(monkeypatch):
    # Bez stance: 10 vs efektywne AC10, volley -2 => pudlo.
    hero = Hero((0, 0))
    enemy = Enemy((1, 0), hp=10, ac=12)
    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.conn.choice = enemy.position

    monkeypatch.setattr(base_attack_range_event, "prompt_for_roll", lambda *_a, **_k: 10)
    miss_result = dispatch_event("longbow", _ctx(game, hero))
    assert miss_result.success is True
    assert "chybia" in str(miss_result.message or "").lower()

    # Ze stance: kara volley ignorowana, ten sam rzut trafia.
    hero2 = Hero((0, 0))
    hero2.add_status(Status(id="point_blank_shot_stance"))
    enemy2 = Enemy((1, 0), hp=10, ac=12)
    game2 = FakeGame()
    game2.heroes = [hero2]
    game2.enemies = [enemy2]
    game2.board.occupants = {hero2.position: hero2, enemy2.position: enemy2}
    game2.conn.choice = enemy2.position

    rolls = iter([10, 3])
    monkeypatch.setattr(base_attack_range_event, "prompt_for_roll", lambda *_a, **_k: next(rolls))
    hit_result = dispatch_event("longbow", _ctx(game2, hero2))

    assert hit_result.success is True
    assert "trafia" in str(hit_result.message or "").lower() or "krytyczne" in str(hit_result.message or "").lower()
    assert enemy2.hp < 10


def test_melee_attack_nat20_promotes_failure_to_hit(monkeypatch):
    hero = Hero((0, 0))
    enemy = Enemy((1, 0), hp=20, ac=25)
    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.conn.choice = enemy.position

    rolls = iter(
        [
            {"roll": 20, "natural_mode": "nat20", "natural_shift": 1},
            4,
        ]
    )
    monkeypatch.setattr(basic_melee_attack_event, "prompt_for_roll", lambda *_a, **_k: next(rolls))
    monkeypatch.setattr(basic_melee_attack_event, "refresh_flanking_statuses", lambda *_a, **_k: None)

    result = dispatch_event("sword", _ctx(game, hero))

    assert result.success is True
    assert bool((result.data or {}).get("hit", False)) is True
    assert enemy.hp == 16


def test_melee_attack_nat1_demotes_success_to_miss(monkeypatch):
    hero = Hero((0, 0))
    enemy = Enemy((1, 0), hp=20, ac=1)
    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.conn.choice = enemy.position

    rolls = iter(
        [
            {"roll": 1, "natural_mode": "nat1", "natural_shift": -1},
        ]
    )
    monkeypatch.setattr(basic_melee_attack_event, "prompt_for_roll", lambda *_a, **_k: next(rolls))
    monkeypatch.setattr(basic_melee_attack_event, "refresh_flanking_statuses", lambda *_a, **_k: None)

    result = dispatch_event("sword", _ctx(game, hero))

    assert result.success is True
    assert bool((result.data or {}).get("hit", False)) is False
    assert enemy.hp == 20
