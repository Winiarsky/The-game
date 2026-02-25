import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.events.sudden_charge_event import SuddenChargeEvent
from GameObjects.events.base import EventContext, EventResult


class FakeConn:
    def __init__(self, choices):
        self._choices = list(choices)
        self.read_calls = 0

    def read_card(self, *_args, **_kwargs):
        self.read_calls += 1
        if not self._choices:
            return ""
        return self._choices.pop(0)


class FakeGame:
    def __init__(self, choices):
        self.conn = FakeConn(choices)
        self.ui_log = lambda *_a, **_k: None
        self.ui_idle_hint = lambda *_a, **_k: None
        from states.combat import Combat

        self.state = Combat(self)


class DummyEvent:
    default_tags = ["attack_melee"]
    available_in_combat = True


class DummyRangedEvent:
    default_tags = ["attack_ranged"]
    available_in_combat = True


def test_sudden_charge_end_skips_attack(monkeypatch):
    move_calls = {"count": 0}

    def _fake_move_execute(_self, _ctx):
        move_calls["count"] += 1
        return EventResult(success=True, consumed_action=True)

    monkeypatch.setattr("GameObjects.events.sudden_charge_event.MoveEvent.execute", _fake_move_execute)
    monkeypatch.setattr(
        "GameObjects.events.sudden_charge_event.list_events",
        lambda: {"attack_sword": DummyEvent, "shoot": DummyRangedEvent},
    )
    monkeypatch.setattr("GameObjects.events.sudden_charge_event.dispatch_event", lambda *_a, **_k: EventResult())

    game = FakeGame(["end"])
    ctx = EventContext(game=game, actor=object())
    result = SuddenChargeEvent().execute(ctx)

    assert move_calls["count"] == 2
    assert result.success
    assert result.actions_spent == 2
    assert "pominięty" in (result.message or "")


def test_sudden_charge_reprompts_until_melee(monkeypatch):
    move_calls = {"count": 0}

    def _fake_move_execute(_self, _ctx):
        move_calls["count"] += 1
        return EventResult(success=True, consumed_action=True)

    def _dispatch(_name, _ctx):
        return EventResult(success=True, consumed_action=True, message="melee ok")

    monkeypatch.setattr("GameObjects.events.sudden_charge_event.MoveEvent.execute", _fake_move_execute)
    monkeypatch.setattr(
        "GameObjects.events.sudden_charge_event.list_events",
        lambda: {"attack_sword": DummyEvent, "shoot": DummyRangedEvent},
    )
    monkeypatch.setattr("GameObjects.events.sudden_charge_event.dispatch_event", _dispatch)

    # najpierw zła akcja, potem dobra melee
    game = FakeGame(["shoot", "attack_sword"])
    ctx = EventContext(game=game, actor=object())
    result = SuddenChargeEvent().execute(ctx)

    assert move_calls["count"] == 2
    assert game.conn.read_calls == 2
    assert result.success
    assert result.actions_spent == 2
    assert "melee ok" in (result.message or "")


def test_sudden_charge_reprompts_then_end(monkeypatch):
    move_calls = {"count": 0}

    def _fake_move_execute(_self, _ctx):
        move_calls["count"] += 1
        return EventResult(success=True, consumed_action=True)

    monkeypatch.setattr("GameObjects.events.sudden_charge_event.MoveEvent.execute", _fake_move_execute)
    monkeypatch.setattr(
        "GameObjects.events.sudden_charge_event.list_events",
        lambda: {"attack_sword": DummyEvent, "shoot": DummyRangedEvent},
    )
    monkeypatch.setattr("GameObjects.events.sudden_charge_event.dispatch_event", lambda *_a, **_k: EventResult())

    game = FakeGame(["shoot", "end"])
    ctx = EventContext(game=game, actor=object())
    result = SuddenChargeEvent().execute(ctx)

    assert move_calls["count"] == 2
    assert game.conn.read_calls == 2
    assert result.success
    assert result.actions_spent == 2
    assert "pominięty" in (result.message or "")
