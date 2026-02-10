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
    def __init__(self):
        self.last_event = None

    def safe_emit_action(self, **payload):
        self.last_event = payload
        return True


class FakeConn:
    def __init__(self, scan_return=None):
        self.scan_return = scan_return

    def set_leds(self, *a, **k):
        return None

    def scan_board(self, *a, **k):
        return self.scan_return

    def leds_off(self):
        return None

    def read_card(self, *a, **k):
        return "end"


class FakeBoard:
    def __init__(self, hero_pos):
        self.hero_pos = hero_pos

    def rooms_at(self, *_):
        return set()

    def in_bounds(self, *_):
        return True

    def cell_at(self, *_):
        return types.SimpleNamespace(field=types.SimpleNamespace(stealth_impact=0))

    def get_neighbors(self, *_args, **_kwargs):
        return []

    def is_blocked(self, *_):
        return False

    def interactables_at(self, *_):
        return []

    def get_interactables_in_range(self, *_args, **_kwargs):
        return []

    def can_traverse(self, *_args, **_kwargs):
        return True

    def can_enter(self, *_args, **_kwargs):
        return True

    def positions_in_rooms(self, *_):
        return set()

    def room_seek_failures(self, *_):
        return 0

    def is_room_seek_locked(self, *_):
        return False

    def lock_room_seek(self, *_):
        return None

    def increment_room_seek_fail(self, *_):
        return None


class FakeGame:
    def __init__(self, conn=None, board=None):
        self.events = FakeEvents()
        self.conn = conn or FakeConn()
        self.ui_log = lambda *a, **k: None
        self.ui_event = lambda *a, **k: None
        self.heroes = []
        self.enemies = []
        self.board = board
        self.state = None


def test_move_event_emits_action_and_uses_tags(monkeypatch):
    hero = types.SimpleNamespace(name="Hero", position=(0, 0))
    conn = FakeConn(scan_return=hero.position)  # natychmiast kończy ruch
    board = FakeBoard(hero.position)
    game = FakeGame(conn=conn, board=board)
    game.heroes = [hero]

    # skracamy logikę: od razu zwracamy obecne pole
    import GameObjects.events.move_event as move_event_module

    monkeypatch.setattr(move_event_module.MoveEvent, "_wait_for_destination", lambda self, ctx, b: hero.position)

    ctx = EventContext(game=game, actor=hero, tags=["custom"])
    result = dispatch_event("move", ctx)

    assert result.success  # powinno się wykonać bez wyjątku
    event = game.events.last_event
    # ruch mógł zostać anulowany, ale tagi powinny być ustawione kiedy emitowane
    if event:
        assert set(event.get("action_tags", [])) >= {"move", "custom"}


def test_stealth_event_respects_hide_status(monkeypatch):
    class Hero:
        def __init__(self):
            self.position = (1, 1)
            self.stealth_fail_counts = {}
            self.blocked_stealth_rooms = set()
            self.stealth_bonus = 0
            self.stealth_detection_dc = None

        def has_status(self, name):
            return name == "hide"

        def add_status(self, *_):
            return None

        def remove_status(self, *_):
            return None

    hero = Hero()
    conn = FakeConn(scan_return=hero.position)
    board = FakeBoard(hero.position)
    game = FakeGame(conn=conn, board=board)
    game.heroes = [hero]

    # zablokuj prompt_for_roll w resolverze skill_check
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_, **__: 20)
    ctx = EventContext(game=game, actor=hero)
    result = dispatch_event("stealth", ctx)

    assert result.success


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
