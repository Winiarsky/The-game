from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from board_grid import BoardGrid
from GameObjects.Interactables.dart_launcher_trap import DartLauncherTrap
from GameObjects.events.base import EventContext
from GameObjects.events.seek_event import SeekEvent
from GameObjects.events.trap_events import DisableDeviceEvent, IdentifyTrapEvent
from statuses.base import Status


class DummyConn:
    def __init__(self, clicks=None):
        self.clicks = list(clicks or [])
        self.led_calls: list[tuple[list[tuple[int, int]], object]] = []
        self.scan_calls: list[list[tuple[int, int]] | None] = []

    def set_leds(self, positions, colors):
        self.led_calls.append((list(positions), colors))

    def scan_board(self, positions=None):
        self.scan_calls.append(list(positions) if isinstance(positions, list) else positions)
        if self.clicks:
            return self.clicks.pop(0)
        return None

    def leds_off(self):
        return None


class DummyEvents:
    def safe_emit_action(self, **_kwargs):
        return None


@dataclass
class Hero:
    object_id: str = "hero-trap"
    name: str = "Rogue"
    position: tuple[int, int] | None = (0, 0)
    statuses: list[Status] = field(default_factory=list)
    bonuses: list = field(default_factory=list)
    hp: int = 20
    ac: int = 16

    def set_position(self, position):
        self.position = position

    def has_status(self, status_id: str) -> bool:
        return any(getattr(item, "id", item) == status_id for item in self.statuses)

    def apply_damage(self, amount, _dtype=""):
        self.hp -= int(amount)
        return self.hp, self.hp <= 0


def _build_game(board, hero, conn):
    game = SimpleNamespace(
        board=board,
        conn=conn,
        heroes=[hero],
        enemies=[],
        events=DummyEvents(),
        state=SimpleNamespace(),  # exploration
        ui_log=lambda *_a, **_k: None,
        ui_event=lambda *_a, **_k: None,
        ui_hero=lambda *_a, **_k: None,
        ui_active_actor=lambda *_a, **_k: None,
    )
    return game


def test_dart_launcher_trap_example_flow_seek_identify_disable(monkeypatch):
    board = BoardGrid(rows=1, cols=2)
    board.apply_rooms([{"id": "hall", "positions": [[0, 0], [1, 0]]}])
    hero = Hero()
    board.place(hero, hero.position)
    trap = DartLauncherTrap()
    board.add_interactable(trap, (1, 0))

    conn = DummyConn()
    game = _build_game(board, hero, conn)

    monkeypatch.setattr(
        "GameObjects.events.seek_event.check_resolver.resolve_skill_check_with_sources",
        lambda **_k: SimpleNamespace(outcome="success", roll=14, total=23),
    )
    monkeypatch.setattr(
        "GameObjects.events.seek_event.check_resolver.resolve_skill_check_with_sources_from_roll",
        lambda **_k: SimpleNamespace(outcome="success", total=23),
    )
    seek_result = SeekEvent().run(EventContext(game=game, actor=hero))

    assert seek_result.success is True
    assert trap.trap_detected is True

    monkeypatch.setattr(
        "GameObjects.events.trap_events.resolve_skill_check_with_sources",
        lambda **_k: SimpleNamespace(outcome="success", roll=11, total=21),
    )
    identify_result = IdentifyTrapEvent().run(EventContext(game=game, actor=hero))
    disable_result = DisableDeviceEvent().run(EventContext(game=game, actor=hero))

    assert identify_result.success is True
    assert trap.trap_identified is True
    assert disable_result.success is True
    assert trap.trap_armed is False


def test_identify_trap_highlights_multiple_and_waits_for_click(monkeypatch):
    board = BoardGrid(rows=1, cols=3)
    hero = Hero(position=(0, 0))
    board.place(hero, hero.position)
    trap_a = DartLauncherTrap()
    trap_b = DartLauncherTrap()
    trap_a.trap_detected = True
    trap_b.trap_detected = True
    board.add_interactable(trap_a, (1, 0))
    board.add_interactable(trap_b, (2, 0))

    conn = DummyConn(clicks=[(2, 0)])
    game = _build_game(board, hero, conn)

    monkeypatch.setattr(
        "GameObjects.events.trap_events.resolve_skill_check_with_sources",
        lambda **_k: SimpleNamespace(outcome="success", roll=12, total=22),
    )

    result = IdentifyTrapEvent().run(EventContext(game=game, actor=hero))

    assert result.success is True
    assert trap_a.trap_identified is False
    assert trap_b.trap_identified is True
    assert any(set(call[0]) == {(1, 0), (2, 0)} for call in conn.led_calls)
    assert any(set(call or []) == {(1, 0), (2, 0)} for call in conn.scan_calls if isinstance(call, list))


def test_trap_finder_auto_detects_before_trigger_on_enter(monkeypatch):
    board = BoardGrid(rows=1, cols=1)
    hero = Hero(position=(0, 0), statuses=[Status(id="trap_finder")])
    board.place(hero, hero.position)
    trap = DartLauncherTrap()
    board.add_interactable(trap, (0, 0))
    game = _build_game(board, hero, DummyConn())

    monkeypatch.setattr(
        "GameObjects.interactions_mixin.skill_check_resolver.resolve_skill_check_with_sources",
        lambda **_k: SimpleNamespace(outcome="success", roll=14, total=23),
    )

    message = trap.on_enter(hero, game)

    assert isinstance(message, str)
    assert message.startswith("Trap Finder:")
    assert trap.trap_detected is True
    assert trap.trap_armed is True

