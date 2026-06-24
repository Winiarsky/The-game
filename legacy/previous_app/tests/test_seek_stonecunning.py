import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import GameObjects.events.seek_event  # noqa: F401
from GameObjects.events.base import EventContext
from GameObjects.events.registry import dispatch_event
from GameObjects.interactions_mixin.hidden_mixin import HiddenMixin
from hero import Hero
from statuses.race.dwarf.feats.stonecunning import STONECUNNING_STATUS


class DummyUI:
    enabled = True

    def prompt_info(self, *_args, **_kwargs):
        return "ok"


class FakeConn:
    def set_leds(self, *_args, **_kwargs):
        return None

    def scan_board(self, *_args, **_kwargs):
        return None

    def leds_off(self):
        return None


class DummyHidden(HiddenMixin):
    def __init__(self, *, reveal_tags=(), reveal_dc=16):
        super().__init__()
        self.hidden = True
        self.revealed = False
        self.reveal_dc = reveal_dc
        self.seekable = True
        self.reveal_tags = tuple(reveal_tags)


class FakeBoard:
    def __init__(self, hero_pos, objects):
        self.hero_pos = hero_pos
        self._objects = objects

    def rooms_at(self, *_):
        return set()

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

    def interactables_at(self, pos):
        if pos == self.hero_pos:
            return list(self._objects)
        return []


class FakeEvents:
    def safe_emit_action(self, **_payload):
        return True


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


def test_seek_applies_stonecunning_only_to_stone_targets(monkeypatch):
    hero = Hero()
    hero.position = (1, 1)
    hero.add_status(STONECUNNING_STATUS)

    stone_obj = DummyHidden(reveal_tags=("stone",), reveal_dc=16)
    wood_obj = DummyHidden(reveal_tags=("wood",), reveal_dc=16)

    board = FakeBoard(hero.position, [stone_obj, wood_obj])
    game = FakeGame(board=board)
    game.heroes = [hero]

    monkeypatch.setattr(
        "GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll",
        lambda *_, **__: 15,
    )
    monkeypatch.setattr(
        "GameObjects.events.seek_event.get_ui_client",
        lambda: DummyUI(),
    )

    monkeypatch.setattr(EventContext, "in_combat", property(lambda _self: False), raising=False)
    ctx = EventContext(game=game, actor=hero)
    result = dispatch_event("seek", ctx)

    assert result.success
    assert stone_obj.revealed is True
    assert wood_obj.revealed is False
