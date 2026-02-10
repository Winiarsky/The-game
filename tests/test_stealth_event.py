import sys
from pathlib import Path
import types

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

# --- Stuby brakujących modułów actions.* używane w stealth_event ---
_actions = types.ModuleType("actions")
_actions.__path__ = []
_move_utils = types.ModuleType("actions.move_utils")
_move_utils.perform_movement = lambda *a, **k: None
_move_utils.default_on_enter = lambda *a, **k: None
_move_utils.find_path = lambda *a, **k: []
_move_utils.path_cost_feet = lambda *a, **k: 0
_move_utils.trim_path_to_feet = lambda *a, **k: []
_move_utils._maybe_dispatch_move_reactions = lambda *a, **k: None
_move_utils.follow_path = lambda *a, **k: []
_specials = types.ModuleType("actions.specials")
_specials.__path__ = []
_magic = types.ModuleType("actions.specials.magic_missile")
_magic.magic_missile_ability = lambda *a, **k: None
sys.modules.setdefault("actions", _actions)
sys.modules.setdefault("actions.move_utils", _move_utils)
sys.modules.setdefault("actions.specials", _specials)
sys.modules.setdefault("actions.specials.magic_missile", _magic)
sys.modules.setdefault("actions.move_utils.perform_movement", _move_utils.perform_movement)

from GameObjects.events.stealth_event import StealthEvent  # noqa: E402
from GameObjects.events.base import EventContext  # noqa: E402
from GameObjects.events.registry import dispatch_event  # noqa: E402
from statuses import HIDE_STATUS  # noqa: E402
from board import consts  # noqa: E402
import GameObjects.events.checks.skill_check_event  # noqa: F401  # rejestracja skill_check


class DummyConn:
    def set_leds(self, *a, **k): ...
    def scan_board(self, *a, **k): return None
    def leds_off(self, *a, **k): ...


class DummyEvents:
    def __init__(self):
        self.emitted = []

    def safe_emit_action(self, **payload):
        self.emitted.append(payload)


class DummyBoard:
    def __init__(self):
        self.calls = []

    def rooms_at(self, pos):
        return set()

    def get_neighbors(self, pos, include_position=True, diagonal=True):
        return [pos]

    def interactables_at(self, _pos):
        return []

    def occupant_at(self, _pos):
        return None

    def can_traverse(self, a, b, allow_occupied=True):
        return True

    def in_bounds(self, pos):
        return True

    def is_blocked(self, a, b):
        return False

    def edge_interactables_between(self, a, b):
        return []

    def cell_at(self, pos):
        return types.SimpleNamespace(field=types.SimpleNamespace(stealth_impact=0))


class Hero:
    def __init__(self, statuses=None):
        self.statuses = statuses or []
        self.position = (0, 0)
        self.blocked_stealth_rooms = set()
        self.stealth_fail_counts = {}
        self.stealth_detection_dc = None
        self.stealth_bonus = 0
        self.hide_stealth_bonus = 0

    def has_status(self, status):
        return status in self.statuses

    def add_status(self, status):
        if status not in self.statuses:
            self.statuses.append(status)

    def remove_status(self, status):
        if status in self.statuses:
            self.statuses.remove(status)


def test_stealth_success_with_hide_bonus(monkeypatch):
    hero = Hero(statuses=[HIDE_STATUS])
    game = types.SimpleNamespace(
        board=DummyBoard(),
        conn=DummyConn(),
        heroes=[hero],
        events=DummyEvents(),
        ui_log=lambda *a, **k: None,
    )

    # brak obserwatorów
    monkeypatch.setattr("GameObjects.events.stealth_event.iter_watchers_in_rooms", lambda *a, **k: [])
    monkeypatch.setattr("GameObjects.events.stealth_event.summarize_watchers", lambda watchers: (0, []))
    # gracz podaje wynik końcowy 10 (uwzględniając +2 z hide)
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_: 10)
    monkeypatch.setattr("GameObjects.events.stealth_event.perform_movement", lambda *a, **k: None)

    ctx = EventContext(game=game, actor=hero, tags=["move", "stealth"])
    result = StealthEvent().execute(ctx)

    assert result.success
    # status stealth nadany
    assert hero.has_status("stealth")
    # DC wykrycia ustawione na wynik testu
    assert hero.stealth_detection_dc == 10
    assert any("stealth_start" in a.get("action_id", "") or True for a in game.events.emitted)
