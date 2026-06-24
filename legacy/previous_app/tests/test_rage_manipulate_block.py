import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.events.base import EventContext, EventResult, GameEvent
from statuses.base import Status


class FakeActor:
    def __init__(self, statuses=None):
        self.statuses = list(statuses or [Status(id="rage")])

    def has_status(self, name):
        wanted = str(name or "")
        return any(getattr(item, "id", item) == wanted for item in self.statuses)


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
    ctx = EventContext(game=FakeGame(), actor=FakeActor([Status(id="rage")]))
    result = ManipulateEvent().run(ctx)
    assert not result.success
    assert "Rage" in (result.message or "")


def test_rage_allows_shove():
    ctx = EventContext(game=FakeGame(), actor=FakeActor([Status(id="rage")]))
    result = ShoveEvent().run(ctx)
    assert result.success


def test_rage_allows_grapple():
    ctx = EventContext(game=FakeGame(), actor=FakeActor([Status(id="rage")]))
    result = GrappleEvent().run(ctx)
    assert result.success


def test_moment_of_clarity_feat_alone_does_not_bypass_rage_manipulate_block():
    ctx = EventContext(game=FakeGame(), actor=FakeActor([Status(id="rage"), Status(id="moment_of_clarity")]))
    result = ManipulateEvent().run(ctx)
    assert not result.success
    assert "Rage" in (result.message or "")


def test_moment_of_clarity_active_bypasses_rage_manipulate_block():
    ctx = EventContext(game=FakeGame(), actor=FakeActor([Status(id="rage"), Status(id="moment_of_clarity_active")]))
    result = ManipulateEvent().run(ctx)
    assert result.success
