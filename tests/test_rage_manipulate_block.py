import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.events.base import EventContext, EventResult, GameEvent


class FakeActor:
    def has_status(self, name):
        return name == "rage"


class FakeGame:
    def __init__(self):
        self.state = None


class ManipulateEvent(GameEvent):
    name = "aid"
    default_tags = ["manipulate"]

    def execute(self, _ctx: EventContext) -> EventResult:
        return EventResult(success=True, consumed_action=False, message="ok")


class ShoveEvent(GameEvent):
    name = "shove"
    default_tags = ["manipulate", "shove"]

    def execute(self, _ctx: EventContext) -> EventResult:
        return EventResult(success=True, consumed_action=False, message="ok")


class GrappleEvent(GameEvent):
    name = "grapple"
    default_tags = ["manipulate", "grapple"]

    def execute(self, _ctx: EventContext) -> EventResult:
        return EventResult(success=True, consumed_action=False, message="ok")


def test_rage_blocks_manipulate_actions():
    ctx = EventContext(game=FakeGame(), actor=FakeActor())
    result = ManipulateEvent().run(ctx)
    assert not result.success
    assert "Rage" in (result.message or "")


def test_rage_allows_shove():
    ctx = EventContext(game=FakeGame(), actor=FakeActor())
    result = ShoveEvent().run(ctx)
    assert result.success


def test_rage_allows_grapple():
    ctx = EventContext(game=FakeGame(), actor=FakeActor())
    result = GrappleEvent().run(ctx)
    assert result.success
