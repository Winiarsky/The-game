import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.Enemies.basic_enemy import BasicEnemy
from GameObjects.Enemies.enemy_types import EnemyType
from GameObjects.events.base import EventContext
from GameObjects.events.attack.basic_melee_attack_event import BasicMeleeAttackEvent
from GameObjects.events.attack import base_attack_range_event
from GameObjects.events.magic.cantrips.events import AcidSplashEvent
from hero import Hero
from statuses.race.dwarf.feats.vengeful_hatred import VengefulHatredStatus


class DummyUI:
    def __init__(self):
        self.prompts = []

    def prompt_info(self, title, *, prompt_long=None, source=None, **_kwargs):
        self.prompts.append((title, prompt_long, source))
        return "ok"

    def prompt_roll(self, *_args, **_kwargs):
        return 5


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

    def get_neighbors(self, pos, *, include_position=False, diagonal=True):
        x, y = pos
        deltas = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        if diagonal:
            deltas += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        neighbors = [(x + dx, y + dy) for dx, dy in deltas]
        if include_position:
            neighbors.insert(0, pos)
        return neighbors


class FakeGame:
    def __init__(self):
        self.events = FakeEvents()
        self.heroes = []
        self.enemies = []
        self.board = FakeBoard()
        self.conn = FakeConn()


def _ctx(game, hero):
    return EventContext(game=game, actor=hero)


def _set_dummy_ui(monkeypatch):
    dummy = DummyUI()
    monkeypatch.setattr("ui_client.get_ui_client", lambda: dummy)
    return dummy


def _setup_game(hero, enemy):
    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.conn.choice = enemy.position
    return game


def test_vengeful_hatred_prompts_for_melee_ranged_magic(monkeypatch):
    dummy_ui = _set_dummy_ui(monkeypatch)

    hero = Hero()
    hero.position = (0, 0)
    hero.add_status(VengefulHatredStatus(EnemyType.ORC))

    enemy = BasicEnemy(name="Orc", enemy_type=EnemyType.ORC)
    enemy.position = (1, 0)
    enemy.ac = 12

    # --- melee ---
    melee_rolls = iter([20, 5])
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.prompt_for_roll",
        lambda *_, **__: next(melee_rolls),
    )
    game = _setup_game(hero, enemy)
    BasicMeleeAttackEvent().run(_ctx(game, hero))

    # --- ranged ---
    enemy.position = (2, 0)
    ranged_rolls = iter([20, 5])
    monkeypatch.setattr(
        "GameObjects.events.attack.base_attack_range_event.prompt_for_roll",
        lambda *_, **__: next(ranged_rolls),
    )
    game = _setup_game(hero, enemy)
    base_attack_range_event.BaseRangeAttackEvent().run(_ctx(game, hero))

    # --- magic ---
    enemy.position = (3, 0)
    magic_rolls = iter([20])
    monkeypatch.setattr(
        "GameObjects.events.magic.base_attack_magic_event.prompt_for_roll",
        lambda *_, **__: next(magic_rolls),
    )
    game = _setup_game(hero, enemy)
    AcidSplashEvent().run(_ctx(game, hero))

    assert len(dummy_ui.prompts) == 3


def test_vengeful_hatred_no_prompt_without_status(monkeypatch):
    dummy_ui = _set_dummy_ui(monkeypatch)

    hero = Hero()
    hero.position = (0, 0)

    enemy = BasicEnemy(name="Orc", enemy_type=EnemyType.ORC)
    enemy.position = (1, 0)
    enemy.ac = 12

    melee_rolls = iter([20, 5])
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.prompt_for_roll",
        lambda *_, **__: next(melee_rolls),
    )
    game = _setup_game(hero, enemy)
    BasicMeleeAttackEvent().run(_ctx(game, hero))

    ranged_rolls = iter([20, 5])
    monkeypatch.setattr(
        "GameObjects.events.attack.base_attack_range_event.prompt_for_roll",
        lambda *_, **__: next(ranged_rolls),
    )
    enemy.position = (2, 0)
    game = _setup_game(hero, enemy)
    base_attack_range_event.BaseRangeAttackEvent().run(_ctx(game, hero))

    magic_rolls = iter([20])
    monkeypatch.setattr(
        "GameObjects.events.magic.base_attack_magic_event.prompt_for_roll",
        lambda *_, **__: next(magic_rolls),
    )
    enemy.position = (3, 0)
    game = _setup_game(hero, enemy)
    AcidSplashEvent().run(_ctx(game, hero))

    assert dummy_ui.prompts == []
