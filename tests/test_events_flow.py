import sys
import types
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import GameObjects.events.all_events  # noqa: F401
from GameObjects.events.registry import dispatch_event
from GameObjects.events.base import EventContext


class FakeEvents:
    def safe_emit_action(self, **payload):
        return True


class FakeConn:
    def set_leds(self, *a, **k):
        return None

    def scan_board(self, *a, **k):
        return None

    def leds_off(self):
        return None

    def read_card(self, *a, **k):
        return "end"


class FakeGame:
    def __init__(self):
        self.events = FakeEvents()
        self.conn = FakeConn()
        self.ui_log = lambda *a, **k: None
        self.heroes = []
        self.enemies = []
        self.board = None
        self.state = None


def test_move_event_passes_actor_and_tags(monkeypatch):
    called = {}

    def fake_execute(self, action_ctx):
        called["actor"] = action_ctx.actor
        called["tags"] = set(action_ctx.action_tags or [])
        return None

    import actions.move as move_module

    monkeypatch.setattr(move_module.MoveAction, "execute", fake_execute)

    hero = types.SimpleNamespace(name="Hero", position=(0, 0))
    game = FakeGame()
    ctx = EventContext(game=game, actor=hero, tags=["custom"])

    result = dispatch_event("move", ctx)

    assert result.success
    assert called["actor"] is hero
    assert called["tags"] == {"move", "custom"}


def test_stealth_event_runs_with_hide(monkeypatch):
    called = {}

    def fake_execute(self, action_ctx):
        called["actor"] = action_ctx.actor
        called["tags"] = set(action_ctx.action_tags or [])
        return None

    import actions.stealth as stealth_module

    monkeypatch.setattr(stealth_module.StealthAction, "execute", fake_execute)

    class Hero:
        def __init__(self):
            self.position = (1, 1)

        def has_status(self, name):
            return name == "hide"

    hero = Hero()
    game = FakeGame()
    ctx = EventContext(game=game, actor=hero)

    result = dispatch_event("stealth", ctx)

    assert result.success
    assert called["actor"] is hero
    assert "stealth" in called["tags"]


def test_delay_reorders_initiative(monkeypatch):
    from states.combat import Combat
    import states.combat as combat_module

    # stały wynik rzutu obniżający inicjatywę o 3
    monkeypatch.setattr(combat_module, "prompt_for_roll", lambda prompt: 3)

    class Hero:
        def __init__(self):
            self.name = "Hero"
            self.position = (0, 0)
            self.initiative = 15

        def reset_reactions(self):
            return None

        def __hash__(self):
            return id(self)

    hero = Hero()
    game = FakeGame()
    game.heroes = [hero]
    game.enemies = []
    combat = Combat(game)
    game.state = combat

    combat.base_initiative[hero] = 15
    combat.round_queue = [hero]
    combat.base_order = [hero]
    combat.actions_used[hero] = 0

    ctx = EventContext(game=game, actor=hero)
    result = dispatch_event("delay", ctx)

    assert result.success
    assert hero in combat.delayed
    assert combat.temp_initiative[hero] == 12  # 15 - 3
    assert combat.round_queue[0] is hero
    assert combat.actions_used[hero] == 0
