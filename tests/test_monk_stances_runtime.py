from __future__ import annotations

import sys
import importlib
import importlib.util
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

MOVE_UTILS_PATH = SRC_ROOT / "actions" / "move_utils.py"
spec = importlib.util.spec_from_file_location("actions.move_utils", MOVE_UTILS_PATH)
move_utils = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(move_utils)  # type: ignore[arg-type]
sys.modules["actions.move_utils"] = move_utils

import GameObjects.events.all_events  # noqa: F401

from GameObjects.events.attack import basic_melee_attack_event
import GameObjects.events.leap_event as leap_event_module
import GameObjects.events.step_event as step_event_module

importlib.reload(leap_event_module)
importlib.reload(step_event_module)

from GameObjects.events.base import EventContext
from GameObjects.events.registry import dispatch_event
from GameObjects.events.trip_event import _save_dc as trip_save_dc
from GameObjects.events.shove_event import _save_dc as shove_save_dc
from GameObjects.interactions_mixin import BonusMixin
from GameObjects.Terrains.rumble_terrain import RumbleTerrain
from actions.move_utils import (
    consume_difficult_terrain_ignores_for_path,
    path_cost_feet,
    reset_turn_movement_runtime,
)
from board_grid import BoardGrid
from states.combat import Combat
from statuses.base import Status

LeapEvent = leap_event_module.LeapEvent
StepEvent = step_event_module.StepEvent


class DummyConn:
    def __init__(self, choice=None):
        self.choice = choice
        self.last_positions = None

    def set_leds(self, positions, _colors):
        self.last_positions = list(positions)
        return None

    def scan_board(self, positions=None):
        if isinstance(self.choice, list):
            if self.choice:
                return self.choice.pop(0)
        elif self.choice is not None:
            return self.choice
        if positions:
            return positions[0]
        return None

    def leds_off(self):
        return None

    def read_card(self, *_args, **_kwargs):
        return "end"


class DummyEvents:
    def __init__(self):
        self.emitted = []

    def safe_emit_action(self, **payload):
        self.emitted.append(payload)
        if payload.get("return_event"):
            return dict(payload)
        return True


class DummyHero(BonusMixin):
    __hash__ = object.__hash__

    def __init__(self, name="Monk", object_id="monk-1", position=(0, 0)):
        super().__init__()
        self.name = name
        self.object_id = object_id
        self.position = position
        self.bonuses = []
        self.statuses = []
        self.level = 1
        self.base_speed_feet = 25
        self.ability_modifiers = {
            "strength": 3,
            "dexterity": 2,
            "constitution": 0,
            "wisdom": 1,
        }
        self.save_ranks = {
            "fortitude": "trained",
            "reflex": "trained",
            "will": "trained",
        }
        self.inventory = []
        self.equipped_weapon_item_ids = []
        self.equipped_shield = None
        self.ac = 15

    def set_position(self, position):
        self.position = position

    def has_status(self, status):
        sid = getattr(status, "id", status)
        return any(getattr(item, "id", item) == sid for item in self.statuses)

    def add_status(self, status):
        if self.has_status(status):
            return False
        self.statuses.append(status)
        return True

    def remove_status(self, status):
        sid = getattr(status, "id", status)
        before = len(self.statuses)
        self.statuses = [item for item in self.statuses if getattr(item, "id", item) != sid]
        return len(self.statuses) != before

    def get_status_data(self, status_id: str, key: str, default=None):
        for status in self.statuses:
            if getattr(status, "id", None) != status_id:
                continue
            data = getattr(status, "data", None) or {}
            return data.get(key, default)
        return default

    def apply_damage(self, amount, _dtype=""):
        self.last_damage = int(amount or 0)
        return 0, False


class DummyEnemy:
    def __init__(self, name="Enemy", object_id="enemy-1", position=(1, 0), ac=10):
        self.name = name
        self.object_id = object_id
        self.position = position
        self.ac = ac
        self.hp = 20

    def set_position(self, position):
        self.position = position

    def apply_damage(self, amount, _dtype=""):
        self.hp -= int(amount or 0)
        return self.hp, self.hp <= 0


class DummyGame:
    def __init__(self, board, conn, heroes=None, enemies=None):
        self.board = board
        self.conn = conn
        self.events = DummyEvents()
        self.heroes = list(heroes or [])
        self.enemies = list(enemies or [])
        self.ui = None
        self.logs = []
        self.state = Combat(self)
        self.ui_log = self.logs.append
        self.ui_event = lambda *_a, **_k: None
        self.ui_hero = lambda *_a, **_k: None
        self.ui_active_actor = lambda *_a, **_k: None
        self.ui_idle_hint = lambda *_a, **_k: None


def _ctx(game, actor):
    return EventContext(game=game, actor=actor)


def _build_open_board(*occupants):
    board = BoardGrid(rows=8, cols=8)
    for occupant in occupants:
        board.place(occupant, occupant.position)
    return board


def test_crane_stance_extends_leap_distance():
    hero = DummyHero(position=(0, 0))
    hero.add_status(Status(id="crane_stance"))
    board = _build_open_board(hero)
    game = DummyGame(board, DummyConn(choice=(3, 0)), heroes=[hero])

    stance = dispatch_event("crane_stance", _ctx(game, hero))
    assert stance.success is True

    result = LeapEvent().execute(_ctx(game, hero))

    assert result.success is True
    assert hero.position == (3, 0)


def test_tiger_stance_allows_ten_foot_step():
    hero = DummyHero(position=(0, 0))
    hero.add_status(Status(id="tiger_stance"))
    board = _build_open_board(hero)
    game = DummyGame(board, DummyConn(choice=(2, 0)), heroes=[hero])

    stance = dispatch_event("tiger_stance", _ctx(game, hero))
    assert stance.success is True

    result = StepEvent().execute(_ctx(game, hero))

    assert result.success is True
    assert hero.position == (2, 0)


