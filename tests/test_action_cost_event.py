from types import SimpleNamespace

from GameObjects.events.base import EventContext, EventResult, ActionCostEvent
from GameObjects.events.magic.magic_event import MagicEvent, MagicEventResolver
from states.combat import Combat


class DummyActor:
    def __init__(self, object_id="actor-1"):
        self.object_id = object_id


class DummyEvent(ActionCostEvent):
    name = "dummy"
    actions_cost = 2

    def execute(self, ctx: EventContext) -> EventResult:
        return EventResult(success=True, consumed_action=True, message="ok")


class DummyMagic(MagicEvent):
    name = "dummy_magic"
    actions_cost = 2

    def execute(self, ctx: EventContext) -> EventResult:
        return EventResult(success=True, consumed_action=True, message="magic ok")


def _game_with_combat(actor, used, limit=3):
    game = SimpleNamespace(heroes=[actor], enemies=[], ui_log=lambda *_a, **_k: None)
    combat = Combat(game)
    combat.actions_used = {actor: used}
    combat.ACTION_LIMIT = limit
    game.state = combat
    return game


def test_action_cost_event_blocks_when_insufficient_actions():
    actor = DummyActor()
    game = _game_with_combat(actor, used=2, limit=3)
    ctx = EventContext(game=game, actor=actor)
    result = DummyEvent().run(ctx)
    assert result.success is False
    assert result.consumed_action is False
    assert "Za mało akcji" in (result.message or "")


def test_magic_event_uses_same_action_cost_validation():
    actor = DummyActor()
    game = _game_with_combat(actor, used=2, limit=3)
    ctx = EventContext(game=game, actor=actor)
    result = MagicEventResolver.resolve(DummyMagic(), ctx)
    assert result.success is False
    assert result.consumed_action is False
    assert "Za mało akcji" in (result.message or "")
