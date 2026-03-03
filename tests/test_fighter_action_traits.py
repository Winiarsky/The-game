from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from GameObjects.events.base import ActionCostEvent, EventContext, EventResult
from GameObjects.events.registry import dispatch_event, register_event
from states.combat import Combat


@register_event
class _TraitAttackEvent(ActionCostEvent):
    name = "zz_test_trait_attack_event"
    default_tags = ["attack"]
    available_in_combat = True
    available_in_exploration = False
    consumes_action = True
    actions_cost = 1

    def execute(self, ctx: EventContext) -> EventResult:
        _ = ctx
        return EventResult(success=True, consumed_action=True)


@register_event
class _TraitOpenEvent(ActionCostEvent):
    name = "zz_test_trait_open_event"
    default_tags = ["open"]
    available_in_combat = True
    available_in_exploration = False
    consumes_action = True
    actions_cost = 1

    def execute(self, ctx: EventContext) -> EventResult:
        _ = ctx
        return EventResult(success=True, consumed_action=True)


@register_event
class _TraitFlourishEvent(ActionCostEvent):
    name = "zz_test_trait_flourish_event"
    default_tags = ["flourish"]
    available_in_combat = True
    available_in_exploration = False
    consumes_action = True
    actions_cost = 1

    def execute(self, ctx: EventContext) -> EventResult:
        _ = ctx
        return EventResult(success=True, consumed_action=True)


@register_event
class _TraitNonAttackEvent(ActionCostEvent):
    name = "zz_test_trait_non_attack_event"
    default_tags = ["skill"]
    available_in_combat = True
    available_in_exploration = False
    consumes_action = True
    actions_cost = 1

    def execute(self, ctx: EventContext) -> EventResult:
        _ = ctx
        return EventResult(success=True, consumed_action=True)


@dataclass(eq=False)
class _Actor:
    name: str = "Hero"
    position: tuple[int, int] | None = (0, 0)


def _ctx() -> tuple[SimpleNamespace, _Actor, EventContext]:
    actor = _Actor()
    game = SimpleNamespace(
        heroes=[actor],
        enemies=[],
        ui_log=lambda *_a, **_k: None,
    )
    game.state = Combat(game)
    return game, actor, EventContext(game=game, actor=actor)


def test_open_trait_is_blocked_after_attack_action():
    _game, _actor, ctx = _ctx()

    first = dispatch_event("zz_test_trait_attack_event", ctx)
    second = dispatch_event("zz_test_trait_open_event", ctx)

    assert first.success is True
    assert second.success is False
    assert "open" in str(second.message or "").lower()


def test_open_trait_not_blocked_by_non_attack_action():
    _game, _actor, ctx = _ctx()

    first = dispatch_event("zz_test_trait_non_attack_event", ctx)
    second = dispatch_event("zz_test_trait_open_event", ctx)

    assert first.success is True
    assert second.success is True


def test_flourish_trait_is_limited_to_once_per_turn():
    _game, _actor, ctx = _ctx()

    first = dispatch_event("zz_test_trait_flourish_event", ctx)
    second = dispatch_event("zz_test_trait_flourish_event", ctx)

    assert first.success is True
    assert second.success is False
    assert "flourish" in str(second.message or "").lower()
