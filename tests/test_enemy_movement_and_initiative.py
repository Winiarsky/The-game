from types import SimpleNamespace
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from GameObjects.events.base import EventContext
from GameObjects.events.enemy.enemy_move_event import EnemyMoveEvent
from GameObjects.events.move_event import MoveEvent
from GameObjects.events.elixirs.juggernaut_mutagen_event import JuggernautMutagenEvent
from states.combat import Combat
from statuses import SpeedPenaltyStatus, ImmobilizedStatus, DeafenedStatus


class BoardStub:
    def __init__(self):
        self.moved = None

    def in_bounds(self, _pos):
        return True

    def can_enter(self, *_args, **_kwargs):
        return True

    def is_blocked(self, *_args, **_kwargs):
        return False

    def edge_interactables_between(self, *_args, **_kwargs):
        return []

    def get_neighbors(self, pos, include_position=False, diagonal=True):
        # zwróć jedno pole docelowe obok bohatera
        return [(pos[0] - 1, pos[1])]

    def move(self, _src, dst):
        self.moved = dst


class DummyConn:
    def set_leds(self, *_args, **_kwargs):
        return None

    def scan_board(self, positions):
        return positions[0]

    def leds_off(self):
        return None


class DummyEnemy:
    def __init__(self, pos=(0, 0), distance=25):
        self.position = pos
        self.distance = distance
        self.statuses = []
        self.object_id = "enemy-1"

    def has_status(self, status_id):
        return any(s.id == status_id for s in self.statuses)

    def add_status(self, status):
        self.statuses.append(status)
        return True


class DummyHero:
    def __init__(self, pos=(2, 0)):
        self.position = pos
        self.statuses = []
        self.object_id = "hero-1"

    def has_status(self, status_id):
        return any(s.id == status_id for s in self.statuses)

    def add_status(self, status):
        self.statuses.append(status)
        return True


def test_enemy_move_respects_speed_penalty(monkeypatch):
    board = BoardStub()
    conn = DummyConn()
    enemy = DummyEnemy(distance=25)
    hero = DummyHero()
    game = SimpleNamespace(board=board, conn=conn, heroes=[hero], enemies=[enemy], ui_event=lambda *a, **k: None)

    enemy.add_status(SpeedPenaltyStatus(penalty_feet=10, source="test", source_id="hero-1", source_turns_left=1))

    captured = {}

    def _find_path(_board, _start, _end, **_kwargs):
        return [(0, 0), (1, 0), (2, 0)]

    def _path_cost(path, _board, **_kwargs):
        return max(0, (len(path) - 1) * 5)

    def _trim(path, budget, _board, **_kwargs):
        captured["budget"] = budget
        # budżet 15 stóp -> 3 pola (0->1->2)
        return path if budget >= 10 else path[:2]

    monkeypatch.setattr("GameObjects.events.enemy.enemy_move_event.find_path", _find_path)
    monkeypatch.setattr("GameObjects.events.enemy.enemy_move_event.path_cost_feet", _path_cost)
    monkeypatch.setattr("GameObjects.events.enemy.enemy_move_event.trim_path_to_feet", _trim)

    ctx = EventContext(game=game, actor=enemy)
    res = EnemyMoveEvent().run(ctx)
    assert res.success
    assert captured["budget"] == 15
    assert board.moved == (2, 0)


def test_enemy_move_blocked_when_speed_zero(monkeypatch):
    board = BoardStub()
    conn = DummyConn()
    enemy = DummyEnemy(distance=10)
    hero = DummyHero()
    game = SimpleNamespace(board=board, conn=conn, heroes=[hero], enemies=[enemy], ui_event=lambda *a, **k: None)

    enemy.add_status(SpeedPenaltyStatus(penalty_feet=20, source="test", source_id="hero-1", source_turns_left=1))

    ctx = EventContext(game=game, actor=enemy)
    res = EnemyMoveEvent().run(ctx)
    assert res.success is False
    assert res.consumed_action is True