def test_dragon_stance_ignores_first_difficult_square_each_turn():
    hero = DummyHero(position=(0, 0))
    hero.add_status(Status(id="dragon_stance"))
    board = BoardGrid(rows=1, cols=4)
    board.set_field((1, 0), RumbleTerrain())
    board.set_field((2, 0), RumbleTerrain())
    board.place(hero, hero.position)
    game = DummyGame(board, DummyConn(choice=(0, 0)), heroes=[hero])

    stance = dispatch_event("dragon_stance", _ctx(game, hero))
    assert stance.success is True

    reset_turn_movement_runtime(hero)
    assert path_cost_feet([(0, 0), (1, 0)], board, mover=hero) == 5
    consume_difficult_terrain_ignores_for_path(hero, board, [(0, 0), (1, 0)])
    assert path_cost_feet([(1, 0), (2, 0)], board, mover=hero) == 10

    reset_turn_movement_runtime(hero)
    assert path_cost_feet([(1, 0), (2, 0)], board, mover=hero) == 5


def test_mountain_stance_applies_ac_speed_and_trip_shove_runtime():
    hero = DummyHero(position=(0, 0))
    hero.add_status(Status(id="mountain_stance"))
    board = _build_open_board(hero)
    game = DummyGame(board, DummyConn(choice=(0, 0)), heroes=[hero])

    stance = dispatch_event("mountain_stance", _ctx(game, hero))
    assert stance.success is True

    assert hero.compute_modifier("ac") == 2
    assert hero.get_status_data("monk_stance_active", "stance_id") == "mountain_stance"

    trip_dc = trip_save_dc(hero, "reflex", ["trip"], _ctx(game, hero))
    shove_dc = shove_save_dc(hero, "fortitude", ["shove"], _ctx(game, hero))

    assert trip_dc == 17
    assert shove_dc == 15

    from actions.move_utils import movement_budget_feet

    assert movement_budget_feet(hero, default_feet=25) == 20


def test_monk_stance_cooldown_blocks_second_stance_until_next_turn():
    hero = DummyHero(position=(0, 0))
    hero.add_status(Status(id="dragon_stance"))
    hero.add_status(Status(id="tiger_stance"))
    board = _build_open_board(hero)
    game = DummyGame(board, DummyConn(choice=(0, 0)), heroes=[hero])

    first = dispatch_event("dragon_stance", _ctx(game, hero))
    second = dispatch_event("tiger_stance", _ctx(game, hero))

    assert first.success is True
    assert second.success is False
    assert "stance action" in str(second.message or "").lower()

    game.state._expire_sourced_statuses(hero)
    third = dispatch_event("tiger_stance", _ctx(game, hero))

    assert third.success is True
    assert hero.get_status_data("monk_stance_active", "stance_id") == "tiger_stance"


def test_monk_stance_persists_after_next_turn_start_and_only_lock_expires():
    hero = DummyHero(position=(0, 0))
    hero.add_status(Status(id="dragon_stance"))
    board = _build_open_board(hero)
    game = DummyGame(board, DummyConn(choice=(0, 0)), heroes=[hero])

    first = dispatch_event("dragon_stance", _ctx(game, hero))
    assert first.success is True
    assert hero.has_status("monk_stance_active")
    assert hero.has_status("monk_stance_lock")

    game.state._expire_sourced_statuses(hero)

    assert hero.has_status("monk_stance_active")
    assert not hero.has_status("monk_stance_lock")
    assert hero.get_status_data("monk_stance_active", "stance_id") == "dragon_stance"


def test_monk_stance_is_cleared_on_combat_end():
    hero = DummyHero(position=(0, 0))
    hero.add_status(Status(id="crane_stance"))
    board = _build_open_board(hero)
    game = DummyGame(board, DummyConn(choice=(0, 0)), heroes=[hero])

    stance = dispatch_event("crane_stance", _ctx(game, hero))
    assert stance.success is True
    assert hero.has_status("monk_stance_active")

    game.state.on_exit()

    assert not hero.has_status("monk_stance_active")
    assert not hero.has_status("monk_stance_lock")
    assert hero.compute_modifier("ac") == 0


def test_representative_monk_turn_tiger_step_and_flurry(monkeypatch):
    hero = DummyHero(position=(0, 0))
    hero.add_status(Status(id="tiger_stance"))
    hero.add_status(Status(id="flurry_of_blows"))
    enemy = DummyEnemy(position=(3, 0), ac=10)
    board = _build_open_board(hero, enemy)
    game = DummyGame(board, DummyConn(choice=[(2, 0), enemy.position, enemy.position]), heroes=[hero], enemies=[enemy])

    prompts = []
    rolls = iter([15, 6, 15, 5])

    def _prompt(prompt, *_args, **_kwargs):
        prompts.append(str(prompt))
        return next(rolls)

    monkeypatch.setattr(basic_melee_attack_event, "prompt_for_roll", _prompt)
    monkeypatch.setattr(basic_melee_attack_event, "refresh_flanking_statuses", lambda *_a, **_k: None)

    stance = dispatch_event("tiger_stance", _ctx(game, hero))
    step = StepEvent().execute(_ctx(game, hero))
    flurry = dispatch_event("flurry_of_blows", _ctx(game, hero))

    assert stance.success is True
    assert step.success is True
    assert hero.position == (2, 0)
    assert flurry.success is True
    assert enemy.hp == 3
    assert any("1k8 + STR" in text for text in prompts)
    assert hero.has_status("monk_stance_active")
