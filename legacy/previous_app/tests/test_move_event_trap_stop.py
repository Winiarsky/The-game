import sys
from pathlib import Path
import types
import importlib
import importlib.util

import pytest

# ensure src on path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

# podmień stub z conftest na realny move_utils (potrzebujemy prawdziwego pathfindera/follow_path)
MOVE_UTILS_PATH = SRC_ROOT / "actions" / "move_utils.py"
spec = importlib.util.spec_from_file_location("actions.move_utils", MOVE_UTILS_PATH)
move_utils = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(move_utils)  # type: ignore[arg-type]
sys.modules["actions.move_utils"] = move_utils

import GameObjects.events.move_event as move_event  # noqa: E402

importlib.reload(move_event)

from GameObjects.events.base import EventContext  # noqa: E402

MoveEvent = move_event.MoveEvent


class DummyConn:
    def __init__(self, clicks):
        # sequence of board clicks to return from scan_board
        self.clicks = list(clicks)
        self.led_calls = []

    def set_leds(self, positions, colors):
        self.led_calls.append((positions, colors))

    def scan_board(self, *_args, **_kwargs):
        if not self.clicks:
            raise RuntimeError("No more clicks queued")
        return self.clicks.pop(0)

    def leds_off(self):
        self.led_calls.append(("off", None))


class DummyEvents:
    def __init__(self):
        self.emitted = []

    def safe_emit_action(self, **payload):
        self.emitted.append(payload)


class Trap:
    def __init__(self):
        self.triggered = False

    def on_enter(self, actor, game):
        self.triggered = True
        return "Pułapka!"  # non-empty -> zatrzymuje ruch


class DummyBoard:
    def __init__(self, trap_pos):
        self.trap_pos = trap_pos
        self.last_move = None

    def in_bounds(self, pos):
        return True

    def is_blocked(self, a, b):
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        if dx == 1 and dy == 1:
            return True
        return False

    def can_enter(self, pos, allow_occupied=False):
        return True

    def get_neighbors(self, pos, include_position=True, diagonal=True):
        x, y = pos
        neigh = [(x, y + 1), (x, y - 1), (x + 1, y), (x - 1, y)]
        if diagonal:
            neigh += [(x + 1, y + 1), (x + 1, y - 1), (x - 1, y + 1), (x - 1, y - 1)]
        if include_position:
            neigh.append(pos)
        return neigh

    def rooms_at(self, pos):
        return set()

    def edge_interactables_between(self, a, b):
        return []

    def interactables_at(self, pos):
        if pos == self.trap_pos:
            return [self.trap_obj]
        return []

    def occupant_at(self, pos):
        return None

    def move(self, a, b):
        self.last_move = (a, b)


class Hero:
    def __init__(self, pos):
        self.position = pos
        self.statuses = []

    def has_status(self, s):
        return s in self.statuses

    def remove_status(self, s):
        if s in self.statuses:
            self.statuses.remove(s)


def test_move_stops_on_trap_on_enter(monkeypatch):
    """
    Ścieżka prowadzi przez pole z pułapką; on_enter pułapki powinien przerwać ruch,
    pozostawiając bohatera na polu pułapki i zwracając wynik noop.
    """
    start = (0, 0)
    trap_pos = (0, 1)
    target = (0, 2)

    # kolejność kliknięć: wybór celu (target), potwierdzenie (target) + bufor
    conn = DummyConn(clicks=[target, target, target, target])
    board = DummyBoard(trap_pos=trap_pos)
    trap = Trap()
    board.trap_obj = trap

    hero = Hero(start)
    game = types.SimpleNamespace(
        board=board,
        conn=conn,
        heroes=[hero],
        enemies=[],
        events=DummyEvents(),
        ui_log=lambda *a, **k: None,
        ui_event=lambda *a, **k: None,
        state=types.SimpleNamespace(__class__=type("Exploration", (), {})),  # nie combat
    )

    ctx = EventContext(game=game, actor=hero)
    result = MoveEvent().execute(ctx)

    assert result.consumed_action is False, "Ruch przerwany nie powinien zużywać akcji."
    assert hero.position == trap_pos, "Bohater powinien zatrzymać się na polu pułapki."
    assert trap.triggered, "Pułapka powinna się aktywować w on_enter."
    assert result.message, "Powinien być komunikat o zatrzymaniu ruchu."


def test_move_confirm_none_retries_without_clearing_path(monkeypatch):
    start = (0, 0)
    target = (0, 2)

    conn = DummyConn(clicks=[target, None, target])
    board = DummyBoard(trap_pos=(9, 9))
    board.trap_obj = Trap()
    hero = Hero(start)
    ui_logs = []
    events = []
    game = types.SimpleNamespace(
        board=board,
        conn=conn,
        heroes=[hero],
        enemies=[],
        events=DummyEvents(),
        ui_log=lambda msg, *a, **k: ui_logs.append(str(msg)),
        ui_event=lambda kind, payload=None: events.append((kind, payload or {})),
        ui_idle_hint=lambda *a, **k: None,
        state=types.SimpleNamespace(__class__=type("Exploration", (), {})),
    )

    ctx = EventContext(game=game, actor=hero)
    result = MoveEvent().execute(ctx)

    assert result.success is True
    assert hero.position == target
    assert any("Nie odczytano potwierdzenia" in msg for msg in ui_logs)
    clear_events = [payload for kind, payload in events if kind == "path_clear"]
    preview_events = [payload for kind, payload in events if kind == "path_preview"]
    assert preview_events
    assert len(clear_events) == 1


def test_move_current_field_click_retries_destination_without_spending_action(monkeypatch):
    start = (0, 0)
    target = (0, 2)

    conn = DummyConn(clicks=[start, target, target])
    board = DummyBoard(trap_pos=(9, 9))
    board.trap_obj = Trap()
    hero = Hero(start)
    ui_logs = []
    game = types.SimpleNamespace(
        board=board,
        conn=conn,
        heroes=[hero],
        enemies=[],
        events=DummyEvents(),
        ui_log=lambda msg, *a, **k: ui_logs.append(str(msg)),
        ui_event=lambda *a, **k: None,
        ui_idle_hint=lambda *a, **k: None,
        state=types.SimpleNamespace(__class__=type("Exploration", (), {})),
    )

    ctx = EventContext(game=game, actor=hero)
    result = MoveEvent().execute(ctx)

    assert result.success is True
    assert hero.position == target
    assert any("Kliknięto aktualne pole bohatera" in msg for msg in ui_logs)