def test_immobilized_blocks_move_for_enemy():
    board = BoardStub()
    conn = DummyConn()
    enemy = DummyEnemy()
    hero = DummyHero()
    game = SimpleNamespace(board=board, conn=conn, heroes=[hero], enemies=[enemy])

    enemy.add_status(ImmobilizedStatus(source="test", source_id="hero-1", source_turns_left=1))
    ctx = EventContext(game=game, actor=enemy)
    res = EnemyMoveEvent().run(ctx)
    assert res.success is False
    assert res.consumed_action is False


def test_immobilized_blocks_move_for_hero(monkeypatch):
    board = BoardStub()
    conn = DummyConn()
    hero = DummyHero(pos=(0, 0))
    hero.add_status(ImmobilizedStatus(source="test", source_id="enemy-1", source_turns_left=1))
    game = SimpleNamespace(board=board, conn=conn, heroes=[hero], enemies=[])

    monkeypatch.setattr("GameObjects.events.move_event.MoveEvent._wait_for_destination", lambda *_args, **_kwargs: hero.position)
    ctx = EventContext(game=game, actor=hero)
    res = MoveEvent().run(ctx)
    assert res.success is False
    assert res.consumed_action is False


def test_deafened_initiative_penalty_reorders_queue():
    game = SimpleNamespace(heroes=[], enemies=[], ui_event=lambda *a, **k: None, ui_log=lambda *a, **k: None)
    combat = Combat(game)

    hero_fast = DummyHero(pos=(0, 0))
    hero_slow = DummyHero(pos=(1, 0))
    game.heroes = [hero_fast, hero_slow]

    combat.base_initiative[hero_fast] = 16
    combat.base_initiative[hero_slow] = 15
    combat.base_order = [hero_fast, hero_slow]
    combat.round_queue = [hero_fast, hero_slow]

    hero_fast.add_status(DeafenedStatus(source="test", source_id="x", source_turns_left=1))
    combat.apply_initiative_penalty(hero_fast, 2)

    assert combat.round_queue[0] is hero_slow
    assert combat.round_queue[1] is hero_fast


def test_juggernaut_mutagen_penalty_lowers_existing_initiative():
    game = SimpleNamespace(heroes=[], enemies=[], ui_event=lambda *a, **k: None, ui_log=lambda *a, **k: None)
    combat = Combat(game)

    hero_fast = DummyHero(pos=(0, 0))
    hero_slow = DummyHero(pos=(1, 0))
    game.heroes = [hero_fast, hero_slow]
    game.state = combat

    combat.base_initiative[hero_fast] = 16
    combat.base_initiative[hero_slow] = 15
    combat.base_order = [hero_fast, hero_slow]
    combat.round_queue = [hero_fast, hero_slow]

    ctx = EventContext(game=game, actor=hero_fast)
    event = JuggernautMutagenEvent()
    event._apply_elixir(ctx, hero_fast, "lesser", event.tiers["lesser"])

    assert combat.base_initiative[hero_fast] == 14
    assert combat.round_queue[0] is hero_slow
    assert combat.round_queue[1] is hero_fast


def test_juggernaut_mutagen_penalty_expires_restores_initiative():
    game = SimpleNamespace(heroes=[], enemies=[], ui_event=lambda *a, **k: None, ui_log=lambda *a, **k: None)
    combat = Combat(game)

    hero = DummyHero(pos=(0, 0))
    game.heroes = [hero]
    game.state = combat

    combat.base_initiative[hero] = 16
    combat.base_order = [hero]
    combat.round_queue = [hero]

    ctx = EventContext(game=game, actor=hero)
    event = JuggernautMutagenEvent()
    event._apply_elixir(ctx, hero, "lesser", event.tiers["lesser"])

    hero.statuses = [s for s in hero.statuses if getattr(s, "id", None) != "juggernaut_mutagen_penalty"]
    combat.sync_status_initiative_penalty(hero, reorder_round_queue=False)

    assert combat.base_initiative[hero] == 16
    assert combat.status_initiative_penalty.get(hero, 0) == 0
