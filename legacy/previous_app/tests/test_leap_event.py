import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.events.leap_event import LeapEvent  # noqa: E402
from GameObjects.interactions_mixin import LeapBlockerMixin  # noqa: E402


class DummyConn:
    def __init__(self, choice=None):
        self.choice = choice
        self.leds = []
        self.last_positions = None

    def set_leds(self, positions, colors):
        self.leds = positions

    def scan_board(self, positions=None):
        self.last_positions = positions
        return self.choice

    def leds_off(self):
        self.leds = []


class DummyBoard:
    def __init__(self):
        self.occupants = {}
        self.blocked_edges = set()
        self.bounds = (5, 5)
        self.moves = []
        self.interactables = {}

    def in_bounds(self, pos):
        x, y = pos
        return 0 <= x < self.bounds[0] and 0 <= y < self.bounds[1]

    def is_blocked(self, a, b):
        return frozenset((a, b)) in self.blocked_edges

    def can_enter(self, pos, allow_occupied=False):
        occ = self.occupants.get(pos)
        if occ is None:
            return True
        return allow_occupied

    def edge_interactables_between(self, a, b):
        return []

    def interactables_at(self, pos):
        return self.interactables.get(pos, [])

    def can_traverse(self, a, b, allow_occupied=False):
        if not (self.in_bounds(a) and self.in_bounds(b)):
            return False
        if self.is_blocked(a, b):
            return False
        return self.can_enter(b, allow_occupied=allow_occupied)

    def occupant_at(self, pos):
        return self.occupants.get(pos)

    def move(self, a, b):
        self.moves.append((a, b))
        occ = self.occupants.pop(a, None)
        if occ is not None:
            self.occupants[b] = occ


class DummyHero:
    def __init__(self, pos):
        self.position = pos
        self.statuses = []
        self.stealth_bonus = 0

    def has_status(self, status):
        sid = getattr(status, "id", status)
        return any(getattr(s, "id", s) == sid for s in self.statuses)

    def remove_status(self, status):
        sid = getattr(status, "id", status)
        self.statuses = [s for s in self.statuses if getattr(s, "id", s) != sid]


class DummyEvents:
    def __init__(self):
        self.emitted = []

    def safe_emit_action(self, **payload):
        self.emitted.append(payload)


class DummyGame:
    def __init__(self, board, conn):
        self.board = board
        self.conn = conn
        self.events = DummyEvents()
        self.heroes = []
        self.enemies = []
        self.ui_log_messages = []

    def ui_log(self, msg):
        self.ui_log_messages.append(msg)


class DummyCtx:
    def __init__(self, game, actor, in_combat=True):
        self.game = game
        self.actor = actor
        self.in_combat = in_combat
        self.tags = None


class DummyLeapBlocker(LeapBlockerMixin):
    def __init__(self, blocked_pos):
        self.blocked_pos = blocked_pos

    def blocks_leap(self, _from, to):
        return to == self.blocked_pos


def test_leap_highlights_only_distance_two(monkeypatch):
    board = DummyBoard()
    hero = DummyHero((2, 2))
    board.occupants[hero.position] = hero
    conn = DummyConn(choice=(4, 2))
    game = DummyGame(board, conn)
    game.heroes = [hero]

    res = LeapEvent().execute(DummyCtx(game, hero, in_combat=True))

    assert res.success
    # neighbor (3,2) should not be highlighted
    assert (3, 2) not in (conn.last_positions or [])
    assert (4, 2) in (conn.last_positions or [])
    assert board.moves[-1] == ((2, 2), (4, 2))
    emitted = game.events.emitted[-1]
    assert "move" in emitted.get("action_tags", [])


def test_leap_blocked_edge_not_offered(monkeypatch):
    board = DummyBoard()
    hero = DummyHero((0, 0))
    board.occupants[hero.position] = hero
    board.blocked_edges.add(frozenset(((0, 0), (0, 2))))
    conn = DummyConn(choice=(0, 2))
    game = DummyGame(board, conn)
    game.heroes = [hero]

    res = LeapEvent().execute(DummyCtx(game, hero, in_combat=True))

    assert not res.success
    assert not board.moves  # no move performed


def test_leap_cancels_when_landing_occupied_by_ally(monkeypatch):
    board = DummyBoard()
    hero = DummyHero((1, 1))
    ally = DummyHero((3, 1))
    board.occupants = {hero.position: hero, ally.position: ally}
    conn = DummyConn(choice=ally.position)
    game = DummyGame(board, conn)
    game.heroes = [hero, ally]

    res = LeapEvent().execute(DummyCtx(game, hero, in_combat=True))

    assert not res.success
    assert not board.moves


def test_leap_not_offered_when_blocked_by_interactable():
    board = DummyBoard()
    hero = DummyHero((1, 1))
    target = (3, 1)
    board.occupants = {hero.position: hero}
    board.interactables[target] = [DummyLeapBlocker(target)]
    conn = DummyConn(choice=target)
    game = DummyGame(board, conn)
    game.heroes = [hero]

    res = LeapEvent().execute(DummyCtx(game, hero, in_combat=True))

    assert not res.success
    assert target not in (conn.last_positions or [])
    assert not board.moves


def test_leap_not_offered_when_wall_in_path():
    board = DummyBoard()
    hero = DummyHero((0, 0))
    target = (0, 2)
    board.occupants = {hero.position: hero}
    board.blocked_edges.add(frozenset(((0, 0), (0, 1))))
    conn = DummyConn(choice=target)
    game = DummyGame(board, conn)
    game.heroes = [hero]

    res = LeapEvent().execute(DummyCtx(game, hero, in_combat=True))

    assert not res.success
    assert target not in (conn.last_positions or [])
    assert not board.moves


def test_leap_not_offered_when_blocker_on_path_tile():
    mid = (1, 1)
    target = (2, 2)

    class MidBlocker(DummyLeapBlocker):
        def __init__(self):
            super().__init__(mid)
            self.position = mid

    board = DummyBoard()
    hero = DummyHero((0, 0))
    board.occupants = {hero.position: hero, mid: MidBlocker()}
    conn = DummyConn(choice=target)
    game = DummyGame(board, conn)
    game.heroes = [hero]

    res = LeapEvent().execute(DummyCtx(game, hero, in_combat=True))

    assert not res.success
    assert target not in (conn.last_positions or [])
    assert not board.moves


def test_leap_not_offered_when_mid_occupant_without_mixin():
    mid = (1, 0)
    target = (2, 0)

    class PlainOccupant:
        def __init__(self):
            self.position = mid

    board = DummyBoard()
    hero = DummyHero((0, 0))
    board.occupants = {hero.position: hero, mid: PlainOccupant()}
    conn = DummyConn(choice=target)
    game = DummyGame(board, conn)
    game.heroes = [hero]

    res = LeapEvent().execute(DummyCtx(game, hero, in_combat=True))

    assert not res.success
    assert target not in (conn.last_positions or [])
    assert not board.moves


def test_leap_allows_landing_on_nonblocking_interactable():
    class NonBlocking(LeapBlockerMixin):
        def blocks_leap(self, _from, to):
            return False

    board = DummyBoard()
    hero = DummyHero((0, 0))
    target = (0, 2)
    board.occupants = {hero.position: hero}
    board.interactables[target] = [NonBlocking()]
    conn = DummyConn(choice=target)
    game = DummyGame(board, conn)
    game.heroes = [hero]

    res = LeapEvent().execute(DummyCtx(game, hero, in_combat=True))

    assert res.success
    assert board.moves[-1] == ((0, 0), target)
